"""Tests unitarios para tests/fake_world.py y core/world.py (lógica de tiles)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame  # instala pygame falso PRIMERO

import unittest
from tests.fake_world import FakeWorld
from constants import TILE_GRASS, TILE_WATER, TILE_TREE, IMPASSABLE_TILES
from core.world import World


# ── FakeWorld ──────────────────────────────────────────────────────────────────

class TestFakeWorldWalkable(unittest.TestCase):

    def test_empty_world_is_fully_walkable(self):
        w = FakeWorld(width=10, height=10, tile_size=32)
        self.assertTrue(w.is_walkable(5, 5))

    def test_impassable_tile_not_walkable(self):
        w = FakeWorld(width=10, height=10, impassable={(3, 4)})
        self.assertFalse(w.is_walkable(3, 4))

    def test_out_of_bounds_not_walkable(self):
        w = FakeWorld(width=10, height=10)
        self.assertFalse(w.is_walkable(-1, 0))
        self.assertFalse(w.is_walkable(0, -1))
        self.assertFalse(w.is_walkable(10, 0))
        self.assertFalse(w.is_walkable(0, 10))

    def test_border_tiles_walkable(self):
        w = FakeWorld(width=10, height=10)
        self.assertTrue(w.is_walkable(0, 0))
        self.assertTrue(w.is_walkable(9, 9))

    def test_adjacent_tile_walkable_when_only_one_blocked(self):
        w = FakeWorld(width=10, height=10, impassable={(5, 5)})
        self.assertTrue(w.is_walkable(5, 4))
        self.assertTrue(w.is_walkable(4, 5))


class TestFakeWorldRectWalkable(unittest.TestCase):

    def test_clear_area_walkable(self):
        w = FakeWorld(width=20, height=20, tile_size=32)
        # Rectángulo bien dentro del mapa
        self.assertTrue(w.is_rect_walkable(64, 64, 96, 96))

    def test_rect_touching_impassable_corner_not_walkable(self):
        # Tile (3,3) = impassable, el rect toca su esquina
        w = FakeWorld(width=20, height=20, tile_size=32, impassable={(3, 3)})
        # El rect cuyos corners son (96,96)-(128,128) cae justo en tile (3,3)
        self.assertFalse(w.is_rect_walkable(96, 96, 128, 128))

    def test_tiny_rect_within_tile(self):
        w = FakeWorld(width=20, height=20, tile_size=32)
        self.assertTrue(w.is_rect_walkable(10, 10, 20, 20))


# ── World (real) lógica de tiles ──────────────────────────────────────────────

class TestRealWorldGeneration(unittest.TestCase):

    def setUp(self):
        # World pequeño para tests rápidos (sin display)
        self.world = World(width=40, height=40, tile_size=32, seed=7)

    def test_dimensions_correct(self):
        self.assertEqual(self.world.width, 40)
        self.assertEqual(self.world.height, 40)
        self.assertEqual(self.world.tile_size, 32)

    def test_tiles_array_correct_shape(self):
        self.assertEqual(len(self.world.tiles), 40)
        self.assertEqual(len(self.world.tiles[0]), 40)

    def test_variants_array_correct_shape(self):
        self.assertEqual(len(self.world.variants), 40)
        self.assertEqual(len(self.world.variants[0]), 40)

    def test_variants_within_range(self):
        for col in range(self.world.width):
            for row in range(self.world.height):
                v = self.world.variants[col][row]
                self.assertIn(v, (0, 1, 2),
                              f"Variant {v} fuera de rango en ({col},{row})")

    def test_all_tile_ids_valid(self):
        valid_ids = {TILE_GRASS, TILE_WATER, TILE_TREE,
                     *range(5)}  # 0-4 según constants
        for col in range(self.world.width):
            for row in range(self.world.height):
                tid = self.world.tiles[col][row]
                self.assertIn(tid, valid_ids,
                              f"Tile ID inválido {tid} en ({col},{row})")

    def test_centre_spawn_is_walkable(self):
        cx, cy = self.world.width // 2, self.world.height // 2
        # El generador despeja un radio de 10 tiles alrededor del centro
        self.assertTrue(self.world.is_walkable(cx, cy))
        self.assertTrue(self.world.is_walkable(cx + 5, cy))
        self.assertTrue(self.world.is_walkable(cx, cy + 5))

    def test_out_of_bounds_not_walkable(self):
        self.assertFalse(self.world.is_walkable(-1, 0))
        self.assertFalse(self.world.is_walkable(0, -1))
        self.assertFalse(self.world.is_walkable(self.world.width, 0))
        self.assertFalse(self.world.is_walkable(0, self.world.height))

    def test_water_tiles_not_walkable(self):
        for col in range(self.world.width):
            for row in range(self.world.height):
                if self.world.tiles[col][row] == TILE_WATER:
                    self.assertFalse(self.world.is_walkable(col, row))

    def test_tree_tiles_not_walkable(self):
        for col in range(self.world.width):
            for row in range(self.world.height):
                if self.world.tiles[col][row] == TILE_TREE:
                    self.assertFalse(self.world.is_walkable(col, row))

    def test_same_seed_produces_same_map(self):
        w1 = World(40, 40, 32, seed=123)
        w2 = World(40, 40, 32, seed=123)
        for col in range(40):
            for row in range(40):
                self.assertEqual(w1.tiles[col][row], w2.tiles[col][row])

    def test_different_seeds_produce_different_maps(self):
        w1 = World(40, 40, 32, seed=1)
        w2 = World(40, 40, 32, seed=2)
        diffs = sum(
            1 for col in range(40) for row in range(40)
            if w1.tiles[col][row] != w2.tiles[col][row]
        )
        self.assertGreater(diffs, 10, "Seeds distintas deberían producir mapas distintos")

    def test_minimap_returns_surface_and_size(self):
        surf, size = self.world.get_minimap()
        self.assertIsNotNone(surf)
        self.assertGreater(size, 0)

    def test_some_grass_tiles_exist(self):
        has_grass = any(
            self.world.tiles[col][row] == TILE_GRASS
            for col in range(self.world.width)
            for row in range(self.world.height)
        )
        self.assertTrue(has_grass)

    def test_impassable_tiles_constant_is_set(self):
        self.assertIn(TILE_WATER, IMPASSABLE_TILES)
        self.assertIn(TILE_TREE, IMPASSABLE_TILES)


class TestRealWorldRectWalkable(unittest.TestCase):

    def setUp(self):
        # Mundo totalmente de hierba (seed genera suelo limpio en el centro)
        self.world = World(40, 40, 32, seed=99)
        self.cx = self.world.width // 2
        self.cy = self.world.height // 2

    def test_clear_centre_area_walkable(self):
        ts = self.world.tile_size
        cx_px = self.cx * ts
        cy_px = self.cy * ts
        self.assertTrue(
            self.world.is_rect_walkable(cx_px - 8, cy_px - 8,
                                        cx_px + 8, cy_px + 8)
        )

    def test_negative_coords_not_walkable(self):
        self.assertFalse(self.world.is_rect_walkable(-100, -100, -50, -50))


if __name__ == '__main__':
    unittest.main()
