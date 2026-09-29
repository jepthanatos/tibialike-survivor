import pygame
import math
import random
from constants import (
    TILE_GRASS, TILE_DIRT, TILE_WATER, TILE_TREE, TILE_STONE,
    TILE_LAVA, TILE_SNOW, TILE_SAND, TILE_SWAMP,
    IMPASSABLE_TILES,
)

MM_SIZE = 120   # minimap px

# ── Tile colour definitions (3 variants each) ─────────────────────────────────
TILE_COLORS = {
    TILE_GRASS: [(34,139,34),(40,150,40),(28,122,28)],
    TILE_DIRT:  [(139,90,43),(125,80,38),(150,98,50)],
    TILE_WATER: [(28,96,192),(22,88,178),(34,108,205)],
    TILE_TREE:  [(15,85,15),(10,70,10),(20,95,20)],
    TILE_STONE: [(115,115,120),(105,105,110),(128,128,132)],
    # Phase 8: biome tiles
    TILE_LAVA:  [(220,60,10),(200,50,5),(240,70,15)],
    TILE_SNOW:  [(220,235,250),(210,225,245),(230,242,255)],
    TILE_SAND:  [(210,185,95),(195,170,80),(225,198,110)],
    TILE_SWAMP: [(48,80,38),(40,72,30),(55,88,44)],
}

# Minimap colour per tile
_MM_COLORS = {
    TILE_WATER: (28, 80,180),
    TILE_TREE:  ( 0, 55,  0),
    TILE_STONE: (88, 88, 88),
    TILE_DIRT:  (100,65, 30),
    TILE_GRASS: (24, 96, 24),
    TILE_LAVA:  (200,50, 10),
    TILE_SNOW:  (200,220,240),
    TILE_SAND:  (200,175, 80),
    TILE_SWAMP: (40, 75, 35),
}


class World:
    def __init__(self, width, height, tile_size, seed=42):
        self.width     = width
        self.height    = height
        self.tile_size = tile_size

        self.tiles    = [[TILE_GRASS] * height for _ in range(width)]
        self.variants = [[0]          * height for _ in range(width)]

        # BiomeMap set externally via apply_biomes() before first draw
        self._biome_map = None

        self._generate(random.Random(seed))
        self._build_tile_surfaces()
        self._build_minimap()

        # ── Fog of War ─────────────────────────────────────────────────────
        self._explored      = [[False]*width  for _ in range(height)]
        self._VISION_RADIUS = 9     # tiles visible around player
        self._fog_tile      = None  # cached black surface

    # ── Generation ────────────────────────────────────────────────────────────
    def _generate(self, rng):
        W, H = self.width, self.height

        # Dirt patches
        if W > 10 and H > 10:
            for _ in range(25):
                cx, cy = rng.randint(5,W-5), rng.randint(5,H-5)
                r = rng.randint(3,min(12,W//4))
                for x in range(max(0,cx-r), min(W,cx+r+1)):
                    for y in range(max(0,cy-r), min(H,cy+r+1)):
                        if (x-cx)**2+(y-cy)**2 <= r*r:
                            self.tiles[x][y] = TILE_DIRT

        # Stone zones (skip if map too small)
        if W > 40 and H > 40:
            for _ in range(7):
                cx, cy = rng.randint(20,W-20), rng.randint(20,H-20)
                w, h   = rng.randint(8,18), rng.randint(8,18)
                for x in range(max(0,cx-w//2), min(W,cx+w//2)):
                    for y in range(max(0,cy-h//2), min(H,cy+h//2)):
                        self.tiles[x][y] = TILE_STONE

        # Water pools
        for _ in range(14):
            cx, cy = rng.randint(10,W-10), rng.randint(10,H-10)
            r = rng.randint(2,7)
            for x in range(max(0,cx-r), min(W,cx+r+1)):
                for y in range(max(0,cy-r), min(H,cy+r+1)):
                    if (x-cx)**2+(y-cy)**2 <= r*r*0.8:
                        self.tiles[x][y] = TILE_WATER

        # Tree clusters
        for _ in range(55):
            cx, cy = rng.randint(3,W-3), rng.randint(3,H-3)
            for _ in range(rng.randint(4,28)):
                x = cx+rng.randint(-5,5); y = cy+rng.randint(-5,5)
                if 2<=x<W-2 and 2<=y<H-2:
                    self.tiles[x][y] = TILE_TREE

        # Colour variants
        for x in range(W):
            for y in range(H):
                self.variants[x][y] = rng.randint(0,2)

        # Clear centre spawn (10-tile radius)
        cx, cy = W//2, H//2
        for x in range(cx-10, cx+11):
            for y in range(cy-10, cy+11):
                if 0<=x<W and 0<=y<H:
                    self.tiles[x][y] = TILE_GRASS

    # ── Biome integration ─────────────────────────────────────────────────────
    def apply_biomes(self, biome_map):
        """
        Overlay biome-specific tiles on top of the base generation.
        Called once after BiomeMap is created.
        """
        from systems.biomes import BIOMES, TILE_LAVA
        self._biome_map = biome_map
        W, H = self.width, self.height
        cx, cy = W//2, H//2
        keep_radius = 15   # protect grassland spawn centre

        for col in range(W):
            for row in range(H):
                if math.hypot(col-cx, row-cy) < keep_radius:
                    continue
                bname = biome_map.get(col, row)
                bd    = BIOMES[bname]
                cur   = self.tiles[col][row]

                # Replace base tile types with biome equivalents
                if bname == "snowfield":
                    if cur == TILE_GRASS: self.tiles[col][row] = TILE_SNOW
                    elif cur == TILE_DIRT: self.tiles[col][row] = TILE_SNOW
                    elif cur == TILE_WATER: self.tiles[col][row] = TILE_SNOW  # frozen lakes
                elif bname == "desert":
                    if cur in (TILE_GRASS, TILE_DIRT): self.tiles[col][row] = TILE_SAND
                    elif cur == TILE_WATER: self.tiles[col][row] = TILE_SAND  # no water
                    elif cur == TILE_TREE:  self.tiles[col][row] = TILE_SAND  # no trees
                elif bname == "swamp":
                    if cur == TILE_GRASS: self.tiles[col][row] = TILE_SWAMP
                    elif cur == TILE_DIRT: self.tiles[col][row] = TILE_SWAMP
                    elif cur == TILE_WATER: self.tiles[col][row] = TILE_SWAMP
                elif bname == "volcanic":
                    if cur == TILE_GRASS: self.tiles[col][row] = TILE_STONE
                    elif cur == TILE_DIRT: self.tiles[col][row] = TILE_STONE
                    elif cur == TILE_WATER: self.tiles[col][row] = TILE_LAVA
                    elif cur == TILE_TREE:  self.tiles[col][row] = TILE_STONE

        self._build_tile_surfaces()
        self._build_minimap()

    # ── Surface cache ─────────────────────────────────────────────────────────
    def _build_tile_surfaces(self):
        ts = self.tile_size
        self._surfs = {}

        # Try loading real sprites from sprites.json
        from core.sprite_loader import sprites as _sl
        _TILE_SPRITE_KEY = {
            TILE_GRASS: 'grass', TILE_DIRT: 'dirt', TILE_WATER: 'water',
            TILE_STONE: 'stone', TILE_LAVA: 'lava', TILE_SNOW: 'snow',
            TILE_SAND: 'sand',   TILE_SWAMP: 'swamp',
        }

        for tile_id, colors in TILE_COLORS.items():
            surfs = []
            # Try real sprite (same for all animation frames)
            _skey = _TILE_SPRITE_KEY.get(tile_id)
            _sprite_surf = None
            if _skey:
                _sprite_surf = _sl.get('tiles', _skey, ts, ts)

            for i, color in enumerate(colors):
                if _sprite_surf is not None:
                    surfs.append(_sprite_surf.copy())
                    continue
                s = pygame.Surface((ts, ts))
                s.fill(color)

                if tile_id == TILE_TREE:
                    s.fill((20,55,20))
                    pygame.draw.circle(s,(25,118,25),(ts//2,ts//2-2),ts//2-3)
                    pygame.draw.rect(s,(88,55,18),(ts//2-3,ts//2+1,6,ts//2-1))

                elif tile_id == TILE_WATER:
                    shimmer = (min(255,color[0]+22),min(255,color[1]+22),min(255,color[2]+32))
                    for j in range(0,ts,8):
                        pygame.draw.line(s,shimmer,(0,j+i*2),(ts//3,j+i*2),1)

                elif tile_id == TILE_STONE:
                    lc = tuple(max(0,c-22) for c in color)
                    pygame.draw.line(s,lc,(ts//2,0),(ts//2,ts),1)
                    pygame.draw.line(s,lc,(0,ts//2),(ts,ts//2),1)

                elif tile_id == TILE_LAVA:
                    # Animated-look cracks
                    dc = tuple(min(255,c+40) for c in color)
                    for j in range(0,ts,6):
                        pygame.draw.line(s,dc,(j,0),(0,j),1)
                    pygame.draw.rect(s,(255,120,20),(ts//2-4,ts//2-4,8,8))

                elif tile_id == TILE_SNOW:
                    # Light grid sparkle
                    sparkle = (240,248,255)
                    for sx2 in range(0,ts,10):
                        for sy2 in range(0,ts,10):
                            if (sx2+sy2+i*3)%3==0:
                                pygame.draw.circle(s,sparkle,(sx2,sy2),1)

                elif tile_id == TILE_SAND:
                    # Subtle ripple lines
                    rc = tuple(max(0,c-15) for c in color)
                    for j in range(2,ts,8):
                        pygame.draw.line(s,rc,(0,j),(ts,j+2),1)

                elif tile_id == TILE_SWAMP:
                    # Dark splotches
                    dc2 = tuple(max(0,c-18) for c in color)
                    for sx2 in range(0,ts,9):
                        for sy2 in range(0,ts,9):
                            if (sx2*sy2+i)%7==0:
                                pygame.draw.circle(s,dc2,(sx2,sy2),2)

                surfs.append(s)
            self._surfs[tile_id] = surfs

    # ── Minimap ───────────────────────────────────────────────────────────────
    def _build_minimap(self):
        self._mm = pygame.Surface((MM_SIZE, MM_SIZE))
        self._mm.fill((15,15,15))
        sx = MM_SIZE / self.width
        sy = MM_SIZE / self.height
        for x in range(self.width):
            for y in range(self.height):
                col = _MM_COLORS.get(self.tiles[x][y], (80,80,80))
                self._mm.set_at(
                    (min(MM_SIZE-1,int(x*sx)), min(MM_SIZE-1,int(y*sy))), col)

    # ── Public helpers ────────────────────────────────────────────────────────
    def get_minimap(self):
        return self._mm, MM_SIZE

    def is_walkable(self, col, row):
        if col<0 or col>=self.width or row<0 or row>=self.height:
            return False
        return self.tiles[col][row] not in IMPASSABLE_TILES

    def is_rect_walkable(self, left, top, right, bottom):
        ts = self.tile_size
        for px, py in ((left,top),(right-1,top),(left,bottom-1),(right-1,bottom-1)):
            if not self.is_walkable(int(px//ts), int(py//ts)):
                return False
        return True

    # ── Rendering ─────────────────────────────────────────────────────────────
    def _draw_fog(self, screen, camera):
        """Render black tiles over unexplored areas (Tibia-style fog of war)."""
        if not hasattr(self, '_explored'):
            return
        ts   = self.tile_size
        ox   = int(camera.offset_x)
        oy   = int(camera.offset_y)
        col0 = max(0, ox // ts - 1)
        col1 = min(self.width,  col0 + camera.view_w // ts + 3)
        row0 = max(0, oy // ts - 1)
        row1 = min(self.height, row0 + camera.view_h // ts + 3)
        # Create/reuse fog tile surface
        if self._fog_tile is None or self._fog_tile.get_size() != (ts, ts):
            self._fog_tile = pygame.Surface((ts, ts))
            self._fog_tile.fill((0, 0, 0))
        fog = self._fog_tile
        for row in range(row0, row1):
            for col in range(col0, col1):
                if not self._explored[row][col]:
                    screen.blit(fog, (col * ts - ox, row * ts - oy))

    def reveal_around(self, px: float, py: float):
        """Mark tiles within vision radius of (px,py) as explored."""
        ts  = self.tile_size
        pcol = int(px // ts)
        prow = int(py // ts)
        r    = self._VISION_RADIUS
        for dr in range(-r, r+1):
            for dc in range(-r, r+1):
                # Circular vision
                if dc*dc + dr*dr <= r*r:
                    col = pcol + dc; row = prow + dr
                    if 0 <= col < self.width and 0 <= row < self.height:
                        self._explored[row][col] = True

    def is_explored(self, col: int, row: int) -> bool:
        if 0 <= col < self.width and 0 <= row < self.height:
            return self._explored[row][col]
        return True  # out-of-bounds = treated as explored (edge)

    def draw(self, screen, camera):
        ts = self.tile_size
        c0 = max(0, int(camera.offset_x//ts))
        r0 = max(0, int(camera.offset_y//ts))
        c1 = min(self.width,  int((camera.offset_x+camera.view_w)//ts)+2)
        r1 = min(self.height, int((camera.offset_y+camera.view_h)//ts)+2)
        ox = round(camera.offset_x); oy = round(camera.offset_y)
        for col in range(c0, c1):
            for row in range(r0, r1):
                surf = self._surfs[self.tiles[col][row]][self.variants[col][row]]
                screen.blit(surf, (col*ts-ox, row*ts-oy))

    # ── Phase 5 dungeon zones ─────────────────────────────────────────────────
        self._draw_fog(screen, camera)

    def apply_dungeon_zones(self, zones):
        from constants import TILE_STONE, TILE_GRASS
        for zone in zones:
            cr, cc, r = zone.center_row, zone.center_col, zone.radius
            for col in range(max(0,cc-r), min(self.width,cc+r+1)):
                for row in range(max(0,cr-r), min(self.height,cr+r+1)):
                    if math.hypot(col-cc,row-cr)<=r:
                        if self.tiles[col][row]==TILE_GRASS:
                            self.tiles[col][row]=TILE_STONE
        self._build_minimap()
        self._build_tile_surfaces()
