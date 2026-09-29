"""
systems/zones.py
════════════════════════════════════════════════════════════════
Zonas de dificultad radiales para el mapa.

El mapa se divide en 4 anillos concéntricos:
  ·  Periferia (>65%)  — monstruos débiles: rat, zombie, skeleton
  ·  Anillo medio (45-65%) — orc, dark_wizard
  ·  Anillo interior (25-45%) — dragon
  ·  Centro (<25%)    — demon, dragon_lord

Esto recrea la mecánica de Tibia donde ir al centro del mapa
es más peligroso y recompensante.
"""
from __future__ import annotations
import math

# Fracción del radio máximo para cada zona
ZONE_THRESHOLDS = [0.25, 0.45, 0.65]   # fracciones del radio máximo
ZONE_NAMES = ["Centro", "Interior", "Medio", "Periferia"]
ZONE_COLORS = [
    (220,  60,  40),   # Centro — rojo
    (220, 140,  40),   # Interior — naranja
    (220, 220,  40),   # Medio — amarillo
    ( 80, 200,  80),   # Periferia — verde
]

# Tipos de monstruos por zona (índice 0 = centro, 3 = periferia)
ZONE_MONSTER_TYPES = [
    ["demon", "dragon_lord", "dragon", "vampire"],       # zona 0: centro
    ["dragon", "vampire", "fire_devil", "dark_wizard"],  # zona 1: interior
    ["cyclops", "orc", "dark_wizard", "fire_devil"],     # zona 2: medio
    ["rat", "wolf", "troll", "zombie", "skeleton", "bear", "orc"],  # zona 3: periferia
]

# XP bonus multiplicador por zona (más riesgo = más XP)
ZONE_XP_MULT = [3.0, 2.0, 1.3, 1.0]

# Level bonus para monstruos según zona
ZONE_LEVEL_BONUS = [15, 8, 3, 0]


def get_zone(px: float, py: float, map_cx: float, map_cy: float,
             map_radius: float) -> int:
    """
    Returns zone index 0-3 based on distance from center.
    0 = most dangerous (center), 3 = safest (periphery).
    """
    dist = math.hypot(px - map_cx, py - map_cy)
    frac = dist / map_radius
    for i, threshold in enumerate(ZONE_THRESHOLDS):
        if frac <= threshold:
            return i
    return 3


def get_zone_name(zone: int) -> str:
    return ZONE_NAMES[zone] if 0 <= zone < len(ZONE_NAMES) else "Periferia"


def get_zone_color(zone: int) -> tuple:
    return ZONE_COLORS[zone] if 0 <= zone < len(ZONE_COLORS) else (80, 200, 80)


def get_zone_monster_types(zone: int) -> list[str]:
    return ZONE_MONSTER_TYPES[zone] if 0 <= zone < len(ZONE_MONSTER_TYPES) else ZONE_MONSTER_TYPES[3]


def get_zone_level_bonus(zone: int) -> int:
    return ZONE_LEVEL_BONUS[zone] if 0 <= zone < len(ZONE_LEVEL_BONUS) else 0


def get_zone_xp_mult(zone: int) -> float:
    return ZONE_XP_MULT[zone] if 0 <= zone < len(ZONE_XP_MULT) else 1.0


def random_spawn_point(world, min_dist_from: list[tuple] = None,
                       min_sep: int = 20, margin: int = 8,
                       max_tries: int = 200) -> tuple[int, int] | None:
    """
    Find a random walkable spawn point, ensuring minimum separation
    from other spawn points (in tiles).

    Returns (col, row) or None if no point found.
    """
    import random
    W, H = world.width, world.height
    min_dist_from = min_dist_from or []
    for _ in range(max_tries):
        col = random.randint(margin, W - margin)
        row = random.randint(margin, H - margin)
        if not world.is_walkable(col, row):
            continue
        # Check separation from all other spawn points
        too_close = any(
            abs(col - oc) + abs(row - or_) < min_sep
            for oc, or_ in min_dist_from
        )
        if not too_close:
            return col, row
    return None
