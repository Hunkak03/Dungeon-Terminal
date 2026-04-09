"""Entity system for monsters, player, and NPCs."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from constants import *
from utils import Vec2


@dataclass
class StatusEffect:
    """Active status effect on an entity."""
    name: str
    duration: int  # turns remaining
    value: float = 0.0
    description: str = ""


@dataclass
class PhaseAbility:
    """Special ability available in a specific boss phase."""
    name: str
    min_phase: int
    cooldown: int
    current_cd: int = 0
    chance: float = 0.5
    description: str = ""


@dataclass
class MonsterTemplate:
    """Template for creating monster instances."""
    key: str
    name: str
    symbol: str
    max_hp: int
    base_damage: int
    xp_given: int
    is_boss: bool = False
    behavior: str = "normal"  # normal, aggressive, cowardly, ambush
    abilities: List[PhaseAbility] = field(default_factory=list)
    phase: int = 1
    phase_thresholds: List[float] = field(default_factory=list)  # HP percentages for phase transitions


@dataclass
class Entity:
    """Base entity for player and monsters."""
    x: int
    y: int
    symbol: str
    name: str
    template_key: str
    max_hp: int
    hp: int
    base_damage: int
    xp_given: int = 0
    is_boss: bool = False
    is_player: bool = False
    
    # Combat
    base_armor: int = 0
    element: str = ELEM_PHYSICAL
    
    # Status effects
    status_effects: List[StatusEffect] = field(default_factory=list)
    
    # Boss phases
    phase: int = 1
    special_cd: int = 0
    abilities: List[PhaseAbility] = field(default_factory=list)
    
    # Tracking
    damage_dealt_total: int = 0
    turns_alive: int = 0
    
    # AI behavior
    behavior: str = "normal"
    aggro_range: int = 8
    wander_target: Optional[Vec2] = None
    
    def pos(self) -> Vec2:
        return (self.x, self.y)
    
    def is_alive(self) -> bool:
        return self.hp > 0
    
    def add_status_effect(self, effect: StatusEffect) -> None:
        # Stack or refresh
        for existing in self.status_effects:
            if existing.name == effect.name:
                existing.duration = max(existing.duration, effect.duration)
                existing.value = max(existing.value, effect.value)
                return
        self.status_effects.append(effect)
    
    def remove_status_effect(self, name: str) -> None:
        self.status_effects = [e for e in self.status_effects if e.name != name]
    
    def has_status_effect(self, name: str) -> bool:
        return any(e.name == name for e in self.status_effects)
    
    def tick_status_effects(self) -> List[str]:
        """Tick down status effects and apply damage. Returns list of applied effects."""
        applied = []
        to_remove = []
        
        for effect in self.status_effects:
            effect.duration -= 1
            
            if effect.name == STATUS_POISONED:
                dmg = int(effect.value)
                self.hp -= dmg
                applied.append(f"{self.name} takes {dmg} poison damage")
            elif effect.name == STATUS_BURNING:
                dmg = int(effect.value)
                self.hp -= dmg
                applied.append(f"{self.name} takes {dmg} fire damage")
            elif effect.name == STATUS_BLEEDING:
                dmg = int(effect.value)
                self.hp -= dmg
                applied.append(f"{self.name} takes {dmg} bleed damage")
            elif effect.name == STATUS_SHIELDED:
                if effect.duration <= 0:
                    to_remove.append(effect.name)
            elif effect.name == STATUS_STUNNED:
                pass  # Stun prevents action, handled elsewhere
            elif effect.duration <= 0:
                to_remove.append(effect.name)
        
        for name in to_remove:
            self.remove_status_effect(name)
        
        return applied


# ---- Boss Definitions ----

BOSS_DEFINITIONS = {
    # Floor 10 Bosses
    "iron_golem": MonsterTemplate(
        key="iron_golem", name="Iron Golem", symbol="G",
        max_hp=350, base_damage=28, xp_given=150, is_boss=True,
        behavior="aggressive",
        phase_thresholds=[0.66, 0.33],
        abilities=[
            PhaseAbility("Shockwave", 1, cooldown=2, chance=0.5, description="AoE damage in radius 2"),
            PhaseAbility("Charge", 2, cooldown=3, chance=0.6, description="Charges toward player"),
            PhaseAbility("Melt Down", 3, cooldown=4, chance=0.7, description="Massive fire AoE"),
        ],
    ),
    "forest_warden": MonsterTemplate(
        key="forest_warden", name="Forest Warden", symbol="W",
        max_hp=320, base_damage=25, xp_given=140, is_boss=True,
        behavior="normal",
        phase_thresholds=[0.70, 0.35],
        abilities=[
            PhaseAbility("Root", 1, cooldown=3, chance=0.4, description="Roots player in place"),
            PhaseAbility("Summon Treants", 2, cooldown=4, chance=0.6, description="Summons 2 treants"),
            PhaseAbility("Nature's Wrath", 3, cooldown=5, chance=0.7, description="Massive AoE"),
        ],
    ),
    
    # Floor 20 Bosses
    "crystal_lich": MonsterTemplate(
        key="crystal_lich", name="Crystal Lich", symbol="L",
        max_hp=500, base_damage=38, xp_given=300, is_boss=True,
        behavior="normal",
        phase_thresholds=[0.75, 0.50, 0.25],
        abilities=[
            PhaseAbility("Void Bolt", 1, cooldown=2, chance=0.5, description="Ranged dark damage"),
            PhaseAbility("Summon Minions", 2, cooldown=4, chance=0.6, description="Summons 2 voidlings"),
            PhaseAbility("Phase Shift", 3, cooldown=3, chance=0.7, description="Teleports near player"),
            PhaseAbility("Death Pulse", 4, cooldown=6, chance=0.8, description="Full floor damage pulse"),
        ],
    ),
    "demon_lord": MonsterTemplate(
        key="demon_lord", name="Demon Lord", symbol="D",
        max_hp=550, base_damage=42, xp_given=320, is_boss=True,
        behavior="aggressive",
        phase_thresholds=[0.70, 0.40],
        abilities=[
            PhaseAbility("Fire Storm", 1, cooldown=3, chance=0.5, description="Fire AoE around boss"),
            PhaseAbility("Summon Imps", 2, cooldown=4, chance=0.6, description="Summons 3 imps"),
            PhaseAbility("Inferno", 3, cooldown=5, chance=0.7, description="Massive fire damage"),
        ],
    ),
    
    # Floor 30 Bosses
    "abyss_king": MonsterTemplate(
        key="abyss_king", name="Abyss King", symbol="Ω",
        max_hp=750, base_damage=52, xp_given=500, is_boss=True,
        behavior="aggressive",
        phase_thresholds=[0.75, 0.50, 0.25],
        abilities=[
            PhaseAbility("Shadow Rend", 1, cooldown=2, chance=0.5, description="Heavy dark damage"),
            PhaseAbility("Abyssal Quake", 2, cooldown=3, chance=0.6, description="Ground slam AoE"),
            PhaseAbility("Summon Wraiths", 3, cooldown=4, chance=0.7, description="Summons 2 wraiths"),
            PhaseAbility("Kingmaker", 4, cooldown=6, chance=0.8, description="Double attack"),
        ],
    ),
    "frost_queen": MonsterTemplate(
        key="frost_queen", name="Frost Queen", symbol="F",
        max_hp=700, base_damage=48, xp_given=480, is_boss=True,
        behavior="normal",
        phase_thresholds=[0.70, 0.45],
        abilities=[
            PhaseAbility("Ice Lance", 1, cooldown=2, chance=0.5, description="Ranged ice damage"),
            PhaseAbility("Blizzard", 2, cooldown=4, chance=0.6, description="Floor-wide ice storm"),
            PhaseAbility("Freeze", 3, cooldown=5, chance=0.7, description="Freezes player in place"),
        ],
    ),
    
    # Floor 40 Bosses
    "void_herald": MonsterTemplate(
        key="void_herald", name="Void Herald", symbol="V",
        max_hp=950, base_damage=62, xp_given=700, is_boss=True,
        behavior="normal",
        phase_thresholds=[0.80, 0.60, 0.40, 0.20],
        abilities=[
            PhaseAbility("Void Beam", 1, cooldown=2, chance=0.5, description="Line of void damage"),
            PhaseAbility("Reality Tear", 2, cooldown=3, chance=0.6, description="Tears space, creates void zones"),
            PhaseAbility("Summon Horrors", 3, cooldown=4, chance=0.7, description="Summons eldritch horrors"),
            PhaseAbility("Null Field", 4, cooldown=5, chance=0.7, description="Disables player abilities"),
            PhaseAbility("Collapse", 5, cooldown=8, chance=0.9, description="Collapses reality"),
        ],
    ),
    "dragon_ancient": MonsterTemplate(
        key="dragon_ancient", name="Ancient Dragon", symbol="Δ",
        max_hp=1000, base_damage=65, xp_given=750, is_boss=True,
        behavior="aggressive",
        phase_thresholds=[0.75, 0.50, 0.25],
        abilities=[
            PhaseAbility("Fire Breath", 1, cooldown=3, chance=0.5, description="Cone of fire"),
            PhaseAbility("Tail Swipe", 2, cooldown=2, chance=0.6, description="AoE around dragon"),
            PhaseAbility("Dragon Fury", 3, cooldown=4, chance=0.7, description="Multi-hit attack"),
            PhaseAbility("Apocalypse", 4, cooldown=8, chance=0.8, description="Massive fire storm"),
        ],
    ),
    
    # Floor 50 Final Boss
    "dark_god": MonsterTemplate(
        key="dark_god", name="The Dark God", symbol="Σ",
        max_hp=1500, base_damage=80, xp_given=2000, is_boss=True,
        behavior="aggressive",
        phase_thresholds=[0.80, 0.60, 0.40, 0.20],
        abilities=[
            PhaseAbility("Dark Pulse", 1, cooldown=2, chance=0.5, description="Pulse of dark energy"),
            PhaseAbility("Summon Legion", 2, cooldown=4, chance=0.6, description="Summons demon legion"),
            PhaseAbility("Soul Drain", 3, cooldown=3, chance=0.7, description="Drains player HP"),
            PhaseAbility("Annihilation", 4, cooldown=5, chance=0.8, description="Massive void damage"),
            PhaseAbility("Oblivion", 5, cooldown=10, chance=0.9, description="Near-instant death attack"),
        ],
    ),
}

# Fallback bosses for other floors
FLOOR_BOSS_POOL = [
    MonsterTemplate("boss_cyclops", "Cyclops Warden", "C", 250, 22, 100, is_boss=True,
                   phase_thresholds=[0.50], abilities=[
                       PhaseAbility("Stomp", 1, 3, chance=0.5, description="Ground slam"),
                   ]),
    MonsterTemplate("boss_hydra", "Hydra Matriarch", "H", 280, 24, 110, is_boss=True,
                   phase_thresholds=[0.66, 0.33], abilities=[
                       PhaseAbility("Multi-Head", 1, 2, chance=0.6, description="Multiple attacks"),
                       PhaseAbility("Regenerate", 2, 4, chance=0.5, description="Heals over time"),
                   ]),
    MonsterTemplate("boss_spider", "Giant Spider Queen", "S", 220, 20, 90, is_boss=True,
                   phase_thresholds=[0.60], abilities=[
                       PhaseAbility("Web Trap", 1, 3, chance=0.5, description="Traps player in web"),
                       PhaseAbility("Poison Bite", 1, 2, chance=0.6, description="Heavy poison damage"),
                   ]),
    MonsterTemplate("boss_titan", "Stone Titan", "T", 300, 26, 120, is_boss=True,
                   phase_thresholds=[0.50], abilities=[
                       PhaseAbility("Earthquake", 1, 4, chance=0.5, description="Floor-wide damage"),
                       PhaseAbility("Stone Skin", 1, 5, chance=0.4, description="Reduces damage taken"),
                   ]),
    MonsterTemplate("boss_wraith", "Greater Wraith", "R", 240, 23, 95, is_boss=True,
                   phase_thresholds=[0.60, 0.30], abilities=[
                       PhaseAbility("Life Drain", 1, 2, chance=0.5, description="Drains HP"),
                       PhaseAbility("Shadow Step", 2, 3, chance=0.6, description="Teleports and attacks"),
                   ]),
]


def get_boss_for_floor(floor: int, rng) -> MonsterTemplate:
    """Get appropriate boss for the floor."""
    # Milestone bosses
    if floor == 10:
        return BOSS_DEFINITIONS["iron_golem"] if rng.random() < 0.5 else BOSS_DEFINITIONS["forest_warden"]
    elif floor == 20:
        return BOSS_DEFINITIONS["crystal_lich"] if rng.random() < 0.5 else BOSS_DEFINITIONS["demon_lord"]
    elif floor == 30:
        return BOSS_DEFINITIONS["abyss_king"] if rng.random() < 0.5 else BOSS_DEFINITIONS["frost_queen"]
    elif floor == 40:
        return BOSS_DEFINITIONS["void_herald"] if rng.random() < 0.5 else BOSS_DEFINITIONS["dragon_ancient"]
    elif floor == 50:
        return BOSS_DEFINITIONS["dark_god"]
    
    # Other boss floors (every 5 floors)
    if floor % 5 == 0:
        return rng.choice(FLOOR_BOSS_POOL)
    
    return None  # No boss on non-boss floors


@dataclass
class Trait:
    """Player trait/perk."""
    key: str
    name: str
    description: str
    trait_type: str  # combat, defense, utility, magic
    rank: int  # 1-3
    stat_bonus: Dict[str, float] = field(default_factory=dict)
    ability: str = ""  # Special ability granted


TRAITS = [
    # Combat traits
    Trait("sharp_blade", "Sharpened Blade", "+8% damage", TRAIT_COMBAT, 1, {"damage_mult": 0.08}),
    Trait("keen_edge", "Keen Edge", "+15% damage", TRAIT_COMBAT, 2, {"damage_mult": 0.15}),
    Trait("master_slayer", "Master Slayer", "+25% damage", TRAIT_COMBAT, 3, {"damage_mult": 0.25}),
    
    Trait("swift_strike", "Swift Strike", "+5% attack speed", TRAIT_COMBAT, 1, {"attack_speed": 0.05}),
    Trait("rapid_assault", "Rapid Assault", "+10% attack speed", TRAIT_COMBAT, 2, {"attack_speed": 0.10}),
    
    Trait("critical_eye", "Critical Eye", "+5% crit chance", TRAIT_COMBAT, 1, {"crit_rate": 0.05}),
    Trait("deadly_precision", "Deadly Precision", "+10% crit chance", TRAIT_COMBAT, 2, {"crit_rate": 0.10}),
    Trait("assassin", "Assassin's Instinct", "+20% crit chance, +30% crit damage", TRAIT_COMBAT, 3, 
          {"crit_rate": 0.20, "crit_damage": 0.30}),
    
    # Defense traits
    Trait("iron_skin", "Iron Skin", "+5% damage reduction", TRAIT_DEFENSE, 1, {"resistance_pct": 0.05}),
    Trait("steel_fortress", "Steel Fortress", "+10% damage reduction", TRAIT_DEFENSE, 2, {"resistance_pct": 0.10}),
    Trait("immovable", "Immovable Object", "+18% damage reduction, +15 max HP", TRAIT_DEFENSE, 3, 
          {"resistance_pct": 0.18, "max_hp": 15}),
    
    Trait("vitality", "Vitality", "+10 max HP", TRAIT_DEFENSE, 1, {"max_hp": 10}),
    Trait("endurance", "Endurance", "+25 max HP", TRAIT_DEFENSE, 2, {"max_hp": 25}),
    Trait("titan_fortitude", "Titan's Fortitude", "+50 max HP, +3 HP/turn regen", TRAIT_DEFENSE, 3,
          {"max_hp": 50, "regen": 3}),
    
    # Utility traits
    Trait("lucky_charm", "Lucky Charm", "+5 luck", TRAIT_UTILITY, 1, {"luck": 5}),
    Trait("fortune", "Fortune's Favor", "+12 luck, +3% item rarity", TRAIT_UTILITY, 2, {"luck": 12}),
    Trait("destiny", "Destiny's Child", "+25 luck, +8% item rarity", TRAIT_UTILITY, 3, {"luck": 25, "rarity": 0.08}),
    
    Trait("scout", "Scout", "+2 FOV radius", TRAIT_UTILITY, 1, {"fov_radius": 2}),
    Trait("explorer", "Explorer", "+4 FOV radius, +5% move speed", TRAIT_UTILITY, 2, {"fov_radius": 4}),
    
    Trait("scavenger", "Scavenger", "+20% gold find", TRAIT_UTILITY, 1, {"gold_find": 0.20}),
    Trait("treasure_hunter", "Treasure Hunter", "+40% gold find, +10% item find", TRAIT_UTILITY, 2,
          {"gold_find": 0.40, "item_find": 0.10}),
    
    # Magic traits
    Trait("elemental_touch", "Elemental Touch", "+5 elemental damage", TRAIT_MAGIC, 1, {"elem_damage": 5}),
    Trait("elemental_mastery", "Elemental Mastery", "+12 elemental damage", TRAIT_MAGIC, 2, {"elem_damage": 12}),
    Trait("elemental_lord", "Elemental Lord", "+25 elemental damage, +10% resist all elements", TRAIT_MAGIC, 3,
          {"elem_damage": 25, "elem_resist": 0.10}),
    
    Trait("life_drain", "Life Drain", "+3% lifesteal", TRAIT_MAGIC, 1, {"lifesteal": 0.03}),
    Trait("siphon", "Siphon Essence", "+6% lifesteal", TRAIT_MAGIC, 2, {"lifesteal": 0.06}),
    Trait("vampire_lord", "Vampire Lord", "+12% lifesteal, +5% damage", TRAIT_MAGIC, 3,
          {"lifesteal": 0.12, "damage_mult": 0.05}),
    
    Trait("ward", "Ward", "+5% magic resistance", TRAIT_MAGIC, 1, {"magic_resist": 0.05}),
    Trait("spell_shield", "Spell Shield", "+12% magic resistance", TRAIT_MAGIC, 2, {"magic_resist": 0.12}),
]


@dataclass
class Achievement:
    """Achievement tracking."""
    key: str
    name: str
    description: str
    unlocked: bool = False
    progress: int = 0
    required: int = 1


ACHIEVEMENTS = [
    Achievement("first_blood", "First Blood", "Defeat your first monster"),
    Achievement("boss_slayer", "Boss Slayer", "Defeat 5 bosses", progress=0, required=5),
    Achievement("floor_10", "Dungeon Delver", "Reach floor 10"),
    Achievement("floor_25", "Deep Explorer", "Reach floor 25"),
    Achievement("floor_50", "Champion", "Reach floor 50 and defeat the Dark God"),
    Achievement("legendary_find", "Legendary!", "Find a legendary item"),
    Achievement("artifact_collector", "Artifact Collector", "Collect 4 pieces of an artifact set", progress=0, required=4),
    Achievement("level_20", "Powerful", "Reach level 20"),
    Achievement("level_40", "Mighty", "Reach level 40"),
    Achievement("no_hit_boss", "Untouchable", "Defeat a boss without taking damage"),
    Achievement("speed_run", "Speed Demon", "Complete the game in under 1000 turns", progress=0, required=1000),
    Achievement("monster_hunter", "Monster Hunter", "Defeat 100 monsters", progress=0, required=100),
    Achievement("trait_master", "Trait Master", "Unlock 10 traits", progress=0, required=10),
    Achievement("potion_hoard", "Potion Hoarder", "Have 10 potions in inventory", progress=0, required=10),
]
