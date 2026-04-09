"""Game constants and enumerations."""

# Tile types
TILE_WALL = 1
TILE_FLOOR = 0
TILE_DOOR = 2
TILE_STAIRS_DOWN = 3
TILE_STAIRS_UP = 4
TILE_TRAP = 5
TILE_SHRINE = 6
TILE_MERCHANT = 7
TILE_CHEST = 8
TILE_WATER = 9
TILE_LAVA = 10
TILE_SECRET_DOOR = 11
TILE_SECRET_ROOM = 12
TILE_BOSS_ARENA = 13
TILE_RUNE = 14

# Biome types
BIOME_DUNGEON = "dungeon"
BIOME_FOREST = "forest"
BIOME_CAVE = "cave"
BIOME_HELL = "hell"
BIOME_VOID = "void"
BIOME_FROST = "frost"

BIOME_NAMES = {
    BIOME_DUNGEON: "Dungeon",
    BIOME_FOREST: "Dark Forest",
    BIOME_CAVE: "Crystal Caves",
    BIOME_HELL: "Infernal Depths",
    BIOME_VOID: "The Void",
    BIOME_FROST: "Frozen Wastes",
}

# Rarity tiers
RARITY_COMMON = "common"
RARITY_UNCOMMON = "uncommon"
RARITY_RARE = "rare"
RARITY_EPIC = "epic"
RARITY_LEGENDARY = "legendary"
RARITY_ARTIFACT = "artifact"

RARITY_ORDER = [RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY, RARITY_ARTIFACT]

# Item slots
SLOT_WEAPON = "weapon"
SLOT_ARMOR = "armor"
SLOT_RING = "ring"
SLOT_AMULET = "amulet"
SLOT_POTION = "potion"
SLOT_SCROLL = "scroll"

# Element types
ELEM_PHYSICAL = "physical"
ELEM_FIRE = "fire"
ELEM_ICE = "ice"
ELEM_LIGHTNING = "lightning"
ELEM_POISON = "poison"
ELEM_DARK = "dark"
ELEM_HOLY = "holy"
ELEM_VOID = "void"

ELEMENT_NAMES = {
    ELEM_PHYSICAL: "Physical",
    ELEM_FIRE: "Fire",
    ELEM_ICE: "Ice",
    ELEM_LIGHTNING: "Lightning",
    ELEM_POISON: "Poison",
    ELEM_DARK: "Dark",
    ELEM_HOLY: "Holy",
    ELEM_VOID: "Void",
}

# Status effects
STATUS_POISONED = "poisoned"
STATUS_BURNING = "burning"
STATUS_FROZEN = "frozen"
STATUS_SHOCKED = "shocked"
STATUS_BLEEDING = "bleeding"
STATUS_STUNNED = "stunned"
STATUS_WEAKENED = "weakened"
STATUS_CURSED = "cursed"
STATUS_BLESSED = "blessed"
STATUS_INVISIBLE = "invisible"
STATUS_ENRAGED = "enraged"
STATUS_SHIELDED = "shielded"

# Curses (negative permanent effects until removed)
CURSE_HP_DRAIN = "hp_drain"
CURSE_XP_DRAIN = "xp_drain"
CURSE_BLINDNESS = "blindness"
CURSE_FRAILTY = "frailty"
CURSE_MISFORTUNE = "misfortune"

# Rune types
RUNE_STRENGTH = "rune_str"
RUNE_RESISTANCE = "rune_res"
RUNE_LUCK = "rune_luck"
RUNE_VITALITY = "rune_vit"
RUNE_FIRE = "rune_fire"
RUNE_ICE = "rune_ice"
RUNE_LIGHTNING = "rune_lightning"
RUNE_LIFESTEAL = "rune_lifesteal"
RUNE_CRIT = "rune_crit"
RUNE_SPEED = "rune_speed"

# Trait types
TRAIT_COMBAT = "combat"
TRAIT_DEFENSE = "defense"
TRAIT_UTILITY = "utility"
TRAIT_MAGIC = "magic"

# Game states
STATE_RUNNING = "running"
STATE_DEAD = "dead"
STATE_VICTORIOUS = "victorious"

# Input keys (curses-compatible)
KEY_ESCAPE = 27
KEY_ENTER = 10
KEY_ENTER2 = 13
KEY_SPACE = 32

# Game settings
MAX_TRAIT_RANK = 3
MAX_INVENTORY_SIZE = 30
SAVE_DIR = "saves"
COMBAT_LOG_MAX = 50
DAMAGE_NUMBER_DURATION = 3  # turns to show
