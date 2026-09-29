"""
core/dungeon_generator.py
═══════════════════════════════════════════════════════════════
Generador procedural de mazmorras por partición binaria (BSP).

Produce un DungeonMap: mapa 2D de tiles oscuros con salas
conectadas por corredores, una entrada, una salida y
posiciones para monstruos y el jefe final.

Tiles de mazmorra
─────────────────
  0  DWALL   pared de piedra (impassable)
  1  DFLOOR  suelo de mazmorra (walkable)
  2  DCORR   corredor (walkable)
  3  DENTRY  entrada (walkable, regresa al mundo)
  4  DEXIT   salida / siguiente sala (walkable, jefe aquí)
  5  DLAVA   lava decorativa (impassable)
"""
from __future__ import annotations
import random
import math
from dataclasses import dataclass, field

# ── Tile constants ─────────────────────────────────────────────────────────────
DWALL  = 0
DFLOOR = 1
DCORR  = 2
DENTRY = 3
DEXIT  = 4
DLAVA  = 5

DUNGEON_WALKABLE = {DFLOOR, DCORR, DENTRY, DEXIT}

# ── Room ──────────────────────────────────────────────────────────────────────

@dataclass
class Room:
    x: int      # tile col of top-left
    y: int      # tile row of top-left
    w: int      # width in tiles
    h: int      # height in tiles

    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    def inner_tiles(self):
        for col in range(self.x + 1, self.x + self.w - 1):
            for row in range(self.y + 1, self.y + self.h - 1):
                yield col, row

    def overlaps(self, other: "Room", margin: int = 1) -> bool:
        return not (
            self.x + self.w + margin <= other.x or
            other.x + other.w + margin <= self.x or
            self.y + self.h + margin <= other.y or
            other.y + other.h + margin <= self.y
        )


# ── DungeonMap ────────────────────────────────────────────────────────────────

@dataclass
class DungeonMap:
    """Complete generated dungeon ready to play."""
    width:  int
    height: int
    tile_size: int
    tiles:  list[list[int]]          # [col][row]
    rooms:  list[Room]
    entry_pos:  tuple[int, int]      # tile (col, row) of entrance
    exit_pos:   tuple[int, int]      # tile (col, row) of exit / boss room centre
    monster_spawns: list[tuple[int,int]]   # tile positions for normal monsters
    boss_spawn:     tuple[int, int]  # tile position for boss
    dungeon_level:  int              # depth (1 = first dungeon)
    biome_name:     str              # inherited from surface biome

    def is_walkable(self, col: int, row: int) -> bool:
        if col < 0 or col >= self.width or row < 0 or row >= self.height:
            return False
        return self.tiles[col][row] in DUNGEON_WALKABLE

    def is_rect_walkable(self, left: float, top: float,
                         right: float, bottom: float) -> bool:
        ts = self.tile_size
        for px, py in ((left, top), (right-1, top),
                       (left, bottom-1), (right-1, bottom-1)):
            if not self.is_walkable(int(px // ts), int(py // ts)):
                return False
        return True

    # Adapter so World API callers work transparently
    def get_minimap(self):
        import pygame
        MM = 120
        surf = pygame.Surface((MM, MM))
        surf.fill((10, 10, 10))
        sx = MM / self.width
        sy = MM / self.height
        _MC = {
            DWALL: (30, 25, 35),
            DFLOOR: (80, 70, 95),
            DCORR: (60, 55, 75),
            DENTRY: (60, 180, 60),
            DEXIT: (220, 80, 40),
            DLAVA: (200, 50, 10),
        }
        for col in range(self.width):
            for row in range(self.height):
                c = _MC.get(self.tiles[col][row], (50, 50, 50))
                surf.set_at((min(MM-1, int(col*sx)), min(MM-1, int(row*sy))), c)
        return surf, MM


# ── Generator ─────────────────────────────────────────────────────────────────

class DungeonGenerator:
    """
    Generates a DungeonMap using a simple room-placement approach.
    Rooms are placed randomly; corridors connect them in a spanning tree.
    """

    # Map size scales with dungeon depth
    BASE_W  = 48
    BASE_H  = 48
    MIN_ROOM_W = 5
    MAX_ROOM_W = 12
    MIN_ROOM_H = 5
    MAX_ROOM_H = 10
    TARGET_ROOMS = 10

    def generate(self, dungeon_level: int = 1, biome_name: str = "grassland",
                 tile_size: int = 32, seed: int = 0) -> DungeonMap:
        rng = random.Random(seed)
        scale = 1 + (dungeon_level - 1) * 0.2
        W = int(self.BASE_W * scale)
        H = int(self.BASE_H * scale)

        tiles = [[DWALL] * H for _ in range(W)]
        rooms: list[Room] = []

        # Place rooms
        target = self.TARGET_ROOMS + dungeon_level
        for _ in range(target * 8):
            if len(rooms) >= target:
                break
            rw  = rng.randint(self.MIN_ROOM_W, self.MAX_ROOM_W)
            rh  = rng.randint(self.MIN_ROOM_H, self.MAX_ROOM_H)
            rx  = rng.randint(1, W - rw - 1)
            ry  = rng.randint(1, H - rh - 1)
            r   = Room(rx, ry, rw, rh)
            if any(r.overlaps(existing) for existing in rooms):
                continue
            rooms.append(r)
            for col, row in r.inner_tiles():
                tiles[col][row] = DFLOOR

        if len(rooms) < 3:
            rooms = self._fallback_rooms(W, H, tiles)

        # Connect rooms with corridors (minimum spanning tree by distance)
        self._connect_rooms(rooms, tiles, rng)

        # Lava decorations (only in volcanic biome or depth ≥ 3)
        if biome_name == "volcanic" or dungeon_level >= 3:
            self._add_lava(rooms, tiles, W, H, rng, dungeon_level)

        # Assign entrance (first room) and exit/boss (last room)
        rooms.sort(key=lambda r: (r.x, r.y))   # deterministic order
        entry_room = rooms[0]
        exit_room  = rooms[-1]

        ecol, erow = entry_room.center()
        tiles[ecol][erow] = DENTRY

        xcol, xrow = exit_room.center()
        tiles[xcol][xrow] = DEXIT

        # Spawn positions (interior tiles of middle rooms, not too close to entry/exit)
        spawns: list[tuple[int,int]] = []
        for room in rooms[1:-1]:
            inner = list(room.inner_tiles())
            rng.shuffle(inner)
            per_room = max(1, 2 + dungeon_level)
            for col, row in inner[:per_room]:
                if tiles[col][row] == DFLOOR:
                    spawns.append((col, row))

        # Boss position: centre of exit room (slightly offset from portal)
        bx = xcol + 2 if xcol + 2 < exit_room.x + exit_room.w - 1 else xcol - 2
        boss_spawn = (max(exit_room.x+1, min(exit_room.x+exit_room.w-2, bx)), xrow)

        return DungeonMap(
            width        = W,
            height       = H,
            tile_size    = tile_size,
            tiles        = tiles,
            rooms        = rooms,
            entry_pos    = (ecol, erow),
            exit_pos     = (xcol, xrow),
            monster_spawns = spawns,
            boss_spawn   = boss_spawn,
            dungeon_level = dungeon_level,
            biome_name   = biome_name,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _connect_rooms(self, rooms: list[Room], tiles, rng):
        """Connect every room to its nearest unconnected neighbour (MST-like)."""
        if len(rooms) < 2:
            return
        connected = {0}
        while len(connected) < len(rooms):
            best_d = float("inf")
            best_pair = (0, 1)
            for ci in connected:
                for cj in range(len(rooms)):
                    if cj in connected:
                        continue
                    d = math.hypot(
                        rooms[ci].center()[0] - rooms[cj].center()[0],
                        rooms[ci].center()[1] - rooms[cj].center()[1],
                    )
                    if d < best_d:
                        best_d = d
                        best_pair = (ci, cj)
            self._carve_corridor(rooms[best_pair[0]], rooms[best_pair[1]],
                                 tiles, rng)
            connected.add(best_pair[1])

    def _carve_corridor(self, a: Room, b: Room, tiles, rng):
        ax, ay = a.center()
        bx, by = b.center()
        # L-shaped corridor: horizontal then vertical (or vice-versa)
        if rng.random() < 0.5:
            self._hcorr(tiles, ax, bx, ay)
            self._vcorr(tiles, ay, by, bx)
        else:
            self._vcorr(tiles, ay, by, ax)
            self._hcorr(tiles, ax, bx, by)

    def _hcorr(self, tiles, x1, x2, y):
        for x in range(min(x1,x2), max(x1,x2)+1):
            if 0 <= x < len(tiles) and 0 <= y < len(tiles[0]):
                if tiles[x][y] == DWALL:
                    tiles[x][y] = DCORR

    def _vcorr(self, tiles, y1, y2, x):
        for y in range(min(y1,y2), max(y1,y2)+1):
            if 0 <= x < len(tiles) and 0 <= y < len(tiles[0]):
                if tiles[x][y] == DWALL:
                    tiles[x][y] = DCORR

    def _add_lava(self, rooms, tiles, W, H, rng, depth):
        n_pools = depth + rng.randint(1, 3)
        for _ in range(n_pools * 10):
            if n_pools <= 0:
                break
            col = rng.randint(2, W-3)
            row = rng.randint(2, H-3)
            if tiles[col][row] != DWALL:
                continue
            # 2×2 lava pool
            for dc in range(2):
                for dr in range(2):
                    if tiles[col+dc][row+dr] == DWALL:
                        tiles[col+dc][row+dr] = DLAVA
            n_pools -= 1

    def _fallback_rooms(self, W, H, tiles) -> list[Room]:
        """Guarantee at least 3 rooms if placement fails."""
        rooms = []
        positions = [(2, 2, 8, 8), (W//2-4, H//2-4, 8, 8), (W-12, H-12, 8, 8)]
        for rx, ry, rw, rh in positions:
            r = Room(rx, ry, rw, rh)
            rooms.append(r)
            for col, row in r.inner_tiles():
                if 0 <= col < W and 0 <= row < H:
                    tiles[col][row] = DFLOOR
        return rooms
