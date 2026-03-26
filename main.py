import curses
import math
import os
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import wave
import struct

try:
    import pygame  # type: ignore
except Exception:
    pygame = None


Vec2 = Tuple[int, int]


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def manhattan(a: Vec2, b: Vec2) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def chebyshev(a: Vec2, b: Vec2) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def in_bounds(x: int, y: int, w: int, h: int) -> bool:
    return 0 <= x < w and 0 <= y < h


def bresenham_line(a: Vec2, b: Vec2) -> List[Vec2]:
    # Integer grid line for LOS checks.
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    pts = []
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return pts


class GameOver(Exception):
    pass


@dataclass
class Booster:
    key: str
    value: float
    description: str


@dataclass
class Item:
    name: str
    rarity: str
    slot: str  # "weapon" or "armor"
    # Stats: these are additive to the player's "points", matching your K panel formulas.
    strength_points: int = 0
    resistance_points: int = 0
    luck_points: int = 0
    # Weapon damage.
    base_damage: int = 0
    # Rare+ boosters.
    boosters: List[Booster] = field(default_factory=list)
    # Flavor / UI char.
    glyph: str = "?"
    color_key: str = "white"

    # Potion heal amount as fraction of max HP (0.25 / 0.50 / 1.0). 0 = not a potion.
    heal_pct: float = 0.0

    def is_weapon(self) -> bool:
        return self.slot == "weapon"

    def is_armor(self) -> bool:
        return self.slot == "armor"

    def is_potion(self) -> bool:
        return self.slot == "potion"


@dataclass
class Status:
    poison_turns: int = 0


@dataclass
class Entity:
    x: int
    y: int
    symbol: str
    name: str
    template_key: str
    max_hp: int
    hp: int
    base_damage: int
    xp_given: int
    is_boss: bool = False
    status: Status = field(default_factory=Status)
    phase: int = 1
    special_cd: int = 0
    # Bestiary accounting
    damage_dealt_total: int = 0
    turns_alive: int = 0

    def pos(self) -> Vec2:
        return (self.x, self.y)


@dataclass
class MonsterTemplate:
    key: str
    name: str
    symbol: str
    max_hp: int
    base_damage: int
    xp_given: int
    is_boss: bool = False


@dataclass
class BestiaryRecord:
    key: str
    name: str
    symbol: str
    hp: int
    xp: int
    defeated_count: int = 0
    total_damage_dealt: int = 0
    total_turns_alive: int = 0

    def dps(self) -> float:
        return self.total_damage_dealt / max(1, self.total_turns_alive)


class DungeonMap:
    def __init__(self, w: int, h: int, rng: random.Random):
        self.w = w
        self.h = h
        self.rng = rng
        self.tiles = [[1 for _ in range(w)] for _ in range(h)]  # 1 wall, 0 floor
        self.explored = [[False for _ in range(w)] for _ in range(h)]
        self.generate()

    def generate(self) -> None:
        self.tiles = [[1 for _ in range(self.w)] for _ in range(self.h)]

        # Room-based generation.
        room_count = self.rng.randint(10, 16)
        rooms: List[Tuple[int, int, int, int]] = []
        for _ in range(room_count):
            rw = self.rng.randint(5, 10)
            rh = self.rng.randint(4, 9)
            rx = self.rng.randint(1, self.w - rw - 2)
            ry = self.rng.randint(1, self.h - rh - 2)

            if any(self._rect_intersects(rx, ry, rw, rh, ox, oy, ow, oh) for (ox, oy, ow, oh) in rooms):
                continue

            self._carve_rect(rx, ry, rw, rh)
            rooms.append((rx, ry, rw, rh))

        if not rooms:
            # Fallback: simple blob.
            cx, cy = self.w // 2, self.h // 2
            for y in range(self.h):
                for x in range(self.w):
                    if (x - cx) ** 2 + (y - cy) ** 2 < (min(self.w, self.h) // 3) ** 2:
                        self.tiles[y][x] = 0
            return

        # Connect rooms with corridors.
        rooms.sort(key=lambda r: r[0] + r[1])
        (x1, y1, _, _) = rooms[0]
        px = x1 + 1
        py = y1 + 1
        for (rx, ry, rw, rh) in rooms[1:]:
            nx = rx + rw // 2
            ny = ry + rh // 2
            self._carve_corridor(px, py, nx, ny)
            px, py = nx, ny

        # Surround with walls (already walls by init, but ensure rooms carve floors).
        for _ in range(2):
            self._smooth_passes()

    def _rect_intersects(self, rx: int, ry: int, rw: int, rh: int, ox: int, oy: int, ow: int, oh: int) -> bool:
        return not (rx + rw + 1 < ox or ox + ow + 1 < rx or ry + rh + 1 < oy or oy + oh + 1 < ry)

    def _carve_rect(self, rx: int, ry: int, rw: int, rh: int) -> None:
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                self.tiles[y][x] = 0

    def _carve_corridor(self, x1: int, y1: int, x2: int, y2: int) -> None:
        # L-shaped corridors with random bend.
        if self.rng.random() < 0.5:
            self._carve_h(x1, x2, y1)
            self._carve_v(y1, y2, x2)
        else:
            self._carve_v(y1, y2, x1)
            self._carve_h(x1, x2, y2)

    def _carve_h(self, x1: int, x2: int, y: int) -> None:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.tiles[y][x] = 0

    def _carve_v(self, y1: int, y2: int, x: int) -> None:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.tiles[y][x] = 0

    def _smooth_passes(self) -> None:
        # Very small smoothing for a more "cave-like" look.
        new_tiles = [row[:] for row in self.tiles]
        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                wall_nei = 0
                for yy in range(y - 1, y + 2):
                    for xx in range(x - 1, x + 2):
                        if xx == x and yy == y:
                            continue
                        if self.tiles[yy][xx] == 1:
                            wall_nei += 1
                # Bias toward floors inside carved area.
                if wall_nei > 6:
                    new_tiles[y][x] = 1
                elif wall_nei < 3:
                    new_tiles[y][x] = 0
        self.tiles = new_tiles

    def is_passable(self, x: int, y: int) -> bool:
        return in_bounds(x, y, self.w, self.h) and self.tiles[y][x] == 0

    def random_floor_cell(self, avoid: Optional[Vec2] = None) -> Vec2:
        # Try random samples then fallback scanning.
        for _ in range(5000):
            x = self.rng.randint(1, self.w - 2)
            y = self.rng.randint(1, self.h - 2)
            if self.is_passable(x, y) and (avoid is None or (x, y) != avoid):
                return (x, y)
        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                if self.is_passable(x, y) and (avoid is None or (x, y) != avoid):
                    return (x, y)
        return (1, 1)

    def compute_fov(self, origin: Vec2, radius: int) -> List[List[bool]]:
        # Simple raycasting-based FOV for speed of implementation:
        # - tiles visible if any line from origin intersects walls at that tile.
        # - works great for turn-based rogue-likes.
        ox, oy = origin
        visible = [[False for _ in range(self.w)] for _ in range(self.h)]
        visible[oy][ox] = True
        r2 = radius * radius

        for y in range(max(0, oy - radius), min(self.h, oy + radius + 1)):
            for x in range(max(0, ox - radius), min(self.w, ox + radius + 1)):
                dx = x - ox
                dy = y - oy
                if dx * dx + dy * dy > r2:
                    continue
                if self._los(origin, (x, y)):
                    visible[y][x] = True
        return visible

    def _los(self, a: Vec2, b: Vec2) -> bool:
        # LOS with Bresenham; walls block sight (but the endpoint can be a wall and still be visible).
        pts = bresenham_line(a, b)
        for i, (x, y) in enumerate(pts):
            if i == 0:
                continue
            if not in_bounds(x, y, self.w, self.h):
                return False
            if self.tiles[y][x] == 1:
                return (x, y) == b
        return True


class AudioSystem:
    """
    Generates simple placeholder .wav files on first run, then plays BGM + SFX via pygame.
    This keeps the project self-contained without needing external sound assets.
    """

    def __init__(self, base_dir: str, log_fn=None):
        self.base_dir = base_dir
        self.log_fn = log_fn or (lambda _msg: None)
        self.audio_dir = os.path.join(self.base_dir, "assets", "audio")
        self.paths = {
            "bgm": os.path.join(self.audio_dir, "bgm.wav"),
            "hit": os.path.join(self.audio_dir, "hit.wav"),
            "crit": os.path.join(self.audio_dir, "crit.wav"),
            "loot": os.path.join(self.audio_dir, "loot.wav"),
            "death": os.path.join(self.audio_dir, "death.wav"),
        }
        self.sfx = {}

    def _ensure_dirs(self) -> None:
        os.makedirs(self.audio_dir, exist_ok=True)

    def _write_wav(self, path: str, samples: List[float], sample_rate: int = 22050) -> None:
        # 16-bit mono PCM.
        import math

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            # Clip and pack.
            out = bytearray()
            for s in samples:
                if s > 1.0:
                    s = 1.0
                elif s < -1.0:
                    s = -1.0
                out += struct.pack("<h", int(s * 32767.0))
            wf.writeframes(bytes(out))

    def _tone(self, freq: float, duration: float, sample_rate: int = 22050, volume: float = 0.4) -> List[float]:
        import math

        n = int(duration * sample_rate)
        if n <= 0:
            return []
        samples: List[float] = []
        fade_in = int(min(n // 10, int(0.02 * sample_rate)))
        fade_out = int(min(n // 10, int(0.05 * sample_rate)))
        for i in range(n):
            t = i / sample_rate
            s = math.sin(2.0 * math.pi * freq * t)
            # Simple ADS envelope.
            env = 1.0
            if i < fade_in:
                env = i / max(1, fade_in)
            elif i > n - fade_out:
                env = (n - i) / max(1, fade_out)
            samples.append(volume * env * s)
        return samples

    def _chord(self, freqs: List[float], duration: float, sample_rate: int = 22050, volume: float = 0.32) -> List[float]:
        import math

        n = int(duration * sample_rate)
        if n <= 0:
            return []
        samples: List[float] = []
        fade_in = int(min(n // 10, int(0.02 * sample_rate)))
        fade_out = int(min(n // 10, int(0.05 * sample_rate)))
        for i in range(n):
            t = i / sample_rate
            s = 0.0
            for f in freqs:
                s += math.sin(2.0 * math.pi * f * t)
            s /= max(1, len(freqs))
            env = 1.0
            if i < fade_in:
                env = i / max(1, fade_in)
            elif i > n - fade_out:
                env = (n - i) / max(1, fade_out)
            samples.append(volume * env * s)
        return samples

    def ensure_assets(self) -> None:
        self._ensure_dirs()
        if all(os.path.exists(p) for p in self.paths.values()):
            return

        self.log_fn("Generating placeholder sound assets...")

        # Background: simple repeating chord progression.
        # Keep it short (loop-friendly) and procedural.
        chord_progression = [
            [220.0, 277.18],  # A and C#
            [261.63, 329.63],  # C and E
            [196.00, 246.94],  # G and B
            [174.61, 220.0],  # F and A
            [220.0, 277.18],
            [261.63, 329.63],
            [293.66, 369.99],  # D and F#
            [246.94, 311.13],  # B and D#
        ]
        bgm_samples: List[float] = []
        for chord in chord_progression:
            bgm_samples.extend(self._chord(chord, duration=1.0))
        bgm_samples = bgm_samples[: int(8.0 * 22050)]
        self._write_wav(self.paths["bgm"], bgm_samples)

        # SFX
        self._write_wav(self.paths["hit"], self._tone(330.0, duration=0.08, volume=0.5))
        self._write_wav(self.paths["crit"], self._tone(660.0, duration=0.10, volume=0.5))
        self._write_wav(self.paths["loot"], self._tone(523.25, duration=0.12, volume=0.45))
        # Death: descending tone.
        death_samples: List[float] = []
        for f in [440.0, 330.0, 220.0]:
            death_samples.extend(self._tone(f, duration=0.10, volume=0.45))
        self._write_wav(self.paths["death"], death_samples)

    def load(self) -> None:
        self.ensure_assets()
        if pygame is None:
            return
        # Music
        pygame.mixer.music.load(self.paths["bgm"])
        # SFX
        for key in ("hit", "crit", "loot", "death"):
            self.sfx[key] = pygame.mixer.Sound(self.paths[key])

    def play_bgm(self, loop: bool = True) -> None:
        if pygame is None:
            return
        loops = -1 if loop else 0
        pygame.mixer.music.play(loops=loops)

    def play_sfx(self, key: str) -> None:
        if pygame is None:
            return
        s = self.sfx.get(key)
        if s is None:
            return
        try:
            s.play()
        except Exception:
            pass


def rarity_roll(luck_points: int, rng: random.Random) -> str:
    # Requested rarity weights:
    # - Base: 1 (legendary), 9 (epic), 20 (rare), 80 (common)
    # - Legendary weight increases by 0.25 per luck point.
    legendary_w = 1.0 + max(0, luck_points) * 0.25
    epic_w = 9.0
    rare_w = 20.0
    common_w = 80.0
    weights = [common_w, rare_w, epic_w, legendary_w]
    names = ["common", "rare", "epic", "legendary"]
    total = max(0.0001, sum(weights))
    roll = rng.random() * total
    acc = 0.0
    for w, name in zip(weights, names):
        acc += w
        if roll <= acc:
            return name
    return "common"


def pick_boosters(rarity: str, rng: random.Random) -> List[Booster]:
    # Requested behavior:
    # - Balanced/basic boosters appear in common and rare.
    # - OP boosters only appear in epic and legendary.
    basic_pool = [
        Booster("damage_mult", 0.03, "+3% damage"),
        Booster("resistance_pct", 0.03, "-3% damage taken"),
        Booster("crit_rate", 0.015, "+1.5% critical chance"),
    ]
    balanced_pool = [
        Booster("damage_mult", 0.06, "+6% damage"),
        Booster("resistance_pct", 0.05, "-5% damage taken"),
        Booster("crit_rate", 0.05, "+5% critical chance"),
        Booster("crit_damage", 0.06, "+6% critical damage"),
    ]
    op_pool = [
        Booster("crit_rate", 0.10, "+10% critical chance"),
        Booster("crit_rate", 0.20, "+20% critical chance"),
        Booster("crit_damage", 0.15, "+15% critical damage"),
        Booster("crit_damage", 0.25, "+25% critical damage"),
        Booster("damage_mult", 0.12, "+12% damage"),
        Booster("damage_mult", 0.20, "+20% damage"),
        Booster("resistance_pct", 0.08, "-8% damage taken"),
        Booster("resistance_pct", 0.10, "-10% damage taken"),
    ]

    if rarity == "common":
        pool = basic_pool
        count = 1
    elif rarity == "rare":
        pool = balanced_pool
        count = 2
    elif rarity == "epic":
        pool = op_pool
        count = 2
    elif rarity == "legendary":
        pool = op_pool
        count = 3
    else:
        return []

    rng.shuffle(pool)
    return pool[:count]


WEAPON_BASES = [
    ("Dagger", "dagger", 8, 12, "weapon", "dagger"),
    ("Sword", "sword", 10, 16, "weapon", "sword"),
    ("Axe", "axe", 12, 18, "weapon", "axe"),
    ("Mace", "mace", 11, 17, "weapon", "mace"),
    ("Spear", "spear", 10, 18, "weapon", "spear"),
    ("Scythe", "scythe", 14, 22, "weapon", "scythe"),
    ("Staff", "staff", 9, 15, "weapon", "staff"),
    ("Bow", "bow", 10, 20, "weapon", "bow"),
    ("Katana", "katana", 13, 21, "weapon", "katana"),
    ("Rapier", "rapier", 10, 18, "weapon", "rapier"),
]

ARMOR_BASES = [
    ("Leather Armor", "armor", 0, 0, "armor", "armor"),
    ("Chainmail", "armor", 0, 0, "armor", "armor"),
    ("Scale Armor", "armor", 0, 0, "armor", "armor"),
    ("Cloak", "armor", 0, 0, "armor", "cloak"),
]

RARITY_GLYPHS = {
    "common": "?",
    "rare": "!",
    "epic": "*",
    "legendary": "$",
}

COLOR_KEYS = ["white", "green", "cyan", "yellow", "magenta", "red"]


def generate_potion(rng: random.Random) -> Item:
    """Return a random health potion. Small is most common, Large is rarest."""
    roll = rng.random()
    if roll < 0.55:
        return Item(name="Small Health Potion",  rarity="rare",      slot="potion", heal_pct=0.25, glyph="+", color_key="green")
    elif roll < 0.85:
        return Item(name="Medium Health Potion", rarity="epic",      slot="potion", heal_pct=0.50, glyph="+", color_key="cyan")
    else:
        return Item(name="Large Health Potion",  rarity="legendary", slot="potion", heal_pct=1.00, glyph="+", color_key="yellow")


def generate_item(rng: random.Random, luck_points: int) -> Item:
    rarity = rarity_roll(luck_points, rng)
    is_weapon = rng.random() < 0.75

    if is_weapon:
        base_name, key, dmg_lo, dmg_hi, slot, glyph_key = rng.choice(WEAPON_BASES)
        dmg = rng.randint(dmg_lo, dmg_hi)

        # Rarity -> stat additions.
        strength_pts = 0
        resistance_pts = 0
        luck_pts = 0
        if rarity == "common":
            strength_pts = rng.choice([0, 1, 2, 3])
            luck_pts = rng.choice([0, 0, 1])
            resistance_pts = rng.choice([0, 0, 1])
        elif rarity == "rare":
            strength_pts = rng.randint(2, 6)
            luck_pts = rng.choice([0, rng.randint(2, 5)])
            resistance_pts = rng.choice([0, rng.randint(1, 3)])
        elif rarity == "epic":
            strength_pts = rng.randint(5, 10)
            luck_pts = rng.randint(4, 9) if rng.random() < 0.7 else rng.randint(2, 5)
            resistance_pts = rng.randint(2, 6) if rng.random() < 0.5 else 0
        else:
            strength_pts = rng.randint(10, 18)
            luck_pts = rng.randint(8, 15) if rng.random() < 0.75 else rng.randint(4, 9)
            resistance_pts = rng.randint(5, 11) if rng.random() < 0.65 else 0

        name_prefix = rng.choice(["Crimson", "Obsidian", "Ethereal", "Verdant", "Storm", "Void", "Frost", "Blazing"])
        name = f"{rarity.title()} {name_prefix} {base_name}"

        glyph = RARITY_GLYPHS[rarity]
        color_key = rng.choice(COLOR_KEYS)
        boosters = pick_boosters(rarity, rng)
        return Item(
            name=name,
            rarity=rarity,
            slot=slot,
            strength_points=strength_pts,
            resistance_points=resistance_pts,
            luck_points=luck_pts,
            base_damage=dmg,
            boosters=boosters,
            glyph=glyph,
            color_key=color_key,
        )

    # Armor
    base_name, _, _, _, slot, _ = rng.choice(ARMOR_BASES)
    resistance_pts = 0
    luck_pts = 0
    strength_pts = 0
    if rarity == "common":
        resistance_pts = rng.randint(1, 4)
        luck_pts = rng.choice([0, 0, 1])
    elif rarity == "rare":
        resistance_pts = rng.randint(4, 8)
        luck_pts = rng.choice([0, rng.randint(2, 4)])
        strength_pts = rng.choice([0, 1, 2, 3])
    elif rarity == "epic":
        resistance_pts = rng.randint(7, 14)
        luck_pts = rng.randint(3, 7) if rng.random() < 0.7 else rng.randint(0, 3)
        strength_pts = rng.randint(0, 6)
    else:
        resistance_pts = rng.randint(12, 20)
        luck_pts = rng.randint(6, 12) if rng.random() < 0.8 else rng.randint(2, 8)
        strength_pts = rng.randint(0, 12)

    name_prefix = rng.choice(["Iron", "Aegis", "Silent", "Gilded", "Thunder", "Night", "Radiant", "Ancient"])
    name = f"{rarity.title()} {name_prefix} {base_name}"

    glyph = RARITY_GLYPHS[rarity]
    color_key = rng.choice(COLOR_KEYS)
    boosters = pick_boosters(rarity, rng)
    return Item(
        name=name,
        rarity=rarity,
        slot=slot,
        strength_points=strength_pts,
        resistance_points=resistance_pts,
        luck_points=luck_pts,
        base_damage=0,
        boosters=boosters,
        glyph=glyph,
        color_key=color_key,
    )


def generate_monsters(depth: int, rng: random.Random, map_w: int, map_h: int) -> List[MonsterTemplate]:
    # Depth lightly scales difficulty.
    # We'll still keep it single-floor, so depth affects counts and stats slightly.
    scale_hp = 1.0 + depth * 0.12
    scale_dmg = 1.0 + depth * 0.08
    scale_xp = 1.0 + depth * 0.10

    templates: List[MonsterTemplate] = [
        MonsterTemplate("slime", "Acid Slime", "s", int(18 * scale_hp), int(4 * scale_dmg), int(6 * scale_xp)),
        MonsterTemplate("goblin", "Goblin", "g", int(28 * scale_hp), int(6 * scale_dmg), int(10 * scale_xp)),
        MonsterTemplate("skeleton", "Skeleton", "k", int(34 * scale_hp), int(7 * scale_dmg), int(12 * scale_xp)),
        MonsterTemplate("bat", "Blood Bat", "b", int(16 * scale_hp), int(5 * scale_dmg), int(7 * scale_xp)),
        MonsterTemplate("orc", "Orc Brute", "o", int(55 * scale_hp), int(10 * scale_dmg), int(18 * scale_xp)),
        MonsterTemplate("imp", "Cinder Imp", "i", int(42 * scale_hp), int(9 * scale_dmg), int(16 * scale_xp)),
        MonsterTemplate("cultist", "Rift Cultist", "c", int(60 * scale_hp), int(11 * scale_dmg), int(20 * scale_xp)),
        MonsterTemplate("wraith", "Wraith", "w", int(48 * scale_hp), int(12 * scale_dmg), int(22 * scale_xp)),
        MonsterTemplate("stone_golem", "Stone Golem", "G", int(85 * scale_hp), int(14 * scale_dmg), int(30 * scale_xp)),
        MonsterTemplate("hunter", "Tangle Hunter", "h", int(40 * scale_hp), int(8 * scale_dmg), int(15 * scale_xp)),
        MonsterTemplate("wyrmling", "Wyrmling", "W", int(75 * scale_hp), int(13 * scale_dmg), int(26 * scale_xp)),
        MonsterTemplate("enforcer", "Dungeon Enforcer", "e", int(70 * scale_hp), int(12 * scale_dmg), int(24 * scale_xp)),
    ]

    bosses: List[MonsterTemplate] = [
        MonsterTemplate("boss_warden", "Forest Warden", "B", int(210 * scale_hp), int(24 * scale_dmg), int(80 * scale_xp), is_boss=True),
        MonsterTemplate("boss_golem", "Crystal Golem", "C", int(240 * scale_hp), int(26 * scale_dmg), int(90 * scale_xp), is_boss=True),
        MonsterTemplate("boss_demon", "Demon Matriarch", "D", int(260 * scale_hp), int(28 * scale_dmg), int(100 * scale_xp), is_boss=True),
    ]

    # Return all templates; later pick spawns.
    return templates + bosses


def format_percent(x: float) -> str:
    return f"{int(round(x * 100))}%"


class RoguelikeGame:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.rng = random.Random(time.time_ns())
        self.map_w = 80
        self.map_h = 26
        self.fov_radius = 12
        self.game_state = "running"  # running | dead

        # Floors
        self.floor = 1
        self.max_floors = 30
        self.stairs_pos: Optional[Vec2] = None

        self.player_class = "adventurer"
        self.unlocked_classes = {
            "adventurer": True,
            "warrior": False,
            "rogue": False,
            "barehand": False,
        }
        # Unlock challenge trackers (per run).
        self.challenge_no_equipment = True
        self.challenge_no_armor = True
        self.challenge_warrior_no_weapon = False
        self.player: Optional[Entity] = None

        self.items_on_ground: List[Tuple[Vec2, Item]] = []
        self.inventory: List[Item] = []
        self.equipped_weapon: Optional[Item] = None
        self.equipped_armor: Optional[Item] = None

        self.monsters: List[Entity] = []
        self.bestiary: Dict[str, BestiaryRecord] = {}

        # Level + upgrade points
        self.level = 1
        self.xp = 0
        self.xp_to_level = 25
        self.upgrade_points = 0

        # Stats (points); your formulas use per-point increments.
        self.str_points = 0
        self.res_points = 0
        self.luck_points = 0
        # Your request says 4 stats, but you only specified 3 formulas.
        # I assume the 4th is "vitality" as max HP scaling.
        self.vit_points = 0

        # Combat derived (updated each action)
        self.base_crit_chance = 0.05  # 5%
        self.crit_damage_mult = 1.5  # crit = +50% dmg
        self.base_damage_no_weapon = 10

        # Input handling
        self.last_move_dir: Vec2 = (1, 0)
        self.message_log: List[str] = []
        self.max_log = 6
        # UI: show enemy HP briefly after you attack.
        self.attack_bar_ticks: int = 0
        self.attack_bar_target: Optional[Tuple[str, int, int]] = None  # (name, cur_hp, max_hp)
        # Player special cooldown (real-time seconds).
        self.special_cooldown_seconds = 30.0
        self.next_special_ready_at = 0.0
        self.skip_monster_turn_once = False

        self._setup_curses()
        # Adapt map size to the current terminal.
        # Leave room for HUD + message log.
        safe_hud = 8
        self.map_w = max(40, min(self.map_w, curses.COLS - 1))
        self.map_h = max(14, min(self.map_h, curses.LINES - safe_hud))

        # Audio system: background + SFX.
        self.audio = None
        self.death_sfx_played = False
        self._init_audio()

    def _init_audio(self) -> None:
        # Create/load audio assets if possible.
        if pygame is None:
            return
        try:
            pygame.mixer.init()
        except Exception:
            return

        self.audio = AudioSystem(
            base_dir=os.path.dirname(os.path.abspath(__file__)),
            log_fn=self.log,
        )
        try:
            self.audio.load()
            self.audio.play_bgm(loop=True)
        except Exception:
            # Fail silently; game should remain playable.
            self.audio = None

    def _sfx(self, key: str) -> None:
        if self.audio is None:
            return
        self.audio.play_sfx(key)

    def floor_enemy_mults(self, floor: int, is_boss: bool) -> Tuple[float, float]:
        # Per your spec, these stack each floor.
        # Normal enemies: +30% HP and +20% DPS per floor.
        # Bosses: +50% HP and +30% DPS per floor.
        f = max(1, floor)
        n = f - 1
        if is_boss:
            return (1.0 * (1.5**n), 1.0 * (1.3**n))
        return (1.0 * (1.3**n), 1.0 * (1.2**n))

    def _setup_curses(self) -> None:
        curses.curs_set(0)
        self.stdscr.keypad(True)
        curses.noecho()
        curses.cbreak()
        try:
            curses.start_color()
            curses.use_default_colors()
            # Basic palette: we'll map our color keys to pairs.
            curses.init_pair(1, curses.COLOR_WHITE, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_CYAN, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            curses.init_pair(5, curses.COLOR_MAGENTA, -1)
            curses.init_pair(6, curses.COLOR_RED, -1)
            curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)
        except Exception:
            pass

    def color_pair(self, key: str) -> int:
        mapping = {"white": 1, "green": 2, "cyan": 3, "yellow": 4, "magenta": 5, "red": 6}
        return mapping.get(key, 1)

    def log(self, msg: str) -> None:
        self.message_log.append(msg)
        if len(self.message_log) > self.max_log:
            self.message_log = self.message_log[-self.max_log :]

    def item_boosters_compact(self, item: Item) -> str:
        if not item.boosters:
            return ""
        # Compact booster text for HUD/log lines.
        parts: List[str] = []
        for b in item.boosters:
            desc = b.description
            if len(desc) > 18:
                desc = desc[:17] + "…"
            parts.append(desc)
        return " | Boosters: " + ", ".join(parts)

    def item_summary_compact(self, item: Item) -> str:
        return f"{item.name} [{item.rarity}]{self.item_boosters_compact(item)}"

    def format_hp_bar(self, cur: int, max_hp: int, width: int = 20) -> str:
        max_hp = max(1, max_hp)
        width = max(4, min(30, width))
        filled = int(round(width * (cur / max_hp)))
        filled = max(0, min(width, filled))
        return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"

    def roll_crit(self) -> bool:
        # Luck: +0.25% critical rate per point.
        _, _, luck_points = self.total_player_stat_points()
        crit_chance = self.base_crit_chance + luck_points * 0.0025
        # Gear boosters may add more.
        crit_chance += self._gear_boost("crit_rate")
        crit_chance = clamp(crit_chance, 0.0, 1.0)
        return self.rng.random() < crit_chance

    def _gear_boost(self, booster_key: str) -> float:
        total = 0.0
        for item in [self.equipped_weapon, self.equipped_armor]:
            if not item:
                continue
            for b in item.boosters:
                if b.key == booster_key:
                    total += b.value
        return total

    def damage_multiplier(self) -> float:
        mult = 1.0
        mult += self._gear_boost("damage_mult")
        # Some boosters give crit damage; separate.
        return mult

    def resistance_multiplier(self) -> float:
        # Resistance: each point reduces dmg by 5%, cap 90%.
        _, res_points, _ = self.total_player_stat_points()
        res_reduction = min(res_points * 0.05, 0.90)
        # Armor boosters provide extra reduction using resistance_pct.
        res_reduction += self._gear_boost("resistance_pct")
        res_reduction = clamp(res_reduction, 0.0, 0.90)
        return 1.0 - res_reduction

    def current_attack_damage(self) -> int:
        weapon_dmg = self.base_damage_no_weapon
        if self.equipped_weapon and self.equipped_weapon.is_weapon():
            weapon_dmg = self.equipped_weapon.base_damage
        # Strength: each point you add gives +0.5% more strength.
        str_points, _, _ = self.total_player_stat_points()
        strength_mult = 1.0 + str_points * 0.005
        # Additive boosters for damage.
        dmg = weapon_dmg * strength_mult * self.damage_multiplier()
        return max(1, int(round(dmg)))

    def current_crit_damage_mult(self) -> float:
        # Base: +50% damage on crit.
        mult = self.crit_damage_mult
        mult += self._gear_boost("crit_damage")
        return max(1.0, mult)

    def max_hp(self) -> int:
        # Base HP scales a little with level; vitality gives more.
        base = 55 + (self.level - 1) * 6
        base += self.vit_points * 10
        return base

    def apply_class_passives_to_spawn(self, template: MonsterTemplate) -> MonsterTemplate:
        if self.player_class == "warrior":
            # Enemies deal more and have more hp.
            return MonsterTemplate(
                key=template.key,
                name=template.name,
                symbol=template.symbol,
                max_hp=int(template.max_hp * 1.25),
                base_damage=int(template.base_damage * 1.15),
                xp_given=int(template.xp_given * 1.05),
                is_boss=template.is_boss,
            )
        if self.player_class == "barehand":
            return MonsterTemplate(
                key=template.key,
                name=template.name,
                symbol=template.symbol,
                max_hp=int(template.max_hp * 3.0),
                base_damage=int(template.base_damage * 2.0),
                xp_given=int(template.xp_given * 2.0),
                is_boss=template.is_boss,
            )
        return template

    def reset_run(self, keep_class: bool = True, carry_equipped: bool = False, carry_inventory: bool = False) -> None:
        self.game_state = "running"
        self.items_on_ground.clear()
        self.death_sfx_played = False
        # Carry items for NG+ if requested.
        carried_weapon = self.equipped_weapon if carry_equipped else None
        carried_armor = self.equipped_armor if carry_equipped else None
        carried_inventory = list(self.inventory) if carry_inventory else []
        if not carry_inventory:
            self.inventory.clear()
        else:
            self.inventory = carried_inventory
        self.equipped_weapon = carried_weapon
        self.equipped_armor = carried_armor
        self.monsters.clear()
        self.bestiary.clear()

        self.level = 1
        self.xp = 0
        self.xp_to_level = 25
        self.upgrade_points = 0

        self.str_points = 0
        self.res_points = 0
        self.luck_points = 0
        self.vit_points = 0
        self.floor = 1
        self.stairs_pos = None
        self.next_special_ready_at = 0.0

        if not keep_class:
            self.player_class = "adventurer"

        self.map = DungeonMap(self.map_w, self.map_h, self.rng)
        # Place player.
        self.player = Entity(0, 0, "@", "You", "player", self.max_hp(), self.max_hp(), 0, 0)
        start = self.map.random_floor_cell()
        self.player.x, self.player.y = start

        # Start loadout only if we are not carrying a NG+ set.
        if not carry_equipped and not carry_inventory:
            self.apply_start_class_loadout()
        else:
            self.log("NG+ active: you kept your items.")

        # Build Floor 1 (reposition on generated map).
        self.start_floor(1, reposition_player=True)

        self.update_player_hp()
        self._recompute_fov()
        self.log(
            "Welcome. Find loot. Survive."
            if self.player_class == "adventurer"
            else f"Class: {self.player_class}. Survive."
        )
        # Initialize challenge flags for this run.
        self.challenge_no_equipment = self.equipped_weapon is None and self.equipped_armor is None
        self.challenge_no_armor = self.equipped_armor is None
        self.challenge_warrior_no_weapon = self.player_class == "warrior" and self.equipped_weapon is None

    def start_floor(self, floor: int, reposition_player: bool = True) -> None:
        assert self.player is not None
        self.floor = max(1, min(self.max_floors, floor))
        self.stairs_pos = None
        self.items_on_ground.clear()
        self.monsters.clear()

        self.map = DungeonMap(self.map_w, self.map_h, self.rng)
        if reposition_player:
            start = self.map.random_floor_cell()
            self.player.x, self.player.y = start

        # Spawn monsters + boss for this floor.
        all_templates = generate_monsters(depth=self.floor, rng=self.rng, map_w=self.map_w, map_h=self.map_h)
        normal_pool = [t for t in all_templates if not t.is_boss]

        # Special bosses on milestone floors.
        if self.floor >= self.max_floors:
            floor_boss = MonsterTemplate("boss_abyss_king", "Abyss King", "Ω", 520, 44, 500, is_boss=True)
        elif self.floor == 20:
            floor_boss = MonsterTemplate("boss_void_lich", "Void Lich", "Λ", 380, 34, 260, is_boss=True)
        elif self.floor == 10:
            floor_boss = MonsterTemplate("boss_iron_colossus", "Iron Colossus", "Π", 320, 28, 170, is_boss=True)
        else:
            floor_boss = self.rng.choice([t for t in all_templates if t.is_boss])

        # Requested difficulty changes:
        # - More enemies than loot
        # - Place enemies spread out (less clustering)

        # Items first: keep them lower than enemy count.
        item_count = int(clamp(10 + self.floor * 0.20, 10, 24))
        item_count += self.rng.randint(0, 2)

        # Enemies: scale gently from early floors so the start isn't overwhelming.
        # Floor 1 spawns ~7, reaching ~21 at floor 10 and capping at 44.
        monster_spawn_count = int(clamp(4 + self.floor * 1.5 + item_count * 0.2, 5, 44))

        # Spread factor: distance between enemy spawns.
        min_dist_between_monsters = 2 if self.floor <= 15 else 2

        for _ in range(monster_spawn_count):
            template = self.rng.choice(normal_pool)
            template = self.apply_class_passives_to_spawn(template)
            template = self.apply_floor_scaling(template)
            self._spawn_monster(template, min_dist_from_others=min_dist_between_monsters)

        boss_template = self.apply_class_passives_to_spawn(floor_boss)
        boss_template = self.apply_floor_scaling(boss_template)
        self._spawn_monster(boss_template, prefer_far_from_player=True)

        # Items on ground (lower than enemy count).
        for _ in range(item_count):
            pos = self.map.random_floor_cell(avoid=self.player.pos())
            _, _, luck_points = self.total_player_stat_points()
            # ~10% chance a floor item is a potion instead of gear.
            if self.rng.random() < 0.10:
                item = generate_potion(self.rng)
            else:
                item = generate_item(self.rng, luck_points=luck_points)
            self.items_on_ground.append((pos, item))

        self.log(f"Floor {self.floor}/{self.max_floors}. Defeat the boss to reveal stairs.")
        self.check_unlocks()

    def apply_floor_scaling(self, template: MonsterTemplate) -> MonsterTemplate:
        hp_mult, dmg_mult = self.floor_enemy_mults(self.floor, template.is_boss)
        # Requested additional difficulty tuning for normal enemies:
        # - HP +10%
        # - DPS nerfed by ~30% (i.e., damage down by 30%)
        if not template.is_boss:
            hp_mult *= 1.10
            dmg_mult *= 0.70
            # Extra damage nerf on early floors so the game isn't unfairly lethal at the start.
            if self.floor == 1:
                dmg_mult *= 0.50   # floor 1: enemies deal ~35% of their base damage
            elif self.floor == 2:
                dmg_mult *= 0.70   # floor 2: ~49%
            elif self.floor == 3:
                dmg_mult *= 0.85   # floor 3: ~60%
        return MonsterTemplate(
            key=template.key,
            name=template.name,
            symbol=template.symbol,
            max_hp=max(1, int(round(template.max_hp * hp_mult))),
            base_damage=max(1, int(round(template.base_damage * dmg_mult))),
            xp_given=max(1, int(round(template.xp_given * (1.0 + 0.08 * (self.floor - 1))))),
            is_boss=template.is_boss,
        )

    def update_player_hp(self) -> None:
        if self.player is None:
            return
        self.player.max_hp = self.max_hp()
        self.player.hp = min(self.player.hp, self.player.max_hp)
        # Keep current hp at least 1 when starting.
        self.player.hp = max(1, self.player.hp)

    def apply_start_class_loadout(self) -> None:
        # Your class modifiers.
        if self.player_class == "adventurer":
            # Start empty so "no equipment" unlock challenge is possible.
            return

        if self.player_class == "warrior":
            self.str_points += 15
            self.res_points += 5
            # Boost crit chance by 15%.
            self.equipped_weapon = Item(
                name="Legendary Great Axe",
                rarity="legendary",
                slot="weapon",
                strength_points=15,
                resistance_points=5,
                luck_points=0,
                base_damage=18,
                boosters=[Booster("crit_rate", 0.15, "+15% critical chance")],
                glyph="$",
                color_key="yellow",
            )
            # Equip and apply stat points via derived calc.
            # (Stat points are already added below as class buff; weapon also contributes)
            # To match "starts with ... gives you +15 strength +5 resistance",
            # we don't double-add: we only count class buff from weapon stats.
            # So reset base points, then rely on equipped item stat additions.
            self.str_points = 0
            self.res_points = 0
            self.inventory = []
            return

        if self.player_class == "rogue":
            self.str_points += 0
            self.res_points += 0
            self.luck_points += 0
            self.equipped_armor = None
            dagger = Item(
                name="Epic Shadow Dagger",
                rarity="epic",
                slot="weapon",
                strength_points=5,
                resistance_points=0,
                luck_points=15,
                base_damage=14,
                boosters=[Booster("crit_rate", 0.35, "+35% critical chance")],
                glyph="*",
                color_key="magenta",
            )
            self.equipped_weapon = dagger
            # Similar to warrior: the item contains the stat boosts; don't double-add.
            self.str_points = 0
            self.res_points = 0
            self.luck_points = 0
            return

        if self.player_class == "barehand":
            self.equipped_weapon = None
            self.equipped_armor = None
            # Bare-handed passive.
            self.str_points += 50
            self.res_points += 20
            return

    def equip_item(self, item: Item) -> bool:
        # Enforce class restrictions.
        if self.player_class == "rogue":
            if item.is_armor():
                self.log("Rogue: cannot equip armor.")
                return False
        if self.player_class == "barehand":
            self.log("Bare-handed: you can't equip anything.")
            return False
        if self.player_class == "warrior":
            # Warrior can equip weapon (including their axe), but keep it simple: allow weapon only.
            if item.is_armor():
                self.log("Warrior: armor is optional (not allowed for this class).")
                return False

        if item.slot == "weapon":
            if self.equipped_weapon:
                self.inventory.append(self.equipped_weapon)
            self.equipped_weapon = item
        elif item.slot == "armor":
            if self.equipped_armor:
                self.inventory.append(self.equipped_armor)
            self.equipped_armor = item
        else:
            return False
        # Remove from inventory if it exists there.
        if item in self.inventory:
            self.inventory.remove(item)
        self.log(f"Equipped: {item.name} ({item.rarity})")
        self.challenge_no_equipment = False
        if item.is_armor():
            self.challenge_no_armor = False
        if self.player_class == "warrior" and item.is_weapon():
            self.challenge_warrior_no_weapon = False
        # Update derived hp etc.
        self.update_player_hp()
        return True

    def unequip_weapon(self) -> None:
        if self.equipped_weapon is None:
            self.log("No weapon equipped.")
            return
        self.inventory.append(self.equipped_weapon)
        self.log(f"Unequipped: {self.equipped_weapon.name}")
        self.equipped_weapon = None
        if self.player_class == "warrior":
            self.challenge_warrior_no_weapon = True

    def unequip_armor(self) -> None:
        if self.equipped_armor is None:
            self.log("No armor equipped.")
            return
        self.inventory.append(self.equipped_armor)
        self.log(f"Unequipped: {self.equipped_armor.name}")
        self.equipped_armor = None

    def _spawn_monster(
        self,
        template: MonsterTemplate,
        prefer_far_from_player: bool = False,
        min_dist_from_others: int = 0,
    ) -> None:
        assert self.player is not None
        avoid = self.player.pos()
        others = [m.pos() for m in self.monsters if m.hp > 0]

        def ok_cell(cx: int, cy: int) -> bool:
            if min_dist_from_others <= 0:
                return True
            for ox, oy in others:
                if chebyshev((cx, cy), (ox, oy)) < min_dist_from_others:
                    return False
            return True

        if not prefer_far_from_player:
            chosen = None
            for _ in range(2000):
                x, y = self.map.random_floor_cell(avoid=avoid)
                if ok_cell(x, y) and (x, y) != avoid:
                    chosen = (x, y)
                    break
            x, y = chosen if chosen else self.map.random_floor_cell(avoid=avoid)
        else:
            # Prefer a tile far from player, but also respect distance from others.
            best = None
            best_d = -1
            for _ in range(5000):
                x, y = self.map.random_floor_cell(avoid=avoid)
                if not ok_cell(x, y) and (x, y) != avoid:
                    continue
                d = manhattan((x, y), avoid)
                if d > best_d:
                    best_d = d
                    best = (x, y)
            x, y = best if best else self.map.random_floor_cell(avoid=avoid)

        max_hp = template.max_hp
        ent = Entity(
            x,
            y,
            template.symbol,
            template.name,
            template.key,
            max_hp,
            max_hp,
            template.base_damage,
            template.xp_given,
            is_boss=template.is_boss,
        )
        self.monsters.append(ent)

    def _recompute_fov(self) -> None:
        assert self.player is not None
        self.fov_visible = self.map.compute_fov(self.player.pos(), self.fov_radius)
        for y in range(self.map_h):
            for x in range(self.map_w):
                if self.fov_visible[y][x]:
                    self.map.explored[y][x] = True

    def get_entities_blocking(self, x: int, y: int) -> bool:
        if not self.map.is_passable(x, y):
            return True
        if self.player and self.player.x == x and self.player.y == y:
            return True
        for m in self.monsters:
            if m.hp > 0 and m.x == x and m.y == y:
                return True
        return False

    def monster_can_see_player(self, m: Entity) -> bool:
        # Use LOS within a short radius, similar to player's FOV but smaller.
        if not self.map.is_passable(m.x, m.y):
            return False
        dist = chebyshev(m.pos(), self.player.pos())  # type: ignore[union-attr]
        if dist > 9:
            return False
        # LOS check.
        return self.map._los(m.pos(), self.player.pos())  # type: ignore[union-attr]

    def step_towards(self, start: Vec2, goal: Vec2) -> Optional[Vec2]:
        # BFS for one step.
        if start == goal:
            return start
        w, h = self.map_w, self.map_h
        q: List[Vec2] = [start]
        prev: Dict[Vec2, Optional[Vec2]] = {start: None}
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        while q:
            cur = q.pop(0)
            cx, cy = cur
            if cur == goal:
                break
            for dx, dy in dirs:
                nx, ny = cx + dx, cy + dy
                if not in_bounds(nx, ny, w, h):
                    continue
                if (nx, ny) in prev:
                    continue
                if self.get_entities_blocking(nx, ny):
                    continue
                if not self.map.is_passable(nx, ny):
                    continue
                prev[(nx, ny)] = cur
                q.append((nx, ny))
        if goal not in prev:
            return None
        # Backtrack to find the next step.
        cur = goal
        while prev.get(cur) is not None and prev[cur] != start:
            cur = prev[cur]  # type: ignore[assignment]
        return cur

    def try_move_player(self, dx: int, dy: int) -> None:
        if self.player is None:
            return
        nx, ny = self.player.x + dx, self.player.y + dy
        if not in_bounds(nx, ny, self.map_w, self.map_h):
            return
        # Attack if monster present.
        for m in self.monsters:
            if m.hp > 0 and m.x == nx and m.y == ny:
                self.player_attack(m)
                return
        if self.map.is_passable(nx, ny) and not self._player_occupied(nx, ny):
            self.player.x, self.player.y = nx, ny
            self.last_move_dir = (dx, dy)
        else:
            self.last_move_dir = (dx, dy)

    def _player_occupied(self, x: int, y: int) -> bool:
        # Only checks for entity occupancy besides player.
        return any(m.hp > 0 and m.x == x and m.y == y for m in self.monsters)

    def player_attack(self, target: Entity, forced_crit: bool = False) -> None:
        assert self.player is not None
        attack_dmg = self.current_attack_damage()
        is_crit = forced_crit or self.roll_crit()
        if is_crit:
            dmg = int(round(attack_dmg * self.current_crit_damage_mult()))
            self.log(f"CRIT! {target.name} takes {dmg}.")
            self._sfx("crit")
        else:
            dmg = attack_dmg
            self.log(f"You hit {target.name} for {dmg}.")
            self._sfx("hit")
        # Apply resistance.
        dmg_to_apply = int(round(dmg * target_resistance_mult(target=None)))
        # For simplicity, monsters currently have no resistance; keep as placeholder.
        dmg_to_apply = dmg
        target.hp -= dmg_to_apply
        # UI: show enemy HP bar briefly after damage is applied.
        self.attack_bar_target = (target.name, max(0, target.hp), target.max_hp)
        self.attack_bar_ticks = 2
        if dmg_to_apply > 0:
            # no tracking for player in bestiary
            pass
        if target.hp <= 0:
            self.monster_died(target)

    def monster_attack(self, attacker: Entity, defender: Entity) -> None:
        dmg = max(1, attacker.base_damage)
        # Player resistance applies.
        mult = self.resistance_multiplier()
        final = max(1, int(round(dmg * mult)))
        defender.hp -= final
        attacker.damage_dealt_total += final
        self.log(f"{attacker.name} hits you for {final}.")
        if defender.hp <= 0 and not self.death_sfx_played:
            self.death_sfx_played = True
            self._sfx("death")

    def monster_died(self, m: Entity) -> None:
        # Record bestiary.
        rec = self.bestiary.get(m.name)
        if rec is None:
            rec = BestiaryRecord(key=m.name, name=m.name, symbol=m.symbol, hp=m.max_hp, xp=m.xp_given)
            self.bestiary[m.name] = rec
        rec.defeated_count += 1
        rec.total_damage_dealt += m.damage_dealt_total
        rec.total_turns_alive += m.turns_alive

        # XP
        assert self.player is not None
        self.gain_xp(m.xp_given)
        self.log(f"{m.name} defeated. XP +{m.xp_given}.")

        # Loot
        drop_roll = self.rng.random()
        if drop_roll < 0.8:
            _, _, luck_points = self.total_player_stat_points()
            # ~8% chance the monster drops a potion instead of gear.
            if self.rng.random() < 0.08:
                loot = generate_potion(self.rng)
            else:
                loot = generate_item(self.rng, luck_points=luck_points)
                # Small chance to drop legendary more frequently for high luck.
                if self.rng.random() < min(0.2, luck_points * 0.01) and loot.rarity != "legendary":
                    loot = generate_item_forced_rarity(self.rng, "legendary", luck_points=luck_points)
            self._place_item_near(m.pos(), loot)

        # Remove from board by setting hp = 0.
        m.hp = 0

        # If this was the boss, spawn stairs.
        if m.is_boss:
            if self.floor >= self.max_floors:
                self.log("The Abyss King falls. The dungeon resets around you...")
                # NG+ loop: restart but keep your items (equipped + inventory).
                self.reset_run(keep_class=True, carry_equipped=True, carry_inventory=True)
                return
            self.spawn_stairs_at(m.pos())
            self.log("A staircase appears! Stand on it and press Shift+. (>) to descend.")

    def spawn_stairs_at(self, pos: Vec2) -> None:
        x, y = pos
        candidates = [
            (x, y),
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
            (x + 1, y + 1),
            (x - 1, y - 1),
            (x + 1, y - 1),
            (x - 1, y + 1),
        ]
        for cx, cy in candidates:
            if self.map.is_passable(cx, cy) and not self._player_occupied(cx, cy):
                self.stairs_pos = (cx, cy)
                return
        self.stairs_pos = self.map.random_floor_cell(avoid=self.player.pos())  # type: ignore[union-attr]

    def _equipped_luck_bonus(self) -> int:
        bonus = 0
        for item in [self.equipped_weapon, self.equipped_armor]:
            if not item:
                continue
            bonus += item.luck_points
        return bonus

    def _place_item_near(self, pos: Vec2, item: Item) -> None:
        x, y = pos
        candidates = [(x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1), (x + 1, y + 1), (x - 1, y - 1)]
        for cx, cy in candidates:
            if self.map.is_passable(cx, cy) and not self._player_occupied(cx, cy) and (self.player.pos() != (cx, cy)):  # type: ignore[union-attr]
                self.items_on_ground.append(((cx, cy), item))
                return
        # fallback: drop on furthest valid tile.
        p = self.map.random_floor_cell(avoid=self.player.pos())  # type: ignore[union-attr]
        self.items_on_ground.append((p, item))

    def gain_xp(self, amount: int) -> None:
        self.xp += amount
        while self.xp >= self.xp_to_level:
            self.xp -= self.xp_to_level
            self.level += 1
            self.upgrade_points += 4
            self.xp_to_level = int(self.xp_to_level * 1.18 + 10)
            self.log(f"Level up! You are now level {self.level}. +4 stat points.")
            # Apply passive stat from equipped items if they exist.
            self.update_player_hp()
            self.check_unlocks()

    def check_unlocks(self) -> None:
        # Warrior: reach level 10 with no equipment at all.
        if (not self.unlocked_classes["warrior"]) and self.level >= 10 and self.challenge_no_equipment:
            self.unlocked_classes["warrior"] = True
            self.log("Class unlocked: Warrior")

        # Rogue: reach level 10 without equipping any armor.
        if (not self.unlocked_classes["rogue"]) and self.level >= 10 and self.challenge_no_armor:
            self.unlocked_classes["rogue"] = True
            self.log("Class unlocked: Rogue")

        # Bare-handed: reach floor 30 with warrior while weaponless.
        if (
            (not self.unlocked_classes["barehand"])
            and self.player_class == "warrior"
            and self.floor >= 30
            and self.challenge_warrior_no_weapon
            and self.equipped_weapon is None
        ):
            self.unlocked_classes["barehand"] = True
            self.log("Class unlocked: Bare-handed")

    def apply_poison_tick(self, ent: Entity) -> None:
        if ent.status.poison_turns > 0:
            ent.hp -= 3
            ent.status.poison_turns -= 1
            if ent.hp <= 0:
                # Handle death outside to keep consistent accounting.
                ent.hp = 0

    def process_monsters_turn(self) -> None:
        assert self.player is not None
        for m in self.monsters:
            if m.hp <= 0:
                continue
            m.turns_alive += 1
            if m.special_cd > 0:
                m.special_cd -= 1
            # Poison tick
            self.apply_poison_tick(m)
            if m.hp <= 0:
                self.monster_died(m)
                continue

            # AI: follow you if they see you.
            sees = self.monster_can_see_player(m)
            if sees:
                # Boss special AI: if it acts specially, skip normal move/attack.
                if m.is_boss:
                    if self.boss_take_action(m):
                        if self.player.hp <= 0:
                            self.game_state = "dead"
                            return
                        continue
                # Move towards player if not adjacent, else attack.
                if chebyshev(m.pos(), self.player.pos()) <= 1:
                    self.monster_attack(m, self.player)
                else:
                    nxt = self.step_towards(m.pos(), self.player.pos())
                    if nxt and not self._player_occupied(nxt[0], nxt[1]):
                        m.x, m.y = nxt
                    # If now adjacent, attack next time.
            else:
                # Wander: small random step if possible.
                dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]
                self.rng.shuffle(dirs)
                for dx, dy in dirs[:3]:
                    nx, ny = m.x + dx, m.y + dy
                    if self.map.is_passable(nx, ny) and not self._player_occupied(nx, ny):
                        m.x, m.y = nx, ny
                        break

            if self.player.hp <= 0:
                self.game_state = "dead"
                return

    def boss_take_action(self, boss: Entity) -> bool:
        # Returns True if the boss used its action (special/attack/move decision).
        assert self.player is not None
        # Phase transitions by HP thresholds.
        hp_pct = boss.hp / max(1, boss.max_hp)
        if boss.template_key == "boss_iron_colossus":
            if hp_pct <= 0.60 and boss.phase == 1:
                boss.phase = 2
                boss.base_damage = int(round(boss.base_damage * 1.15))
                self.log("Iron Colossus enters Phase 2: Overdrive!")
            if hp_pct <= 0.30 and boss.phase == 2:
                boss.phase = 3
                boss.base_damage = int(round(boss.base_damage * 1.20))
                self.log("Iron Colossus enters Phase 3: Meltdown!")
            return self._boss_colossus_ai(boss)

        if boss.template_key == "boss_void_lich":
            if hp_pct <= 0.70 and boss.phase == 1:
                boss.phase = 2
                self.log("Void Lich enters Phase 2: Rift Ritual!")
            if hp_pct <= 0.35 and boss.phase == 2:
                boss.phase = 3
                self.log("Void Lich enters Phase 3: Absolute Darkness!")
            return self._boss_lich_ai(boss)

        if boss.template_key == "boss_abyss_king":
            if hp_pct <= 0.75 and boss.phase == 1:
                boss.phase = 2
                self.log("Abyss King enters Phase 2: Shadow Dominion!")
            if hp_pct <= 0.40 and boss.phase == 2:
                boss.phase = 3
                boss.base_damage = int(round(boss.base_damage * 1.20))
                self.log("Abyss King enters Phase 3: End of Kings!")
            return self._boss_abyss_ai(boss)

        return False

    def _boss_colossus_ai(self, boss: Entity) -> bool:
        # Specials:
        # - Shockwave: AoE around boss (Phase 1+)
        # - Charge: leaps 2 tiles toward player and hits if lands adjacent (Phase 2+)
        # - Furnace Burst: ranged line slam (Phase 3)
        assert self.player is not None
        if boss.special_cd == 0:
            if boss.phase >= 3 and self.rng.random() < 0.55:
                # Furnace burst: if LOS, deal heavy damage.
                if self.map._los(boss.pos(), self.player.pos()):
                    dmg = int(round(boss.base_damage * 1.35))
                    self.log("Iron Colossus unleashes Furnace Burst!")
                    self._boss_deal_player_damage(dmg, boss)
                    boss.special_cd = 3
                    return True
            if boss.phase >= 2 and self.rng.random() < 0.50:
                # Charge: move up to 2 steps toward player ignoring other monsters.
                self.log("Iron Colossus charges!")
                for _ in range(2):
                    step = self._step_towards_ignoring_monsters(boss.pos(), self.player.pos())
                    if step is None:
                        break
                    bx, by = step
                    if self.map.is_passable(bx, by) and not (self.player.x == bx and self.player.y == by):
                        boss.x, boss.y = bx, by
                if chebyshev(boss.pos(), self.player.pos()) <= 1:
                    self.monster_attack(boss, self.player)
                boss.special_cd = 2
                return True
            # Shockwave: AoE around boss.
            self.log("Iron Colossus stomps: Shockwave!")
            for _m in self.monsters:
                pass
            if chebyshev(boss.pos(), self.player.pos()) <= 2:
                dmg = int(round(boss.base_damage * 1.10))
                self._boss_deal_player_damage(dmg, boss)
            boss.special_cd = 2
            return True
        return False

    def _boss_lich_ai(self, boss: Entity) -> bool:
        # Specials:
        # - Void Bolt: ranged damage if LOS (Phase 1+)
        # - Summon: spawns 2 adds (Phase 2+)
        # - Rift Swap: teleports near player (Phase 3)
        assert self.player is not None
        if boss.special_cd == 0:
            if boss.phase >= 3 and self.rng.random() < 0.55:
                # Rift Swap: teleport to a tile 2 away from player.
                self.log("Void Lich bends space: Rift Swap!")
                px, py = self.player.pos()
                candidates = []
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        if dx == 0 and dy == 0:
                            continue
                        x, y = px + dx, py + dy
                        if self.map.is_passable(x, y) and not self._player_occupied(x, y):
                            candidates.append((x, y))
                if candidates:
                    boss.x, boss.y = self.rng.choice(candidates)
                # Immediately cast a bolt.
                if self.map._los(boss.pos(), self.player.pos()):
                    dmg = int(round(boss.base_damage * 1.25))
                    self._boss_deal_player_damage(dmg, boss)
                boss.special_cd = 3
                return True

            if boss.phase >= 2 and self.rng.random() < 0.60:
                # Summon adds.
                self.log("Void Lich summons voidlings!")
                add_template = MonsterTemplate("voidling", "Voidling", "v", max(12, boss.max_hp // 12), max(4, boss.base_damage // 3), max(8, boss.xp_given // 8))
                add_template = self.apply_floor_scaling(add_template)
                for _ in range(2):
                    self._spawn_monster(add_template, prefer_far_from_player=False)
                boss.special_cd = 3
                return True

            # Void Bolt
            if self.map._los(boss.pos(), self.player.pos()):
                self.log("Void Lich casts Void Bolt!")
                dmg = int(round(boss.base_damage * 1.15))
                self._boss_deal_player_damage(dmg, boss)
                # Small curse: poison as a DoT
                self.player.status.poison_turns = max(self.player.status.poison_turns, 6)
                boss.special_cd = 2
                return True
        return False

    def _boss_abyss_ai(self, boss: Entity) -> bool:
        # Specials:
        # - Shadow Rend: cone-ish (adjacent burst) (Phase 1+)
        # - Abyssal Quake: hits around player (Phase 2+)
        # - Kingmaker: double-action (move+attack twice) (Phase 3)
        assert self.player is not None
        if boss.special_cd == 0:
            if boss.phase >= 3 and self.rng.random() < 0.60:
                self.log("Abyss King invokes Kingmaker: two strikes!")
                # First strike: move closer then attack if adjacent.
                step = self._step_towards_ignoring_monsters(boss.pos(), self.player.pos())
                if step and self.map.is_passable(step[0], step[1]) and not (step == self.player.pos()):
                    boss.x, boss.y = step
                if chebyshev(boss.pos(), self.player.pos()) <= 1:
                    self.monster_attack(boss, self.player)
                # Second strike
                if self.player.hp > 0 and chebyshev(boss.pos(), self.player.pos()) <= 1:
                    self.monster_attack(boss, self.player)
                boss.special_cd = 3
                return True

            if boss.phase >= 2 and self.rng.random() < 0.55:
                self.log("Abyss King shatters the ground: Abyssal Quake!")
                px, py = self.player.pos()
                # Damage in radius 1 around player (including player).
                if chebyshev((px, py), self.player.pos()) <= 1:
                    dmg = int(round(boss.base_damage * 1.20))
                    self._boss_deal_player_damage(dmg, boss)
                boss.special_cd = 2
                return True

            # Shadow Rend: if close, heavy hit.
            if chebyshev(boss.pos(), self.player.pos()) <= 2:
                self.log("Abyss King slashes: Shadow Rend!")
                dmg = int(round(boss.base_damage * 1.30))
                self._boss_deal_player_damage(dmg, boss)
                boss.special_cd = 2
                return True
        return False

    def _boss_deal_player_damage(self, raw_dmg: int, boss: Entity) -> None:
        # Apply player resistance in the same way as monster_attack, but with custom damage.
        assert self.player is not None
        mult = self.resistance_multiplier()
        final = max(1, int(round(raw_dmg * mult)))
        self.player.hp -= final
        boss.damage_dealt_total += final
        self.log(f"{boss.name} deals {final} to you.")
        if self.player.hp <= 0 and not self.death_sfx_played:
            self.death_sfx_played = True
            self._sfx("death")

    def _step_towards_ignoring_monsters(self, start: Vec2, goal: Vec2) -> Optional[Vec2]:
        # Like step_towards but ignores monster occupancy (boss can shove through).
        if start == goal:
            return start
        w, h = self.map_w, self.map_h
        q: List[Vec2] = [start]
        prev: Dict[Vec2, Optional[Vec2]] = {start: None}
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        while q:
            cur = q.pop(0)
            cx, cy = cur
            if cur == goal:
                break
            for dx, dy in dirs:
                nx, ny = cx + dx, cy + dy
                if not in_bounds(nx, ny, w, h):
                    continue
                if (nx, ny) in prev:
                    continue
                if not self.map.is_passable(nx, ny):
                    continue
                # Still block on player tile.
                if self.player and (nx, ny) == self.player.pos():
                    continue
                prev[(nx, ny)] = cur
                q.append((nx, ny))
        if goal not in prev:
            return None
        cur = goal
        while prev.get(cur) is not None and prev[cur] != start:
            cur = prev[cur]  # type: ignore[assignment]
        return cur

    def execute_player_special(self) -> None:
        if self.player is None or self.game_state != "running":
            return
        if self.player_class == "adventurer":
            self.log("Adventurer has no special skill.")
            self.skip_monster_turn_once = True
            return
        now = time.time()
        if now < self.next_special_ready_at:
            remaining = int(math.ceil(self.next_special_ready_at - now))
            self.log(f"Special on cooldown: {remaining}s")
            self.skip_monster_turn_once = True
            return
        if self.player_class == "warrior":
            self._special_warrior_spin()
        elif self.player_class == "rogue":
            self._special_rogue_dash()
        elif self.player_class == "barehand":
            self._special_barehand_punch()
        self.next_special_ready_at = time.time() + self.special_cooldown_seconds

    def _select_closest_enemy(self, max_dist: int = 99) -> Optional[Entity]:
        assert self.player is not None
        best = None
        best_d = 10 ** 9
        for m in self.monsters:
            if m.hp <= 0:
                continue
            d = manhattan(self.player.pos(), m.pos())
            if d <= max_dist and d < best_d:
                best_d = d
                best = m
        return best

    def _special_warrior_spin(self) -> None:
        assert self.player is not None
        self.log("Warrior spin! Fury around you.")
        for m in self.monsters:
            if m.hp <= 0:
                continue
            if chebyshev(self.player.pos(), m.pos()) <= 1:
                # High damage: 2.1x base.
                dmg_base = self.current_attack_damage()
                is_crit = self.roll_crit()
                if is_crit:
                    dmg = int(round(dmg_base * 2.1 * self.current_crit_damage_mult()))
                    self.log(f"CRIT SPIN! {m.name} takes {dmg}.")
                else:
                    dmg = int(round(dmg_base * 2.1))
                    self.log(f"{m.name} takes {dmg} from the spin.")
                m.hp -= dmg
                if m.hp <= 0:
                    self.monster_died(m)

    def _special_rogue_dash(self) -> None:
        assert self.player is not None
        dx, dy = self.last_move_dir
        # Normalize direction to -1/0/1
        dx = 0 if dx == 0 else (1 if dx > 0 else -1)
        dy = 0 if dy == 0 else (1 if dy > 0 else -1)
        if dx == 0 and dy == 0:
            dx, dy = (1, 0)

        self.log("Rogue dash: shadow steps forward.")
        # Move 3 tiles, skipping. Track enemies "transpassed" along the path.
        path_tiles: List[Vec2] = []
        curx, cury = self.player.x, self.player.y
        for _ in range(3):
            curx += dx
            cury += dy
            if not in_bounds(curx, cury, self.map_w, self.map_h) or not self.map.is_passable(curx, cury):
                break
            path_tiles.append((curx, cury))

        passed_enemies: List[Entity] = []
        for tx, ty in path_tiles:
            for m in self.monsters:
                if m.hp > 0 and (m.x, m.y) == (tx, ty):
                    passed_enemies.append(m)

        # Teleport to final valid tile.
        if path_tiles:
            self.player.x, self.player.y = path_tiles[-1]

        # Apply effects.
        for m in passed_enemies:
            # Transpassed ability:
            hp_pct = m.hp / max(1, m.max_hp)
            if hp_pct < 0.50:
                self.log(f"{m.name} gets executed by the dash!")
                m.hp = 0
                self.monster_died(m)
            else:
                # Poison: -3hp for 20 seconds (turns). We'll interpret as 20 turns.
                m.status.poison_turns = max(m.status.poison_turns, 20)
                self.log(f"{m.name} is poisoned by shadow!")

    def _special_barehand_punch(self) -> None:
        assert self.player is not None
        target = self._select_closest_enemy(max_dist=99)
        if not target:
            self.log("Punch whiffs. No targets.")
            return
        self.log(f"Bare-handed punch! {target.name} is targeted.")
        # 100% critical.
        self.player_attack(target, forced_crit=True)

    def total_player_stat_points(self) -> Tuple[int, int, int]:
        # Base points + equipment points.
        eq_str = self.equipped_weapon.strength_points if self.equipped_weapon else 0
        eq_res = (self.equipped_weapon.resistance_points if self.equipped_weapon else 0) + (self.equipped_armor.resistance_points if self.equipped_armor else 0)
        eq_luck = (self.equipped_weapon.luck_points if self.equipped_weapon else 0) + (self.equipped_armor.luck_points if self.equipped_armor else 0)
        return self.str_points + eq_str, self.res_points + eq_res, self.luck_points + eq_luck

    def sync_stats_from_equipment(self) -> None:
        # Keep self.str_points/res_points/luck_points as "spent points" plus class passives.
        # Equipment points are applied through derived stat math by temporarily folding them in.
        # For simplicity in this single-file code, we directly fold equipment points into base points
        # at the time we render derived stats. We'll instead maintain these as spent and compute on demand.
        pass

    # ---- UI helpers ----
    def draw(self) -> None:
        self.stdscr.erase()

        # Fold in equipment points for display; combat math reads total stats directly.
        base_str, base_res, base_luck = self.total_player_stat_points()

        # Recompute FOV each frame (cheap enough).
        self._recompute_fov()

        # Draw tiles and entities.
        for y in range(self.map_h):
            for x in range(self.map_w):
                if self.fov_visible[y][x]:
                    self.map.explored[y][x] = True
                ch = " "
                if self.map.explored[y][x]:
                    if self.map.tiles[y][x] == 1:
                        ch = "#"
                    else:
                        ch = "."
                if not self.fov_visible[y][x]:
                    if ch == ".":
                        ch = "·"
                    elif ch == "#":
                        ch = "#"
                if self.fov_visible[y][x]:
                    if self.map.tiles[y][x] == 1:
                        ch = "#"
                    else:
                        ch = "."
                if self.fov_visible[y][x]:
                    if (x, y) == self.player.pos():  # type: ignore[union-attr]
                        ch = "@"
                self.stdscr.addch(y, x, ch)

        # Items
        for (pos, item) in self.items_on_ground:
            x, y = pos
            if self.fov_visible[y][x]:
                self.stdscr.addch(y, x, item.glyph, curses.color_pair(self.color_pair(item.color_key)))

        # Monsters
        for m in self.monsters:
            if m.hp <= 0:
                continue
            if self.fov_visible[m.y][m.x]:
                self.stdscr.addch(m.y, m.x, m.symbol)

        # Stairs
        if self.stairs_pos is not None:
            sx, sy = self.stairs_pos
            if self.fov_visible[sy][sx]:
                self.stdscr.addch(sy, sx, ">", curses.A_BOLD)

        # HUD
        p = self.player
        assert p is not None
        hud_y = self.map_h + 1
        # curses screen may be smaller; guard.
        if hud_y < curses.LINES - 1:
            self.stdscr.addstr(
                hud_y,
                0,
                f"Floor {self.floor}/{self.max_floors}  Lvl {self.level}  XP {self.xp}/{self.xp_to_level}  Upg {self.upgrade_points}  Class {self.player_class}",
            )
        if hud_y + 1 < curses.LINES - 1:
            crit_chance = clamp(self.base_crit_chance + base_luck * 0.0025 + self._gear_boost("crit_rate"), 0.0, 1.0)
            self.stdscr.addstr(hud_y + 1, 0, f"HP {max(0, p.hp)}/{p.max_hp}  STR {base_str}  RES {base_res}  LUCK {base_luck}  Crit {format_percent(crit_chance)}")

        # Enemy HP bar (after your attack).
        health_line_y = hud_y + 2
        if self.attack_bar_ticks > 0 and health_line_y < curses.LINES - 1 and self.attack_bar_target:
            name, cur_hp, max_hp = self.attack_bar_target
            bar = self.format_hp_bar(cur_hp, max_hp, width=min(24, curses.COLS - 22))
            msg = f"Target HP: {name} {bar} {cur_hp}/{max_hp}"
            self.stdscr.addstr(health_line_y, 0, msg[: curses.COLS - 1])
        elif health_line_y < curses.LINES - 1:
            # Show live rarity weights/percentages based on current LUCK.
            luck_points = base_luck
            legendary_w = 1.0 + max(0.0, luck_points) * 0.25
            epic_w = 9.0
            rare_w = 20.0
            common_w = 80.0
            total = max(0.0001, common_w + rare_w + epic_w + legendary_w)
            common_pct = 100.0 * common_w / total
            rare_pct = 100.0 * rare_w / total
            epic_pct = 100.0 * epic_w / total
            legendary_pct = 100.0 * legendary_w / total
            msg = (
                f"Rarity% (LUCK={base_luck}): "
                f"C{common_pct:.1f} R{rare_pct:.1f} E{epic_pct:.1f} L{legendary_pct:.1f}"
            )
            self.stdscr.addstr(health_line_y, 0, msg[: curses.COLS - 1])

        # Item under your feet label (next to the logs).
        log_y = hud_y + 3
        side_width = min(46, curses.COLS - 2)
        side_x = max(0, curses.COLS - side_width - 1)
        item_here = None
        for (pos, it) in self.items_on_ground:
            if pos == self.player.pos():
                item_here = it
                break
        item_here_text = "(none)" if item_here is None else self.item_summary_compact(item_here)
        if log_y < curses.LINES - 1:
            self.stdscr.addstr(log_y, side_x, f"ITEM: {item_here_text}"[: curses.COLS - side_x - 1])

        # Message log (left column).
        for i, msg in enumerate(self.message_log[-self.max_log :]):
            yy = log_y + i
            if yy >= curses.LINES - 1:
                continue
            # Keep logs from overwriting the side label on the first row.
            if yy == log_y:
                self.stdscr.addstr(yy, 0, msg[: max(0, side_x - 2)])
            else:
                self.stdscr.addstr(yy, 0, msg[: curses.COLS - 1])

        # Decay attack bar ticks.
        if self.attack_bar_ticks > 0:
            self.attack_bar_ticks -= 1
            if self.attack_bar_ticks <= 0:
                self.attack_bar_target = None

        self.stdscr.refresh()

    def show_overlay(self, title: str, lines: List[str], extra_instructions: str = "") -> None:
        # Full-screen-ish panel centered.
        h, w = curses.LINES, curses.COLS
        panel_w = min(w - 4, 78)
        panel_h = min(h - 4, len(lines) + (2 if extra_instructions else 1) + 2)
        panel_x = max(1, (w - panel_w) // 2)
        panel_y = max(1, (h - panel_h) // 2)

        # Draw border
        win = curses.newwin(panel_h, panel_w, panel_y, panel_x)
        win.keypad(True)
        win.box()
        win.addstr(1, 2, title[: panel_w - 4], curses.A_BOLD)

        # Content
        max_content = panel_h - 4
        start = 0
        while True:
            win.erase()
            win.box()
            win.addstr(1, 2, title[: panel_w - 4], curses.A_BOLD)
            start = max(0, min(start, max(0, len(lines) - max_content)))
            for i in range(max_content):
                idx = start + i
                if idx >= len(lines):
                    break
                win.addstr(2 + i, 2, lines[idx][: panel_w - 4])
            if extra_instructions:
                win.addstr(panel_h - 2, 2, extra_instructions[: panel_w - 4])
            win.refresh()

            ch = win.getch()
            if ch in (27, ord("q"), ord("Q")):
                return
            if ch in (curses.KEY_UP, ord("k")):
                start -= 1
            elif ch in (curses.KEY_DOWN, ord("j")):
                start += 1
            elif ch in (curses.KEY_NPAGE,):
                start += max_content
            elif ch in (curses.KEY_PPAGE,):
                start -= max_content
            elif ch in (10, 13) and panel_h <= len(lines) + 4:
                # If short, Enter closes too.
                return

    def menu_select(self, title: str, options: List[str], default_index: int = 0) -> Optional[int]:
        # Up/down to move, Enter to select, Esc to cancel.
        if not options:
            return None
        h, w = curses.LINES, curses.COLS
        panel_w = min(w - 4, 78)
        panel_h = min(h - 4, max(10, min(len(options) + 6, h - 4)))
        panel_x = max(1, (w - panel_w) // 2)
        panel_y = max(1, (h - panel_h) // 2)
        win = curses.newwin(panel_h, panel_w, panel_y, panel_x)
        win.keypad(True)

        max_visible = panel_h - 6
        idx = clamp(default_index, 0, len(options) - 1)
        start = max(0, idx - max_visible // 2)
        while True:
            win.erase()
            win.box()
            win.addstr(1, 2, title[: panel_w - 4], curses.A_BOLD)
            start = max(0, min(start, max(0, len(options) - max_visible)))
            # Render visible options
            for i in range(max_visible):
                opt_i = start + i
                if opt_i >= len(options):
                    break
                prefix = ">" if opt_i == idx else " "
                text = options[opt_i][: panel_w - 6]
                win.addstr(2 + i, 2, f"{prefix} {text}")
            win.addstr(panel_h - 2, 2, "Enter=Select  Esc=Cancel")
            win.refresh()
            ch = win.getch()
            if ch in (27,):
                return None
            if ch in (10, 13):
                return idx
            if ch == curses.KEY_UP or ch == ord("k"):
                idx -= 1
                if idx < 0:
                    idx = 0
                start = max(0, idx - max_visible // 2)
            elif ch == curses.KEY_DOWN or ch == ord("j"):
                idx += 1
                if idx > len(options) - 1:
                    idx = len(options) - 1
                start = max(0, idx - max_visible // 2)
            elif ch == curses.KEY_PPAGE:
                idx -= max_visible
                if idx < 0:
                    idx = 0
                start = max(0, idx - max_visible // 2)
            elif ch == curses.KEY_NPAGE:
                idx += max_visible
                if idx > len(options) - 1:
                    idx = len(options) - 1
                start = max(0, idx - max_visible // 2)

    def open_equipment(self) -> None:
        lines: List[str] = []
        lines.append(f"Class: {self.player_class}")
        lines.append("")

        if self.equipped_weapon:
            it = self.equipped_weapon
            lines.append(f"WEP: {it.name} [{it.rarity}]")
            lines.append(f"  Stats: +{it.strength_points} STR  +{it.resistance_points} RES  +{it.luck_points} LUCK")
            if it.base_damage:
                lines.append(f"  Base Damage: {it.base_damage}")
            if it.boosters:
                lines.append("  Boosters:")
                for b in it.boosters:
                    lines.append(f"    - {b.description}")
        else:
            lines.append("WEP: (none)")

        if self.equipped_armor:
            it = self.equipped_armor
            lines.append(f"ARM: {it.name} [{it.rarity}]")
            lines.append(f"  Stats: +{it.strength_points} STR  +{it.resistance_points} RES  +{it.luck_points} LUCK")
            if it.boosters:
                lines.append("  Boosters:")
                for b in it.boosters:
                    lines.append(f"    - {b.description}")
        else:
            lines.append("ARM: (none)")

        self.show_overlay("Equipped (C)", lines, "Esc to close")

    def open_inventory(self) -> None:
        if self.player is None:
            return
        while True:
            inv = list(self.inventory)
            equip_lines = []
            for i, it in enumerate(inv):
                if it.is_potion():
                    equip_lines.append(f"{i+1}. {it.name} [{it.rarity}] (Heals {int(it.heal_pct*100)}% HP) [USE]")
                else:
                    extra = []
                    if it.slot == "weapon":
                        extra.append(f"dmg {it.base_damage}")
                    extra.append(f"+{it.strength_points} STR")
                    extra.append(f"+{it.resistance_points} RES")
                    extra.append(f"+{it.luck_points} LUCK")
                    boosters = ""
                    if it.boosters:
                        boosters = f" | {len(it.boosters)} boosters"
                    equip_lines.append(f"{i+1}. {it.name} [{it.rarity}] ({' '.join(extra)}){boosters}")

            if not inv:
                self.show_overlay("Inventory (I)", ["(empty)"], "Esc to close")
                return

            choice_idx = self.menu_select("Inventory (I): Enter to equip/use", equip_lines, default_index=0)
            if choice_idx is None:
                return
            it = inv[choice_idx]
            if it.is_potion():
                self._use_potion(it)
                return
            ok = self.equip_item(it)
            if not ok:
                continue
            self.update_player_hp()
            return

    def _use_potion(self, item: Item) -> None:
        assert self.player is not None
        if item not in self.inventory:
            return
        heal_amount = int(round(self.max_hp() * item.heal_pct))
        before = self.player.hp
        self.player.hp = min(self.player.max_hp, self.player.hp + heal_amount)
        healed = self.player.hp - before
        self.inventory.remove(item)
        self.log(f"Used {item.name}. Restored {healed} HP. ({self.player.hp}/{self.player.max_hp})")
        self._sfx("loot")



    def open_stats_panel(self) -> None:
        while True:
            # Fold equipment points into calculations.
            base_str, base_res, base_luck = self.total_player_stat_points()
            strength_mult = 1.0 + base_str * 0.005
            res_reduction = min(base_res * 0.05, 0.90)
            luck_mult = 1.0 + base_luck * 0.0015
            crit_chance = clamp(
                self.base_crit_chance + base_luck * 0.0025 + self._gear_boost("crit_rate"),
                0.0,
                1.0,
            )

            options = [
                f"Strength (+1) | STR={base_str} => x{strength_mult:.3f}",
                f"Resistance (+1) | RES={base_res} => {format_percent(res_reduction)} dmg reduction (cap 90%)",
                f"Luck (+1) | LUCK={base_luck} => crit {format_percent(crit_chance)} | luck x{luck_mult:.3f}",
                f"Vitality (+1) | VIT={self.vit_points} => +{(self.vit_points + 1) * 10} max HP (assumption)",
                "Cancel",
            ]
            sel = self.menu_select(f"Stats (K) - Spend points | Points: {self.upgrade_points}", options, default_index=0)
            if sel is None:
                return
            if sel == 4:
                return
            if self.upgrade_points <= 0:
                self.log("No upgrade points left.")
                return
            if sel == 0:
                self.str_points += 1
            elif sel == 1:
                self.res_points += 1
            elif sel == 2:
                self.luck_points += 1
            elif sel == 3:
                self.vit_points += 1
            self.upgrade_points -= 1
            self.update_player_hp()
            self.log("Stats upgraded.")
            # Allow spending multiple points in one panel.
            if self.upgrade_points <= 0:
                return

    def pick_up_items(self) -> None:
        # Items are picked by standing on them, or pressing G to grab one adjacent item.
        assert self.player is not None
        px, py = self.player.pos()
        to_take: List[Tuple[int, int, Item]] = []
        # First: current tile (pick all).
        for i, (pos, item) in enumerate(self.items_on_ground):
            if pos == (px, py):
                to_take.append((i, pos[1], item))
        if to_take:
            taken = 0
            # Take by collecting indices then deleting after.
            indices = [idx for idx, _, _ in to_take]
            for _, _, item in to_take:
                self.inventory.append(item)
                taken += 1
            self.items_on_ground = [pair for j, pair in enumerate(self.items_on_ground) if j not in set(indices)]
            # Log the exact item(s) picked up (name + rarity + boosters).
            for _, _, item in to_take:
                self.log(f"Picked up: {self.item_summary_compact(item)}")
            self._sfx("loot")
            return

        # Adjacent: take first item found (4-dir).
        candidates = [(px, py), (px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)]
        for cx, cy in candidates[1:]:
            for pos, item in list(self.items_on_ground):
                if pos == (cx, cy):
                    self.inventory.append(item)
                    self.items_on_ground = [pair for pair in self.items_on_ground if pair != (pos, item)]
                    self.log(f"Picked up: {self.item_summary_compact(item)}")
                    self._sfx("loot")
                    return

        self.log("Nothing to pick up here.")

    def open_bestiary(self) -> None:
        if not self.bestiary:
            self.show_overlay("Bestiary (B)", ["(defeat monsters to fill this list)"], "Esc to close")
            return
        records = list(self.bestiary.values())
        records.sort(key=lambda r: r.xp, reverse=True)
        lines: List[str] = []
        for r in records:
            lines.append(f"{r.name} [{r.symbol}]")
            lines.append(f"  Defeated: {r.defeated_count}")
            lines.append(f"  HP: {r.hp}")
            lines.append(f"  XP: {r.xp}")
            lines.append(f"  DPS dealt: {r.dps():.2f}")
            lines.append("")
        self.show_overlay("Bestiary (B)", lines, "Esc to close")

    def open_help_panel(self) -> None:
        lines = [
            "Move: arrows / WASD",
            "Pick up: G",
            "Descend stairs: Shift+. (>) while standing on stairs",
            "Unequip weapon/armor: R / T",
            "",
            "I: Inventory",
            "C: Equipped",
            "K: Stats (upgrade points)",
            "B: Bestiary (defeated enemies)",
            "U: Class special attack",
            "",
            "Esc: close panels",
            "Enter: close menu / restart after death",
            "Q: quit",
        ]
        self.show_overlay("Help", lines, "Esc to close")

    def draw_death_screen(self) -> None:
        self.stdscr.erase()
        mid_y = curses.LINES // 2
        msg1 = "YOU DIED"
        msg2 = "Press Enter to restart, or Q to quit."
        self.stdscr.addstr(mid_y - 2, max(0, (curses.COLS - len(msg1)) // 2), msg1, curses.A_BOLD)
        self.stdscr.addstr(mid_y, max(0, (curses.COLS - len(msg2)) // 2), msg2)
        self.stdscr.refresh()

    def choose_class_screen(self) -> None:
        options = [
            ("adventurer", "1) Adventurer - balanced starter"),
            ("warrior", "2) Warrior - Legendary Great Axe, +15 STR +5 RES, +15% crit; enemies stronger; U=Spin"),
            ("rogue", "3) Rogue - Epic Dagger, +5 STR +15 LUCK, +35% crit; U=Shadow Dash + poison/execute"),
            ("barehand", "4) Bare-handed - +50 STR +20 RES; enemies x2 dmg/x2 xp and x3 hp; U=Auto-aim critical punch"),
        ]
        sel = 0
        while True:
            self.stdscr.erase()
            self.stdscr.addstr(2, 2, "Terminal Roguelike", curses.A_BOLD)
            self.stdscr.addstr(4, 2, "Choose a class:")
            for i, (key, opt) in enumerate(options):
                prefix = ">" if i == sel else " "
                lock = "" if self.unlocked_classes.get(key, False) else " [LOCKED]"
                self.stdscr.addstr(6 + i * 2, 4, f"{prefix} {opt}{lock}")
            self.stdscr.addstr(6 + len(options) * 2, 4, "Unlocks: Warrior(L10 no equipment), Rogue(L10 no armor), Bare-handed(F30 Warrior weaponless)")
            self.stdscr.addstr(8 + len(options) * 2, 4, "Enter to confirm. Esc to quit.")
            self.stdscr.refresh()
            ch = self.stdscr.getch()
            if ch in (27, ord("q"), ord("Q")):
                raise GameOver()
            if ch in (curses.KEY_UP, ord("k")):
                sel = max(0, sel - 1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                sel = min(len(options) - 1, sel + 1)
            elif ch in (10, 13):
                key, _ = options[sel]
                if not self.unlocked_classes.get(key, False):
                    continue
                self.player_class = key
                return

    def run(self) -> None:
        try:
            self.choose_class_screen()
            self.reset_run(keep_class=True)
            while True:
                self.skip_monster_turn_once = False
                if self.game_state == "dead":
                    self.draw_death_screen()
                    ch = self.stdscr.getch()
                    if ch in (ord("q"), ord("Q")):
                        return
                    if ch in (10, 13):
                        # Restart from the beginning with a new map + randomized items/monsters.
                        self.reset_run(keep_class=True)
                        continue
                    continue

                self.draw()
                ch = self.stdscr.getch()
                if ch in (ord("q"), ord("Q")):
                    return
                if ch in (ord("h"),):
                    self.try_move_player(-1, 0)
                elif ch in (ord("l"),):
                    self.try_move_player(1, 0)
                elif ch in (ord("a"), ord("A")):
                    self.try_move_player(-1, 0)
                elif ch in (ord("d"), ord("D")):
                    self.try_move_player(1, 0)
                elif ch in (ord("j"),):
                    self.try_move_player(0, 1)
                elif ch in (ord("w"), ord("W")):
                    self.try_move_player(0, -1)
                elif ch in (ord("s"), ord("S")):
                    self.try_move_player(0, 1)
                elif ch == curses.KEY_LEFT:
                    self.try_move_player(-1, 0)
                elif ch == curses.KEY_RIGHT:
                    self.try_move_player(1, 0)
                elif ch == curses.KEY_UP:
                    self.try_move_player(0, -1)
                elif ch == curses.KEY_DOWN:
                    self.try_move_player(0, 1)
                elif ch in (ord("i"), ord("I")):
                    self.open_inventory()
                elif ch in (ord("c"), ord("C")):
                    self.open_equipment()
                elif ch in (ord("k"), ord("K")):
                    self.open_stats_panel()
                elif ch in (ord("b"), ord("B")):
                    self.open_bestiary()
                elif ch in (ord("u"), ord("U")):
                    self.execute_player_special()
                elif ch in (ord("g"), ord("G")):
                    self.pick_up_items()
                elif ch in (ord("r"), ord("R")):
                    self.unequip_weapon()
                elif ch in (ord("t"), ord("T")):
                    self.unequip_armor()
                elif ch == ord(">"):
                    # Descend stairs only if boss is dead and you stand on the stairs tile.
                    if self.stairs_pos is None:
                        self.log("No stairs yet. Kill the boss first.")
                    else:
                        assert self.player is not None
                        if self.player.pos() != self.stairs_pos:
                            self.log("Stand on the stairs (>) to descend.")
                        else:
                            if self.floor >= self.max_floors:
                                # Should be handled on boss death, but keep safe.
                                self.reset_run(keep_class=True, carry_equipped=True)
                            else:
                                self.start_floor(self.floor + 1, reposition_player=True)
                elif ch in (ord("?"),):
                    self.open_help_panel()
                elif ch in (ord(" "), ord(".")):
                    # Wait.
                    pass
                elif ch in (10, 13):
                    # No generic menu; Enter just waits.
                    pass
                # After any "turn" input: process monsters.
                if ch in (ord("?"), ord("i"), ord("I"), ord("c"), ord("C"), ord("k"), ord("K"), ord("b"), ord("B")):
                    # Panels already consumed the turn.
                    continue
                if self.skip_monster_turn_once:
                    continue
                # Special attack counts as a turn.
                if ch in (ord("u"), ord("U")):
                    pass
                # Only process monsters when game isn't paused by menus.
                # Simplification: treat movement/wait/special as actions.
                if ch not in (ord("i"), ord("I"), ord("c"), ord("C"), ord("k"), ord("K"), ord("b"), ord("B")):
                    # If player moved/attacked, monsters react.
                    # Poison ticks for player handled here too.
                    if self.player is not None and self.player.status.poison_turns > 0:
                        self.apply_poison_tick(self.player)
                        if self.player.hp <= 0:
                            self.game_state = "dead"
                            continue
                    self.process_monsters_turn()
        finally:
            # curses wraps cleanup automatically on exit; but be safe.
            pass


def target_resistance_mult(target: Optional[Entity]) -> float:
    # Placeholder if we later add monster resistances.
    return 1.0


def generate_item_forced_rarity(rng: random.Random, rarity: str, luck_points: int) -> Item:
    # Quick override: generate an item then coerce its rarity by regenerating.
    # This keeps things simple without rewriting generator internals.
    # We'll loop until we get the desired rarity.
    for _ in range(200):
        it = generate_item(rng, luck_points=luck_points)
        if it.rarity == rarity:
            return it
    # Fallback: create a legendary weapon quickly.
    it = generate_item(rng, luck_points=luck_points)
    it.rarity = rarity
    return it


def main(stdscr) -> None:
    # Ensure deterministic-ish in a run, but still random across restarts.
    game = RoguelikeGame(stdscr)
    game.run()


if __name__ == "__main__":
    # Windows users need windows-curses; if they didn't install it, fail with guidance.
    try:
        curses.initscr()
        curses.endwin()
    except Exception as e:
        print("Curses initialization failed. On Windows, install 'windows-curses'.")
        raise

    curses.wrapper(main)