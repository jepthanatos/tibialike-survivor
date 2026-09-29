"""Tests unitarios para systems/zones.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame

import unittest
import math
from systems.zones import (
    get_zone, get_zone_name, get_zone_color,
    get_zone_monster_types, get_zone_level_bonus, get_zone_xp_mult,
    random_spawn_point, ZONE_THRESHOLDS, ZONE_NAMES, ZONE_COLORS,
    ZONE_MONSTER_TYPES, ZONE_LEVEL_BONUS, ZONE_XP_MULT,
)


class TestGetZone(unittest.TestCase):
    """Test radial zone assignment."""

    MAP_CX = 2400.0
    MAP_CY = 2400.0
    MAP_R  = 2400.0   # half of 4800px map

    def _zone(self, dist_frac):
        px = self.MAP_CX + dist_frac * self.MAP_R
        return get_zone(px, self.MAP_CY, self.MAP_CX, self.MAP_CY, self.MAP_R)

    def test_center_is_zone_0(self):
        zone = get_zone(self.MAP_CX, self.MAP_CY, self.MAP_CX, self.MAP_CY, self.MAP_R)
        self.assertEqual(zone, 0)

    def test_exact_center_zone_0(self):
        self.assertEqual(self._zone(0.0), 0)

    def test_inner_zone_0(self):
        self.assertEqual(self._zone(0.20), 0)   # 20% < 25% threshold

    def test_boundary_zone_0_to_1(self):
        # At 25% = threshold → zone 0 (<=)
        self.assertEqual(self._zone(0.25), 0)

    def test_just_past_first_threshold(self):
        self.assertEqual(self._zone(0.30), 1)

    def test_mid_zone_1(self):
        self.assertEqual(self._zone(0.35), 1)

    def test_boundary_zone_1_to_2(self):
        self.assertEqual(self._zone(0.45), 1)   # <= threshold

    def test_just_past_second_threshold(self):
        self.assertEqual(self._zone(0.50), 2)

    def test_mid_zone_2(self):
        self.assertEqual(self._zone(0.55), 2)

    def test_boundary_zone_2_to_3(self):
        self.assertEqual(self._zone(0.65), 2)   # <= threshold

    def test_periphery_is_zone_3(self):
        self.assertEqual(self._zone(0.80), 3)

    def test_far_periphery_zone_3(self):
        self.assertEqual(self._zone(0.99), 3)

    def test_all_directions_same_distance(self):
        """Equal distance from center in all directions should give same zone."""
        dist = 0.3 * self.MAP_R
        for angle in [0, math.pi/2, math.pi, 3*math.pi/2]:
            px = self.MAP_CX + math.cos(angle) * dist
            py = self.MAP_CY + math.sin(angle) * dist
            self.assertEqual(
                get_zone(px, py, self.MAP_CX, self.MAP_CY, self.MAP_R), 1
            )


class TestZoneProperties(unittest.TestCase):

    def test_zone_names_exist_for_all_zones(self):
        for z in range(4):
            name = get_zone_name(z)
            self.assertIsInstance(name, str)
            self.assertGreater(len(name), 0)

    def test_zone_colors_are_rgb_tuples(self):
        for z in range(4):
            col = get_zone_color(z)
            self.assertEqual(len(col), 3)
            for c in col:
                self.assertGreaterEqual(c, 0)
                self.assertLessEqual(c, 255)

    def test_zone_monster_types_not_empty(self):
        for z in range(4):
            types = get_zone_monster_types(z)
            self.assertGreater(len(types), 0)
            for mtype in types:
                self.assertIsInstance(mtype, str)

    def test_center_has_toughest_monsters(self):
        center_types = set(get_zone_monster_types(0))
        # Center should have demon or dragon_lord
        self.assertTrue(
            'demon' in center_types or 'dragon_lord' in center_types or 'dragon' in center_types,
            f"Center zone has {center_types} — expected tough monsters"
        )

    def test_periphery_has_weakest_monsters(self):
        outer_types = set(get_zone_monster_types(3))
        # Periphery should have rat or zombie or skeleton
        self.assertTrue(
            'rat' in outer_types or 'zombie' in outer_types or 'skeleton' in outer_types,
            f"Periphery zone has {outer_types} — expected weak monsters"
        )

    def test_level_bonus_decreases_outward(self):
        """Inner zones should have higher level bonuses."""
        bonuses = [get_zone_level_bonus(z) for z in range(4)]
        for i in range(len(bonuses)-1):
            self.assertGreaterEqual(bonuses[i], bonuses[i+1],
                f"Zone {i} bonus {bonuses[i]} < zone {i+1} bonus {bonuses[i+1]}")

    def test_center_has_highest_level_bonus(self):
        self.assertGreater(get_zone_level_bonus(0), get_zone_level_bonus(3))

    def test_periphery_level_bonus_is_zero(self):
        self.assertEqual(get_zone_level_bonus(3), 0)

    def test_xp_mult_decreases_outward(self):
        mults = [get_zone_xp_mult(z) for z in range(4)]
        for i in range(len(mults)-1):
            self.assertGreaterEqual(mults[i], mults[i+1])

    def test_center_xp_mult_above_1(self):
        self.assertGreater(get_zone_xp_mult(0), 1.0)

    def test_periphery_xp_mult_is_1(self):
        self.assertAlmostEqual(get_zone_xp_mult(3), 1.0)

    def test_invalid_zone_returns_periphery_values(self):
        # Out-of-range zone → defaults to last/safest values
        name = get_zone_name(99)
        self.assertIsInstance(name, str)
        types = get_zone_monster_types(99)
        self.assertGreater(len(types), 0)

    def test_constants_consistency(self):
        self.assertEqual(len(ZONE_NAMES),         len(ZONE_COLORS))
        self.assertEqual(len(ZONE_COLORS),        len(ZONE_MONSTER_TYPES))
        self.assertEqual(len(ZONE_MONSTER_TYPES), len(ZONE_LEVEL_BONUS))
        self.assertEqual(len(ZONE_LEVEL_BONUS),   len(ZONE_XP_MULT))


class TestRandomSpawnPoint(unittest.TestCase):

    def _make_world(self):
        """Create a real walkable world for spawn tests."""
        import tests.mock_pygame
        from core.world import World
        from constants import MAP_W, MAP_H, TILE_SIZE
        from systems.biomes import BiomeMap
        w = World(MAP_W, MAP_H, TILE_SIZE, seed=99)
        bm = BiomeMap(MAP_W, MAP_H, seed=99)
        w.apply_biomes(bm)
        return w

    def test_returns_walkable_tile(self):
        world = self._make_world()
        result = random_spawn_point(world)
        self.assertIsNotNone(result)
        col, row = result
        self.assertTrue(world.is_walkable(col, row))

    def test_returns_tuple_of_two(self):
        world = self._make_world()
        result = random_spawn_point(world)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)

    def test_respects_min_separation(self):
        world = self._make_world()
        taken = [(75, 75)]   # center
        result = random_spawn_point(world, min_dist_from=taken, min_sep=20)
        if result:
            col, row = result
            dist = abs(col-75)+abs(row-75)
            self.assertGreaterEqual(dist, 20)

    def test_multiple_spawns_separated(self):
        world = self._make_world()
        spawned = []
        for _ in range(5):
            pt = random_spawn_point(world, min_dist_from=spawned, min_sep=20)
            if pt:
                spawned.append(pt)
        # Verify all pairs are separated
        for i, (c1,r1) in enumerate(spawned):
            for c2,r2 in spawned[i+1:]:
                self.assertGreaterEqual(abs(c1-c2)+abs(r1-r2), 20)

    def test_returns_none_when_impossible(self):
        """If min_sep is huge, may return None (graceful failure)."""
        world = self._make_world()
        # Occupy everywhere with very large separation
        taken = [(75, 75)]
        result = random_spawn_point(world, min_dist_from=taken,
                                    min_sep=10000, max_tries=5)
        # Either None or a point (world is large enough, could still find one)
        if result is not None:
            col, row = result
            self.assertTrue(world.is_walkable(col, row))


class TestSpawnDistribution(unittest.TestCase):
    """Verify that zone-based spawning distributes monsters correctly."""

    def test_center_zone_has_demon_or_dragon(self):
        types = get_zone_monster_types(0)
        has_tough = any(t in types for t in ['demon','dragon_lord','dragon'])
        self.assertTrue(has_tough, f"Center zone should have tough monsters, got {types}")

    def test_all_zones_have_valid_monster_types(self):
        from entities.monster import MONSTER_DATA
        valid = set(MONSTER_DATA.keys())
        for z in range(4):
            for mtype in get_zone_monster_types(z):
                self.assertIn(mtype, valid,
                              f"Zone {z} has unknown monster type '{mtype}'")

    def test_zone_boundaries_cover_full_map(self):
        """ZONE_THRESHOLDS should cover 0..1 range with zone 3 as catch-all."""
        # Zone 0: [0, t0], Zone 1: (t0, t1], Zone 2: (t1, t2], Zone 3: (t2, 1.0]
        prev = 0.0
        for threshold in ZONE_THRESHOLDS:
            self.assertGreater(threshold, prev)
            prev = threshold
        self.assertLess(ZONE_THRESHOLDS[-1], 1.0)  # zone 3 catches the rest


if __name__ == '__main__':
    unittest.main()
