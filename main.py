"""
EPIC TERMINAL ROGUELIKE
A comprehensive roguelike with 50 floors, multiple biomes, epic bosses, artifacts, traits, and more!

Controls:
- Move: Arrow keys or WASD
- Attack: Move into enemy
- Pick up items: G
- Use potion/scroll: I (inventory)
- View equipment: C
- Stats/Traits: K
- Bestiary: B
- Special ability: U
- Descend stairs: > (when on stairs)
- Help: ?
- Quit: Q
"""

import curses
import math
import os
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    import pygame  # type: ignore
except Exception:
    pygame = None

# Import game modules from src/
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from constants import *
from utils import Vec2, manhattan, chebyshev, clamp
from entities import Entity, MonsterTemplate, get_boss_for_floor, Trait, TRAITS, Achievement, ACHIEVEMENTS, StatusEffect
from items import Item, Booster, generate_item, generate_potion, generate_artifact, ARTIFACT_SETS
from dungeon import DungeonMap, get_biome_for_floor, BIOME_MODIFIERS, BIOME_NAMES
from combat import CombatSystem, BossAI, MonsterAI
from events import Shrine, Merchant, TreasureChest, Trap
from game_systems import (
    SaveData, serialize_item, save_game, load_game, get_save_slots,
    DamageNumberSystem, AchievementPopupSystem, GameStatistics
)


class RoguelikeGame:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.rng = random.Random(time.time_ns())
        
        # Display settings
        self.map_w = 80
        self.map_h = 26
        self.fov_radius = 10
        
        # Game state
        self.game_state = STATE_RUNNING
        self.turn_count = 0
        self.monsters_killed = 0
        self.bosses_killed = 0
        
        # Floor system
        self.floor = 1
        self.max_floors = 50
        self.map: Optional[DungeonMap] = None
        self.fov_visible = []
        self.stairs_pos: Optional[Vec2] = None
        self.shrines: List[Shrine] = []
        self.merchants: List[Merchant] = []
        self.chests: List[TreasureChest] = []
        self.traps: List[Trap] = []
        
        # Player
        self.player: Optional[Entity] = None
        self.player_class = "warrior"
        self.level = 1
        self.xp = 0
        self.xp_to_level = 30
        self.gold = 0
        
        # Stats
        self.str_points = 0
        self.res_points = 0
        self.luck_points = 0
        self.vit_points = 0
        
        # Equipment
        self.equipped_weapon: Optional[Item] = None
        self.equipped_armor: Optional[Item] = None
        self.equipped_ring: Optional[Item] = None
        self.equipped_amulet: Optional[Item] = None
        self.inventory: List[Item] = []
        self.items_on_ground: List[Tuple[Vec2, Item]] = []
        
        # Monsters
        self.monsters: List[Entity] = []
        self.bestiary: Dict[str, Dict] = {}
        self.boss_ai: Optional[BossAI] = None
        self.monster_ai = MonsterAI(self.rng)
        
        # Combat
        self.combat = CombatSystem(self.rng)
        
        # NEW: Damage numbers & achievement popups
        self.damage_numbers = DamageNumberSystem()
        self.achievement_popups = AchievementPopupSystem()
        
        # NEW: Game statistics
        self.stats = GameStatistics()
        self.stats.start_time = time.time()

        # Traits
        self.traits: List[Trait] = []
        self.trait_points = 0
        self.available_traits: List[Trait] = TRAITS
        
        # Achievements
        self.achievements: Dict[str, Achievement] = {a.key: a for a in ACHIEVEMENTS}
        
        # Save/Load
        self.save_slot = 1
        
        # Class abilities
        self.class_abilities = {
            "warrior": {"name": "War Cry", "cooldown": 30, "last_used": 0},
            "mage": {"name": "Fireball", "cooldown": 25, "last_used": 0},
            "rogue": {"name": "Shadow Step", "cooldown": 20, "last_used": 0},
            "paladin": {"name": "Divine Shield", "cooldown": 35, "last_used": 0},
        }
        
        # UI
        self.message_log: List[str] = []
        self.max_log = 5
        self.last_move_dir: Vec2 = (1, 0)
        self.attack_bar_ticks = 0
        self.attack_bar_target = None
        
        # Audio
        self.audio = None
        self._init_audio()
        
        # Setup
        self._setup_curses()
        self._adapt_to_terminal()
    
    def _init_audio(self):
        """Initialize audio system."""
        if pygame is None:
            return
        try:
            pygame.mixer.init()
        except:
            return
    
    def _setup_curses(self):
        """Setup curses colors."""
        curses.curs_set(0)
        self.stdscr.keypad(True)
        curses.noecho()
        curses.cbreak()
        try:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_WHITE, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_CYAN, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            curses.init_pair(5, curses.COLOR_MAGENTA, -1)
            curses.init_pair(6, curses.COLOR_RED, -1)
            curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_WHITE)
        except:
            pass
    
    def _adapt_to_terminal(self):
        """Adapt map size to terminal."""
        try:
            h, w = self.stdscr.getmaxyx()
            self.map_w = max(50, min(self.map_w, w - 2))
            self.map_h = max(15, min(self.map_h, h - 10))
        except:
            pass
    
    def color_pair(self, key: str) -> int:
        """Get curses color pair for key."""
        mapping = {
            "white": 1, "green": 2, "cyan": 3, "yellow": 4, 
            "magenta": 5, "red": 6, "black": 7
        }
        return mapping.get(key, 1)
    
    def log(self, msg: str):
        """Add message to log."""
        self.message_log.append(msg)
        if len(self.message_log) > self.max_log:
            self.message_log = self.message_log[-self.max_log:]
    
    # ---- Game Flow ----
    
    def start_game(self):
        """Start a new game."""
        self._choose_class()
        self._start_floor(1, True)
        self.log("Welcome to the Epic Roguelike! Descend 50 floors and defeat the Dark God!")
    
    def _choose_class(self):
        """Class selection screen."""
        classes = [
            ("warrior", "Warrior", "High STR, starts with weapon, ability: War Cry (AoE damage)"),
            ("mage", "Mage", "High LUCK/VIT, ability: Fireball (ranged damage)"),
            ("rogue", "Rogue", "High LUCK, high crit, ability: Shadow Step (teleport+attack)"),
            ("paladin", "Paladin", "High RES/VIT, ability: Divine Shield (damage immunity)"),
        ]
        
        sel = 0
        while True:
            self.stdscr.erase()
            h, w = self.stdscr.getmaxyx()
            
            self.stdscr.addstr(2, 2, "Choose Your Class", curses.A_BOLD)
            
            for i, (key, name, desc) in enumerate(classes):
                prefix = ">> " if i == sel else "   "
                color = curses.color_pair(4) if i == sel else 0
                try:
                    self.stdscr.addstr(4 + i * 2, 4, f"{prefix}{name}: {desc}", color)
                except:
                    pass
            
            try:
                self.stdscr.addstr(4 + len(classes) * 2 + 1, 4, "Arrow keys to select, Enter to confirm")
            except:
                pass
            
            self.stdscr.refresh()
            ch = self.stdscr.getch()
            
            if ch == curses.KEY_UP:
                sel = max(0, sel - 1)
            elif ch == curses.KEY_DOWN:
                sel = min(len(classes) - 1, sel + 1)
            elif ch in [KEY_ENTER, KEY_ENTER2]:
                self.player_class = classes[sel][0]
                self._apply_class_starting_stats()
                return
            elif ch == KEY_ESCAPE:
                raise Exception("Game cancelled")
    
    def _apply_class_starting_stats(self):
        """Apply starting stats based on class."""
        if self.player_class == "warrior":
            self.str_points = 15
            self.res_points = 5
            self.equipped_weapon = Item(
                name="Steel Longsword", rarity=RARITY_UNCOMMON, slot=SLOT_WEAPON,
                glyph="/", color_key="cyan", strength_points=5, base_damage=18
            )
        elif self.player_class == "mage":
            self.luck_points = 10
            self.vit_points = 8
            self.res_points = 5
            self.equipped_weapon = Item(
                name="Apprentice Staff", rarity=RARITY_UNCOMMON, slot=SLOT_WEAPON,
                glyph="/", color_key="green", strength_points=3, base_damage=12,
                element=ELEM_FIRE
            )
        elif self.player_class == "rogue":
            self.luck_points = 15
            self.str_points = 8
            self.equipped_weapon = Item(
                name="Shadow Dagger", rarity=RARITY_RARE, slot=SLOT_WEAPON,
                glyph="/", color_key="magenta", strength_points=4, base_damage=14,
                crit_bonus=0.15
            )
        elif self.player_class == "paladin":
            self.res_points = 12
            self.vit_points = 10
            self.str_points = 5
            self.equipped_armor = Item(
                name="Holy Chainmail", rarity=RARITY_UNCOMMON, slot=SLOT_ARMOR,
                glyph="[", color_key="yellow", resistance_points=8, vitality_points=5
            )
    
    def _start_floor(self, floor: int, first_floor: bool = False):
        """Start a new floor."""
        self.floor = max(1, min(self.max_floors, floor))
        biome = get_biome_for_floor(self.floor)
        
        # Generate dungeon
        self.map = DungeonMap(self.map_w, self.map_h, self.floor, biome, self.rng)
        
        # Clear entities
        self.monsters.clear()
        self.items_on_ground.clear()
        self.shrines.clear()
        self.merchants.clear()
        self.chests.clear()
        
        # Place player
        if first_floor:
            start_pos = self.map.random_floor_cell()
            self.player = Entity(
                start_pos[0], start_pos[1], "@", "Player", "player",
                self._max_hp(), self._max_hp(), 10, 0, is_player=True
            )
        else:
            # Place on stairs from previous floor
            start_pos = self.map.random_floor_cell()
            self.player.x, self.player.y = start_pos
        
        # Spawn monsters
        self._spawn_monsters()
        
        # Spawn boss if applicable
        boss_template = get_boss_for_floor(self.floor, self.rng)
        if boss_template:
            self._spawn_boss(boss_template)
        
        # Spawn items
        self._spawn_items()
        
        # Place stairs (if boss floor, stairs appear after boss death)
        if not boss_template:
            self._place_stairs()
        
        # FOV
        self._update_fov()
        
        biome_info = BIOME_MODIFIERS[biome]
        self.log(f"Floor {self.floor}/{self.max_floors} - {BIOME_NAMES[biome]}")
        self.log(biome_info["description"])
    
    def _spawn_monsters(self):
        """Spawn monsters on the floor."""
        # More monsters on deeper floors, scaled gently
        monster_count = 4 + self.floor // 3
        
        # Monster templates by biome
        biome = get_biome_for_floor(self.floor)
        templates = self._get_monster_templates(biome)
        
        # Get rooms for better placement
        available_rooms = self.map.rooms[1:] if len(self.map.rooms) > 1 else []
        self.rng.shuffle(available_rooms)
        
        monsters_placed = 0
        room_idx = 0
        
        for _ in range(monster_count):
            template = self.rng.choice(templates)
            # Scale with floor
            scaled = self._scale_monster(template, self.floor)
            
            # Try to place in rooms first, then random
            if available_rooms and room_idx < len(available_rooms):
                room = available_rooms[room_idx % len(available_rooms)]
                room_idx += 1
                # Place 1-2 monsters per room
                count_in_room = self.rng.randint(1, 2) if self.floor > 5 else 1
                
                for _ in range(count_in_room):
                    if monsters_placed >= monster_count:
                        break
                    
                    # Random position within room
                    mx = self.rng.randint(room.x + 1, room.x + room.w - 2)
                    my = self.rng.randint(room.y + 1, room.y + room.h - 2)
                    
                    if self.map.is_walkable(mx, my) and manhattan((mx, my), self.player.pos()) >= 4:
                        monster = Entity(
                            mx, my, template.symbol, template.name, template.key,
                            scaled.max_hp, scaled.max_hp, scaled.base_damage, scaled.xp_given,
                            behavior=template.behavior
                        )
                        monster.aggro_range = 6 + self.floor // 10
                        self.monsters.append(monster)
                        monsters_placed += 1
            else:
                # Fallback to random placement
                pos = self.map.random_floor_cell(avoid=self.player.pos())
                
                # Ensure not too close to player
                attempts = 0
                while manhattan(pos, self.player.pos()) < 5 and attempts < 20:
                    pos = self.map.random_floor_cell(avoid=self.player.pos())
                    attempts += 1
                
                monster = Entity(
                    pos[0], pos[1], template.symbol, template.name, template.key,
                    scaled.max_hp, scaled.max_hp, scaled.base_damage, scaled.xp_given,
                    behavior=template.behavior
                )
                monster.aggro_range = 6 + self.floor // 10
                self.monsters.append(monster)
                monsters_placed += 1
    
    def _spawn_boss(self, template: MonsterTemplate):
        """Spawn the floor boss."""
        pos = self.map.random_floor_cell(avoid=self.player.pos())
        
        # Ensure far from player
        attempts = 0
        while manhattan(pos, self.player.pos()) < 10 and attempts < 30:
            pos = self.map.random_floor_cell(avoid=self.player.pos())
            attempts += 1
        
        # Scale boss with floor
        hp_mult = 1.0 + (self.floor - 1) * 0.15
        dmg_mult = 1.0 + (self.floor - 1) * 0.10
        
        boss = Entity(
            pos[0], pos[1], template.symbol, template.name, template.key,
            int(template.max_hp * hp_mult), int(template.max_hp * hp_mult),
            int(template.base_damage * dmg_mult), template.xp_given,
            is_boss=True, phase=1
        )
        boss.abilities = list(template.abilities)
        boss.phase_thresholds = template.phase_thresholds
        
        self.monsters.append(boss)
        self.boss_ai = BossAI(boss, template, self.rng)
        
        self.log(f"WARNING: {template.name} guards this floor!")
    
    def _spawn_items(self):
        """Spawn items on the floor with better room distribution."""
        # More items on deeper floors
        item_count = 4 + self.floor // 3
        
        # Get rooms for item placement
        available_rooms = self.map.rooms[1:] if len(self.map.rooms) > 1 else []
        self.rng.shuffle(available_rooms)
        
        # Place items in rooms for better exploration rewards
        items_placed = 0
        room_idx = 0
        
        for _ in range(item_count):
            # Try to place in rooms first
            if available_rooms and room_idx < len(available_rooms):
                room = available_rooms[room_idx % len(available_rooms)]
                room_idx += 1
                
                # Random position within room
                ix = self.rng.randint(room.x + 1, room.x + room.w - 2)
                iy = self.rng.randint(room.y + 1, room.y + room.h - 2)
                
                if self.map.is_walkable(ix, iy) and manhattan((ix, iy), self.player.pos()) >= 3:
                    # Generate item with luck scaling
                    item = self._generate_floor_item(self.floor)
                    self.items_on_ground.append(((ix, iy), item))
                    items_placed += 1
            else:
                # Fallback to random placement
                pos = self.map.random_floor_cell(avoid=self.player.pos())
                item = self._generate_floor_item(self.floor)
                self.items_on_ground.append((pos, item))
                items_placed += 1
        
        # Bonus: Place extra items in treasure rooms
        for room in available_rooms[:2]:
            if self.rng.random() < 0.30:  # 30% chance per room
                ix = self.rng.randint(room.x + 2, room.x + room.w - 3)
                iy = self.rng.randint(room.y + 2, room.y + room.h - 3)
                
                if self.map.is_walkable(ix, iy):
                    # Better chance for rare+ items in treasure rooms
                    item = self._generate_floor_item(self.floor, bonus_luck=5)
                    self.items_on_ground.append(((ix, iy), item))
        
        # Spawn shrines
        if self.rng.random() < 0.40:
            pos = self.map.random_floor_cell(avoid=self.player.pos())
            shrine = Shrine(pos, self.rng)
            self.shrines.append(shrine)
            if self.map.is_passable(pos[0], pos[1]):
                self.map.tiles[pos[1]][pos[0]] = TILE_SHRINE

        # Spawn merchants (every 5 floors)
        if self.floor % 5 == 0:
            pos = self.map.random_floor_cell(avoid=self.player.pos())
            merchant = Merchant(pos, self.floor, self.rng)
            self.merchants.append(merchant)
            if self.map.is_passable(pos[0], pos[1]):
                self.map.tiles[pos[1]][pos[0]] = TILE_MERCHANT
    
    def _generate_floor_item(self, floor: int, bonus_luck: int = 0):
        """Generate an item for the floor with random stats and rarity."""
        # Base luck for item generation
        luck = self.luck_points + bonus_luck
        
        # Small chance for guaranteed rare+ items on deeper floors
        roll = self.rng.random()
        if floor >= 20 and roll < 0.10:
            # 10% chance for epic+ on floor 20+
            from items import generate_item
            return generate_item(self.rng, luck, floor, force_rarity=RARITY_EPIC if roll < 0.08 else RARITY_RARE)
        elif floor >= 10 and roll < 0.20:
            # 20% chance for rare+ on floor 10+
            from items import generate_item
            return generate_item(self.rng, luck, floor, force_rarity=RARITY_RARE)
        else:
            # Normal random generation
            from items import generate_item
            return generate_item(self.rng, luck, floor)
    
    def _place_stairs(self):
        """Place stairs down."""
        pos = self.map.random_floor_cell(avoid=self.player.pos())
        self.stairs_pos = pos
        self.map.place_stairs(pos)
    
    def _scale_monster(self, template: MonsterTemplate, floor: int) -> MonsterTemplate:
        """Scale monster with floor depth."""
        hp_mult = 1.0 + (floor - 1) * 0.12
        dmg_mult = 1.0 + (floor - 1) * 0.08
        xp_mult = 1.0 + (floor - 1) * 0.10
        
        return MonsterTemplate(
            template.key, template.name, template.symbol,
            int(template.max_hp * hp_mult),
            int(template.base_damage * dmg_mult),
            int(template.xp_given * xp_mult),
            template.is_boss, template.behavior
        )
    
    def _get_monster_templates(self, biome: str) -> List[MonsterTemplate]:
        """Get monster templates for biome."""
        # Common monsters (available in all biomes)
        common = [
            MonsterTemplate("slime", "Slime", "s", 20, 5, 8),
            MonsterTemplate("goblin", "Goblin", "g", 28, 7, 12),
            MonsterTemplate("skeleton", "Skeleton", "k", 35, 9, 15),
            MonsterTemplate("bat", "Giant Bat", "b", 18, 6, 7),
            MonsterTemplate("orc", "Orc", "o", 45, 11, 20),
            MonsterTemplate("spider", "Giant Spider", "S", 30, 8, 13),
            MonsterTemplate("rat", "Plague Rat", "r", 22, 6, 9),
        ]
        
        # Elite monsters (appear on deeper floors)
        elite = [
            MonsterTemplate("ogre", "Ogre", "O", 70, 15, 35),
            MonsterTemplate("wraith", "Wraith", "w", 55, 14, 30),
            MonsterTemplate("troll", "Troll", "T", 80, 16, 40),
            MonsterTemplate("demon", "Lesser Demon", "d", 65, 17, 38),
            MonsterTemplate("cultist", "Dark Cultist", "c", 50, 13, 28),
            MonsterTemplate("golem", "Stone Golem", "G", 90, 18, 45),
        ]
        
        # Biome-specific monsters
        biome_specific = {
            BIOME_DUNGEON: [
                MonsterTemplate("guard", "Dungeon Guard", "D", 40, 10, 18),
                MonsterTemplate("prisoner", "Undead Prisoner", "P", 32, 8, 14),
            ],
            BIOME_FOREST: [
                MonsterTemplate("wolf", "Dire Wolf", "W", 38, 10, 16),
                MonsterTemplate("treant", "Corrupted Treant", "T", 60, 12, 22),
                MonsterTemplate("dryad", "Shadow Dryad", "d", 35, 9, 17),
            ],
            BIOME_CAVE: [
                MonsterTemplate("crystal_bug", "Crystal Bug", "C", 42, 11, 19),
                MonsterTemplate("troglodyte", "Troglodyte", "t", 48, 13, 21),
                MonsterTemplate("earth_elemental", "Earth Elemental", "E", 65, 15, 30),
            ],
            BIOME_HELL: [
                MonsterTemplate("imp", "Fire Imp", "i", 45, 14, 24),
                MonsterTemplate("hellhound", "Hellhound", "h", 52, 16, 27),
                MonsterTemplate("balrog", "Young Balrog", "B", 85, 20, 50),
            ],
            BIOME_VOID: [
                MonsterTemplate("voidling", "Voidling", "v", 50, 15, 26),
                MonsterTemplate("horror", "Eldritch Horror", "H", 75, 18, 42),
                MonsterTemplate("warp_stalker", "Warp Stalker", "W", 60, 17, 33),
            ],
        }
        
        # Combine based on floor depth
        if self.floor <= 5:
            return common
        elif self.floor <= 10:
            return common + biome_specific.get(biome, [])
        elif self.floor <= 20:
            return common + elite[:3] + biome_specific.get(biome, [])
        else:
            return common + elite + biome_specific.get(biome, [])
    
    # ---- Player Stats ----
    
    def _max_hp(self) -> int:
        """Calculate max HP."""
        base = 60
        base += self.vit_points * 12
        base += (self.level - 1) * 8
        
        # Equipment bonuses
        for item in [self.equipped_armor, self.equipped_ring, self.equipped_amulet]:
            if item and item.vitality_points:
                base += item.vitality_points * 10
        
        return base
    
    def _update_max_hp(self):
        """Update player max HP."""
        new_max = self._max_hp()
        if self.player:
            hp_diff = new_max - self.player.max_hp
            self.player.max_hp = new_max
            self.player.hp = max(1, min(self.player.hp + hp_diff, new_max))
    
    def _total_stat(self, stat: str) -> int:
        """Get total stat including equipment."""
        base = getattr(self, f"{stat}_points", 0)
        
        for item in [self.equipped_weapon, self.equipped_armor, self.equipped_ring, self.equipped_amulet]:
            if item:
                base += getattr(item, f"{stat}_points", 0)
        
        # Trait bonuses
        for trait in self.traits:
            base += int(trait.stat_bonus.get(stat, 0))
        
        return base
    
    def _attack_damage(self) -> int:
        """Calculate player attack damage."""
        if self.equipped_weapon:
            base = self.equipped_weapon.base_damage
        else:
            base = 10
        
        # Strength multiplier
        str_pts = self._total_stat("str")
        mult = 1.0 + str_pts * 0.005
        
        # Damage boosters
        boost_mult = 1.0
        for item in [self.equipped_weapon, self.equipped_armor, self.equipped_ring, self.equipped_amulet]:
            if item:
                for booster in item.boosters:
                    if booster.key == "damage_mult":
                        boost_mult += booster.value
        
        # Trait bonuses
        for trait in self.traits:
            if "damage_mult" in trait.stat_bonus:
                boost_mult += trait.stat_bonus["damage_mult"]
        
        dmg = int(base * mult * boost_mult)
        return max(1, dmg)
    
    def _crit_chance(self) -> float:
        """Calculate critical hit chance."""
        base = 0.05
        luck_pts = self._total_stat("luck")
        base += luck_pts * 0.003
        
        # Equipment bonuses
        if self.equipped_weapon and self.equipped_weapon.crit_bonus:
            base += self.equipped_weapon.crit_bonus
        
        for item in [self.equipped_armor, self.equipped_ring, self.equipped_amulet]:
            if item:
                for booster in item.boosters:
                    if booster.key == "crit_rate":
                        base += booster.value
        
        return min(0.80, base)
    
    def _crit_damage_mult(self) -> float:
        """Calculate critical damage multiplier."""
        base = 1.5
        
        for item in [self.equipped_weapon, self.equipped_armor, self.equipped_ring, self.equipped_amulet]:
            if item:
                for booster in item.boosters:
                    if booster.key == "crit_damage":
                        base += booster.value
        
        return base
    
    def _resistance_mult(self) -> float:
        """Calculate damage resistance (returns multiplier < 1.0)."""
        res_pts = self._total_stat("res")
        reduction = min(res_pts * 0.005, 0.75)
        
        # Equipment bonuses
        for item in [self.equipped_armor, self.equipped_ring, self.equipped_amulet]:
            if item:
                for booster in item.boosters:
                    if booster.key == "resistance_pct":
                        reduction += booster.value
        
        reduction = min(reduction, 0.85)
        return 1.0 - reduction
    
    # ---- Combat ----
    
    def _player_attack(self, target: Entity, forced_crit: bool = False):
        """Player attacks a monster."""
        dmg = self._attack_damage()
        
        # Critical hit
        is_crit = forced_crit or (self.rng.random() < self._crit_chance())
        if is_crit:
            dmg = int(dmg * self._crit_damage_mult())
        
        # Elemental damage
        if self.equipped_weapon and self.equipped_weapon.element != ELEM_PHYSICAL:
            elem_dmg = int(self.equipped_weapon.base_damage * 0.3)
            dmg += elem_dmg
        
        # Apply damage
        target.hp -= dmg
        target.damage_dealt_total += dmg
        
        if is_crit:
            self.log(f"CRITICAL! You hit {target.name} for {dmg} damage!")
        else:
            self.log(f"You hit {target.name} for {dmg} damage.")
        
        # Lifesteal
        lifesteal = 0.0
        for item in [self.equipped_weapon, self.equipped_ring, self.equipped_amulet]:
            if item:
                for booster in item.boosters:
                    if booster.key == "lifesteal":
                        lifesteal += booster.value
        
        if lifesteal > 0:
            heal = int(dmg * lifesteal)
            if heal > 0:
                self.player.hp = min(self.player.max_hp, self.player.hp + heal)
        
        # Check if monster died
        if target.hp <= 0:
            self._monster_died(target)
    
    def _monster_died(self, monster: Entity):
        """Handle monster death."""
        # XP
        self._gain_xp(monster.xp_given)
        
        # Track bestiary
        if monster.name not in self.bestiary:
            self.bestiary[monster.name] = {"count": 0, "symbol": monster.symbol}
        self.bestiary[monster.name]["count"] += 1
        
        self.monsters_killed += 1
        if monster.is_boss:
            self.bosses_killed += 1
            self.log(f"BOSS DEFEATED: {monster.name}!")
            # Spawn stairs
            self._place_stairs()
        
        # Drop loot
        if self.rng.random() < 0.75:
            pos = monster.pos()
            item = generate_item(self.rng, self.luck_points, self.floor)
            self.items_on_ground.append((pos, item))
            self.log(f"{monster.name} dropped {item.name}!")
        
        # Gold drop
        gold = self.rng.randint(5, 20) + self.floor * 2
        self.gold += gold
        self.log(f"+{gold} gold")
    
    def _gain_xp(self, amount: int):
        """Gain XP and level up if applicable."""
        self.xp += amount
        
        while self.xp >= self.xp_to_level:
            self.xp -= self.xp_to_level
            self.level += 1
            self.trait_points += 1
            self.xp_to_level = int(self.xp_to_level * 1.2 + 15)
            self.log(f"LEVEL UP! You are now level {self.level}! +1 Trait Point")
            self._update_max_hp()
    
    def _monster_attack(self, monster: Entity):
        """Monster attacks player."""
        dmg = max(1, monster.base_damage)
        
        # Apply resistance
        dmg = int(dmg * self._resistance_mult())
        dmg = max(1, dmg)
        
        self.player.hp -= dmg
        self.log(f"{monster.name} hits you for {dmg} damage!")
        
        if self.player.hp <= 0:
            self.game_state = STATE_DEAD
    
    # ---- Monster AI ----
    
    def _process_monsters(self):
        """Process all monster turns."""
        for monster in self.monsters:
            if not monster.is_alive():
                continue
            
            monster.turns_alive += 1
            
            # Tick status effects
            monster.tick_status_effects()
            if not monster.is_alive():
                self._monster_died(monster)
                continue
            
            # Boss AI
            if monster.is_boss and self.boss_ai:
                # Check phase transition
                phase_msg = self.boss_ai.check_phase_transition()
                if phase_msg:
                    self.log(phase_msg)
                
                # Try special ability
                game_state = {
                    'map': self.map, 'player': self.player, 
                    'combat': self.combat, 'log': self.log,
                    'spawn_minion': self._spawn_minion_near
                }
                
                if self.boss_ai.execute_special_ability(self.player, game_state):
                    if self.player.hp <= 0:
                        self.game_state = STATE_DEAD
                    continue
                
                # Normal AI action
                dist = manhattan(monster.pos(), self.player.pos())
                if dist <= 1:
                    self._monster_attack(monster)
                else:
                    self._move_monster_toward(monster, self.player.pos())
                continue
            
            # Regular monster AI
            action = self.monster_ai.decide_action(monster, self.player, {'map': self.map})
            
            if action == "attack":
                if manhattan(monster.pos(), self.player.pos()) <= 1:
                    self._monster_attack(monster)
            elif action == "move":
                self._move_monster_toward(monster, self.player.pos())
            elif action == "wander":
                self._wander_monster(monster)
    
    def _move_monster_toward(self, monster: Entity, target: Vec2):
        """Move monster one step toward target."""
        mx, my = monster.pos()
        tx, ty = target
        
        dx = 0 if mx == tx else (1 if mx < tx else -1)
        dy = 0 if my == ty else (1 if my < ty else -1)
        
        # Try to move
        if self.map.is_walkable(mx + dx, my + dy):
            if not (mx + dx == self.player.x and my + dy == self.player.y):
                monster.x, monster.y = mx + dx, my + dy
        elif self.map.is_walkable(mx + dx, my):
            if not (mx + dx == self.player.x and my == self.player.y):
                monster.x, monster.y = mx + dx, my
        elif self.map.is_walkable(mx, my + dy):
            if not (mx == self.player.x and my + dy == self.player.y):
                monster.x, monster.y = mx, my + dy
    
    def _wander_monster(self, monster: Entity):
        """Random wander."""
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        self.rng.shuffle(dirs)
        
        for dx, dy in dirs:
            nx, ny = monster.x + dx, monster.y + dy
            if self.map.is_walkable(nx, ny):
                if not (nx == self.player.x and ny == self.player.y):
                    monster.x, monster.y = nx, ny
                    break
    
    def _spawn_minion_near(self, template: MonsterTemplate, pos: Vec2):
        """Spawn a minion near position."""
        for _ in range(10):
            dx = self.rng.randint(-2, 2)
            dy = self.rng.randint(-2, 2)
            nx, ny = pos[0] + dx, pos[1] + dy
            if self.map.is_walkable(nx, ny):
                minion = Entity(
                    nx, ny, template.symbol, template.name, template.key,
                    template.max_hp, template.max_hp, template.base_damage, template.xp_given
                )
                self.monsters.append(minion)
                self.log(f"{template.name} appears!")
                return
    
    # ---- Player Actions ----
    
    def _move_player(self, dx: int, dy: int):
        """Move player in direction."""
        if not self.player or self.game_state != STATE_RUNNING:
            return
        
        nx, ny = self.player.x + dx, self.player.y + dy
        self.last_move_dir = (dx, dy)
        
        # Check for monster
        for monster in self.monsters:
            if monster.is_alive() and monster.x == nx and monster.y == ny:
                self._player_attack(monster)
                self._end_turn()
                return
        
        # Move if passable
        if self.map.is_walkable(nx, ny):
            self.player.x, self.player.y = nx, ny
            self._check_tile_events()
            self._end_turn()
    
    def _check_tile_events(self):
        """Check for events on current tile."""
        if not self.player:
            return
        
        px, py = self.player.pos()
        
        # Check for items
        items_here = [(i, pos) for i, (pos, item) in enumerate(self.items_on_ground) if pos == (px, py)]
        if items_here:
            pass  # Player needs to press G to pick up
        
        # Check for stairs
        if self.stairs_pos and (px, py) == self.stairs_pos:
            pass  # Player needs to press >
        
        # Check for shrines
        for shrine in self.shrines:
            if shrine.pos == (px, py) and not shrine.activated:
                self.log(f"You see a {shrine.name}. Press 'e' to activate.")
        
        # Check for merchants
        for merchant in self.merchants:
            if merchant.pos == (px, py):
                self.log("You see a merchant. Press 'e' to trade.")
    
    def _pick_up_items(self):
        """Pick up items on current tile."""
        if not self.player:
            return
        
        px, py = self.player.pos()
        to_pick = []
        
        for i, (pos, item) in enumerate(self.items_on_ground):
            if pos == (px, py):
                to_pick.append(i)
        
        if to_pick:
            for i in reversed(to_pick):
                pos, item = self.items_on_ground.pop(i)
                self.inventory.append(item)
                self.log(f"Picked up: {item.name}")
        else:
            self.log("Nothing to pick up here.")
    
    def _descend_stairs(self):
        """Descend to next floor."""
        if not self.player or not self.stairs_pos:
            self.log("No stairs here.")
            return
        
        if self.player.pos() != self.stairs_pos:
            self.log("Stand on the stairs to descend.")
            return
        
        if self.floor >= self.max_floors:
            self.game_state = STATE_VICTORIOUS
            return
        
        self._start_floor(self.floor + 1)
        self.log(f"You descend to floor {self.floor}.")
    
    def _end_turn(self):
        """End player turn."""
        if self.game_state != STATE_RUNNING:
            return
        
        self.turn_count += 1
        
        # Process monsters
        self._process_monsters()
        
        # Check player death
        if self.player and self.player.hp <= 0:
            self.game_state = STATE_DEAD
        
        # Tick player status effects
        if self.player:
            self.player.tick_status_effects()
        
        # Update FOV
        self._update_fov()
    
    def _update_fov(self):
        """Update field of view."""
        if self.player and self.map:
            radius = self.fov_radius
            # Trait bonuses
            for trait in self.traits:
                if "fov_radius" in trait.stat_bonus:
                    radius += int(trait.stat_bonus["fov_radius"])
            
            self.fov_visible = self.map.compute_fov(self.player.pos(), radius)
            
            # Update explored
            for y in range(self.map.h):
                for x in range(self.map.w):
                    if self.fov_visible[y][x]:
                        self.map.explored[y][x] = True
    
    # ---- UI ----
    
    def draw(self):
        """Draw the game screen."""
        self.stdscr.erase()
        
        # Draw map
        for y in range(self.map_h):
            for x in range(self.map_w):
                if y >= self.map.h or x >= self.map.w:
                    continue
                
                if not self.map.explored[y][x]:
                    continue
                
                visible = self.fov_visible[y][x] if y < len(self.fov_visible) and x < len(self.fov_visible[0]) else False
                tile = self.map.tiles[y][x]
                
                ch = " "
                if tile == TILE_WALL:
                    ch = "#" if visible else " "
                elif tile == TILE_FLOOR:
                    ch = "." if visible else "·"
                elif tile == TILE_STAIRS_DOWN:
                    ch = ">" if visible else " "
                elif tile == TILE_SHRINE:
                    ch = "?" if visible else " "
                elif tile == TILE_MERCHANT:
                    ch = "$" if visible else " "
                elif tile == TILE_LAVA:
                    ch = "~" if visible else " "
                
                if visible:
                    try:
                        if ch == "#":
                            self.stdscr.addch(y, x, '#', curses.color_pair(4))
                        elif ch == "~":
                            self.stdscr.addch(y, x, '~', curses.color_pair(6))
                        else:
                            self.stdscr.addch(y, x, ch)
                    except:
                        pass
        
        # Draw items
        for (pos, item) in self.items_on_ground:
            x, y = pos
            if y < self.map_h and x < self.map_w and self.fov_visible[y][x]:
                try:
                    self.stdscr.addch(y, x, item.glyph, curses.color_pair(self.color_pair(item.color_key)))
                except:
                    pass
        
        # Draw monsters
        for monster in self.monsters:
            if monster.is_alive():
                x, y = monster.x, monster.y
                if y < self.map_h and x < self.map_w and self.fov_visible[y][x]:
                    try:
                        color = curses.color_pair(6) if monster.is_boss else 0
                        self.stdscr.addch(y, x, monster.symbol, color)
                    except:
                        pass
        
        # Draw player
        if self.player:
            x, y = self.player.x, self.player.y
            if y < self.map_h and x < self.map_w:
                try:
                    self.stdscr.addch(y, x, '@', curses.color_pair(2) | curses.A_BOLD)
                except:
                    pass

        # Show item name when player is standing on it
        self._draw_items_on_player_tile()

        # Draw HUD
        self._draw_hud()

        self.stdscr.refresh()

    def _draw_items_on_player_tile(self):
        """Display item name(s) when player is on the same tile."""
        if not self.player:
            return
        
        px, py = self.player.pos()
        items_here = []
        
        for (pos, item) in self.items_on_ground:
            if pos == (px, py):
                items_here.append(item)
        
        if not items_here:
            return
        
        # Display items on current tile
        display_y = self.map_h - 2
        try:
            if len(items_here) == 1:
                item = items_here[0]
                msg = f"[G] {item.name} [{item.rarity.upper()}]"
                self.stdscr.addstr(display_y, 2, msg[:self.map_w-4], 
                                 curses.color_pair(self.color_pair(item.color_key)) | curses.A_BOLD)
            else:
                msg = f"[G] {len(items_here)} items here - Press G to pick up"
                self.stdscr.addstr(display_y, 2, msg[:self.map_w-4], curses.color_pair(4) | curses.A_BOLD)
        except:
            pass
    
    def _draw_hud(self):
        """Draw HUD."""
        if not self.player:
            return
        
        hud_y = self.map_h + 1
        
        try:
            # Top line
            hp_bar = self._format_hp_bar(self.player.hp, self.player.max_hp, 20)
            self.stdscr.addstr(hud_y, 0, f"Floor {self.floor}/{self.max_floors} | Lvl {self.level} | XP {self.xp}/{self.xp_to_level}")
            self.stdscr.addstr(hud_y + 1, 0, f"HP: {hp_bar} {self.player.hp}/{self.player.max_hp}")
            self.stdscr.addstr(hud_y + 2, 0, f"STR:{self._total_stat('str')} RES:{self._total_stat('res')} LUCK:{self._total_stat('luck')} VIT:{self._total_stat('vit')} | Gold: {self.gold}")
            self.stdscr.addstr(hud_y + 3, 0, f"Class: {self.player_class.title()} | Trait Pts: {self.trait_points}")
            
            # Message log
            log_y = hud_y + 5
            for i, msg in enumerate(self.message_log[-self.max_log:]):
                yy = log_y + i
                if yy < curses.LINES - 1:
                    self.stdscr.addstr(yy, 0, msg[:self.map_w])
        except:
            pass
    
    def _format_hp_bar(self, hp: int, max_hp: int, width: int) -> str:
        """Format HP bar."""
        if max_hp <= 0:
            return "[" + " " * width + "]"
        
        filled = int(width * hp / max_hp)
        filled = max(0, min(width, filled))
        
        if hp / max_hp > 0.5:
            return "[" + "#" * filled + "-" * (width - filled) + "]"
        elif hp / max_hp > 0.25:
            return "[" + "=" * filled + "-" * (width - filled) + "]"
        else:
            return "[" + "!" * filled + "-" * (width - filled) + "]"
    
    # ---- Input Handling ----
    
    def handle_input(self) -> bool:
        """Handle player input. Returns False to quit."""
        ch = self.stdscr.getch()

        if ch in [ord('q'), ord('Q')]:
            return False
        elif ch == curses.KEY_LEFT or ch in [ord('h'), ord('H')]:
            self._move_player(-1, 0)
        elif ch == curses.KEY_RIGHT or ch in [ord('l'), ord('L')]:
            self._move_player(1, 0)
        elif ch == curses.KEY_UP or ch in [ord('w'), ord('W')]:
            self._move_player(0, -1)
        elif ch == curses.KEY_DOWN or ch in [ord('s'), ord('S')]:
            self._move_player(0, 1)
        elif ch in [ord('g'), ord('G')]:
            self._pick_up_items()
        elif ch == ord('>'):
            self._descend_stairs()
        elif ch in [ord('i'), ord('I')]:
            self._show_inventory()
        elif ch in [ord('c'), ord('C')]:
            self._show_equipment()
        elif ch in [ord('k'), ord('K')]:
            self._show_stats()
        elif ch in [ord('b'), ord('B')]:
            self._show_bestiary()
        elif ch in [ord('u'), ord('U')]:
            self._use_class_ability()
        elif ch == ord('?'):
            self._show_help()
        elif ch == ord('.'):
            self._end_turn()  # Wait
        elif ch == curses.KEY_F5:
            self._save_game()
        elif ch == curses.KEY_F9:
            if self._load_game_menu():
                return True

        return True
    
    def _show_inventory(self):
        """Show inventory screen."""
        if not self.inventory:
            self.log("Inventory is empty.")
            return
        
        while True:
            self.stdscr.erase()
            h, w = self.stdscr.getmaxyx()
            
            self.stdscr.addstr(1, 2, "Inventory (Enter to use/equip, Esc to close)", curses.A_BOLD)
            
            for i, item in enumerate(self.inventory[:h-4]):
                line = f"{i+1}. {item.name} [{item.rarity}] - {item.slot}"
                if item.is_potion():
                    line += f" (Heals {int(item.heal_pct*100)}%)"
                try:
                    self.stdscr.addstr(3 + i, 4, line)
                except:
                    pass
            
            self.stdscr.refresh()
            ch = self.stdscr.getch()
            
            if ch == KEY_ESCAPE:
                return
            elif ch in range(ord('1'), ord('9') + 1):
                idx = ch - ord('1')
                if idx < len(self.inventory):
                    self._use_item(idx)
    
    def _use_item(self, index: int):
        """Use/equip item from inventory."""
        if index < 0 or index >= len(self.inventory):
            return
        
        item = self.inventory[index]
        
        if item.is_potion():
            # Use potion
            heal = int(self.player.max_hp * item.heal_pct)
            self.player.hp = min(self.player.max_hp, self.player.hp + heal)
            self.inventory.pop(index)
            self.log(f"Used {item.name}. Healed {heal} HP.")
        elif item.is_scroll():
            # Use scroll
            self.log(f"Used {item.name}!")
            self.inventory.pop(index)
            # Implement scroll effects
        elif item.is_weapon() or item.is_armor() or item.is_ring() or item.is_amulet():
            # Equip item
            self._equip_item(item)
            self.inventory.pop(index)
    
    def _equip_item(self, item: Item):
        """Equip an item."""
        if item.is_weapon():
            if self.equipped_weapon:
                self.inventory.append(self.equipped_weapon)
            self.equipped_weapon = item
            self.log(f"Equipped: {item.name}")
        elif item.is_armor():
            if self.equipped_armor:
                self.inventory.append(self.equipped_armor)
            self.equipped_armor = item
            self.log(f"Equipped: {item.name}")
        elif item.is_ring():
            if self.equipped_ring:
                self.inventory.append(self.equipped_ring)
            self.equipped_ring = item
            self.log(f"Equipped: {item.name}")
        elif item.is_amulet():
            if self.equipped_amulet:
                self.inventory.append(self.equipped_amulet)
            self.equipped_amulet = item
            self.log(f"Equipped: {item.name}")
        
        self._update_max_hp()
    
    def _show_equipment(self):
        """Show equipped items."""
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        
        self.stdscr.addstr(1, 2, "Equipment (Esc to close)", curses.A_BOLD)
        
        y = 3
        if self.equipped_weapon:
            self.stdscr.addstr(y, 4, f"Weapon: {self.equipped_weapon.name} [{self.equipped_weapon.rarity}]")
            y += 1
        else:
            self.stdscr.addstr(y, 4, "Weapon: (none)")
            y += 1
        
        if self.equipped_armor:
            self.stdscr.addstr(y, 4, f"Armor: {self.equipped_armor.name} [{self.equipped_armor.rarity}]")
            y += 1
        else:
            self.stdscr.addstr(y, 4, "Armor: (none)")
            y += 1
        
        if self.equipped_ring:
            self.stdscr.addstr(y, 4, f"Ring: {self.equipped_ring.name} [{self.equipped_ring.rarity}]")
            y += 1
        else:
            self.stdscr.addstr(y, 4, "Ring: (none)")
            y += 1
        
        if self.equipped_amulet:
            self.stdscr.addstr(y, 4, f"Amulet: {self.equipped_amulet.name} [{self.equipped_amulet.rarity}]")
            y += 1
        else:
            self.stdscr.addstr(y, 4, "Amulet: (none)")
            y += 1
        
        self.stdscr.addstr(y + 1, 4, "Press Esc to close")
        self.stdscr.refresh()
        self.stdscr.getch()
    
    def _show_stats(self):
        """Show stats and traits."""
        while True:
            self.stdscr.erase()
            h, w = self.stdscr.getmaxyx()
            
            self.stdscr.addstr(1, 2, f"Stats (Trait Points: {self.trait_points}) (Esc to close)", curses.A_BOLD)
            
            y = 3
            self.stdscr.addstr(y, 4, f"Strength: {self._total_stat('str')} (+{self._total_stat('str')*0.5:.1f}% dmg)")
            y += 1
            self.stdscr.addstr(y, 4, f"Resistance: {self._total_stat('res')} ({(1-self._resistance_mult())*100:.1f}% reduction)")
            y += 1
            self.stdscr.addstr(y, 4, f"Luck: {self._total_stat('luck')} ({self._crit_chance()*100:.1f}% crit)")
            y += 1
            self.stdscr.addstr(y, 4, f"Vitality: {self._total_stat('vit')} ({self._max_hp()} max HP)")
            y += 2
            
            if self.trait_points > 0:
                self.stdscr.addstr(y, 4, "Choose a trait:", curses.A_BOLD)
                y += 1
                
                for i, trait in enumerate(self.available_traits[:h-y-3]):
                    self.stdscr.addstr(y + i, 6, f"{i+1}. {trait.name} - {trait.description}")
            else:
                self.stdscr.addstr(y, 4, "No trait points available.")
            
            self.stdscr.refresh()
            ch = self.stdscr.getch()
            
            if ch == KEY_ESCAPE:
                return
            elif self.trait_points > 0 and ch in range(ord('1'), ord('9') + 1):
                idx = ch - ord('1')
                if idx < len(self.available_traits):
                    self.traits.append(self.available_traits.pop(idx))
                    self.trait_points -= 1
                    self.log(f"Learned trait: {self.traits[-1].name}")
                    self._update_max_hp()
    
    def _show_bestiary(self):
        """Show bestiary."""
        if not self.bestiary:
            self.log("Bestiary is empty. Kill some monsters!")
            return
        
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        
        self.stdscr.addstr(1, 2, "Bestiary (Esc to close)", curses.A_BOLD)
        
        y = 3
        for name, data in list(self.bestiary.items())[:h-4]:
            self.stdscr.addstr(y, 4, f"{name} [{data['symbol']}] - Defeated: {data['count']}")
            y += 1
        
        self.stdscr.addstr(y + 1, 4, "Press Esc to close")
        self.stdscr.refresh()
        self.stdscr.getch()
    
    def _use_class_ability(self):
        """Use class special ability."""
        if not self.player:
            return
        
        ability = self.class_abilities[self.player_class]
        now = time.time()
        
        if now - ability["last_used"] < ability["cooldown"]:
            remaining = int(ability["cooldown"] - (now - ability["last_used"]))
            self.log(f"Ability on cooldown: {remaining}s remaining")
            return
        
        ability["last_used"] = now
        
        if self.player_class == "warrior":
            # War Cry: AoE damage around player
            self.log("WAR CRY! All nearby enemies take damage!")
            for monster in self.monsters:
                if monster.is_alive() and manhattan(self.player.pos(), monster.pos()) <= 2:
                    dmg = self._attack_damage() * 2
                    monster.hp -= dmg
                    self.log(f"{monster.name} takes {dmg} damage!")
                    if not monster.is_alive():
                        self._monster_died(monster)
        
        elif self.player_class == "mage":
            # Fireball: Ranged damage
            self.log("FIREBALL! Launching fireball...")
            # Find closest monster
            closest = None
            closest_dist = 999
            for monster in self.monsters:
                if monster.is_alive():
                    dist = manhattan(self.player.pos(), monster.pos())
                    if dist < closest_dist:
                        closest_dist = dist
                        closest = monster
            
            if closest:
                dmg = self._attack_damage() * 3
                closest.hp -= dmg
                self.log(f"Fireball hits {closest.name} for {dmg} damage!")
                if not closest.is_alive():
                    self._monster_died(closest)
        
        elif self.player_class == "rogue":
            # Shadow Step: Teleport to monster and crit
            self.log("SHADOW STEP! Teleporting to enemy...")
            for monster in self.monsters:
                if monster.is_alive():
                    self.player.x, self.player.y = monster.x, monster.y
                    self._player_attack(monster, forced_crit=True)
                    break
        
        elif self.player_class == "paladin":
            # Divine Shield: Immunity for 3 turns
            self.log("DIVINE SHIELD! Immune to damage for 3 turns!")
            self.player.status_effects.append(StatusEffect(STATUS_SHIELDED, 3))
        
        self._end_turn()
    
    def _show_help(self):
        """Show help screen."""
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        
        help_text = [
            "=== EPIC ROGUELIKE HELP ===",
            "",
            "Movement: Arrow keys or WASD",
            "Attack: Move into enemy",
            "Pick up items: G",
            "Use item: I (inventory)",
            "Equipment: C",
            "Stats/Traits: K",
            "Bestiary: B",
            "Class ability: U",
            "Descend stairs: > (stand on stairs)",
            "Wait: . (period)",
            "Help: ?",
            "Save game: F5",
            "Load game: F9",
            "Quit: Q",
            "",
            "Goal: Descend 50 floors and defeat the Dark God!",
        ]
        
        for i, line in enumerate(help_text[:h-2]):
            try:
                self.stdscr.addstr(1 + i, 2, line)
            except:
                pass
        
        self.stdscr.addstr(h - 2, 2, "Press any key to close")
        self.stdscr.refresh()
        self.stdscr.getch()
    
    def _save_game(self):
        """Save current game state."""
        save_data = SaveData(
            player_class=self.player_class,
            level=self.level,
            xp=self.xp,
            xp_to_level=self.xp_to_level,
            gold=self.gold,
            floor=self.floor,
            turn_count=self.turn_count,
            str_points=self.str_points,
            res_points=self.res_points,
            luck_points=self.luck_points,
            vit_points=self.vit_points,
            equipped_weapon=serialize_item(self.equipped_weapon),
            equipped_armor=serialize_item(self.equipped_armor),
            equipped_ring=serialize_item(self.equipped_ring),
            equipped_amulet=serialize_item(self.equipped_amulet),
            inventory=[serialize_item(item) for item in self.inventory],
            traits=[t.key for t in self.traits],
            trait_points=self.trait_points,
            monsters_killed=self.monsters_killed,
            bosses_killed=self.bosses_killed,
            achievements_unlocked=[k for k, v in self.achievements.items() if v.unlocked],
        )
        
        result = save_game(save_data, self.save_slot)
        self.log(result)
    
    def _load_game_menu(self):
        """Show load game menu."""
        slots = get_save_slots()
        
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        
        self.stdscr.addstr(2, 2, "Load Game (Esc to cancel)", curses.A_BOLD)
        self.stdscr.addstr(3, 2, "Available save slots:", curses.color_pair(4))
        
        from datetime import datetime
        for slot_num in range(1, 4):
            save_data = slots.get(slot_num)
            y = 5 + slot_num * 2
            
            if save_data:
                save_time = datetime.fromtimestamp(save_data.save_time).strftime("%Y-%m-%d %H:%M")
                text = f"Slot {slot_num}: Floor {save_data.floor} | Lvl {save_data.level} | {save_data.player_class} | {save_time}"
                try:
                    self.stdscr.addstr(y, 4, text, curses.color_pair(2))
                except:
                    pass
            else:
                try:
                    self.stdscr.addstr(y, 4, f"Slot {slot_num}: [Empty]")
                except:
                    pass
        
        try:
            self.stdscr.addstr(13, 4, "Press 1-3 to load, Esc to cancel", curses.A_BOLD | curses.color_pair(4))
        except:
            pass
        self.stdscr.refresh()
        
        ch = self.stdscr.getch()
        if ch in [ord('1'), ord('2'), ord('3')]:
            slot = ch - ord('0')
            save_data = load_game(slot)
            if save_data:
                self._apply_save_data(save_data)
                return True
        
        return False
    
    def _apply_save_data(self, save_data: SaveData):
        """Apply loaded save data to game state."""
        self.player_class = save_data.player_class
        self.level = save_data.level
        self.xp = save_data.xp
        self.xp_to_level = save_data.xp_to_level
        self.gold = save_data.gold
        self.floor = save_data.floor
        self.turn_count = save_data.turn_count
        self.str_points = save_data.str_points
        self.res_points = save_data.res_points
        self.luck_points = save_data.luck_points
        self.vit_points = save_data.vit_points
        self.trait_points = save_data.trait_points
        self.monsters_killed = save_data.monsters_killed
        self.bosses_killed = save_data.bosses_killed
        
        # Recreate player
        self.player = Entity(0, 0, "@", "Player", "player",
                            self._max_hp(), self._max_hp(), 10, 0, is_player=True)
        
        # Start the floor
        self._start_floor(self.floor, first_floor=True)
        
        self.log(f"✅ Game loaded! Floor {self.floor}, Level {self.level}, Class: {self.player_class}")
    
    # ---- Game Loop ----

    def _show_controls_screen(self):
        """Show comprehensive controls guide before game starts."""
        while True:
            self.stdscr.erase()
            h, w = self.stdscr.getmaxyx()
            
            # Title
            title = "🎮 EPIC ROGUELIKE - CONTROLS GUIDE 🎮"
            self.stdscr.addstr(1, max(0, (w - len(title)) // 2), title, 
                             curses.A_BOLD | curses.color_pair(4))
            
            # Movement
            y = 3
            self.stdscr.addstr(y, 4, "📍 MOVEMENT", curses.A_BOLD | curses.color_pair(2))
            y += 1
            controls_move = [
                ("↑ ↓ ← → / WASD", "Move around the dungeon"),
                ("Move into enemy", "Attack monsters"),
                (". (period)", "Wait one turn (skip)"),
            ]
            for key, desc in controls_move:
                self.stdscr.addstr(y, 6, f"{key:25} - {desc}")
                y += 1
            
            # Items & Equipment
            y += 1
            self.stdscr.addstr(y, 4, "🎒 ITEMS & EQUIPMENT", curses.A_BOLD | curses.color_pair(3))
            y += 1
            controls_items = [
                ("G", "Pick up items on your tile"),
                ("I", "Open inventory (use/equip items)"),
                ("C", "View equipped items"),
                ("E", "Interact (merchants, shrines, events)"),
            ]
            for key, desc in controls_items:
                self.stdscr.addstr(y, 6, f"{key:25} - {desc}")
                y += 1
            
            # Character
            y += 1
            self.stdscr.addstr(y, 4, "👤 CHARACTER", curses.A_BOLD | curses.color_pair(5))
            y += 1
            controls_char = [
                ("K", "View stats & learn traits"),
                ("U", "Use class special ability"),
            ]
            for key, desc in controls_char:
                self.stdscr.addstr(y, 6, f"{key:25} - {desc}")
                y += 1
            
            # Exploration
            y += 1
            self.stdscr.addstr(y, 4, "🗺️ EXPLORATION", curses.A_BOLD | curses.color_pair(6))
            y += 1
            controls_explore = [
                (">", "Descend stairs to next floor"),
                ("B", "View bestiary (monsters defeated)"),
                ("?", "Show this help screen"),
            ]
            for key, desc in controls_explore:
                self.stdscr.addstr(y, 6, f"{key:25} - {desc}")
                y += 1
            
            # System
            y += 1
            self.stdscr.addstr(y, 4, "⚙️ SYSTEM", curses.A_BOLD | curses.color_pair(4))
            y += 1
            controls_sys = [
                ("F5", "Save game (slot 1)"),
                ("F9", "Load game"),
                ("Q", "Quit game"),
                ("Esc", "Close menus/panels"),
                ("Enter", "Confirm selections"),
            ]
            for key, desc in controls_sys:
                self.stdscr.addstr(y, 6, f"{key:25} - {desc}")
                y += 1
            
            # Tips
            y += 2
            self.stdscr.addstr(y, 4, "💡 QUICK TIPS", curses.A_BOLD | curses.color_pair(2))
            y += 1
            tips = [
                "• Walk over items to see their names and rarity",
                "• Explore every room - items are distributed across rooms",
                "• Floor 10+ drops better rarity items (Rare+)",
                "• Floor 20+ has chances for Epic items",
                "• Secret rooms hide behind walls (12% chance per floor)",
                "• Press 'e' to interact with shrines, merchants, and events",
                "• Use class abilities (U) strategically - they have cooldowns!",
                "• Invest in Luck stat for better item drops",
                "• Boss floors (10, 20, 30, 40, 50) have epic multi-phase fights",
            ]
            for tip in tips:
                if y < h - 3:
                    self.stdscr.addstr(y, 6, tip)
                    y += 1
            
            # Footer
            footer_y = h - 2
            self.stdscr.addstr(footer_y, max(0, (w - 50) // 2), 
                             "Press ENTER to start playing, Q to quit",
                             curses.A_BOLD | curses.color_pair(4))
            
            self.stdscr.refresh()
            ch = self.stdscr.getch()
            
            if ch in [KEY_ENTER, KEY_ENTER2]:
                return  # Start game
            elif ch in [ord('q'), ord('Q')]:
                raise Exception("Game cancelled by user")

    def run(self):
        """Main game loop."""
        try:
            # Show controls guide first
            self._show_controls_screen()
            
            # Start the game
            self.start_game()

            while True:
                if self.game_state == STATE_DEAD:
                    self._draw_death_screen()
                    ch = self.stdscr.getch()
                    if ch in [ord('q'), ord('Q'), KEY_ESCAPE]:
                        break
                    elif ch in [KEY_ENTER, KEY_ENTER2]:
                        # Restart
                        self.__init__(self.stdscr)
                        self.start_game()
                    continue

                if self.game_state == STATE_VICTORIOUS:
                    self._draw_victory_screen()
                    ch = self.stdscr.getch()
                    if ch in [ord('q'), ord('Q'), KEY_ESCAPE, KEY_ENTER, KEY_ENTER2]:
                        break
                    continue

                self.draw()

                if not self.handle_input():
                    break

        finally:
            curses.endwin()
    
    def _draw_death_screen(self):
        """Draw death screen."""
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        
        mid_y = h // 2
        
        try:
            self.stdscr.addstr(mid_y - 3, max(0, (w - 20) // 2), "YOU DIED", curses.A_BOLD | curses.color_pair(6))
            self.stdscr.addstr(mid_y - 1, max(0, (w - 40) // 2), f"Floor {self.floor} | Level {self.level} | Turn {self.turn_count}")
            self.stdscr.addstr(mid_y + 1, max(0, (w - 35) // 2), "Press Enter to restart, Q to quit")
        except:
            pass
        
        self.stdscr.refresh()
    
    def _draw_victory_screen(self):
        """Draw victory screen."""
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        
        mid_y = h // 2
        
        try:
            self.stdscr.addstr(mid_y - 4, max(0, (w - 30) // 2), "VICTORY!", curses.A_BOLD | curses.color_pair(2))
            self.stdscr.addstr(mid_y - 2, max(0, (w - 50) // 2), "You have defeated the Dark God and escaped!")
            self.stdscr.addstr(mid_y, max(0, (w - 40) // 2), f"Turns: {self.turn_count} | Level: {self.level}")
            self.stdscr.addstr(mid_y + 2, max(0, (w - 35) // 2), "Press Enter or Q to exit")
        except:
            pass
        
        self.stdscr.refresh()


def main(stdscr):
    """Main entry point."""
    game = RoguelikeGame(stdscr)
    game.run()


if __name__ == "__main__":
    curses.wrapper(main)
