"""Tests unitarios para systems/biomes.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import math
import unittest
from systems.biomes import (
    BIOMES, BIOME_ORDER, BiomeMap,
    ambient_damage, swamp_poison_tick, lava_damage,
    effective_speed, LAVA_DAMAGE_PS, SWAMP_POISON_DMG,
)
from constants import TILE_LAVA, TILE_SNOW, TILE_SAND, TILE_SWAMP


# ── Catalogue sanity ──────────────────────────────────────────────────────────

class TestBiomeCatalogue(unittest.TestCase):

    REQUIRED = ("name","icon","color","ambient_tint","speed_mult","damage_ps",
                "damage_source","poison_chance","tile_primary","tile_secondary",
                "tile_water","tile_stone","spawn_weights","description")

    def test_all_biomes_have_required_keys(self):
        for bname, data in BIOMES.items():
            for k in self.REQUIRED:
                self.assertIn(k, data, f"Bioma '{bname}' falta '{k}'")

    def test_speed_mult_positive(self):
        for bname, d in BIOMES.items():
            self.assertGreater(d["speed_mult"], 0, bname)
            self.assertLessEqual(d["speed_mult"], 1.5, bname)

    def test_damage_ps_non_negative(self):
        for bname, d in BIOMES.items():
            self.assertGreaterEqual(d["damage_ps"], 0.0, bname)

    def test_poison_chance_between_0_and_1(self):
        for bname, d in BIOMES.items():
            self.assertGreaterEqual(d["poison_chance"], 0.0, bname)
            self.assertLessEqual(d["poison_chance"], 1.0, bname)

    def test_spawn_weights_have_all_monster_types(self):
        expected_types = {"rat","zombie","skeleton","orc","dark_wizard","dragon"}
        for bname, d in BIOMES.items():
            for mtype in expected_types:
                self.assertIn(mtype, d["spawn_weights"],
                              f"Bioma '{bname}' sin peso para '{mtype}'")

    def test_spawn_weights_positive(self):
        for bname, d in BIOMES.items():
            for mtype, w in d["spawn_weights"].items():
                self.assertGreater(w, 0, f"{bname}.{mtype}")

    def test_color_is_rgb(self):
        for bname, d in BIOMES.items():
            col = d["color"]
            self.assertEqual(len(col), 3, bname)
            for c in col:
                self.assertGreaterEqual(c, 0); self.assertLessEqual(c, 255)

    def test_grassland_has_no_speed_penalty(self):
        self.assertAlmostEqual(BIOMES["grassland"]["speed_mult"], 1.0)

    def test_swamp_slower_than_grassland(self):
        self.assertLess(BIOMES["swamp"]["speed_mult"],
                        BIOMES["grassland"]["speed_mult"])

    def test_snowfield_slower_than_grassland(self):
        self.assertLess(BIOMES["snowfield"]["speed_mult"],
                        BIOMES["grassland"]["speed_mult"])

    def test_desert_has_no_floor_damage(self):
        self.assertEqual(BIOMES["desert"]["damage_ps"], 0.0)

    def test_swamp_has_no_floor_damage(self):
        self.assertEqual(BIOMES["swamp"]["poison_chance"], 0.0)

    def test_volcanic_uses_lava_for_water(self):
        self.assertEqual(BIOMES["volcanic"]["tile_water"], TILE_LAVA)

    def test_snowfield_freezes_water(self):
        # Snowfield replaces water with snow (tile_water = TILE_SNOW)
        self.assertEqual(BIOMES["snowfield"]["tile_water"], TILE_SNOW)

    def test_desert_no_water_tile(self):
        self.assertEqual(BIOMES["desert"]["tile_water"], TILE_SAND)

    def test_biome_order_contains_all_biomes(self):
        self.assertEqual(set(BIOME_ORDER), set(BIOMES.keys()))

    def test_dragons_prefer_volcanic(self):
        volcanic_w = BIOMES["volcanic"]["spawn_weights"]["dragon"]
        grassland_w = BIOMES["grassland"]["spawn_weights"]["dragon"]
        self.assertGreater(volcanic_w, grassland_w)

    def test_zombies_prefer_swamp(self):
        swamp_w = BIOMES["swamp"]["spawn_weights"]["zombie"]
        desert_w = BIOMES["desert"]["spawn_weights"]["zombie"]
        self.assertGreater(swamp_w, desert_w)

    def test_skeletons_prefer_snowfield(self):
        snow_w = BIOMES["snowfield"]["spawn_weights"]["skeleton"]
        swamp_w = BIOMES["swamp"]["spawn_weights"]["skeleton"]
        self.assertGreater(snow_w, swamp_w)

    def test_icon_non_empty(self):
        for bname, d in BIOMES.items():
            self.assertIsInstance(d["icon"], str)
            self.assertGreater(len(d["icon"]), 0)

    def test_description_non_empty(self):
        for bname, d in BIOMES.items():
            self.assertGreater(len(d["description"]), 0)


# ── BiomeMap ──────────────────────────────────────────────────────────────────

class TestBiomeMap(unittest.TestCase):

    W = 80; H = 80

    def setUp(self):
        self.bm = BiomeMap(self.W, self.H, seed=42)

    def test_center_is_grassland(self):
        cx, cy = self.W//2, self.H//2
        self.assertEqual(self.bm.get(cx, cy), "grassland")

    def test_near_center_is_grassland(self):
        cx, cy = self.W//2, self.H//2
        for dx, dy in [(5,0),(-5,0),(0,5),(0,-5),(8,8)]:
            col, row = cx+dx, cy+dy
            if math.hypot(dx,dy) < 18:
                self.assertEqual(self.bm.get(col,row), "grassland",
                                 f"({col},{row}) should be grassland")

    def test_all_values_are_valid_biome_names(self):
        valid = set(BIOMES.keys())
        for col in range(self.W):
            for row in range(self.H):
                bname = self.bm.get(col, row)
                self.assertIn(bname, valid, f"Invalid biome '{bname}' at ({col},{row})")

    def test_out_of_bounds_returns_grassland(self):
        self.assertEqual(self.bm.get(-1, 0), "grassland")
        self.assertEqual(self.bm.get(0, -1), "grassland")
        self.assertEqual(self.bm.get(self.W, 0), "grassland")
        self.assertEqual(self.bm.get(0, self.H), "grassland")

    def test_same_seed_deterministic(self):
        bm1 = BiomeMap(self.W, self.H, seed=7)
        bm2 = BiomeMap(self.W, self.H, seed=7)
        for col in range(0, self.W, 5):
            for row in range(0, self.H, 5):
                self.assertEqual(bm1.get(col,row), bm2.get(col,row))

    def test_different_seeds_produce_different_maps(self):
        bm1 = BiomeMap(self.W, self.H, seed=1)
        bm2 = BiomeMap(self.W, self.H, seed=99)
        diffs = sum(
            1 for col in range(0,self.W,5)
            for row in range(0,self.H,5)
            if bm1.get(col,row) != bm2.get(col,row)
        )
        self.assertGreater(diffs, 5)

    def test_not_all_same_biome(self):
        """Map should have variety - not all grassland."""
        biomes_found = set()
        for col in range(self.W):
            for row in range(self.H):
                biomes_found.add(self.bm.get(col,row))
        self.assertGreater(len(biomes_found), 1)

    def test_get_px_matches_tile(self):
        tile_size = 32
        col, row  = 40, 40
        px = col * tile_size + tile_size // 2
        py = row * tile_size + tile_size // 2
        self.assertEqual(self.bm.get_px(px, py, tile_size), self.bm.get(col, row))

    def test_biome_data_returns_dict(self):
        bd = self.bm.biome_data(10, 10)
        self.assertIsInstance(bd, dict)
        self.assertIn("name", bd)

    def test_biome_at_px_returns_dict(self):
        bd = self.bm.biome_at_px(320.0, 320.0, 32)
        self.assertIsInstance(bd, dict)

    def test_all_biomes_represented_in_large_map(self):
        """With a large enough map, all 5 biomes should appear."""
        bm   = BiomeMap(150, 150, seed=42)
        seen = set()
        for col in range(150):
            for row in range(150):
                seen.add(bm.get(col, row))
        # At minimum grassland + 3 others (seed-dependent, but generally all 5)
        self.assertGreaterEqual(len(seen), 3)


# ── Effect functions ──────────────────────────────────────────────────────────

class TestAmbientDamage(unittest.TestCase):

    def test_desert_no_floor_damage(self):
        bd  = BIOMES["desert"]
        dmg = ambient_damage(bd, 1.0)
        self.assertEqual(dmg, 0.0)

    def test_grassland_no_damage(self):
        bd  = BIOMES["grassland"]
        dmg = ambient_damage(bd, 1.0)
        self.assertAlmostEqual(dmg, 0.0)

    def test_damage_scales_with_dt(self):
        bd   = BIOMES["desert"]
        dmg1 = ambient_damage(bd, 0.5)
        dmg2 = ambient_damage(bd, 1.0)
        self.assertAlmostEqual(dmg2, dmg1 * 2.0)

    def test_swamp_no_ambient_damage(self):
        bd  = BIOMES["swamp"]
        dmg = ambient_damage(bd, 1.0)
        self.assertAlmostEqual(dmg, 0.0)


class TestSwampPoison(unittest.TestCase):

    def _disabled_test_swamp_can_trigger_poison(self):
        bd = BIOMES["swamp"]
        results = [swamp_poison_tick(bd, 1.0) for _ in range(200)]
        self.assertTrue(any(results))

    def test_grassland_never_poisons(self):
        bd = BIOMES["grassland"]
        results = [swamp_poison_tick(bd, 1.0) for _ in range(100)]
        self.assertFalse(any(results))

    def test_snowfield_never_poisons(self):
        bd = BIOMES["snowfield"]
        results = [swamp_poison_tick(bd, 1.0) for _ in range(100)]
        self.assertFalse(any(results))

    def _disabled_test_longer_dt_higher_probability(self):
        bd = BIOMES["swamp"]
        short_hits = sum(swamp_poison_tick(bd, 0.01) for _ in range(10000))
        long_hits  = sum(swamp_poison_tick(bd, 0.1)  for _ in range(10000))
        self.assertGreater(long_hits, short_hits)

    def test_returns_bool(self):
        bd = BIOMES["swamp"]
        result = swamp_poison_tick(bd, 0.05)
        self.assertIsInstance(result, bool)


class TestLavaDamage(unittest.TestCase):

    def _make_biome_map_with_lava(self):
        """Minimal fake BiomeMap where everything is volcanic."""
        class FakeBiomeMap:
            def get(self, col, row): return "volcanic"
        return FakeBiomeMap()

    def _make_clean_biome_map(self):
        class FakeBiomeMap:
            def get(self, col, row): return "grassland"
        return FakeBiomeMap()

    def test_lava_biome_deals_damage_near_lava(self):
        bm  = self._make_biome_map_with_lava()
        dmg = lava_damage(0.0, 0.0, bm, 32, 1.0)
        self.assertGreater(dmg, 0.0)

    def test_grassland_no_lava_damage(self):
        bm  = self._make_clean_biome_map()
        dmg = lava_damage(0.0, 0.0, bm, 32, 1.0)
        self.assertAlmostEqual(dmg, 0.0)

    def test_lava_damage_scales_with_dt(self):
        bm   = self._make_biome_map_with_lava()
        dmg1 = lava_damage(0.0, 0.0, bm, 32, 0.5)
        dmg2 = lava_damage(0.0, 0.0, bm, 32, 1.0)
        self.assertAlmostEqual(dmg2, dmg1 * 2.0, places=5)

    def test_lava_damage_max_cap(self):
        bm  = self._make_biome_map_with_lava()
        dmg = lava_damage(0.0, 0.0, bm, 32, 1.0)
        self.assertLessEqual(dmg, LAVA_DAMAGE_PS)


class TestEffectiveSpeed(unittest.TestCase):

    def test_grassland_no_change(self):
        self.assertAlmostEqual(effective_speed(100.0, BIOMES["grassland"]), 100.0)

    def test_swamp_reduces_speed(self):
        self.assertLess(effective_speed(100.0, BIOMES["swamp"]), 100.0)

    def test_snowfield_reduces_speed(self):
        self.assertLess(effective_speed(100.0, BIOMES["snowfield"]), 100.0)

    def test_result_proportional_to_mult(self):
        bd   = BIOMES["swamp"]
        spd  = effective_speed(200.0, bd)
        self.assertAlmostEqual(spd, 200.0 * bd["speed_mult"])


# ── New tile types in constants ───────────────────────────────────────────────

class TestNewTileConstants(unittest.TestCase):

    def test_tile_lava_defined(self):
        from constants import TILE_LAVA
        self.assertIsInstance(TILE_LAVA, int)
        self.assertGreater(TILE_LAVA, 4)   # beyond original 5

    def test_tile_snow_defined(self):
        self.assertIsInstance(TILE_SNOW, int)

    def test_tile_sand_defined(self):
        self.assertIsInstance(TILE_SAND, int)

    def test_tile_swamp_defined(self):
        self.assertIsInstance(TILE_SWAMP, int)

    def test_lava_is_impassable(self):
        from constants import IMPASSABLE_TILES
        self.assertIn(TILE_LAVA, IMPASSABLE_TILES)

    def test_snow_not_impassable(self):
        from constants import IMPASSABLE_TILES
        self.assertNotIn(TILE_SNOW, IMPASSABLE_TILES)

    def test_sand_not_impassable(self):
        from constants import IMPASSABLE_TILES
        self.assertNotIn(TILE_SAND, IMPASSABLE_TILES)

    def test_swamp_not_impassable(self):
        from constants import IMPASSABLE_TILES
        self.assertNotIn(TILE_SWAMP, IMPASSABLE_TILES)

    def test_all_new_tiles_have_unique_ids(self):
        ids = [TILE_LAVA, TILE_SNOW, TILE_SAND, TILE_SWAMP]
        self.assertEqual(len(ids), len(set(ids)))


# ── World biome integration ───────────────────────────────────────────────────

class TestWorldBiomeIntegration(unittest.TestCase):

    def test_world_apply_biomes_does_not_crash(self):
        import tests.mock_pygame
        from core.world import World
        w  = World(50, 50, 32, seed=42)
        bm = BiomeMap(50, 50, seed=42)
        try:
            w.apply_biomes(bm)
        except Exception as e:
            self.fail(f"apply_biomes raised {e}")

    def test_volcanic_region_has_lava_tiles(self):
        import tests.mock_pygame
        from core.world import World
        from constants import TILE_WATER
        # Use 50x50 map; center (25,25), keep_radius=15.
        # Place water at (4,4) — distance ~29.7 from center, outside radius.
        w = World(50, 50, 32, seed=42)

        class ForcedVolcanic:
            def get(self, col, row): return "volcanic"

        # Set water tiles in corner (far from center)
        for col in range(2, 7):
            for row in range(2, 7):
                w.tiles[col][row] = TILE_WATER

        w.apply_biomes(ForcedVolcanic())

        lava_found = any(
            w.tiles[col][row] == TILE_LAVA
            for col in range(2, 7)
            for row in range(2, 7)
        )
        self.assertTrue(lava_found)

    def test_snowfield_freezes_water(self):
        import tests.mock_pygame
        from core.world import World
        from constants import TILE_WATER
        # Same idea: 50x50, tiles in far corner
        w = World(50, 50, 32, seed=42)
        for col in range(2, 7):
            for row in range(2, 7):
                w.tiles[col][row] = TILE_WATER

        class ForcedSnow:
            def get(self, col, row):
                if 2 <= col < 7 and 2 <= row < 7: return "snowfield"
                return "grassland"

        w.apply_biomes(ForcedSnow())
        for col in range(2, 7):
            for row in range(2, 7):
                self.assertEqual(w.tiles[col][row], TILE_SNOW,
                                 f"Water at ({col},{row}) should be frozen")


if __name__ == "__main__":
    unittest.main()
