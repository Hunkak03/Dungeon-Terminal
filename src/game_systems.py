"""Additional game systems: save/load, events, damage numbers, achievements, statistics."""
import json
import os
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from constants import *
from utils import Vec2


# ---- Save/Load System ----

@dataclass
class SaveData:
    """Complete game state for saving."""
    # Player
    player_class: str
    level: int
    xp: int
    xp_to_level: int
    gold: int
    floor: int
    turn_count: int
    
    # Stats
    str_points: int
    res_points: int
    luck_points: int
    vit_points: int
    
    # Equipment (serialized)
    equipped_weapon: Optional[dict]
    equipped_armor: Optional[dict]
    equipped_ring: Optional[dict]
    equipped_amulet: Optional[dict]
    inventory: List[dict]
    
    # Traits
    traits: List[str]
    trait_points: int
    
    # Progress
    monsters_killed: int
    bosses_killed: int
    achievements_unlocked: List[str]
    
    # Timestamp
    save_time: float = 0.0
    
    def __post_init__(self):
        if self.save_time == 0.0:
            self.save_time = time.time()


def serialize_item(item) -> dict:
    """Serialize an Item to dict."""
    if item is None:
        return None
    from items import Item
    return {
        'name': item.name,
        'rarity': item.rarity,
        'slot': item.slot,
        'glyph': item.glyph,
        'color_key': item.color_key,
        'strength_points': item.strength_points,
        'resistance_points': item.resistance_points,
        'luck_points': item.luck_points,
        'vitality_points': item.vitality_points,
        'base_damage': item.base_damage,
        'element': item.element,
        'crit_bonus': item.crit_bonus,
        'lifesteal': item.lifesteal,
        'heal_pct': item.heal_pct,
        'consumable': item.consumable,
        'description': item.description,
        'enchant_level': item.enchant_level,
        'rune_sockets': item.rune_sockets,
        'boosters': [{'key': b.key, 'value': b.value, 'description': b.description} for b in item.boosters],
    }


def save_game(game_data: SaveData, slot: int = 1) -> str:
    """Save game to file. Returns filename or error message."""
    try:
        save_dir = SAVE_DIR
        os.makedirs(save_dir, exist_ok=True)
        
        filename = os.path.join(save_dir, f"save_slot_{slot}.json")
        
        save_dict = asdict(game_data)
        
        with open(filename, 'w') as f:
            json.dump(save_dict, f, indent=2)
        
        return f"Game saved to slot {slot}!"
    except Exception as e:
        return f"Save failed: {str(e)}"


def load_game(slot: int = 1) -> Optional[SaveData]:
    """Load game from file. Returns SaveData or None."""
    try:
        filename = os.path.join(SAVE_DIR, f"save_slot_{slot}.json")
        
        if not os.path.exists(filename):
            return None
        
        with open(filename, 'r') as f:
            save_dict = json.load(f)
        
        return SaveData(**save_dict)
    except Exception as e:
        print(f"Load failed: {str(e)}")
        return None


def get_save_slots() -> Dict[int, Optional[SaveData]]:
    """Get all available save slots."""
    slots = {}
    for i in range(1, 4):  # 3 save slots
        slots[i] = load_game(i)
    return slots


# ---- Damage Numbers System ----

@dataclass
class DamageNumber:
    """Floating damage number for visual feedback."""
    x: int
    y: int
    value: int
    is_crit: bool
    turns_left: int
    color: str = "red"


class DamageNumberSystem:
    """Manages floating damage numbers."""
    def __init__(self):
        self.numbers: List[DamageNumber] = []
    
    def add_damage(self, x: int, y: int, damage: int, is_crit: bool = False):
        """Add a damage number at position."""
        color = "yellow" if is_crit else "red"
        self.numbers.append(DamageNumber(
            x=x, y=y, value=damage, is_crit=is_crit,
            turns_left=DAMAGE_NUMBER_DURATION, color=color
        ))
    
    def add_heal(self, x: int, y: int, amount: int):
        """Add a healing number (green)."""
        self.numbers.append(DamageNumber(
            x=x, y=y, value=amount, is_crit=False,
            turns_left=DAMAGE_NUMBER_DURATION, color="green"
        ))
    
    def tick(self):
        """Decrement all damage numbers and remove expired ones."""
        for num in self.numbers:
            num.turns_left -= 1
        
        self.numbers = [n for n in self.numbers if n.turns_left > 0]
    
    def get_visible(self) -> List[DamageNumber]:
        """Get currently visible damage numbers."""
        return self.numbers


# ---- Achievement Popup System ----

@dataclass
class AchievementPopup:
    """Temporary achievement notification."""
    name: str
    description: str
    turns_left: int


class AchievementPopupSystem:
    """Manages achievement popups."""
    def __init__(self):
        self.popups: List[AchievementPopup] = []
    
    def show(self, name: str, description: str, duration: int = 50):
        """Show an achievement popup."""
        self.popups.append(AchievementPopup(
            name=name, description=description, turns_left=duration
        ))
    
    def tick(self):
        """Decrement popups."""
        for popup in self.popups:
            popup.turns_left -= 1
        
        self.popups = [p for p in self.popups if p.turns_left > 0]
    
    def get_active(self) -> List[AchievementPopup]:
        """Get active popups."""
        return self.popups


# ---- Game Statistics Tracker ----

@dataclass
class GameStatistics:
    """Tracks comprehensive game statistics."""
    # Combat
    total_damage_dealt: int = 0
    total_damage_taken: int = 0
    total_healing_received: int = 0
    monsters_killed: int = 0
    bosses_killed: int = 0
    crits_landed: int = 0
    highest_damage_hit: int = 0
    
    # Exploration
    floors_cleared: int = 0
    rooms_explored: int = 0
    secret_rooms_found: int = 0
    tiles_explored: int = 0
    traps_triggered: int = 0
    traps_disarmed: int = 0
    
    # Items
    items_found: int = 0
    items_consumed: int = 0
    gold_earned: int = 0
    gold_spent: int = 0
    runes_socketed: int = 0
    items_enchanted: int = 0
    
    # Events
    shrines_activated: int = 0
    merchants_visited: int = 0
    chests_opened: int = 0
    events_triggered: int = 0
    
    # Progression
    levels_gained: int = 0
    traits_learned: int = 0
    achievements_unlocked: int = 0
    
    # Time
    turns_played: int = 0
    start_time: float = 0.0
    
    def get_play_time(self) -> str:
        """Get formatted play time."""
        if self.start_time == 0.0:
            return "0:00"
        
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"{minutes}:{seconds:02d}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for display."""
        return {
            "Damage Dealt": f"{self.total_damage_dealt:,}",
            "Damage Taken": f"{self.total_damage_taken:,}",
            "Healing Received": f"{self.total_healing_received:,}",
            "Monsters Killed": str(self.monsters_killed),
            "Bosses Killed": str(self.bosses_killed),
            "Crits Landed": str(self.crits_landed),
            "Highest Damage Hit": str(self.highest_damage_hit),
            "Floors Cleared": str(self.floors_cleared),
            "Rooms Explored": str(self.rooms_explored),
            "Secret Rooms Found": str(self.secret_rooms_found),
            "Tiles Explored": str(self.tiles_explored),
            "Traps Triggered": str(self.traps_triggered),
            "Traps Disarmed": str(self.traps_disarmed),
            "Items Found": str(self.items_found),
            "Items Consumed": str(self.items_consumed),
            "Gold Earned": f"{self.gold_earned:,}",
            "Gold Spent": f"{self.gold_spent:,}",
            "Runes Socketed": str(self.runes_socketed),
            "Items Enchanted": str(self.items_enchanted),
            "Shrines Activated": str(self.shrines_activated),
            "Merchants Visited": str(self.merchants_visited),
            "Chests Opened": str(self.chests_opened),
            "Events Triggered": str(self.events_triggered),
            "Levels Gained": str(self.levels_gained),
            "Traits Learned": str(self.traits_learned),
            "Play Time": self.get_play_time(),
        }


# ---- Floor Event System ----

FLOOR_EVENTS = [
    {
        "name": "Mysterious Merchant",
        "text": "A hooded figure approaches: 'I have rare wares, but they come at a price...'",
        "choices": [
            ("Buy mystery item (50 gold)", "pay_merchant"),
            ("Decline", "decline"),
        ],
        "outcomes": {
            "pay_merchant": {"gold_cost": 50, "reward": "random_item", "text": "You receive a mysterious package..."},
            "decline": {"text": "The merchant vanishes into the shadows."},
        }
    },
    {
        "name": "Ancient Shrine",
        "text": "You discover an ancient shrine pulsing with power.",
        "choices": [
            ("Pray for blessing", "pray"),
            ("Desecrate shrine", "desecrate"),
            ("Leave respectfully", "leave"),
        ],
        "outcomes": {
            "pray": {"reward": "stat_boost", "text": "The shrine blesses you with power! +3 to a random stat."},
            "desecrate": {"reward": "curse_or_gold", "text": "You smash the shrine... Was that wise?"},
            "leave": {"reward": "small_heal", "text": "You feel peaceful. HP restored."},
        }
    },
    {
        "name": "Trapped Adventurer",
        "text": "You find a wounded adventurer caught in a trap.",
        "choices": [
            ("Help them (risk trap)", "help"),
            ("Take their items", "rob"),
            ("Leave them", "leave"),
        ],
        "outcomes": {
            "help": {"reward": "ally_or_trap", "text": "You try to free them..."},
            "rob": {"reward": "loot", "text": "You take what they have. Not proud, but practical."},
            "leave": {"text": "You leave them behind. Their cries fade..."},
        }
    },
    {
        "name": "Cursed Treasure",
        "text": "A pile of gold sits in the open. Something feels wrong...",
        "choices": [
            ("Take the gold", "take"),
            ("Inspect carefully", "inspect"),
            ("Leave it", "leave"),
        ],
        "outcomes": {
            "take": {"reward": "gold_or_curse", "text": "You grab the gold!"},
            "inspect": {"reward": "safe_gold", "text": "You carefully disarm the traps and take the gold safely."},
            "leave": {"text": "Better safe than sorry."},
        }
    },
    {
        "name": "Rune Master",
        "text": "A spectral figure offers to teach you about runes.",
        "choices": [
            ("Learn (costs 1 trait point)", "learn"),
            ("Receive free rune", "free_rune"),
            ("Decline", "decline"),
        ],
        "outcomes": {
            "learn": {"cost": "trait_point", "reward": "rune_knowledge", "text": "You gain deep understanding of runes!"},
            "free_rune": {"reward": "random_rune", "text": "The spirit gifts you a rune."},
            "decline": {"text": "The spirit fades."},
        }
    },
    {
        "name": "Enchantment Forge",
        "text": "An ancient forge still burns with magical fire.",
        "choices": [
            ("Enchant weapon (30 gold)", "enchant_weapon"),
            ("Enchant armor (30 gold)", "enchant_armor"),
            ("Leave", "leave"),
        ],
        "outcomes": {
            "enchant_weapon": {"gold_cost": 30, "reward": "weapon_enchant", "text": "Your weapon glows with power!"},
            "enchant_armor": {"gold_cost": 30, "reward": "armor_enchant", "text": "Your armor shimmers with protection!"},
            "leave": {"text": "The forge continues to burn."},
        }
    },
    {
        "name": "Fountain of Youth",
        "text": "A crystal-clear fountain sparkles with magical energy.",
        "choices": [
            ("Drink deeply", "drink"),
            ("Fill vials", "fill"),
            ("Leave", "leave"),
        ],
        "outcomes": {
            "drink": {"reward": "full_heal", "text": "The water heals you completely!"},
            "fill": {"reward": "potions", "text": "You fill your vials with healing water."},
            "leave": {"text": "You move on, refreshed just by being near."},
        }
    },
]


@dataclass
class FloorEvent:
    """An active floor event."""
    event_type: str
    name: str
    text: str
    choices: List[Tuple[str, str]]
    outcomes: Dict[str, dict]
    position: Optional[Vec2] = None
    triggered: bool = False
    completed: bool = False
    
    def get_choice_text(self, index: int) -> str:
        """Get text for a choice."""
        if 0 <= index < len(self.choices):
            return self.choices[index][0]
        return ""
    
    def execute_choice(self, choice_index: int, game) -> str:
        """Execute a choice and return result text."""
        if 0 <= choice_index < len(self.choices):
            choice_text, outcome_key = self.choices[choice_index]
            outcome = self.outcomes.get(outcome_key, {})
            
            # Apply costs
            if "gold_cost" in outcome:
                if game.gold < outcome["gold_cost"]:
                    return "Not enough gold!"
                game.gold -= outcome["gold_cost"]
            
            if "cost" in outcome:
                if outcome["cost"] == "trait_point":
                    if game.trait_points < 1:
                        return "No trait points available!"
                    game.trait_points -= 1
            
            # Apply rewards (game logic will handle these)
            reward = outcome.get("reward")
            if reward:
                game.pending_event_reward = reward
            
            self.completed = True
            return outcome.get("text", "Something happened...")
        
        return "Invalid choice."


def generate_random_event(position: Vec2, floor: int, rng) -> Optional[FloorEvent]:
    """Generate a random floor event."""
    if rng.random() > 0.15:  # 15% chance per room
        return None
    
    event_template = rng.choice(FLOOR_EVENTS)
    
    return FloorEvent(
        event_type=event_template["name"].lower().replace(" ", "_"),
        name=event_template["name"],
        text=event_template["text"],
        choices=event_template["choices"],
        outcomes=event_template["outcomes"],
        position=position,
    )
