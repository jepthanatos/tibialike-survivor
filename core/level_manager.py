"""
core/level_manager.py
═══════════════════════════════════════════════════════════════
Gestiona la pila de niveles: mundo superficial + mazmorras.

Flujo
─────
  Mundo          → jugador llega a una entrada de mazmorra
                    y pulsa E → push(DungeonLevel)
  Mazmorra       → jugador llega al portal de salida y pulsa E
                    → pop() back al mundo superficial
  Mazmorra       → jugador muere → pop() sin recompensa

DungeonEntry  : portal visible en el mundo superficial
DungeonLevel  : nivel generado de mazmorra activo
"""
from __future__ import annotations
import math
import pygame
import random

from core.dungeon_generator import DungeonGenerator, DungeonMap
from core.dungeon_generator import DENTRY, DEXIT, DLAVA, DWALL
from core.dungeon_generator import DUNGEON_WALKABLE
from constants import TILE_SIZE


# ── Portal de entrada (mundo superficial) ─────────────────────────────────────

class DungeonEntrance:
    """
    Portal visible en el mapa principal en el centro de cada zona de mazmorra.
    Muestra [E] para entrar cuando el jugador está cerca.
    """
    INTERACT_RADIUS = 48.0

    def __init__(self, x: float, y: float, zone_id: int, zone_name: str,
                 biome_name: str = "grassland"):
        self.x         = x
        self.y         = y
        self.zone_id   = zone_id
        self.zone_name = zone_name
        self.biome_name= biome_name
        self._time     = 0.0

    def near_player(self, player) -> bool:
        return math.hypot(self.x - player.x, self.y - player.y) <= self.INTERACT_RADIUS

    def update(self, dt: float):
        self._time += dt

    def draw(self, screen, camera):
        sx = int(self.x - camera.offset_x)
        sy = int(self.y - camera.offset_y)

        if not (-80 <= sx <= camera.view_w + 80 and
                -80 <= sy <= camera.view_h + 80):
            return

        pulse  = 0.7 + 0.3 * math.sin(self._time * 2.5)
        radius = int(18 * pulse)

        # Outer glow
        glow = pygame.Surface((radius*2+8, radius*2+8), pygame.SRCALPHA)
        pygame.draw.circle(glow, (160, 60, 220, int(90*pulse)),
                           (radius+4, radius+4), radius+4)
        screen.blit(glow, (sx - radius - 4, sy - radius - 4))

        # Portal ring
        pygame.draw.circle(screen, (60, 20, 80), (sx, sy), radius+1)
        pygame.draw.circle(screen, (180, 80, 240), (sx, sy), radius, 3)
        # Inner swirl (simplified)
        inner_col = (int(100 + 80*pulse), 20, int(180 + 60*pulse))
        pygame.draw.circle(screen, inner_col, (sx, sy), radius-4)

        # Skull icon
        f = pygame.font.SysFont("Arial", 16, bold=True)
        sk = f.render("⬇", True, (220, 200, 255))
        screen.blit(sk, (sx - sk.get_width()//2, sy - sk.get_height()//2))

        # Zone name label
        fl = pygame.font.SysFont("Arial", 11, bold=True)
        lbl = fl.render(self.zone_name, True, (200, 150, 255))
        screen.blit(lbl, (sx - lbl.get_width()//2, sy - radius - 18))

        # Hint
        fh = pygame.font.SysFont("Arial", 11)
        hint = fh.render("[E] Entrar", True, (180, 180, 200))
        screen.blit(hint, (sx - hint.get_width()//2, sy + radius + 4))


# ── Exit portal (dentro de la mazmorra) ───────────────────────────────────────

class ExitPortal:
    """Portal de salida dentro de la mazmorra."""

    INTERACT_RADIUS = 52.0

    def __init__(self, x: float, y: float):
        self.x    = x
        self.y    = y
        self._time= 0.0

    def near_player(self, player) -> bool:
        return math.hypot(self.x - player.x, self.y - player.y) <= self.INTERACT_RADIUS

    def update(self, dt: float):
        self._time += dt

    def draw(self, screen, camera):
        sx = int(self.x - camera.offset_x)
        sy = int(self.y - camera.offset_y)
        if not (-80 <= sx <= camera.view_w+80 and -80 <= sy <= camera.view_h+80):
            return

        pulse  = 0.7 + 0.3 * math.sin(self._time * 3.0)
        radius = int(16 * pulse)

        glow = pygame.Surface((radius*2+8, radius*2+8), pygame.SRCALPHA)
        pygame.draw.circle(glow, (60, 200, 80, int(90*pulse)),
                           (radius+4, radius+4), radius+4)
        screen.blit(glow, (sx-radius-4, sy-radius-4))

        pygame.draw.circle(screen, (10, 50, 15), (sx, sy), radius+1)
        pygame.draw.circle(screen, (60, 220, 80), (sx, sy), radius, 3)
        pygame.draw.circle(screen, (20, 120, 30), (sx, sy), radius-4)

        f  = pygame.font.SysFont("Arial", 14, bold=True)
        sk = f.render("⬆", True, (180, 255, 180))
        screen.blit(sk, (sx - sk.get_width()//2, sy - sk.get_height()//2))

        fh = pygame.font.SysFont("Arial", 11)
        hint = fh.render("[E] Salir", True, (150, 220, 150))
        screen.blit(hint, (sx - hint.get_width()//2, sy + radius + 4))


# ── Active dungeon level ───────────────────────────────────────────────────────

class DungeonLevel:
    """
    Encapsula todo el estado de una mazmorra activa:
    mapa generado, portal de salida, oscuridad, overlay.
    """

    def __init__(self, dmap: DungeonMap, return_px: float, return_py: float):
        self.dmap        = dmap
        self.return_px   = return_px   # surface position to teleport back to
        self.return_py   = return_py
        ts               = dmap.tile_size

        # Exit portal in world coordinates
        ecol, erow       = dmap.exit_pos
        self.exit_portal = ExitPortal(ecol*ts + ts//2, erow*ts + ts//2)

        # Entry position in world coordinates (where player spawns inside)
        icol, irow       = dmap.entry_pos
        self.spawn_x     = icol * ts + ts//2
        self.spawn_y     = irow * ts + ts//2

        # Darkness overlay (dungeon is darker than surface)
        self._dark_surf  = None   # built on first draw
        self._time       = 0.0

    def update(self, dt: float):
        self._time += dt
        self.exit_portal.update(dt)

    def player_at_exit(self, player) -> bool:
        return self.exit_portal.near_player(player)

    def player_at_entry(self, player) -> bool:
        ts   = self.dmap.tile_size
        icol, irow = self.dmap.entry_pos
        ex   = icol * ts + ts//2
        ey   = irow * ts + ts//2
        return math.hypot(player.x - ex, player.y - ey) < 52.0

    def draw_overlay(self, screen, camera):
        """Dark ambient overlay — drawn after world but before entities."""
        vw, vh = camera.view_w, camera.view_h
        if self._dark_surf is None or self._dark_surf.get_size() != (vw, vh):
            self._dark_surf = pygame.Surface((vw, vh), pygame.SRCALPHA)
            self._dark_surf.fill((0, 0, 12, 110))
        screen.blit(self._dark_surf, (0, 0))

    def draw_portals(self, screen, camera, player):
        self.exit_portal.draw(screen, camera)

    def draw_hud_banner(self, screen, screen_w: int):
        """Shows dungeon depth indicator at top of screen."""
        f    = pygame.font.SysFont("Arial", 14, bold=True)
        depth = self.dmap.dungeon_level
        text  = f.render(f"⬇  Mazmorra — Nivel {depth}  ⬇", True, (180, 120, 240))
        sx    = screen_w//2 - text.get_width()//2
        pygame.draw.rect(screen, (10, 5, 20),
                         (sx-8, 2, text.get_width()+16, text.get_height()+4),
                         border_radius=4)
        screen.blit(text, (sx, 4))


# ── Level manager ─────────────────────────────────────────────────────────────

class LevelManager:
    """
    Pila de niveles.  level_stack[0] es siempre el mundo superficial;
    level_stack[1] (si existe) es la mazmorra activa.

    in_dungeon → True cuando hay una mazmorra activa.
    """

    def __init__(self, surface_world, surface_camera,
                 dungeon_entrances: list[DungeonEntrance]):
        self._world    = surface_world
        self._camera   = surface_camera
        self.entrances = dungeon_entrances
        self._dungeons: list[DungeonLevel] = []
        self._gen      = DungeonGenerator()
        self._seed_base = random.randint(0, 999999)

    # ── Queries ───────────────────────────────────────────────────────────────

    @property
    def in_dungeon(self) -> bool:
        return bool(self._dungeons)

    @property
    def current_dungeon(self) -> DungeonLevel | None:
        return self._dungeons[-1] if self._dungeons else None

    @property
    def active_map(self):
        """Returns the DungeonMap if in dungeon, else the surface World."""
        if self._dungeons:
            return self._dungeons[-1].dmap
        return self._world

    # ── Transitions ───────────────────────────────────────────────────────────

    def try_enter(self, player, biome_map) -> bool:
        """
        Check if player is near any entrance and trigger transition.
        Returns True if entered a dungeon this frame.
        """
        if self.in_dungeon:
            return False
        for ent in self.entrances:
            if ent.near_player(player):
                self._enter(ent, player, biome_map)
                return True
        return False

    def try_exit(self, player) -> bool:
        """
        Check if player is at the exit portal of the current dungeon.
        Returns True if exited this frame.
        """
        if not self.in_dungeon:
            return False
        dlvl = self.current_dungeon
        if dlvl.player_at_exit(player):
            self._exit(player)
            return True
        return False

    def _enter(self, entrance: DungeonEntrance, player, biome_map):
        """Generate and push a new dungeon level."""
        depth    = len(self._dungeons) + 1
        bname    = entrance.biome_name
        seed     = self._seed_base ^ (entrance.zone_id * 31337) ^ depth
        dmap     = self._gen.generate(
            dungeon_level=depth,
            biome_name=bname,
            tile_size=TILE_SIZE,
            seed=seed,
        )
        dlvl     = DungeonLevel(dmap, player.x, player.y)
        self._dungeons.append(dlvl)

        # Teleport player to dungeon entry spawn
        player.x = dlvl.spawn_x
        player.y = dlvl.spawn_y
        player.rect.center = (int(player.x), int(player.y))

        # Update camera bounds for new map
        self._camera.world_w = dmap.width  * TILE_SIZE
        self._camera.world_h = dmap.height * TILE_SIZE
        self._camera.snap(player.x, player.y)

    def _exit(self, player):
        """Pop current dungeon and return player to surface."""
        if not self._dungeons:
            return
        dlvl = self._dungeons.pop()
        player.x = dlvl.return_px
        player.y = dlvl.return_py
        player.rect.center = (int(player.x), int(player.y))

        # Restore camera bounds
        self._camera.world_w = self._world.width  * TILE_SIZE
        self._camera.world_h = self._world.height * TILE_SIZE
        self._camera.snap(player.x, player.y)

    # ── Build entrances from dungeon zones ────────────────────────────────────

    @staticmethod
    def build_entrances(dungeon_zones, biome_map, tile_size: int) -> list[DungeonEntrance]:
        """Creates one DungeonEntrance per surface dungeon zone."""
        entrances = []
        for zone in dungeon_zones:
            cx_px = zone.center_col * tile_size + tile_size // 2
            cy_px = zone.center_row * tile_size + tile_size // 2
            bname = biome_map.get(zone.center_col, zone.center_row) \
                    if biome_map else "grassland"
            entrances.append(DungeonEntrance(
                x         = float(cx_px),
                y         = float(cy_px),
                zone_id   = zone.zone_id,
                zone_name = zone.name,
                biome_name= bname,
            ))
        return entrances
