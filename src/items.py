"""Item system with weapons, armor, artifacts, and consumables."""
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from constants import *
from utils import clamp, roll_dice


@dataclass
class Booster:
    """Stat booster from an item."""
    key: str
    value: float
    description: str


@dataclass
class ItemEffect:
    """Special effect on use or equip."""
    trigger: str  # "on_equip", "on_use", "on_hit", "on_kill", "on_damaged"
    effect_type: str  # "heal", "damage", "shield", "teleport", "summon", "buff", "debuff"
    value: float = 0.0
    duration: int = 0
    description: str = ""


@dataclass
class Item:
    """Base item class."""
    name: str
    rarity: str
    slot: str
    glyph: str = "?"
    color_key: str = "white"
    
    # Stats
    strength_points: int = 0
    resistance_points: int = 0
    luck_points: int = 0
    vitality_points: int = 0
    
    # Combat
    base_damage: int = 0
    element: str = ELEM_PHYSICAL
    crit_bonus: float = 0.0
    lifesteal: float = 0.0
    
    # Boosters
    boosters: List[Booster] = field(default_factory=list)
    effects: List[ItemEffect] = field(default_factory=list)
    
    # Consumable
    heal_pct: float = 0.0  # For potions
    consumable: bool = False
    
    # Artifact set
    set_name: Optional[str] = None
    
    # Rune sockets
    rune_sockets: int = 0
    inserted_runes: List['Item'] = field(default_factory=list)
    
    # Enchantment level
    enchant_level: int = 0
    
    # Flavor
    description: str = ""
    
    def is_weapon(self) -> bool:
        return self.slot == SLOT_WEAPON
    
    def is_armor(self) -> bool:
        return self.slot == SLOT_ARMOR
    
    def is_ring(self) -> bool:
        return self.slot == SLOT_RING
    
    def is_amulet(self) -> bool:
        return self.slot == SLOT_AMULET
    
    def is_potion(self) -> bool:
        return self.slot == SLOT_POTION
    
    def is_scroll(self) -> bool:
        return self.slot == SLOT_SCROLL
    
    def is_rune(self) -> bool:
        return self.slot == "rune"
    
    def is_consumable(self) -> bool:
        return self.consumable or self.is_potion() or self.is_scroll()


# ---- Item Generation ----

WEAPON_BASES = [
    ("Dagger", 8, 12, ELEM_PHYSICAL, 0.05),
    ("Short Sword", 10, 16, ELEM_PHYSICAL, 0.0),
    ("Long Sword", 12, 20, ELEM_PHYSICAL, 0.0),
    ("Battle Axe", 14, 22, ELEM_PHYSICAL, 0.0),
    ("War Hammer", 16, 24, ELEM_PHYSICAL, 0.0),
    ("Spear", 11, 19, ELEM_PHYSICAL, 0.0),
    ("Scythe", 15, 25, ELEM_PHYSICAL, 0.0),
    ("Staff", 9, 15, ELEM_PHYSICAL, 0.0),
    ("Bow", 10, 18, ELEM_PHYSICAL, 0.0),
    ("Katana", 13, 21, ELEM_PHYSICAL, 0.08),
    ("Rapier", 10, 17, ELEM_PHYSICAL, 0.10),
    ("Great Sword", 18, 28, ELEM_PHYSICAL, 0.0),
    ("Warhammer", 20, 30, ELEM_PHYSICAL, 0.0),
    ("Halberd", 16, 26, ELEM_PHYSICAL, 0.0),
    ("Flail", 12, 20, ELEM_PHYSICAL, 0.0),
    # Elemental weapons
    ("Flame Blade", 14, 22, ELEM_FIRE, 0.05),
    ("Frost Edge", 12, 20, ELEM_ICE, 0.05),
    ("Storm Bow", 13, 21, ELEM_LIGHTNING, 0.05),
    ("Venom Fang", 11, 19, ELEM_POISON, 0.05),
    ("Shadow Blade", 14, 23, ELEM_DARK, 0.08),
    ("Holy Avenger", 15, 24, ELEM_HOLY, 0.05),
    ("Void Scepter", 13, 22, ELEM_VOID, 0.06),
]

ARMOR_BASES = [
    ("Leather Armor", 2, 4),
    ("Chainmail", 4, 7),
    ("Scale Armor", 5, 9),
    ("Plate Armor", 7, 12),
    ("Cloak", 1, 3),
    ("Robe", 1, 4),
    ("Hide Armor", 3, 5),
    ("Brigandine", 5, 8),
]

ARTIFACT_SETS = {
    "Dragon Slayer": {
        2: [Booster("damage_mult", 0.15, "+15% damage"), Booster("crit_rate", 0.10, "+10% crit")],
        4: [Booster("damage_mult", 0.25, "+25% damage"), Booster("crit_damage", 0.50, "+50% crit damage"), 
            Booster("fire_resist", 0.50, "+50% fire resist")],
    },
    "Void Walker": {
        2: [Booster("damage_mult", 0.10, "+10% damage"), Booster("crit_rate", 0.15, "+15% crit")],
        4: [Booster("void_damage", 10, "+10 void dmg"), Booster("crit_rate", 0.20, "+20% crit"),
            Booster("dodge", 0.15, "+15% dodge")],
    },
    "Frozen Heart": {
        2: [Booster("resistance_pct", 0.10, "-10% dmg taken"), Booster("ice_damage", 8, "+8 ice dmg")],
        4: [Booster("resistance_pct", 0.20, "-20% dmg taken"), Booster("ice_damage", 15, "+15 ice dmg"),
            Booster("freeze_chance", 0.10, "+10% freeze chance")],
    },
    "Inferno Lord": {
        2: [Booster("damage_mult", 0.12, "+12% damage"), Booster("fire_damage", 8, "+8 fire dmg")],
        4: [Booster("damage_mult", 0.20, "+20% damage"), Booster("fire_damage", 15, "+15 fire dmg"),
            Booster("burn_aura", 5, "5 burn aura dmg")],
    },
    "Divine Guardian": {
        2: [Booster("resistance_pct", 0.15, "-15% dmg taken"), Booster("holy_damage", 8, "+8 holy dmg")],
        4: [Booster("resistance_pct", 0.25, "-25% dmg taken"), Booster("holy_damage", 15, "+15 holy dmg"),
            Booster("regen", 3, "+3 HP/turn regen")],
    },
    "Storm Caller": {
        2: [Booster("damage_mult", 0.10, "+10% damage"), Booster("lightning_damage", 8, "+8 lightning dmg")],
        4: [Booster("damage_mult", 0.18, "+18% damage"), Booster("lightning_damage", 15, "+15 lightning dmg"),
            Booster("chain_lightning", 0.20, "20% chain lightning")],
    },
}

RARITY_COLORS = {
    RARITY_COMMON: "white",
    RARITY_UNCOMMON: "green",
    RARITY_RARE: "cyan",
    RARITY_EPIC: "magenta",
    RARITY_LEGENDARY: "yellow",
    RARITY_ARTIFACT: "red",
}

RARITY_GLYPHS = {
    RARITY_COMMON: "?",
    RARITY_UNCOMMON: "?",
    RARITY_RARE: "!",
    RARITY_EPIC: "*",
    RARITY_LEGENDARY: "$",
    RARITY_ARTIFACT: "&",
}


def rarity_roll(luck_points: int, rng: random.Random) -> str:
    """Roll for item rarity based on luck."""
    legendary_w = 1.0 + max(0, luck_points) * 0.3
    epic_w = 8.0
    rare_w = 18.0
    uncommon_w = 35.0
    common_w = 70.0
    
    weights = [common_w, uncommon_w, rare_w, epic_w, legendary_w]
    names = [RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY]
    total = sum(weights)
    roll = rng.random() * total
    acc = 0.0
    for w, name in zip(weights, names):
        acc += w
        if roll <= acc:
            return name
    return RARITY_COMMON


def pick_boosters(rarity: str, slot: str, rng: random.Random) -> List[Booster]:
    """Pick boosters based on rarity."""
    basic_pool = [
        Booster("damage_mult", 0.03, "+3% damage"),
        Booster("resistance_pct", 0.03, "-3% damage taken"),
        Booster("crit_rate", 0.015, "+1.5% crit chance"),
    ]
    balanced_pool = [
        Booster("damage_mult", 0.06, "+6% damage"),
        Booster("resistance_pct", 0.05, "-5% damage taken"),
        Booster("crit_rate", 0.04, "+4% crit chance"),
        Booster("crit_damage", 0.06, "+6% crit damage"),
        Booster("lifesteal", 0.03, "+3% lifesteal"),
    ]
    op_pool = [
        Booster("damage_mult", 0.12, "+12% damage"),
        Booster("resistance_pct", 0.08, "-8% damage taken"),
        Booster("crit_rate", 0.10, "+10% crit chance"),
        Booster("crit_damage", 0.15, "+15% crit damage"),
        Booster("lifesteal", 0.06, "+6% lifesteal"),
        Booster("dodge", 0.05, "+5% dodge"),
    ]
    god_pool = [
        Booster("damage_mult", 0.20, "+20% damage"),
        Booster("resistance_pct", 0.12, "-12% damage taken"),
        Booster("crit_rate", 0.15, "+15% crit chance"),
        Booster("crit_damage", 0.25, "+25% crit damage"),
        Booster("lifesteal", 0.10, "+10% lifesteal"),
        Booster("dodge", 0.10, "+10% dodge"),
        Booster("regen", 2, "+2 HP/turn regen"),
    ]

    if rarity == RARITY_COMMON:
        pool, count = basic_pool, 1
    elif rarity == RARITY_UNCOMMON:
        pool, count = balanced_pool, 1
    elif rarity == RARITY_RARE:
        pool, count = balanced_pool, 2
    elif rarity == RARITY_EPIC:
        pool, count = op_pool, 2
    elif rarity == RARITY_LEGENDARY:
        pool, count = god_pool, 3
    else:
        return []

    rng.shuffle(pool)
    return pool[:count]


def generate_weapon(rng: random.Random, luck_points: int, floor: int = 1) -> Item:
    """Generate a random weapon."""
    base_name, dmg_lo, dmg_hi, element, crit_bonus = rng.choice(WEAPON_BASES)
    rarity = rarity_roll(luck_points, rng)
    
    dmg = rng.randint(dmg_lo, dmg_hi) + floor // 3
    
    strength_pts = rng.randint(1, 3) + floor // 5
    luck_pts = rng.randint(0, 2) if rarity != RARITY_COMMON else 0
    resistance_pts = rng.randint(0, 2) if rarity in [RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY] else 0
    
    if rarity == RARITY_EPIC:
        strength_pts += rng.randint(3, 6)
        luck_pts += rng.randint(2, 4)
        dmg += rng.randint(5, 10)
    elif rarity == RARITY_LEGENDARY:
        strength_pts += rng.randint(8, 14)
        luck_pts += rng.randint(5, 10)
        resistance_pts += rng.randint(4, 8)
        dmg += rng.randint(10, 20)
    
    name_prefixes = {
        RARITY_COMMON: ["Old", "Worn", "Simple"],
        RARITY_UNCOMMON: ["Fine", "Sturdy", "Balanced"],
        RARITY_RARE: ["Enchanted", "Gleaming", "Runed"],
        RARITY_EPIC: ["Crimson", "Ethereal", "Storm", "Void", "Frost"],
        RARITY_LEGENDARY: ["Dragon's", "Godly", "Ancient", "Legendary"],
    }
    
    prefix = rng.choice(name_prefixes.get(rarity, [""]))
    name = f"{prefix} {base_name}" if prefix else base_name
    
    glyph = RARITY_GLYPHS[rarity]
    color_key = RARITY_COLORS[rarity]
    boosters = pick_boosters(rarity, SLOT_WEAPON, rng)
    
    return Item(
        name=name, rarity=rarity, slot=SLOT_WEAPON,
        glyph=glyph, color_key=color_key,
        strength_points=strength_pts, resistance_points=resistance_pts,
        luck_points=luck_pts, base_damage=dmg,
        element=element, crit_bonus=crit_bonus,
        boosters=boosters,
    )


def generate_armor(rng: random.Random, luck_points: int, floor: int = 1) -> Item:
    """Generate random armor."""
    base_name, res_lo, res_hi = rng.choice(ARMOR_BASES)
    rarity = rarity_roll(luck_points, rng)
    
    resistance_pts = rng.randint(res_lo, res_hi) + floor // 3
    vitality_pts = rng.randint(0, 2) + floor // 5
    
    if rarity == RARITY_EPIC:
        resistance_pts += rng.randint(5, 10)
        vitality_pts += rng.randint(3, 6)
    elif rarity == RARITY_LEGENDARY:
        resistance_pts += rng.randint(10, 18)
        vitality_pts += rng.randint(6, 12)
        strength_pts = rng.randint(3, 8)
    
    name_prefixes = {
        RARITY_COMMON: ["Worn", "Old", "Simple"],
        RARITY_UNCOMMON: ["Sturdy", "Reinforced", "Hardened"],
        RARITY_RARE: ["Fortified", "Warded", "Blessed"],
        RARITY_EPIC: ["Aegis", "Thunder", "Night", "Radiant"],
        RARITY_LEGENDARY: ["Dragon's", "Immortal", "Titan's", "Divine"],
    }
    
    prefix = rng.choice(name_prefixes.get(rarity, [""]))
    name = f"{prefix} {base_name}" if prefix else base_name
    
    glyph = RARITY_GLYPHS[rarity]
    color_key = RARITY_COLORS[rarity]
    boosters = pick_boosters(rarity, SLOT_ARMOR, rng)
    
    return Item(
        name=name, rarity=rarity, slot=SLOT_ARMOR,
        glyph=glyph, color_key=color_key,
        resistance_points=resistance_pts, vitality_points=vitality_pts,
        strength_points=strength_pts if rarity == RARITY_LEGENDARY else 0,
        boosters=boosters,
    )


def generate_potion(rng: random.Random) -> Item:
    """Generate a random potion."""
    roll = rng.random()
    if roll < 0.50:
        return Item(name="Minor Health Potion", rarity=RARITY_COMMON, slot=SLOT_POTION,
                   heal_pct=0.25, glyph="!", color_key="green", consumable=True,
                   description="Restores 25% HP")
    elif roll < 0.80:
        return Item(name="Health Potion", rarity=RARITY_UNCOMMON, slot=SLOT_POTION,
                   heal_pct=0.50, glyph="!", color_key="cyan", consumable=True,
                   description="Restores 50% HP")
    elif roll < 0.95:
        return Item(name="Greater Health Potion", rarity=RARITY_RARE, slot=SLOT_POTION,
                   heal_pct=0.75, glyph="!", color_key="magenta", consumable=True,
                   description="Restores 75% HP")
    else:
        return Item(name="Elixir of Life", rarity=RARITY_EPIC, slot=SLOT_POTION,
                   heal_pct=1.0, glyph="!", color_key="yellow", consumable=True,
                   description="Restores 100% HP")


def generate_scroll(rng: random.Random, floor: int = 1) -> Item:
    """Generate a random scroll."""
    scrolls = [
        ("Scroll of Teleportation", "Teleports you to a random floor tile", "teleport"),
        ("Scroll of Identification", "Reveals the entire floor", "reveal"),
        ("Scroll of Enchanting", "Temporarily boosts weapon damage", "enchant"),
        ("Scroll of Protection", "Creates a damage-absorbing shield", "shield"),
        ("Scroll of Rage", "Temporarily increases damage dealt", "rage"),
        ("Scroll of Healing", "Heals status effects and some HP", "cleanse"),
    ]
    
    name, desc, effect_type = rng.choice(scrolls)
    rarity = RARITY_RARE if floor > 10 else RARITY_UNCOMMON
    
    return Item(
        name=name, rarity=rarity, slot=SLOT_SCROLL,
        glyph="~", color_key="cyan", consumable=True,
        description=desc,
        effects=[ItemEffect(trigger="on_use", effect_type=effect_type, 
                           value=5.0 + floor, duration=10 + floor, description=desc)],
    )


def generate_artifact(rng: random.Random, floor: int = 1, set_name: str = None) -> Item:
    """Generate an artifact item."""
    if set_name is None:
        set_name = rng.choice(list(ARTIFACT_SETS.keys()))
    
    set_data = ARTIFACT_SETS[set_name]
    is_weapon = rng.random() < 0.5
    
    if is_weapon:
        base_name = f"{set_name.split()[0]} Blade"
        base_dmg = 25 + floor // 2
        slot = SLOT_WEAPON
    else:
        base_name = f"{set_name.split()[0]} Guard"
        base_dmg = 0
        slot = SLOT_ARMOR
    
    return Item(
        name=f"Artifact: {base_name}", rarity=RARITY_ARTIFACT, slot=slot,
        glyph="&", color_key="red",
        strength_points=10 + floor // 3,
        resistance_points=8 + floor // 3,
        luck_points=5 + floor // 4,
        base_damage=base_dmg,
        set_name=set_name,
        boosters=set_data[2],  # 2-piece bonus always active
        description=f"Part of the {set_name} set. Equip more pieces for bonuses!",
    )


def generate_item(rng: random.Random, luck_points: int, floor: int = 1, force_rarity: str = None) -> Item:
    """Generate a random item (weapon/armor/consumable)."""
    if force_rarity:
        # Override rarity roll
        item = generate_item(rng, luck_points, floor)
        item.rarity = force_rarity
        return item

    roll = rng.random()
    if roll < 0.06:
        return generate_potion(rng)
    elif roll < 0.10:
        return generate_scroll(rng, floor)
    elif roll < 0.13:
        return generate_rune(rng, floor)
    elif roll < 0.50:
        return generate_weapon(rng, luck_points, floor)
    else:
        return generate_armor(rng, luck_points, floor)


def generate_rune(rng: random.Random, floor: int = 1) -> Item:
    """Generate a rune for socketing into equipment."""
    rune_types = [
        (RUNE_STRENGTH, "Rune of Strength", "+3 STR", {"strength_points": 3}),
        (RUNE_RESISTANCE, "Rune of Resistance", "+3 RES", {"resistance_points": 3}),
        (RUNE_LUCK, "Rune of Luck", "+3 LUCK", {"luck_points": 3}),
        (RUNE_VITALITY, "Rune of Vitality", "+20 HP", {"vitality_points": 2}),
        (RUNE_FIRE, "Rune of Fire", "+5 fire dmg", {"fire_damage": 5}),
        (RUNE_ICE, "Rune of Ice", "+5 ice dmg", {"ice_damage": 5}),
        (RUNE_LIGHTNING, "Rune of Lightning", "+5 lightning dmg", {"lightning_damage": 5}),
        (RUNE_LIFESTEAL, "Rune of Life", "+3% lifesteal", {"lifesteal": 0.03}),
        (RUNE_CRIT, "Rune of Critical", "+3% crit", {"crit_rate": 0.03}),
        (RUNE_SPEED, "Rune of Haste", "+2% dmg", {"damage_mult": 0.02}),
    ]
    
    rune_key, name, desc, stats = rng.choice(rune_types)
    
    # Scale with floor
    booster_value = 0.0
    for key, value in stats.items():
        if isinstance(value, float) and value < 1:
            booster_value += value * (1.0 + floor * 0.05)
    
    booster = Booster(rune_key, booster_value if booster_value > 0 else list(stats.values())[0], desc)
    
    return Item(
        name=name, rarity=RARITY_RARE, slot="rune",
        glyph="°", color_key="magenta",
        strength_points=stats.get("strength_points", 0),
        resistance_points=stats.get("resistance_points", 0),
        luck_points=stats.get("luck_points", 0),
        vitality_points=stats.get("vitality_points", 0),
        boosters=[booster],
        description=f"{desc}. Socket into equipment with 'e'.",
        consumable=True,
    )


def generate_bomb(rng: random.Random, floor: int = 1) -> Item:
    """Generate a bomb consumable."""
    dmg = 20 + floor * 3
    return Item(
        name="Fire Bomb", rarity=RARITY_UNCOMMON, slot="consumable",
        glyph="!", color_key="yellow",
        consumable=True,
        description=f"Throws a bomb dealing {dmg} fire damage in area.",
        effects=[ItemEffect(trigger="on_use", effect_type="bomb", value=float(dmg), description=f"Deals {dmg} fire damage")],
    )


def generate_elixir(rng: random.Random, floor: int = 1) -> Item:
    """Generate a temporary stat boost elixir."""
    stat_type = rng.choice(["strength", "resistance", "luck", "damage"])
    duration = 10 + floor // 2
    value = 5 + floor // 3
    
    stat_map = {
        "strength": ("Elixir of Might", "+5 STR for 10 turns", {"strength_points": value}),
        "resistance": ("Elixir of Warding", "+5 RES for 10 turns", {"resistance_points": value}),
        "luck": ("Elixir of Fortune", "+5 LUCK for 10 turns", {"luck_points": value}),
        "damage": ("Elixir of Power", "+10% dmg for 10 turns", {"damage_mult": 0.10}),
    }
    
    name, desc, stats = stat_map[stat_type]
    
    return Item(
        name=name, rarity=RARITY_RARE, slot="consumable",
        glyph="!", color_key="cyan",
        consumable=True,
        description=desc,
        effects=[ItemEffect(trigger="on_use", effect_type="elixir", value=value, duration=duration, description=desc)],
    )


def generate_escape_scroll(rng: random.Random, floor: int = 1) -> Item:
    """Generate escape scroll (teleport to stairs)."""
    return Item(
        name="Scroll of Escape", rarity=RARITY_EPIC, slot=SLOT_SCROLL,
        glyph="~", color_key="yellow",
        consumable=True,
        description="Instantly teleports you to the stairs down.",
        effects=[ItemEffect(trigger="on_use", effect_type="escape", description="Teleport to stairs")],
    )


def generate_identify_scroll(rng: random.Random, floor: int = 1) -> Item:
    """Generate identify scroll."""
    return Item(
        name="Scroll of Identify", rarity=RARITY_UNCOMMON, slot=SLOT_SCROLL,
        glyph="~", color_key="green",
        consumable=True,
        description="Reveals all items on the floor and their stats.",
        effects=[ItemEffect(trigger="on_use", effect_type="identify", description="Reveal all items")],
    )


def generate_enchant_scroll(rng: random.Random, floor: int = 1) -> Item:
    """Generate enchant scroll (adds random booster to item)."""
    return Item(
        name="Scroll of Enchanting", rarity=RARITY_EPIC, slot=SLOT_SCROLL,
        glyph="~", color_key="magenta",
        consumable=True,
        description="Adds a random booster to an equipped item.",
        effects=[ItemEffect(trigger="on_use", effect_type="enchant", description="Enchant equipment")],
    )


def generate_new_consumable(rng: random.Random, floor: int = 1) -> Item:
    """Generate a new type of consumable."""
    roll = rng.random()
    if roll < 0.25:
        return generate_bomb(rng, floor)
    elif roll < 0.45:
        return generate_elixir(rng, floor)
    elif roll < 0.65:
        return generate_escape_scroll(rng, floor)
    elif roll < 0.80:
        return generate_identify_scroll(rng, floor)
    else:
        return generate_enchant_scroll(rng, floor)
