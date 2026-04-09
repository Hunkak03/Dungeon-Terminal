"""Event system for shrines, merchants, treasures, and random events."""
import random
from typing import Dict, List, Optional, Tuple
from constants import *
from utils import Vec2
from items import Item, generate_item, generate_potion, generate_artifact
from entities import Entity, MonsterTemplate


class Shrine:
    """Shrine that grants boons or curses."""
    
    SHRINE_TYPES = [
        ("shrine_of_power", "Shrine of Power", "grants_stat_boost"),
        ("shrine_of_healing", "Shrine of Healing", "full_heal"),
        ("shrine_of_fate", "Shrine of Fate", "rarity_boost"),
        ("cursed_shrine", "Cursed Shrine", "curse_with_reward"),
        ("shrine_of_knowledge", "Shrine of Knowledge", "trait_point"),
        ("shrine_of_elements", "Shrine of Elements", "elemental_enchant"),
    ]
    
    def __init__(self, pos: Vec2, rng: random.Random):
        self.pos = pos
        self.rng = rng
        self.type, self.name, self.effect = self.rng.choice(self.SHRINE_TYPES)
        self.activated = False
    
    def activate(self, player) -> Tuple[bool, str]:
        """Activate shrine. Returns (success, message)."""
        if self.activated:
            return False, "This shrine has already been used."
        
        self.activated = True
        
        if self.effect == "grants_stat_boost":
            stat = self.rng.choice(["strength", "resistance", "luck", "vitality"])
            amount = self.rng.randint(3, 8)
            if hasattr(player, f"{stat}_points"):
                setattr(player, f"{stat}_points", getattr(player, f"{stat}_points") + amount)
            return True, f"{self.name}: +{amount} {stat.title()}!"
        
        elif self.effect == "full_heal":
            player.hp = player.max_hp
            player.status_effects.clear()
            return True, f"{self.name}: Fully healed and cleansed!"
        
        elif self.effect == "rarity_boost":
            player.luck_points += self.rng.randint(5, 15)
            return True, f"{self.name}: +{player.luck_points} Luck for future drops!"
        
        elif self.effect == "curse_with_reward":
            # 50/50 chance of curse or reward
            if self.rng.random() < 0.5:
                curse = self.rng.choice(list(CURSE_MAP.values()))
                player.curses.append(curse)
                item = generate_item(self.rng, player.luck_points, force_rarity=RARITY_EPIC)
                player.inventory.append(item)
                return True, f"{self.name}: Cursed with {curse}, but gained {item.name}!"
            else:
                item = generate_item(self.rng, player.luck_points, force_rarity=RARITY_LEGENDARY)
                player.inventory.append(item)
                return True, f"{self.name}: Blessed! Found {item.name}!"
        
        elif self.effect == "trait_point":
            player.trait_points += 1
            return True, f"{self.name}: +1 Trait Point!"
        
        elif self.effect == "elemental_enchant":
            element = self.rng.choice([ELEM_FIRE, ELEM_ICE, ELEM_LIGHTNING, ELEM_HOLY, ELEM_DARK])
            if player.equipped_weapon:
                player.equipped_weapon.element = element
                player.equipped_weapon.base_damage += 5
                return True, f"{self.name}: Weapon enchanted with {ELEMENT_NAMES[element]}!"
            else:
                player.luck_points += 5
                return True, f"{self.name}: No weapon to enchant, +5 Luck instead."
        
        return False, "Nothing happened."


CURSE_MAP = {
    CURSE_HP_DRAIN: "HP Drain: Lose 1 HP every 10 steps",
    CURSE_XP_DRAIN: "XP Drain: Lose 5% XP on monster kill",
    CURSE_BLINDNESS: "Blindness: -3 FOV radius",
    CURSE_FRAILTY: "Frailty: +20% damage taken",
    CURSE_MISFORTUNE: "Misfortune: -20% item rarity",
}


class Merchant:
    """Shop merchant."""
    
    def __init__(self, pos: Vec2, floor: int, rng: random.Random):
        self.pos = pos
        self.floor = floor
        self.rng = rng
        self.inventory = self._generate_stock()
        self.gold = 0  # Player currency
    
    def _generate_stock(self) -> List[Tuple[Item, int]]:
        """Generate items for sale with prices."""
        stock = []
        item_count = self.rng.randint(4, 8)
        
        for _ in range(item_count):
            item = generate_item(self.rng, 0, self.floor)
            price = self._calculate_price(item)
            stock.append((item, price))
        
        # Always have potions
        potion = generate_potion(self.rng)
        stock.append((potion, self._calculate_price(potion)))
        
        # Rare chance for artifact
        if self.rng.random() < 0.10:
            artifact = generate_artifact(self.rng, self.floor)
            stock.append((artifact, self._calculate_price(artifact) * 3))
        
        return stock
    
    def _calculate_price(self, item: Item) -> int:
        """Calculate item price based on rarity and stats."""
        base_price = 20
        
        rarity_mult = {
            RARITY_COMMON: 1.0,
            RARITY_UNCOMMON: 1.5,
            RARITY_RARE: 2.5,
            RARITY_EPIC: 5.0,
            RARITY_LEGENDARY: 10.0,
            RARITY_ARTIFACT: 25.0,
        }
        
        stat_value = (item.strength_points + item.resistance_points + 
                     item.luck_points + item.vitality_points)
        
        price = base_price * rarity_mult.get(item.rarity, 1.0)
        price += stat_value * 5
        price += item.base_damage * 3
        
        return int(price)
    
    def buy_item(self, index: int, player_gold: int) -> Tuple[Optional[Item], int, str]:
        """
        Buy item from merchant.
        Returns: (item, new_gold, message)
        """
        if index < 0 or index >= len(self.inventory):
            return None, player_gold, "Invalid item."
        
        item, price = self.inventory[index]
        
        if player_gold < price:
            return None, player_gold, f"Not enough gold! Need {price}, have {player_gold}."
        
        player_gold -= price
        self.inventory.pop(index)
        
        return item, player_gold, f"Bought {item.name} for {price} gold!"


class TreasureChest:
    """Treasure chest with loot."""
    
    def __init__(self, pos: Vec2, floor: int, rng: random.Random, is_trapped: bool = False):
        self.pos = pos
        self.floor = floor
        self.rng = rng
        self.is_trapped = is_trapped
        self.opened = False
    
    def open(self, luck_points: int) -> Tuple[List[Item], Optional[str]]:
        """
        Open chest.
        Returns: (items, trap_message)
        """
        if self.opened:
            return [], "Already opened."
        
        self.opened = True
        
        # Check for trap
        if self.is_trapped and self.rng.random() < 0.6:
            # Disarm check based on luck
            if self.rng.random() > luck_points * 0.02:
                # Trap triggers
                trap_effect = self.rng.choice(["poison", "damage", "curse"])
                if trap_effect == "poison":
                    return [], "Trap! Poison dart hits you!"
                elif trap_effect == "damage":
                    return [], "Trap! Spike deals 15 damage!"
                else:
                    return [], "Trap! You feel cursed..."
        
        # Generate loot
        loot_count = self.rng.randint(1, 3)
        loot = []
        
        for _ in range(loot_count):
            # Better loot on deeper floors
            roll = self.rng.random()
            if roll < 0.05:
                loot.append(generate_artifact(self.rng, self.floor))
            elif roll < 0.15:
                loot.append(generate_item(self.rng, luck_points, self.floor, RARITY_LEGENDARY))
            elif roll < 0.35:
                loot.append(generate_item(self.rng, luck_points, self.floor, RARITY_EPIC))
            else:
                loot.append(generate_item(self.rng, luck_points, self.floor))
        
        # Gold
        gold_amount = self.rng.randint(10, 50) + self.floor * 5
        
        message = f"Found {len(loot)} items and {gold_amount} gold!"
        return loot, message


class RandomEvent:
    """Random encounter or event."""
    
    @staticmethod
    def generate_event(pos: Vec2, floor: int, rng: random.Random) -> Optional[str]:
        """Generate a random event at position."""
        roll = rng.random()
        
        if roll < 0.15:
            return "You find a dead adventurer's belongings..."
        elif roll < 0.25:
            return "A mysterious fog surrounds you..."
        elif roll < 0.35:
            return "You hear whispers in the darkness..."
        
        return None


class Trap:
    """Trap on the dungeon floor."""
    
    TRAP_TYPES = {
        "spike": {"damage": 15, "effect": "damage"},
        "poison_dart": {"damage": 5, "effect": STATUS_POISONED, "duration": 10},
        "fire": {"damage": 20, "effect": STATUS_BURNING, "duration": 5},
        "teleport": {"damage": 0, "effect": "teleport"},
        "curse": {"damage": 0, "effect": "curse"},
        "ice": {"damage": 5, "effect": STATUS_FROZEN, "duration": 2},
    }
    
    def __init__(self, pos: Vec2, trap_type: str, rng: random.Random):
        self.pos = pos
        self.trap_type = trap_type
        self.rng = rng
        self.triggered = False
        self.data = self.TRAP_TYPES.get(trap_type, self.TRAP_TYPES["spike"])
    
    def trigger(self, player) -> Tuple[int, str]:
        """
        Trigger trap.
        Returns: (damage, message)
        """
        if self.triggered and self.trap_type != "ice":
            return 0, ""
        
        self.triggered = True
        
        effect = self.data["effect"]
        damage = self.data.get("damage", 0)
        
        if effect == "damage" or effect == STATUS_POISONED or effect == STATUS_BURNING:
            # Apply damage
            if effect in [STATUS_POISONED, STATUS_BURNING]:
                duration = self.data.get("duration", 5)
                value = damage
                player.status_effects.append(StatusEffect(effect, duration, value))
                return 0, f"Trap! {effect.title()} for {duration} turns!"
            else:
                player.hp -= damage
                return damage, f"Trap! {self.trap_type.title()} deals {damage} damage!"
        
        elif effect == "teleport":
            # Teleport player to random location
            return 0, "Trap! You're teleported!"
        
        elif effect == "curse":
            # Apply random curse
            return 0, "Trap! You feel a dark energy..."
        
        return 0, f"Trap! {self.trap_type}"
