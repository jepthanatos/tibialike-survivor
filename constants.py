SCREEN_W  = 1280
SCREEN_H  = 720
TILE_SIZE = 32
FPS       = 60
MAP_W     = 150   # tiles
MAP_H     = 150   # tiles

HUD_H  = 90
GAME_H = SCREEN_H - HUD_H

# ── Tile IDs ─────────────────────────────────────────────────────────────────
TILE_GRASS = 0
TILE_DIRT  = 1
TILE_WATER = 2
TILE_TREE  = 3
TILE_STONE = 4

IMPASSABLE_TILES = {TILE_WATER, TILE_TREE}

# 3 colour variants per tile type
TILE_COLORS = {
    TILE_GRASS: [(34, 139, 34), (40, 150, 40), (28, 122, 28)],
    TILE_DIRT:  [(139, 90, 43), (125, 80, 38), (150, 98, 50)],
    TILE_WATER: [(28, 96, 192), (22, 88, 178), (34, 108, 205)],
    TILE_TREE:  [(15, 85, 15),  (10, 70, 10),  (20, 95, 20)],
    TILE_STONE: [(115,115,120), (105,105,110), (128,128,132)],
}

# ── Palette ───────────────────────────────────────────────────────────────────
C_BLACK     = (  0,   0,   0)
C_WHITE     = (255, 255, 255)
C_GRAY      = (160, 160, 160)
C_DARK      = ( 20,  20,  20)
C_DARK_GRAY = ( 45,  45,  45)
C_RED       = (220,  50,  50)
C_YELLOW    = (255, 220,  50)
C_ORANGE    = (255, 140,   0)
C_GREEN     = ( 50, 200,  80)
C_BLUE      = ( 70, 130, 200)
C_CYAN      = ( 50, 200, 220)
C_PURPLE    = (160,  50, 200)

C_PLAYER   = ( 80, 140, 210)
C_PLAYER_H = (150, 200, 245)   # highlight dot

C_HP_BAR   = (210,  50,  50)
C_HP_BG    = ( 60,   0,   0)
C_MP_BAR   = ( 60,  90, 230)
C_MP_BG    = (  0,   0,  60)
C_XP_BAR   = ( 50, 200,  90)
C_XP_BG    = (  0,  40,  10)

# ── Storm ─────────────────────────────────────────────────────────────────────
C_STORM_FOG    = ( 45,  10,  80)   # purple-dark fog fill
C_STORM_EDGE   = (140,  40, 220)   # edge glow colour
C_STORM_NEXT   = ( 80, 180, 255)   # next-zone preview ring
C_STORM_SAFE   = ( 55, 210,  90)   # "SAFE" text
C_STORM_DANGER = (220,  50,  50)   # "STORM" warning text

# ── Biome tile IDs (added in Phase 8) ────────────────────────────────────────
TILE_LAVA      = 5   # impassable, deals damage at edges
TILE_SNOW      = 6   # walkable but slows
TILE_SAND      = 7   # walkable, desert
TILE_SWAMP     = 8   # walkable swamp floor (slow + poison risk)

IMPASSABLE_TILES = {TILE_WATER, TILE_TREE, TILE_LAVA}   # override previous set

# ── Biome colours ─────────────────────────────────────────────────────────────
C_BIOME_BANNER   = (200, 220, 255)
