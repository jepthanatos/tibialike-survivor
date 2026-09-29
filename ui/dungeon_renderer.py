"""
ui/dungeon_renderer.py
═══════════════════════════════════════════════════════════════
Renderizado del mapa de mazmorra (DungeonMap).

Tiles
─────
  DWALL  → pared de piedra oscura, con textura de bloques
  DFLOOR → suelo de losa, ligeramente más claro
  DCORR  → corredor, ligeramente distinto al suelo
  DENTRY → portal de entrada (verde)
  DEXIT  → portal de salida / jefe (naranja-rojo)
  DLAVA  → lava (naranja brillante)

Efectos
───────
  · Oscuridad ambient sobre toda la pantalla (ya aplicada en DungeonLevel)
  · Antorcha parpadeante en el centro de cada sala
  · Borde de pantalla con viñeta oscura
"""
from __future__ import annotations
import pygame
import math

from core.dungeon_generator import (
    DungeonMap, DWALL, DFLOOR, DCORR, DENTRY, DEXIT, DLAVA
)

# ── Tile colours ──────────────────────────────────────────────────────────────
_WALL_COLORS  = [(28,22,35),(32,26,40),(24,18,30)]
_FLOOR_COLORS = [(55,48,68),(60,52,74),(50,44,62)]
_CORR_COLORS  = [(45,40,58),(50,44,64),(40,36,52)]
_ENTRY_COLOR  = (30,100,35)
_EXIT_COLOR   = (110,35,15)
_LAVA_COLORS  = [(200,60,10),(180,50,5),(220,70,15)]


class DungeonRenderer:
    """Caches tile surfaces and draws a DungeonMap each frame."""

    def __init__(self, tile_size: int):
        self.ts     = tile_size
        self._surfs = self._build_surfaces(tile_size)
        self._time  = 0.0
        # Vignette overlay (built lazily)
        self._vig: pygame.Surface | None = None

    # ── Surface cache ─────────────────────────────────────────────────────────

    def _build_surfaces(self, ts: int) -> dict:
        surfs = {}

        def _make(colors, extra_fn=None):
            result = []
            for i, col in enumerate(colors):
                s = pygame.Surface((ts, ts))
                s.fill(col)
                if extra_fn:
                    extra_fn(s, ts, i, col)
                result.append(s)
            return result

        def _wall_extra(s, ts, i, col):
            # Brick pattern
            lc = tuple(max(0, c-12) for c in col)
            hc = tuple(min(255, c+10) for c in col)
            # Horizontal mortar every 8 px
            for y in range(0, ts, 8):
                pygame.draw.line(s, lc, (0, y), (ts, y))
            # Vertical mortar staggered
            offset = (i * 8) % 16
            for y in range(0, ts, 16):
                pygame.draw.line(s, lc, (offset, y), (offset, y+7))
                pygame.draw.line(s, lc, (offset+8, y+8), (offset+8, y+15))
            # Top highlight
            pygame.draw.line(s, hc, (0, 0), (ts-1, 0))

        def _floor_extra(s, ts, i, col):
            lc = tuple(max(0, c-8) for c in col)
            # Subtle tile grid
            for x in range(0, ts, 16):
                pygame.draw.line(s, lc, (x, 0), (x, ts), 1)
            for y in range(0, ts, 16):
                pygame.draw.line(s, lc, (0, y), (ts, y), 1)

        def _lava_extra(s, ts, i, col):
            dc = tuple(min(255, c+60) for c in col)
            for j in range(0, ts, 6):
                pygame.draw.line(s, dc, (j, 0), (0, j), 1)
            pygame.draw.circle(s, (255,160,20), (ts//2, ts//2), 5)

        surfs[DWALL]  = _make(_WALL_COLORS,  _wall_extra)
        surfs[DFLOOR] = _make(_FLOOR_COLORS, _floor_extra)
        surfs[DCORR]  = _make(_CORR_COLORS,  _floor_extra)
        surfs[DLAVA]  = _make(_LAVA_COLORS,  _lava_extra)

        # Entry portal tile (green glow)
        s = pygame.Surface((ts, ts))
        s.fill(_FLOOR_COLORS[0])
        pygame.draw.circle(s, _ENTRY_COLOR, (ts//2, ts//2), ts//2-4, 2)
        pygame.draw.circle(s, (60,200,60),  (ts//2, ts//2), ts//4)
        surfs[DENTRY] = [s, s, s]

        # Exit portal tile (orange-red glow)
        s2 = pygame.Surface((ts, ts))
        s2.fill(_FLOOR_COLORS[1])
        pygame.draw.circle(s2, _EXIT_COLOR, (ts//2, ts//2), ts//2-4, 2)
        pygame.draw.circle(s2, (220,80,20), (ts//2, ts//2), ts//4)
        surfs[DEXIT] = [s2, s2, s2]

        return surfs

    def _get_vignette(self, vw: int, vh: int) -> pygame.Surface:
        if self._vig is None or self._vig.get_size() != (vw, vh):
            self._vig = pygame.Surface((vw, vh), pygame.SRCALPHA)
            self._vig.fill((0, 0, 0, 0))
            for t in range(40, 0, -1):
                a = int(180 * ((40 - t) / 40) ** 2)
                pygame.draw.rect(self._vig, (0, 0, 0, a),
                                 (t, t, vw - t*2, vh - t*2), 1)
        return self._vig

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen, camera, dmap: DungeonMap,
             player_x: float = 0, player_y: float = 0):
        self._time += 0.016
        ts = self.ts
        vw = camera.view_w
        vh = camera.view_h

        c0 = max(0, int(camera.offset_x // ts))
        r0 = max(0, int(camera.offset_y // ts))
        c1 = min(dmap.width,  int((camera.offset_x + vw) // ts) + 2)
        r1 = min(dmap.height, int((camera.offset_y + vh) // ts) + 2)

        ox = round(camera.offset_x)
        oy = round(camera.offset_y)

        for col in range(c0, c1):
            for row in range(r0, r1):
                tid  = dmap.tiles[col][row]
                surfs = self._surfs.get(tid, self._surfs[DWALL])
                variant = (col * 3 + row * 7) % 3
                screen.blit(surfs[variant], (col*ts - ox, row*ts - oy))

        # Torch flicker in room centres
        self._draw_torches(screen, camera, dmap, ox, oy)

        # Vignette
        screen.blit(self._get_vignette(vw, vh), (0, 0))

    def _draw_torches(self, screen, camera, dmap, ox, oy):
        ts    = self.ts
        pulse = 0.7 + 0.3 * math.sin(self._time * 4.5)
        alpha = int(80 * pulse)

        for room in dmap.rooms:
            cx, cy = room.center()
            sx = cx * ts + ts//2 - ox
            sy = cy * ts + ts//2 - oy
            if not (-60 <= sx <= camera.view_w+60 and -60 <= sy <= camera.view_h+60):
                continue
            # Warm glow circle
            r    = int(room.w * ts * 0.55 * pulse)
            glow = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 160, 60, alpha), (r+2, r+2), r)
            screen.blit(glow, (sx - r - 2, sy - r - 2))
            # Small flame dot
            pygame.draw.circle(screen, (255, 220, 100), (sx, sy), 3)
