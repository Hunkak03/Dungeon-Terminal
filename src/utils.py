"""Utility functions for the game."""
import math
import random
from typing import List, Tuple

Vec2 = Tuple[int, int]


def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp value between lo and hi."""
    return lo if x < lo else hi if x > hi else x


def manhattan(a: Vec2, b: Vec2) -> int:
    """Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def chebyshev(a: Vec2, b: Vec2) -> int:
    """Chebyshev distance (chessboard distance)."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def euclidean(a: Vec2, b: Vec2) -> float:
    """Euclidean distance."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def in_bounds(x: int, y: int, w: int, h: int) -> bool:
    """Check if point is within bounds."""
    return 0 <= x < w and 0 <= y < h


def bresenham_line(a: Vec2, b: Vec2) -> List[Vec2]:
    """Bresenham's line algorithm for LOS checks."""
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


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation."""
    return a + (b - a) * t


def format_percent(x: float) -> str:
    """Format float as percentage string."""
    return f"{int(round(x * 100))}%"


def roll_dice(count: int, sides: int, rng: random.Random) -> int:
    """Roll NdX dice."""
    return sum(rng.randint(1, sides) for _ in range(count))


def pick_weighted(weights: dict, rng: random.Random):
    """Pick a random key based on weights."""
    total = sum(weights.values())
    roll = rng.random() * total
    acc = 0.0
    for key, weight in weights.items():
        acc += weight
        if roll <= acc:
            return key
    return list(weights.keys())[-1]


def circle_points(cx: int, cy: int, radius: int) -> List[Vec2]:
    """Get all points in a circle."""
    points = []
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                points.append((cx + dx, cy + dy))
    return points
