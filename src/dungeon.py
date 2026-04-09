"""Dungeon generation with biomes and special rooms."""
import random
from typing import Dict, List, Optional, Tuple
from constants import *
from utils import Vec2, in_bounds, manhattan, chebyshev


class Room:
    """A room in the dungeon."""
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.cx = x + w // 2
        self.cy = y + h // 2
        self.special = None  # "treasure", "shrine", "trap", "merchant", "chest"
    
    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.w and self.y <= y < self.y + self.h
    
    def intersects(self, other: 'Room', padding: int = 1) -> bool:
        return not (self.x + self.w + padding < other.x or 
                   other.x + other.w + padding < self.x or
                   self.y + self.h + padding < other.y or
                   other.y + other.h + padding < self.y)


class DungeonMap:
    """Procedurally generated dungeon map."""
    def __init__(self, w: int, h: int, floor: int, biome: str, rng: random.Random):
        self.w = w
        self.h = h
        self.floor = floor
        self.biome = biome
        self.rng = rng
        self.tiles = [[TILE_WALL for _ in range(w)] for _ in range(h)]
        self.explored = [[False for _ in range(w)] for _ in range(h)]
        self.rooms: List[Room] = []
        self.secret_rooms: List[Room] = []
        self.traps: List[Tuple[Vec2, str]] = []  # (position, trap_type)
        self.events: List[Tuple[Vec2, str]] = []  # (position, event_type)
        self.is_boss_arena = False
        self.generate()
    
    def generate(self) -> None:
        """Generate the dungeon."""
        self._carve_rooms()
        self._connect_rooms()
        self._add_special_rooms()
        self._add_traps()
        self._add_environmental_hazards()
        self._smooth()
    
    def _carve_rooms(self) -> None:
        """Carve rooms based on floor and biome."""
        self.tiles = [[TILE_WALL for _ in range(self.w)] for _ in range(self.h)]
        
        # More rooms on deeper floors
        room_count = self.rng.randint(8, 14) + self.floor // 5
        self.rooms = []
        
        # Biome affects room size
        if self.biome == BIOME_CAVE:
            # Caves have fewer, larger rooms
            min_size, max_size = 8, 14
        elif self.biome == BIOME_HELL:
            min_size, max_size = 5, 9
        else:
            min_size, max_size = 6, 11
        
        attempts = 0
        while len(self.rooms) < room_count and attempts < 200:
            attempts += 1
            rw = self.rng.randint(min_size, max_size)
            rh = self.rng.randint(min_size - 2, max_size - 2)
            rx = self.rng.randint(1, self.w - rw - 2)
            ry = self.rng.randint(1, self.h - rh - 2)
            
            new_room = Room(rx, ry, rw, rh)
            
            if any(new_room.intersects(existing) for existing in self.rooms):
                continue
            
            self._carve_room(new_room)
            self.rooms.append(new_room)
    
    def _carve_room(self, room: Room) -> None:
        """Carve a room into the map."""
        for y in range(room.y, room.y + room.h):
            for x in range(room.x, room.x + room.w):
                self.tiles[y][x] = TILE_FLOOR
    
    def _connect_rooms(self) -> None:
        """Connect rooms with corridors."""
        # Sort rooms by position for better connectivity
        sorted_rooms = sorted(self.rooms, key=lambda r: r.cx + r.cy)
        
        for i in range(len(sorted_rooms) - 1):
            r1 = sorted_rooms[i]
            r2 = sorted_rooms[i + 1]
            self._carve_corridor(r1.cx, r1.cy, r2.cx, r2.cy)
        
        # Add some extra connections for loops
        extra = min(3, len(self.rooms) // 4)
        for _ in range(extra):
            r1 = self.rng.choice(self.rooms)
            r2 = self.rng.choice(self.rooms)
            if r1 != r2:
                self._carve_corridor(r1.cx, r1.cy, r2.cx, r2.cy)
    
    def _carve_corridor(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Carve an L-shaped corridor."""
        if self.rng.random() < 0.5:
            self._carve_horizontal(x1, x2, y1)
            self._carve_vertical(y1, y2, x2)
        else:
            self._carve_vertical(y1, y2, x1)
            self._carve_horizontal(x1, x2, y2)
    
    def _carve_horizontal(self, x1: int, x2: int, y: int) -> None:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if in_bounds(x, y, self.w, self.h):
                self.tiles[y][x] = TILE_FLOOR
    
    def _carve_vertical(self, y1: int, y2: int, x: int) -> None:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if in_bounds(x, y, self.w, self.h):
                self.tiles[y][x] = TILE_FLOOR
    
    def _add_special_rooms(self) -> None:
        """Mark some rooms as special."""
        if len(self.rooms) < 2:
            return
        
        # Pick rooms for special features
        available = list(self.rooms[1:])  # Exclude first room (player start)
        self.rng.shuffle(available)
        
        # Shrine room
        if self.rng.random() < 0.40 and available:
            room = available.pop(0)
            room.special = "shrine"
            self.events.append((room.cx, room.cy, "shrine"))
        
        # Merchant room (every 5 floors)
        if self.floor % 5 == 0 and available:
            room = available.pop(0)
            room.special = "merchant"
            self.events.append((room.cx, room.cy, "merchant"))
        
        # Treasure room
        if self.rng.random() < 0.25 and available:
            room = available.pop(0)
            room.special = "treasure"
            self.events.append((room.cx, room.cy, "treasure"))
        
        # Trap room
        if self.rng.random() < 0.30 and available:
            room = available.pop(0)
            room.special = "trap"
        
        # Boss arena (boss floors)
        if self.floor % 10 == 0 and available:
            room = available.pop(0)
            room.special = "boss_arena"
            self.is_boss_arena = True
            # Make it bigger
            self._expand_room(room)
        
        # Secret rooms (10-15% chance per floor)
        if self.rng.random() < 0.12:
            self._create_secret_rooms(available)
    
    def _expand_room(self, room: Room) -> None:
        """Expand a room for special purposes."""
        expansion = 3
        room.x = max(1, room.x - expansion)
        room.y = max(1, room.y - expansion)
        room.w = min(self.w - 2, room.w + expansion * 2)
        room.h = min(self.h - 2, room.h + expansion * 2)
        room.cx = room.x + room.w // 2
        room.cy = room.y + room.h // 2
        
        # Re-carve with new size
        for y in range(room.y, room.y + room.h):
            for x in range(room.x, room.x + room.w):
                if in_bounds(x, y, self.w, self.h):
                    self.tiles[y][x] = TILE_FLOOR
    
    def _create_secret_rooms(self, available_rooms: List[Room]) -> None:
        """Create secret rooms hidden behind walls."""
        num_secret = self.rng.randint(1, 2)
        
        for _ in range(num_secret):
            if not available_rooms:
                break
            
            # Pick a room to attach secret room to
            parent_room = self.rng.choice(available_rooms)
            
            # Create secret room adjacent to parent
            secret_x = parent_room.x + parent_room.w + 2
            secret_y = parent_room.cy - 3
            
            # Ensure in bounds
            if secret_x + 8 > self.w or secret_y < 1 or secret_y + 6 > self.h:
                continue
            
            secret_w = self.rng.randint(6, 10)
            secret_h = self.rng.randint(5, 8)
            
            secret_room = Room(secret_x, secret_y, secret_w, secret_h)
            
            # Carve secret room
            for y in range(secret_y, secret_y + secret_h):
                for x in range(secret_x, secret_x + secret_w):
                    if in_bounds(x, y, self.w, self.h):
                        self.tiles[y][x] = TILE_SECRET_ROOM
            
            # Create secret door (hidden wall tile)
            door_x = secret_x - 1
            door_y = parent_room.cy
            if in_bounds(door_x, door_y, self.w, self.h):
                self.tiles[door_y][door_x] = TILE_SECRET_DOOR
            
            secret_room.special = "secret"
            self.secret_rooms.append(secret_room)
    
    def _add_traps(self) -> None:
        """Add traps to hallways and rooms."""
        trap_count = self.floor // 3
        if self.biome == BIOME_DUNGEON:
            trap_count = int(trap_count * 1.5)
        
        for _ in range(trap_count):
            pos = self.random_floor_cell()
            trap_type = self.rng.choice(["spike", "poison_dart", "fire", "teleport", "curse"])
            self.traps.append((pos, trap_type))
            self.tiles[pos[1]][pos[0]] = TILE_TRAP
    
    def _add_environmental_hazards(self) -> None:
        """Add biome-specific hazards."""
        if self.biome == BIOME_HELL:
            # Lava pools
            for _ in range(self.rng.randint(2, 5)):
                pos = self.random_floor_cell()
                x, y = pos
                # Create small lava pool
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        nx, ny = x + dx, y + dy
                        if in_bounds(nx, ny, self.w, self.h) and self.tiles[ny][nx] == TILE_FLOOR:
                            if self.rng.random() < 0.6:
                                self.tiles[ny][nx] = TILE_LAVA
        
        elif self.biome == BIOME_FROST:
            # Ice patches (slippery)
            for _ in range(self.rng.randint(3, 8)):
                pos = self.random_floor_cell()
                x, y = pos
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        nx, ny = x + dx, y + dy
                        if in_bounds(nx, ny, self.w, self.h) and self.tiles[ny][nx] == TILE_FLOOR:
                            # Mark as ice (using trap tile for now)
                            if self.rng.random() < 0.4:
                                self.tiles[ny][nx] = TILE_TRAP
                                self.traps.append(((nx, ny), "ice"))
    
    def _smooth(self) -> None:
        """Smooth the dungeon for better aesthetics."""
        # Minimal smoothing to preserve room structure
        pass
    
    def is_passable(self, x: int, y: int) -> bool:
        """Check if a tile is passable."""
        if not in_bounds(x, y, self.w, self.h):
            return False
        tile = self.tiles[y][x]
        return tile in [TILE_FLOOR, TILE_DOOR, TILE_STAIRS_DOWN, TILE_STAIRS_UP, TILE_TRAP, TILE_SHRINE, TILE_MERCHANT, TILE_CHEST]
    
    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a tile can be walked on (excludes entities)."""
        return self.is_passable(x, y) and self.tiles[y][x] not in [TILE_WALL, TILE_LAVA]
    
    def random_floor_cell(self, avoid: Optional[Vec2] = None) -> Vec2:
        """Get a random floor cell."""
        for _ in range(5000):
            x = self.rng.randint(1, self.w - 2)
            y = self.rng.randint(1, self.h - 2)
            if self.is_walkable(x, y) and (avoid is None or (x, y) != avoid):
                return (x, y)
        # Fallback scan
        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                if self.is_walkable(x, y) and (avoid is None or (x, y) != avoid):
                    return (x, y)
        return (1, 1)
    
    def compute_fov(self, origin: Vec2, radius: int) -> List[List[bool]]:
        """Compute field of view using raycasting."""
        ox, oy = origin
        visible = [[False for _ in range(self.w)] for _ in range(self.h)]
        visible[oy][ox] = True
        
        # Cast rays in all directions
        import math
        angles = 360
        for i in range(angles):
            angle = 2.0 * math.pi * i / angles
            dx = math.cos(angle)
            dy = math.sin(angle)
            
            x, y = float(ox) + 0.5, float(oy) + 0.5
            for _ in range(radius * 2):
                tx, ty = int(x), int(y)
                if not in_bounds(tx, ty, self.w, self.h):
                    break
                visible[ty][tx] = True
                if self.tiles[ty][tx] == TILE_WALL:
                    break
                x += dx * 0.5
                y += dy * 0.5
        
        return visible
    
    def place_stairs(self, pos: Vec2) -> None:
        """Place stairs down at position."""
        x, y = pos
        if in_bounds(x, y, self.w, self.h):
            self.tiles[y][x] = TILE_STAIRS_DOWN


def get_biome_for_floor(floor: int) -> str:
    """Determine biome based on floor number."""
    if floor <= 10:
        return BIOME_DUNGEON
    elif floor <= 20:
        return BIOME_FOREST
    elif floor <= 30:
        return BIOME_CAVE
    elif floor <= 40:
        return BIOME_HELL
    else:
        return BIOME_VOID


BIOME_MODIFIERS = {
    BIOME_DUNGEON: {
        "trap_frequency": 1.5,
        "monster_aggro": 1.0,
        "description": "A dark, damp dungeon filled with traps and cunning monsters.",
    },
    BIOME_FOREST: {
        "trap_frequency": 0.7,
        "monster_aggro": 1.2,
        "description": "A dense, dark forest where predators lurk behind every tree.",
    },
    BIOME_CAVE: {
        "trap_frequency": 1.2,
        "monster_aggro": 0.9,
        "description": "Crystal caves that glow eerily, home to strange creatures.",
    },
    BIOME_HELL: {
        "trap_frequency": 1.8,
        "monster_aggro": 1.5,
        "description": "The infernal depths. Lava burns everywhere.",
    },
    BIOME_VOID: {
        "trap_frequency": 1.3,
        "monster_aggro": 1.4,
        "description": "The Void itself. Reality bends and warps here.",
    },
    BIOME_FROST: {
        "trap_frequency": 1.0,
        "monster_aggro": 1.1,
        "description": "Frozen wastes where ice covers everything.",
    },
}
