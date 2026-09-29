"""
systems/dungeons.py
Zonas de mazmorra en el mapa: áreas delimitadas que tienen mayor densidad
de monstruos y mejores drops, pero la tormenta NO hace daño dentro.

Cada zona se define como un rectángulo en coordenadas de tile.
"""
from __future__ import annotations
import random
import math
import pygame

from constants import TILE_SIZE

# ── Dungeon zone definition ───────────────────────────────────────────────────

NUM_DUNGEONS    = 4     # número de zonas en el mapa
MIN_RADIUS      = 12    # tiles de radio mínimo
MAX_RADIUS      = 22    # tiles de radio máximo
LOOT_MULT       = 1.65  # multiplicador de probabilidad de drop
MONSTER_DENSITY = 2.0   # factor de densidad extra dentro

# Color scheme para tiles de mazmorra (se superpone como overlay visual)
DUNGEON_OVERLAY_COLOR = (15, 10, 30, 85)   # rgba


class DungeonZone:
    """Circular dungeon zone on the tile map."""

    def __init__(self, center_col: int, center_row: int, radius: int, zone_id: int):
        self.center_col = center_col
        self.center_row = center_row
        self.radius     = radius
        self.zone_id    = zone_id
        self.name       = _ZONE_NAMES[zone_id % len(_ZONE_NAMES)]
        self._entrance_col = center_col
        self._entrance_row = center_row - radius - 2

    def contains_tile(self, col: int, row: int) -> bool:
        return math.hypot(col - self.center_col, row - self.center_row) <= self.radius

    def contains_px(self, px: float, py: float) -> bool:
        cx = self.center_col * TILE_SIZE + TILE_SIZE // 2
        cy = self.center_row * TILE_SIZE + TILE_SIZE // 2
        r  = self.radius * TILE_SIZE
        return math.hypot(px - cx, py - cy) <= r

    def center_px(self):
        return (self.center_col * TILE_SIZE + TILE_SIZE // 2,
                self.center_row * TILE_SIZE + TILE_SIZE // 2)


_ZONE_NAMES = [
    "Catacumbas",
    "Torre del Nigromante",
    "Fortaleza Oscura",
    "Templo Maldito",
    "Minas Profundas",
    "Cripta Antigua",
]


# ── Generator ─────────────────────────────────────────────────────────────────

def generate_dungeons(world_w: int, world_h: int, seed: int = 42) -> list[DungeonZone]:
    """
    Places NUM_DUNGEONS dungeon zones spread around the map,
    avoiding the centre spawn area (radius 25 around center).
    """
    rng    = random.Random(seed + 9999)
    zones: list[DungeonZone] = []
    cx     = world_w // 2
    cy     = world_h // 2
    margin = 15

    attempts = 0
    while len(zones) < NUM_DUNGEONS and attempts < 400:
        attempts += 1
        col    = rng.randint(margin, world_w - margin)
        row    = rng.randint(margin, world_h - margin)
        radius = rng.randint(MIN_RADIUS, MAX_RADIUS)

        # Keep away from centre
        if math.hypot(col - cx, row - cy) < 30 + radius:
            continue
        # Keep away from edges
        if col - radius < margin or col + radius > world_w - margin:
            continue
        if row - radius < margin or row + radius > world_h - margin:
            continue
        # Keep away from each other
        too_close = any(
            math.hypot(col - z.center_col, row - z.center_row) < radius + z.radius + 8
            for z in zones
        )
        if too_close:
            continue

        zones.append(DungeonZone(col, row, radius, len(zones)))

    return zones


# ── Query helpers ─────────────────────────────────────────────────────────────

def in_any_dungeon(zones: list[DungeonZone], px: float, py: float) -> DungeonZone | None:
    """Returns the dungeon zone containing (px, py), or None."""
    for z in zones:
        if z.contains_px(px, py):
            return z
    return None


def loot_multiplier(zones: list[DungeonZone], px: float, py: float) -> float:
    """Returns loot drop chance multiplier for position (px, py)."""
    if in_any_dungeon(zones, px, py):
        return LOOT_MULT
    return 1.0


# ── Rendering ─────────────────────────────────────────────────────────────────

def draw_dungeons(screen, camera, zones: list[DungeonZone], player_x: float, player_y: float):
    """
    Draws circular dungeon overlays and entrance markers.
    Called before monsters but after world tiles.
    """
    vw = camera.view_w
    vh = camera.view_h

    for zone in zones:
        cx_px, cy_px = zone.center_px()
        sx, sy = camera.world_to_screen(cx_px, cy_px)
        r_px   = zone.radius * TILE_SIZE

        # Out of view culling
        if sx + r_px < -50 or sx - r_px > vw + 50:
            continue
        if sy + r_px < -50 or sy - r_px > vh + 50:
            continue

        # Draw circular overlay (dark fog-of-doom effect)
        d_size = r_px * 2 + 8
        surf   = pygame.Surface((d_size, d_size), pygame.SRCALPHA)

        # Gradient circle: darker in centre, lighter at edge
        for step in range(6, 0, -1):
            frac  = step / 6.0
            alpha = int(110 * frac)
            inner_r = int(r_px * frac)
            pygame.draw.circle(surf, (10, 5, 25, alpha),
                               (d_size // 2, d_size // 2), inner_r)

        # Border glow
        pygame.draw.circle(surf, (80, 40, 160, 180),
                           (d_size // 2, d_size // 2), r_px, 3)

        screen.blit(surf, (int(sx) - d_size // 2, int(sy) - d_size // 2))

        # Zone name label at entrance
        label_x = sx
        label_y = sy - r_px - 20

        inside   = zone.contains_px(player_x, player_y)
        lbl_col  = (200, 160, 255) if inside else (120, 80, 180)

        font = pygame.font.SysFont("Arial", 12, bold=True)
        lbl  = font.render(f"⚔  {zone.name}", True, lbl_col)
        screen.blit(lbl, (int(label_x) - lbl.get_width() // 2, int(label_y)))

        # Inner skull icons at centre (decorative)
        if -60 < sx < vw + 60 and -60 < sy < vh + 60:
            sf2 = pygame.font.SysFont("Arial", 18)
            sk  = sf2.render("☠", True, (90, 50, 130, 160))
            screen.blit(sk, (int(sx) - sk.get_width() // 2,
                             int(sy) - sk.get_height() // 2))
