"""
systems/biomes.py
══════════════════════════════════════════════════════════════════
5 biomas que cubren diferentes regiones del mapa.

Bioma        Tiles propios       Efecto jugador       Spawn destacado
───────────  ──────────────────  ───────────────────  ───────────────
Grassland    hierba/suciedad     ninguno              todos equitativo
Snowfield    nieve/hielo         -18% velocidad       skeleton, orc
Desert       arena/roca arenosa  -0.8 HP/s al sol     orc, dark_wizard
Swamp        pantano/agua turbia -22% vel, veneno     zombie, dark_wizard
Volcanic     lava/roca negra     lava -15 HP/s        dragon, orc

Efectos aplicados en `main.py` cada frame al actualizar el jugador.
"""
from __future__ import annotations
import math
import random
from constants import (
    TILE_GRASS, TILE_DIRT, TILE_WATER, TILE_TREE, TILE_STONE,
    TILE_LAVA, TILE_SNOW, TILE_SAND, TILE_SWAMP,
)

# ── Catálogo ──────────────────────────────────────────────────────────────────

BIOMES: dict[str, dict] = {
    "grassland": {
        "name":         "Praderas",
        "icon":         "🌿",
        "color":        ( 34, 139,  34),   # minimap tint
        "ambient_tint": None,              # no tint overlay
        "speed_mult":   1.00,
        "damage_ps":    0.0,               # HP por segundo de daño ambiental
        "damage_source":"",
        "poison_chance":0.0,              # prob/s de envenenamiento en swamp
        "tile_primary": TILE_GRASS,
        "tile_secondary":TILE_DIRT,
        "tile_water":   TILE_WATER,
        "tile_stone":   TILE_STONE,
        "spawn_weights": {                 # multiplicadores de peso de spawn
            "rat":1.2, "zombie":1.0, "skeleton":1.0,
            "orc":0.8, "dark_wizard":0.7, "dragon":0.5,
        },
        "description": "Terreno equilibrado. Sin efectos especiales.",
    },
    "snowfield": {
        "name":         "Tundra",
        "icon":         "❄",
        "color":        (180, 215, 240),
        "ambient_tint": (160, 200, 255, 28),   # rgba overlay ligero azul-blanco
        "speed_mult":   0.82,
        "damage_ps":    0.0,
        "damage_source":"",
        "poison_chance":0.0,
        "tile_primary": TILE_SNOW,
        "tile_secondary":TILE_STONE,
        "tile_water":   TILE_SNOW,
        "tile_stone":   TILE_STONE,
        "spawn_weights": {
            "rat":0.6, "zombie":0.8, "skeleton":1.6,
            "orc":1.4, "dark_wizard":0.8, "dragon":0.8,
        },
        "description": "El frío reduce tu velocidad un 18 %.",
    },
    "desert": {
        "name":         "Desierto",
        "icon":         "🏜",
        "color":        (210, 180,  80),
        "ambient_tint": (255, 200,  60, 22),   # tinte cálido anaranjado
        "speed_mult":   1.00,
        "damage_ps":    0.0,                   # el desierto no daña por suelo
        "damage_source":"",
        "poison_chance":0.0,
        "tile_primary": TILE_SAND,
        "tile_secondary":TILE_SAND,
        "tile_water":   TILE_SAND,             # no hay agua en desierto
        "tile_stone":   TILE_STONE,
        "spawn_weights": {
            "rat":0.7, "zombie":0.5, "skeleton":0.8,
            "orc":1.8, "dark_wizard":1.5, "dragon":0.9,
        },
        "description": "Terreno árido. Velocidad normal, sin efectos.",
    },
    "swamp": {
        "name":         "Pantano",
        "icon":         "🌿",
        "color":        ( 40, 100,  50),
        "ambient_tint": ( 50, 120,  30, 35),   # tinte verde oscuro
        "speed_mult":   0.78,
        "damage_ps":    0.0,
        "damage_source":"swamp",
        "poison_chance":0.0,                   # pantano no hace daño de suelo
        "tile_primary": TILE_SWAMP,
        "tile_secondary":TILE_SWAMP,
        "tile_water":   TILE_SWAMP,
        "tile_stone":   TILE_STONE,
        "spawn_weights": {
            "rat":0.8, "zombie":1.9, "skeleton":0.9,
            "orc":0.7, "dark_wizard":1.7, "dragon":0.6,
        },
        "description": "El fango frena tu velocidad un 22%.",
    },
    "volcanic": {
        "name":         "Tierra Volcánica",
        "icon":         "🌋",
        "color":        (180,  50,  20),
        "ambient_tint": (255,  80,  10, 32),   # tinte rojo intenso
        "speed_mult":   1.00,
        "damage_ps":    0.0,                   # la lava hace el daño al tocarla
        "damage_source":"",
        "poison_chance":0.0,
        "tile_primary": TILE_STONE,
        "tile_secondary":TILE_STONE,
        "tile_water":   TILE_LAVA,             # el agua es lava aquí
        "tile_stone":   TILE_STONE,
        "spawn_weights": {
            "rat":0.5, "zombie":0.6, "skeleton":1.0,
            "orc":1.3, "dark_wizard":1.1, "dragon":2.2,
        },
        "description": "La lava es letal. Los dragones campan a sus anchas.",
    },
}

BIOME_ORDER = list(BIOMES.keys())

# Daño de lava por segundo cuando el jugador está dentro de un tile de lava
LAVA_DAMAGE_PS = 15.0

# Veneno del pantano: dmg por pulso cuando se activa
SWAMP_POISON_DMG = 2


# ── Biome map generator (Voronoi simplificado) ────────────────────────────────

class BiomeMap:
    """
    Asigna un bioma a cada tile del mapa usando centros de Voronoi aleatorios.
    El centro del mapa (spawn) es siempre 'grassland'.
    """

    def __init__(self, world_w: int, world_h: int, seed: int = 42):
        self.world_w = world_w
        self.world_h = world_h
        self._map: list[list[str]] = [
            ["grassland"] * world_h for _ in range(world_w)
        ]
        self._generate(seed)

    def _generate(self, seed: int):
        rng = random.Random(seed + 31337)
        W, H = self.world_w, self.world_h
        cx, cy = W // 2, H // 2

        # Crear entre 4 y 6 centros de Voronoi por bioma no-grassland
        non_grass = [b for b in BIOME_ORDER if b != "grassland"]
        centers: list[tuple[int, int, str]] = []

        # grassland: 2 centros cerca del spawn
        for _ in range(2):
            offset = rng.randint(15, 30)
            angle  = rng.uniform(0, math.tau)
            ccx    = int(cx + math.cos(angle) * offset)
            ccy    = int(cy + math.sin(angle) * offset)
            centers.append((ccx, ccy, "grassland"))

        # Resto de biomas: 1-2 centros cada uno
        for biome in non_grass:
            for _ in range(rng.randint(1, 2)):
                for _ in range(40):
                    bx = rng.randint(10, W - 10)
                    by = rng.randint(10, H - 10)
                    if math.hypot(bx - cx, by - cy) > 28:
                        centers.append((bx, by, biome))
                        break

        # Asignar cada tile al centro más cercano
        for col in range(W):
            for row in range(H):
                best_d  = float("inf")
                best_b  = "grassland"
                for bcx, bcy, bname in centers:
                    d = math.hypot(col - bcx, row - bcy)
                    if d < best_d:
                        best_d = d
                        best_b = bname
                self._map[col][row] = best_b

        # Forzar spawn center como grassland
        r_clear = 20
        for col in range(max(0, cx - r_clear), min(W, cx + r_clear + 1)):
            for row in range(max(0, cy - r_clear), min(H, cy + r_clear + 1)):
                if math.hypot(col - cx, row - cy) <= r_clear:
                    self._map[col][row] = "grassland"

    def get(self, col: int, row: int) -> str:
        if 0 <= col < self.world_w and 0 <= row < self.world_h:
            return self._map[col][row]
        return "grassland"

    def get_px(self, px: float, py: float, tile_size: int) -> str:
        return self.get(int(px // tile_size), int(py // tile_size))

    def biome_data(self, col: int, row: int) -> dict:
        return BIOMES[self.get(col, row)]

    def biome_at_px(self, px: float, py: float, tile_size: int) -> dict:
        return BIOMES[self.get_px(px, py, tile_size)]


# ── Player effect helpers ─────────────────────────────────────────────────────

def effective_speed(base_speed: float, biome: dict) -> float:
    return base_speed * biome["speed_mult"]


def ambient_damage(biome: dict, dt: float) -> float:
    """Returns HP damage per frame from biome ambient effect (desert heat)."""
    return biome["damage_ps"] * dt


def swamp_poison_tick(biome: dict, dt: float, rng=random) -> bool:
    """Returns True if a swamp poison pulse triggers this frame."""
    if biome.get("poison_chance", 0) <= 0:
        return False
    return rng.random() < biome["poison_chance"] * dt


def lava_damage(player_x: float, player_y: float,
                biome_map: "BiomeMap", tile_size: int, dt: float) -> float:
    """
    Checks the 4 tiles under the player. Returns lava damage per frame
    proportional to how many adjacent tiles are lava.
    """
    col = int(player_x // tile_size)
    row = int(player_y // tile_size)
    lava_count = 0
    for dc, dr in ((0,0),(1,0),(-1,0),(0,1),(0,-1)):
        b = biome_map.get(col+dc, row+dr)
        if BIOMES.get(b, {}).get("tile_water") == TILE_LAVA:
            lava_count += 1
    if lava_count == 0:
        return 0.0
    return LAVA_DAMAGE_PS * (lava_count / 5.0) * dt
