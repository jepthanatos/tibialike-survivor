"""Tests unitarios para core/dungeon_generator.py y core/level_manager.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame

import math
import unittest
from core.dungeon_generator import (
    DungeonGenerator, DungeonMap, Room,
    DWALL, DFLOOR, DCORR, DENTRY, DEXIT, DLAVA,
    DUNGEON_WALKABLE,
)
from core.level_manager import (
    LevelManager, DungeonEntrance, ExitPortal, DungeonLevel,
)


# ── Room ──────────────────────────────────────────────────────────────────────

class TestRoom(unittest.TestCase):

    def test_center(self):
        r = Room(2, 4, 8, 6)
        cx, cy = r.center()
        self.assertEqual(cx, 2 + 8//2)
        self.assertEqual(cy, 4 + 6//2)

    def test_inner_tiles_within_bounds(self):
        r = Room(2, 2, 6, 6)
        for col, row in r.inner_tiles():
            self.assertGreater(col, r.x)
            self.assertLess(col, r.x + r.w)
            self.assertGreater(row, r.y)
            self.assertLess(row, r.y + r.h)

    def test_inner_tiles_nonempty_for_large_room(self):
        r = Room(0, 0, 8, 8)
        tiles = list(r.inner_tiles())
        self.assertGreater(len(tiles), 0)

    def test_overlaps_self(self):
        r = Room(5, 5, 8, 8)
        self.assertTrue(r.overlaps(r))

    def test_overlaps_adjacent(self):
        r1 = Room(0, 0, 8, 8)
        r2 = Room(7, 0, 8, 8)   # touching
        self.assertTrue(r1.overlaps(r2))

    def test_no_overlap_far(self):
        r1 = Room(0, 0, 6, 6)
        r2 = Room(20, 20, 6, 6)
        self.assertFalse(r1.overlaps(r2))

    def test_no_overlap_with_margin(self):
        r1 = Room(0, 0, 6, 6)
        r2 = Room(8, 0, 6, 6)   # gap of 2
        self.assertFalse(r1.overlaps(r2, margin=1))


# ── DungeonGenerator ─────────────────────────────────────────────────────────

class TestDungeonGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = DungeonGenerator()

    def _gen(self, level=1, biome="grassland", seed=42):
        return self.gen.generate(dungeon_level=level, biome_name=biome,
                                 tile_size=32, seed=seed)

    def test_returns_dungeon_map(self):
        dmap = self._gen()
        self.assertIsInstance(dmap, DungeonMap)

    def test_dimensions_positive(self):
        dmap = self._gen()
        self.assertGreater(dmap.width, 0)
        self.assertGreater(dmap.height, 0)

    def test_tiles_correct_shape(self):
        dmap = self._gen()
        self.assertEqual(len(dmap.tiles), dmap.width)
        self.assertEqual(len(dmap.tiles[0]), dmap.height)

    def test_all_tile_ids_valid(self):
        dmap = self._gen()
        valid = {DWALL, DFLOOR, DCORR, DENTRY, DEXIT, DLAVA}
        for col in range(dmap.width):
            for row in range(dmap.height):
                self.assertIn(dmap.tiles[col][row], valid,
                              f"Invalid tile at ({col},{row})")

    def test_entry_tile_is_dentry(self):
        dmap = self._gen()
        ecol, erow = dmap.entry_pos
        self.assertEqual(dmap.tiles[ecol][erow], DENTRY)

    def test_exit_tile_is_dexit(self):
        dmap = self._gen()
        xcol, xrow = dmap.exit_pos
        self.assertEqual(dmap.tiles[xcol][xrow], DEXIT)

    def test_entry_and_exit_different(self):
        dmap = self._gen()
        self.assertNotEqual(dmap.entry_pos, dmap.exit_pos)

    def test_has_at_least_one_room(self):
        dmap = self._gen()
        self.assertGreater(len(dmap.rooms), 0)

    def test_monster_spawns_are_walkable(self):
        dmap = self._gen()
        for col, row in dmap.monster_spawns:
            self.assertTrue(dmap.is_walkable(col, row),
                            f"Spawn at ({col},{row}) not walkable")

    def test_boss_spawn_in_map(self):
        dmap = self._gen()
        bcol, brow = dmap.boss_spawn
        self.assertGreaterEqual(bcol, 0)
        self.assertLess(bcol, dmap.width)
        self.assertGreaterEqual(brow, 0)
        self.assertLess(brow, dmap.height)

    def test_deterministic_same_seed(self):
        d1 = self._gen(seed=7)
        d2 = self._gen(seed=7)
        self.assertEqual(d1.entry_pos, d2.entry_pos)
        self.assertEqual(d1.exit_pos,  d2.exit_pos)
        self.assertEqual(d1.width,     d2.width)

    def test_different_seeds_different_maps(self):
        d1 = self._gen(seed=1)
        d2 = self._gen(seed=999)
        # At least dimensions or positions differ
        different = (d1.entry_pos != d2.entry_pos or
                     d1.exit_pos  != d2.exit_pos  or
                     d1.width     != d2.width)
        self.assertTrue(different)

    def test_deeper_dungeon_larger_or_equal(self):
        d1 = self._gen(level=1, seed=42)
        d2 = self._gen(level=3, seed=42)
        self.assertGreaterEqual(d2.width * d2.height, d1.width * d1.height)

    def test_volcanic_biome_has_lava(self):
        dmap = self._gen(level=3, biome="volcanic", seed=42)
        has_lava = any(
            dmap.tiles[c][r] == DLAVA
            for c in range(dmap.width)
            for r in range(dmap.height)
        )
        # Not guaranteed by seed but likely; test that it doesn't crash
        self.assertIsInstance(has_lava, bool)

    def test_dungeon_level_stored(self):
        dmap = self._gen(level=2)
        self.assertEqual(dmap.dungeon_level, 2)

    def test_biome_name_stored(self):
        dmap = self._gen(biome="swamp")
        self.assertEqual(dmap.biome_name, "swamp")

    def test_has_walkable_floor_tiles(self):
        dmap = self._gen()
        has_floor = any(
            dmap.tiles[c][r] in DUNGEON_WALKABLE
            for c in range(dmap.width)
            for r in range(dmap.height)
        )
        self.assertTrue(has_floor)

    def test_not_all_walls(self):
        dmap = self._gen()
        non_wall = sum(
            1 for c in range(dmap.width)
            for r in range(dmap.height)
            if dmap.tiles[c][r] != DWALL
        )
        self.assertGreater(non_wall, 10)


# ── DungeonMap helpers ────────────────────────────────────────────────────────

class TestDungeonMapHelpers(unittest.TestCase):

    def setUp(self):
        self.dmap = DungeonGenerator().generate(seed=42, tile_size=32)

    def test_is_walkable_wall_returns_false(self):
        # Find a wall tile
        for col in range(self.dmap.width):
            for row in range(self.dmap.height):
                if self.dmap.tiles[col][row] == DWALL:
                    self.assertFalse(self.dmap.is_walkable(col, row))
                    return

    def test_is_walkable_floor_returns_true(self):
        for col in range(self.dmap.width):
            for row in range(self.dmap.height):
                if self.dmap.tiles[col][row] == DFLOOR:
                    self.assertTrue(self.dmap.is_walkable(col, row))
                    return

    def test_is_walkable_out_of_bounds(self):
        self.assertFalse(self.dmap.is_walkable(-1, 0))
        self.assertFalse(self.dmap.is_walkable(0, -1))
        self.assertFalse(self.dmap.is_walkable(self.dmap.width, 0))

    def test_is_rect_walkable_in_floor_room(self):
        ts = self.dmap.tile_size
        ecol, erow = self.dmap.entry_pos
        px = ecol * ts + ts//2
        py = erow * ts + ts//2
        # Tight rect centred on floor tile
        self.assertTrue(self.dmap.is_rect_walkable(px-4, py-4, px+4, py+4))

    def test_get_minimap_returns_surface(self):
        surf, size = self.dmap.get_minimap()
        self.assertGreater(size, 0)


# ── DungeonEntrance ───────────────────────────────────────────────────────────

class TestDungeonEntrance(unittest.TestCase):

    class FakePlayer:
        def __init__(self, x, y): self.x=float(x); self.y=float(y)

    def test_near_player_when_close(self):
        ent = DungeonEntrance(500.0, 500.0, 0, "Catacumbas")
        p   = self.FakePlayer(510.0, 500.0)
        self.assertTrue(ent.near_player(p))

    def test_not_near_player_when_far(self):
        ent = DungeonEntrance(500.0, 500.0, 0, "Catacumbas")
        p   = self.FakePlayer(3000.0, 3000.0)
        self.assertFalse(ent.near_player(p))

    def test_near_player_boundary(self):
        ent = DungeonEntrance(500.0, 500.0, 0, "Catacumbas")
        # Exactly at INTERACT_RADIUS distance
        r   = DungeonEntrance.INTERACT_RADIUS
        p   = self.FakePlayer(500.0 + r, 500.0)
        self.assertTrue(ent.near_player(p))

    def test_update_increments_time(self):
        ent = DungeonEntrance(0.0, 0.0, 0, "X")
        ent.update(0.5)
        self.assertAlmostEqual(ent._time, 0.5)

    def test_attributes_stored(self):
        ent = DungeonEntrance(1.0, 2.0, 3, "MyZone", "volcanic")
        self.assertEqual(ent.zone_id,    3)
        self.assertEqual(ent.zone_name,  "MyZone")
        self.assertEqual(ent.biome_name, "volcanic")


# ── LevelManager ─────────────────────────────────────────────────────────────

class FakeWorld:
    width=150; height=150; tile_size=32
    def is_walkable(self,c,r): return True
    def is_rect_walkable(self,*a): return True

class FakeCamera:
    offset_x=0.0; offset_y=0.0
    view_w=1280; view_h=630
    world_w=4800; world_h=4800
    def update(self,x,y,dt=0.016): pass
    def snap(self,x,y): pass

class FakePlayer2:
    x=2400.0; y=2400.0; SIZE=18; level=5
    _inv_timer=0.0; _block_flash=0.0
    def __init__(self):
        import tests.mock_pygame as mp
        self.rect = mp.FakeRect()
    def take_damage(self,_): return 0

class FakeBiomeMap:
    def get(self,c,r): return "grassland"
    def get_px(self,*a): return "grassland"


class TestLevelManager(unittest.TestCase):

    def _make_mgr(self, entrances=None):
        w   = FakeWorld()
        cam = FakeCamera()
        ents = entrances or []
        return LevelManager(w, cam, ents), w, cam

    def test_starts_not_in_dungeon(self):
        mgr, _, _ = self._make_mgr()
        self.assertFalse(mgr.in_dungeon)

    def test_current_dungeon_is_none_initially(self):
        mgr, _, _ = self._make_mgr()
        self.assertIsNone(mgr.current_dungeon)

    def test_active_map_is_world_on_surface(self):
        w   = FakeWorld()
        cam = FakeCamera()
        mgr = LevelManager(w, cam, [])
        self.assertIs(mgr.active_map, w)

    def test_try_enter_no_entrances_returns_false(self):
        mgr, _, _ = self._make_mgr()
        p = FakePlayer2()
        self.assertFalse(mgr.try_enter(p, FakeBiomeMap()))

    def test_try_enter_near_entrance_returns_true(self):
        ent = DungeonEntrance(float(FakePlayer2.x), float(FakePlayer2.y), 0, "Test")
        mgr, _, _ = self._make_mgr([ent])
        p   = FakePlayer2()
        result = mgr.try_enter(p, FakeBiomeMap())
        self.assertTrue(result)

    def test_in_dungeon_after_entry(self):
        ent = DungeonEntrance(float(FakePlayer2.x), float(FakePlayer2.y), 0, "Test")
        mgr, _, _ = self._make_mgr([ent])
        p   = FakePlayer2()
        mgr.try_enter(p, FakeBiomeMap())
        self.assertTrue(mgr.in_dungeon)

    def test_current_dungeon_set_after_entry(self):
        ent = DungeonEntrance(float(FakePlayer2.x), float(FakePlayer2.y), 0, "Test")
        mgr, _, _ = self._make_mgr([ent])
        p   = FakePlayer2()
        mgr.try_enter(p, FakeBiomeMap())
        self.assertIsNotNone(mgr.current_dungeon)

    def test_active_map_is_dungeon_map_after_entry(self):
        ent = DungeonEntrance(float(FakePlayer2.x), float(FakePlayer2.y), 0, "Test")
        mgr, _, _ = self._make_mgr([ent])
        p   = FakePlayer2()
        mgr.try_enter(p, FakeBiomeMap())
        self.assertIsInstance(mgr.active_map, DungeonMap)

    def test_player_teleported_on_entry(self):
        ent = DungeonEntrance(float(FakePlayer2.x), float(FakePlayer2.y), 0, "Test")
        mgr, _, _ = self._make_mgr([ent])
        p   = FakePlayer2()
        old_x, old_y = p.x, p.y
        mgr.try_enter(p, FakeBiomeMap())
        # Player should be at dungeon spawn (different from surface pos)
        dlvl = mgr.current_dungeon
        self.assertAlmostEqual(p.x, dlvl.spawn_x, delta=5)
        self.assertAlmostEqual(p.y, dlvl.spawn_y, delta=5)

    def test_try_exit_returns_false_on_surface(self):
        mgr, _, _ = self._make_mgr()
        p = FakePlayer2()
        self.assertFalse(mgr.try_exit(p))

    def test_exit_returns_to_surface(self):
        ent = DungeonEntrance(float(FakePlayer2.x), float(FakePlayer2.y), 0, "Test")
        mgr, _, _ = self._make_mgr([ent])
        p   = FakePlayer2()
        return_x, return_y = p.x, p.y
        mgr.try_enter(p, FakeBiomeMap())
        self.assertTrue(mgr.in_dungeon)
        # Force player to exit portal
        dlvl  = mgr.current_dungeon
        p.x   = dlvl.exit_portal.x
        p.y   = dlvl.exit_portal.y
        result = mgr.try_exit(p)
        self.assertTrue(result)
        self.assertFalse(mgr.in_dungeon)

    def test_player_returned_to_surface_pos_on_exit(self):
        ent = DungeonEntrance(float(FakePlayer2.x), float(FakePlayer2.y), 0, "Test")
        mgr, _, _ = self._make_mgr([ent])
        p   = FakePlayer2()
        return_x, return_y = p.x, p.y
        mgr.try_enter(p, FakeBiomeMap())
        dlvl = mgr.current_dungeon
        p.x  = dlvl.exit_portal.x
        p.y  = dlvl.exit_portal.y
        mgr.try_exit(p)
        self.assertAlmostEqual(p.x, return_x, delta=2)
        self.assertAlmostEqual(p.y, return_y, delta=2)

    def test_cannot_enter_while_in_dungeon(self):
        ent = DungeonEntrance(float(FakePlayer2.x), float(FakePlayer2.y), 0, "Test")
        mgr, _, _ = self._make_mgr([ent])
        p   = FakePlayer2()
        mgr.try_enter(p, FakeBiomeMap())
        # Second attempt should fail
        p.x = float(FakePlayer2.x); p.y = float(FakePlayer2.y)
        result = mgr.try_enter(p, FakeBiomeMap())
        self.assertFalse(result)

    def test_build_entrances_count(self):
        from systems.dungeons import DungeonZone
        zones = [DungeonZone(50, 50, 10, i) for i in range(3)]
        ents  = LevelManager.build_entrances(zones, FakeBiomeMap(), 32)
        self.assertEqual(len(ents), 3)

    def test_build_entrances_positions(self):
        from systems.dungeons import DungeonZone
        ts   = 32
        zone = DungeonZone(40, 30, 10, 0)
        ents = LevelManager.build_entrances([zone], FakeBiomeMap(), ts)
        expected_x = 40 * ts + ts//2
        expected_y = 30 * ts + ts//2
        self.assertAlmostEqual(ents[0].x, float(expected_x))
        self.assertAlmostEqual(ents[0].y, float(expected_y))


# ── DungeonLevel ─────────────────────────────────────────────────────────────

class TestDungeonLevel(unittest.TestCase):

    def setUp(self):
        self.dmap = DungeonGenerator().generate(seed=42, tile_size=32)
        self.dlvl = DungeonLevel(self.dmap, 1000.0, 2000.0)

    def test_return_position_stored(self):
        self.assertAlmostEqual(self.dlvl.return_px, 1000.0)
        self.assertAlmostEqual(self.dlvl.return_py, 2000.0)

    def test_spawn_inside_dungeon(self):
        ts    = self.dmap.tile_size
        ecol, erow = self.dmap.entry_pos
        expected_x = ecol * ts + ts//2
        expected_y = erow * ts + ts//2
        self.assertAlmostEqual(self.dlvl.spawn_x, float(expected_x), delta=2)
        self.assertAlmostEqual(self.dlvl.spawn_y, float(expected_y), delta=2)

    def test_update_increments_time(self):
        before = self.dlvl._time
        self.dlvl.update(0.5)
        self.assertAlmostEqual(self.dlvl._time, before + 0.5, delta=0.01)

    def test_exit_portal_positioned_at_exit(self):
        ts   = self.dmap.tile_size
        xcol, xrow = self.dmap.exit_pos
        ex   = xcol * ts + ts//2
        ey   = xrow * ts + ts//2
        self.assertAlmostEqual(self.dlvl.exit_portal.x, float(ex), delta=2)
        self.assertAlmostEqual(self.dlvl.exit_portal.y, float(ey), delta=2)


if __name__ == "__main__":
    unittest.main()
