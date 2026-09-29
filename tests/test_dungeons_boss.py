"""Tests unitarios para systems/dungeons.py y systems/boss.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame

import math
import unittest
from systems.dungeons import (
    DungeonZone, generate_dungeons, in_any_dungeon,
    loot_multiplier, NUM_DUNGEONS, LOOT_MULT,
)
from systems.boss import BossManager, BOSS_SPAWN_TIMES, BOSS_TYPES


# ── DungeonZone ───────────────────────────────────────────────────────────────

class TestDungeonZone(unittest.TestCase):

    def _zone(self, cc=50, cr=50, r=15):
        return DungeonZone(cc, cr, r, 0)

    def test_contains_tile_center(self):
        z = self._zone()
        self.assertTrue(z.contains_tile(50, 50))

    def test_contains_tile_on_edge(self):
        z = self._zone(cc=50, cr=50, r=15)
        self.assertTrue(z.contains_tile(50, 65))   # exactly on edge

    def test_does_not_contain_outside_tile(self):
        z = self._zone()
        self.assertFalse(z.contains_tile(50, 70))

    def test_contains_px_center(self):
        z = self._zone(cc=50, cr=50, r=15)
        cx, cy = z.center_px()
        self.assertTrue(z.contains_px(cx, cy))

    def test_does_not_contain_far_px(self):
        z = self._zone(cc=50, cr=50, r=15)
        self.assertFalse(z.contains_px(0.0, 0.0))

    def test_center_px_matches_tile_center(self):
        from constants import TILE_SIZE
        z = self._zone(cc=40, cr=30, r=10)
        cx, cy = z.center_px()
        self.assertAlmostEqual(cx, 40 * TILE_SIZE + TILE_SIZE // 2)
        self.assertAlmostEqual(cy, 30 * TILE_SIZE + TILE_SIZE // 2)

    def test_has_name(self):
        z = self._zone()
        self.assertIsInstance(z.name, str)
        self.assertGreater(len(z.name), 0)

    def test_zone_id_stored(self):
        z = DungeonZone(50, 50, 15, 3)
        self.assertEqual(z.zone_id, 3)


class TestGenerateDungeons(unittest.TestCase):

    def test_generates_correct_count(self):
        zones = generate_dungeons(150, 150, seed=42)
        self.assertEqual(len(zones), NUM_DUNGEONS)

    def test_zones_within_world_bounds(self):
        W, H  = 150, 150
        zones = generate_dungeons(W, H, seed=42)
        for z in zones:
            self.assertGreater(z.center_col - z.radius, 0)
            self.assertLess(z.center_col + z.radius, W)
            self.assertGreater(z.center_row - z.radius, 0)
            self.assertLess(z.center_row + z.radius, H)

    def test_zones_not_overlapping_each_other(self):
        zones = generate_dungeons(150, 150, seed=42)
        for i, z1 in enumerate(zones):
            for j, z2 in enumerate(zones):
                if i >= j:
                    continue
                dist = math.hypot(z1.center_col - z2.center_col,
                                  z1.center_row - z2.center_row)
                # They should be at least somewhat separated
                self.assertGreater(dist, 5)

    def test_zones_away_from_center(self):
        W, H  = 150, 150
        zones = generate_dungeons(W, H, seed=42)
        cx, cy = W // 2, H // 2
        for z in zones:
            dist = math.hypot(z.center_col - cx, z.center_row - cy)
            self.assertGreater(dist, 20)   # not spawning inside spawn area

    def test_same_seed_deterministic(self):
        z1 = generate_dungeons(150, 150, seed=7)
        z2 = generate_dungeons(150, 150, seed=7)
        self.assertEqual(len(z1), len(z2))
        for a, b in zip(z1, z2):
            self.assertEqual(a.center_col, b.center_col)
            self.assertEqual(a.center_row, b.center_row)

    def test_different_seeds_different_positions(self):
        z1 = generate_dungeons(150, 150, seed=1)
        z2 = generate_dungeons(150, 150, seed=2)
        positions1 = [(z.center_col, z.center_row) for z in z1]
        positions2 = [(z.center_col, z.center_row) for z in z2]
        self.assertNotEqual(positions1, positions2)


class TestInAnyDungeon(unittest.TestCase):

    def _zones(self):
        return [DungeonZone(50, 50, 15, 0), DungeonZone(100, 80, 12, 1)]

    def test_returns_zone_when_inside(self):
        zones = self._zones()
        from constants import TILE_SIZE
        cx, cy = zones[0].center_px()
        result = in_any_dungeon(zones, cx, cy)
        self.assertIsNotNone(result)
        self.assertEqual(result.zone_id, 0)

    def test_returns_none_when_outside(self):
        zones = self._zones()
        result = in_any_dungeon(zones, 0.0, 0.0)
        self.assertIsNone(result)

    def test_correct_zone_returned(self):
        zones = self._zones()
        from constants import TILE_SIZE
        cx, cy = zones[1].center_px()
        result = in_any_dungeon(zones, cx, cy)
        self.assertIsNotNone(result)
        self.assertEqual(result.zone_id, 1)


class TestLootMultiplier(unittest.TestCase):

    def test_outside_dungeon_returns_1(self):
        zones = [DungeonZone(50, 50, 10, 0)]
        mult  = loot_multiplier(zones, 0.0, 0.0)
        self.assertAlmostEqual(mult, 1.0)

    def test_inside_dungeon_returns_multiplier(self):
        zones = [DungeonZone(50, 50, 10, 0)]
        from constants import TILE_SIZE
        cx, cy = zones[0].center_px()
        mult   = loot_multiplier(zones, cx, cy)
        self.assertAlmostEqual(mult, LOOT_MULT)

    def test_multiplier_greater_than_one(self):
        self.assertGreater(LOOT_MULT, 1.0)


# ── BossManager ───────────────────────────────────────────────────────────────

class FakeWorld:
    width = 150; height = 150; tile_size = 32
    def is_walkable(self, col, row): return True

class FakePlayer:
    x = 2400.0; y = 2400.0; SIZE = 18; level = 20
    _inv_timer = 0.0
    def take_damage(self, _): return 0


class TestBossManager(unittest.TestCase):

    def test_init_no_active_boss(self):
        bm = BossManager()
        self.assertIsNone(bm.active_boss)

    def test_no_boss_before_first_threshold(self):
        bm = BossManager()
        w  = FakeWorld(); p = FakePlayer()
        # Simulate just under first threshold
        result = bm.update(BOSS_SPAWN_TIMES[0] - 1, p.level, w, p)
        self.assertIsNone(result)

    def test_boss_spawns_at_first_threshold(self):
        bm = BossManager()
        w  = FakeWorld(); p = FakePlayer()
        # Simulate just past first threshold in one update
        result = bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        self.assertIsNotNone(result)

    def test_no_second_boss_while_first_alive(self):
        bm = BossManager()
        w  = FakeWorld(); p = FakePlayer()
        bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        # Second threshold passed but first boss still alive
        result = bm.update(BOSS_SPAWN_TIMES[1] - BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        self.assertIsNone(result)

    def test_active_boss_set_after_spawn(self):
        bm = BossManager()
        w  = FakeWorld(); p = FakePlayer()
        boss = bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        self.assertIs(bm.active_boss, boss)

    def test_boss_name_set_after_spawn(self):
        bm = BossManager()
        w  = FakeWorld(); p = FakePlayer()
        bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        self.assertGreater(len(bm.boss_name), 0)

    def test_active_boss_cleared_on_death(self):
        bm   = BossManager()
        w    = FakeWorld(); p = FakePlayer()
        boss = bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        boss.hp = 0.0   # kill it
        bm.update(0.016, p.level, w, p)
        self.assertIsNone(bm.active_boss)

    def test_on_boss_death_returns_items(self):
        bm   = BossManager()
        w    = FakeWorld(); p = FakePlayer()
        boss = bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        items = bm.on_boss_death(boss)
        self.assertGreaterEqual(len(items), 2)
        for item in items:
            self.assertIn('name', item)
            self.assertIn('stats', item)

    def test_boss_death_items_at_least_rare(self):
        bm   = BossManager()
        w    = FakeWorld(); p = FakePlayer()
        boss = bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        items = bm.on_boss_death(boss)
        order = ["common","uncommon","rare","epic"]
        for item in items:
            self.assertGreaterEqual(order.index(item['rarity']), order.index('rare'),
                                    f"Boss drop {item['name']} should be at least rare")

    def test_boss_has_is_boss_flag(self):
        bm   = BossManager()
        w    = FakeWorld(); p = FakePlayer()
        boss = bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        self.assertTrue(getattr(boss, 'is_boss', False))

    def test_boss_has_elite_mods(self):
        bm   = BossManager()
        w    = FakeWorld(); p = FakePlayer()
        boss = bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        self.assertGreaterEqual(len(getattr(boss, 'elite_mods', [])), 2)

    def test_boss_display_name_is_string(self):
        bm   = BossManager()
        w    = FakeWorld(); p = FakePlayer()
        boss = bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        self.assertIsInstance(getattr(boss, 'boss_display_name', ''), str)

    def test_seconds_to_next_boss_initially_positive(self):
        bm = BossManager()
        self.assertGreater(bm.seconds_to_next_boss, 0)

    def test_seconds_to_next_boss_decreases_over_time(self):
        bm = BossManager()
        before = bm.seconds_to_next_boss
        bm._elapsed += 10
        after = bm.seconds_to_next_boss
        self.assertLess(after, before)

    def test_boss_types_have_required_fields(self):
        required = ("base_type","name","color","size","hp_base",
                    "dmg_base","speed","xp_base","min_level")
        for btype, data in BOSS_TYPES.items():
            for k in required:
                self.assertIn(k, data, f"Boss '{btype}' missing '{k}'")

    def test_boss_spawn_times_ascending(self):
        for i in range(len(BOSS_SPAWN_TIMES) - 1):
            self.assertLess(BOSS_SPAWN_TIMES[i], BOSS_SPAWN_TIMES[i+1])

    def test_announcement_active_after_spawn(self):
        bm = BossManager()
        w  = FakeWorld(); p = FakePlayer()
        bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        self.assertTrue(bm.announcement_active)

    def test_announcement_expires(self):
        bm = BossManager()
        w  = FakeWorld(); p = FakePlayer()
        bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        # Fast-forward announcement timer
        bm._announce_timer = 0.0
        self.assertFalse(bm.announcement_active)


# ── Loot multiplier integration ───────────────────────────────────────────────

class TestLootWithMultiplier(unittest.TestCase):

    class FakeMon:
        mtype='rat'; level=0; is_boss=False

    def test_higher_multiplier_increases_drops(self):
        from systems.loot import try_drop_with_mult
        m = self.FakeMon()
        drops_normal = sum(1 for _ in range(500)
                           if try_drop_with_mult(m, 1.0) is not None)
        drops_boosted = sum(1 for _ in range(500)
                            if try_drop_with_mult(m, 2.0) is not None)
        self.assertGreater(drops_boosted, drops_normal)

    def test_boss_always_drops(self):
        from systems.loot import try_drop_with_mult
        m = self.FakeMon()
        m.is_boss = True
        for _ in range(20):
            result = try_drop_with_mult(m, 1.0)
            self.assertIsNotNone(result)

    def test_generate_guaranteed_at_least_min_rarity(self):
        from systems.loot import generate_guaranteed
        order = ["common","uncommon","rare","epic"]
        for _ in range(20):
            item = generate_guaranteed(5, min_rarity="rare")
            self.assertGreaterEqual(order.index(item['rarity']),
                                    order.index('rare'))


if __name__ == '__main__':
    unittest.main()
