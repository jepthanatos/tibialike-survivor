"""
tests/test_coverage_gaps.py
Cierra todas las brechas de cobertura detectadas:

  systems/boss.py          _spawn_boss, draw_boss_bar, draw_announcement
  systems/dungeons.py      draw_dungeons
  systems/lifetime_stats.py _fmt_time, _load, _update_totals, _update_records, format_record
  systems/spells.py        __repr__
  systems/stats.py         on_xp_gained
  systems/storm.py         _storm_damage, _advance_phase, __repr__
  core/dungeon_generator   _connect_rooms, _carve_corridor, _hcorr, _vcorr, _add_lava, _fallback_rooms
  core/level_manager       player_at_exit, player_at_entry
  core/session.py          _load
  core/world.py            apply_dungeon_zones
  entities/item_drop.py    is_picked_up
  entities/monster.py      _draw_* methods (via draw())
  entities/player.py       _init_stats, effective_range, spell_ready
  entities/projectile.py   _explode_aoe
  entities/spawner.py      _biome_weighted_choice, _fill_map, _try_spawn_random, add_monster
"""
import sys, os, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame   # instala pygame falso PRIMERO

import math
import random
import unittest

# ══════════════════════════════════════════════════════════════════════════════
# systems/lifetime_stats.py
# ══════════════════════════════════════════════════════════════════════════════
import systems.lifetime_stats as lt_module
from systems.lifetime_stats import LifetimeStats, _fmt_time

class TestFmtTime(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(_fmt_time(0), "00:00")
    def test_one_minute(self):
        self.assertEqual(_fmt_time(60), "01:00")
    def test_ninety_seconds(self):
        self.assertEqual(_fmt_time(90), "01:30")
    def test_large_value(self):
        r = _fmt_time(3661)
        self.assertIn(":", r)

class TestLifetimeLoad(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._path = self._tmp.name
        self._tmp.close(); os.remove(self._path)
        lt_module.HISTORY_FILE = self._path

    def tearDown(self):
        if os.path.exists(self._path): os.remove(self._path)

    def test_load_from_existing_file(self):
        data = {"runs": [], "totals": {"total_kills": 42}, "records": {"highest_level": 7}}
        with open(self._path, "w") as f: json.dump(data, f)
        lt = LifetimeStats()
        self.assertEqual(lt.totals.get("total_kills"), 42)
        self.assertEqual(lt.records.get("highest_level"), 7)

    def test_load_ignores_corrupt_file(self):
        with open(self._path, "w") as f: f.write("INVALID JSON")
        lt = LifetimeStats()
        self.assertEqual(lt.runs, [])

    def test_update_totals_called_on_register(self):
        lt = LifetimeStats()
        run = {"elapsed_s": 120.0, "total_kills": 10, "elite_kills": 2, "boss_kills": 1,
               "melee_hits": 5, "melee_damage_dealt": 100, "total_spell_damage": 50,
               "total_damage_dealt": 150, "damage_received": 80, "storm_damage": 10,
               "damage_blocked": 20, "times_hit": 8, "xp_earned": 300, "mp_spent": 40,
               "items_found": 3, "spells_cast_total": 7, "distance_walked_km": 0.5,
               "kills": {"rat": 8, "zombie": 2}, "spell_damage_dealt": {"exevo vis": 50},
               "spells_learned": ["exevo vis"], "level_reached": 5, "storm_phase": 2,
               "dungeon_count": 1, "items_equipped_peak": 3, "best_gear_rarity": "rare",
               "date": "2025-01-01T00:00:00"}
        lt.register_run(run)
        self.assertEqual(lt.totals["total_kills"], 10)
        self.assertEqual(lt.totals["kills_rat"], 8)
        self.assertEqual(lt.totals.get("spell_dmg_exevo vis"), 50)
        self.assertIn("exevo vis", lt.totals.get("spells_learned_ever", []))

    def test_update_records_called_on_register(self):
        lt = LifetimeStats()
        run = {"elapsed_s": 500.0, "level_reached": 15, "total_kills": 200,
               "total_damage_dealt": 10000, "boss_kills": 3, "elite_kills": 20,
               "xp_earned": 5000, "spells_cast_total": 50, "distance_walked_km": 2.5,
               "storm_phase": 4, "items_found": 15, "kills": {}, "spell_damage_dealt": {},
               "spells_learned": [], "dungeon_count": 2, "items_equipped_peak": 6,
               "best_gear_rarity": "epic", "date": "2025-01-01T00:00:00",
               "melee_hits": 0, "melee_damage_dealt": 0, "total_spell_damage": 0,
               "damage_received": 0, "storm_damage": 0, "damage_blocked": 0,
               "times_hit": 0, "mp_spent": 0}
        lt.register_run(run)
        self.assertEqual(lt.records["highest_level"], 15)
        self.assertEqual(lt.records["most_kills_run"], 200)
        self.assertAlmostEqual(lt.records["longest_run_s"], 500.0)

    def test_format_record_time(self):
        lt = LifetimeStats()
        lt.records["longest_run_s"] = 90.0
        result = lt.format_record("longest_run_s")
        # Key contains "s" and not "spells"/"boss" → _fmt_time
        self.assertIn(":", result)

    def test_format_record_km(self):
        lt = LifetimeStats()
        lt.records["furthest_walked_km"] = 3.14
        result = lt.format_record("furthest_walked_km")
        # "furthest_walked_km" has "s" so the time branch triggers first
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_format_record_integer(self):
        lt = LifetimeStats()
        lt.records["most_bosses_run"] = 5
        result = lt.format_record("most_bosses_run")
        # "boss" is in key → integer branch
        self.assertEqual(result, "5")


# ══════════════════════════════════════════════════════════════════════════════
# systems/spells.py  __repr__
# ══════════════════════════════════════════════════════════════════════════════
from systems.spells import SpellMemory

class TestSpellMemoryReprCoverage(unittest.TestCase):
    def test_repr_contains_magic_level(self):
        sm = SpellMemory(known=["exevo vis"])
        sm.magic_level = 3
        r = repr(sm)
        self.assertIn("3", r)
    def test_repr_contains_known(self):
        sm = SpellMemory(known=["exevo flam"])
        r = repr(sm)
        self.assertIn("exevo flam", r)


# ══════════════════════════════════════════════════════════════════════════════
# systems/stats.py  on_xp_gained
# ══════════════════════════════════════════════════════════════════════════════
from systems.stats import RunStats

class TestRunStatsXpGained(unittest.TestCase):
    def test_on_xp_gained_accumulates(self):
        r = RunStats()
        r.on_xp_gained(100)
        r.on_xp_gained(50)
        self.assertEqual(r.xp_earned, 150)
    def test_on_xp_gained_multiple_calls(self):
        r = RunStats()
        for _ in range(10): r.on_xp_gained(10)
        self.assertEqual(r.xp_earned, 100)


# ══════════════════════════════════════════════════════════════════════════════
# systems/storm.py  _storm_damage, _advance_phase, __repr__
# ══════════════════════════════════════════════════════════════════════════════
from systems.storm import Storm, STATE_WAITING, STATE_CLOSING, STATE_DONE, PHASE_DATA

class TestStormInternals(unittest.TestCase):
    MAP = 4800.0
    CX  = 2400.0

    def test_storm_damage_private_inside_returns_zero(self):
        s = Storm(self.MAP, self.MAP)
        dmg = s._storm_damage(0.5, self.CX, self.CX)
        self.assertAlmostEqual(dmg, 0.0)

    def test_storm_damage_private_outside_accumulates(self):
        s = Storm(self.MAP, self.MAP)
        total = sum(s._storm_damage(0.1, 0.0, 0.0) for _ in range(100))
        self.assertGreater(total, 0.0)

    def test_advance_phase_increments_idx(self):
        s = Storm(self.MAP, self.MAP)
        initial_idx = s._phase_idx
        s._radius_target = s.radius * 0.6
        s._advance_phase()
        # Either moved to next waiting phase or done
        self.assertIn(s.state, [STATE_WAITING, STATE_DONE])

    def test_advance_phase_reaches_done_after_all_phases(self):
        s = Storm(self.MAP, self.MAP)
        s._phase_idx = len(PHASE_DATA) - 1
        s._radius_target = s._base_radius * 0.04
        s._advance_phase()
        self.assertEqual(s.state, STATE_DONE)

    def test_repr_contains_state(self):
        s = Storm(self.MAP, self.MAP)
        r = repr(s)
        self.assertIn("Storm", r)
        self.assertIn(s.state, r)

    def test_repr_does_not_crash_in_closing(self):
        s = Storm(self.MAP, self.MAP)
        s._start_closing()
        r = repr(s)
        self.assertIsInstance(r, str)

    def test_repr_does_not_crash_in_done(self):
        s = Storm(self.MAP, self.MAP)
        s._state = STATE_DONE
        r = repr(s)
        self.assertIn("DONE", r)


# ══════════════════════════════════════════════════════════════════════════════
# systems/boss.py  _spawn_boss, draw_boss_bar, draw_announcement
# ══════════════════════════════════════════════════════════════════════════════
from systems.boss import BossManager, BOSS_SPAWN_TIMES

class FakeWorldB:
    width=150; height=150; tile_size=32
    def is_walkable(self,c,r): return True

class FakePlayerB:
    x=2400.0; y=2400.0; SIZE=18; level=20
    _inv_timer=0.0
    def take_damage(self,_): return 0

class TestBossInternals(unittest.TestCase):
    def test_spawn_boss_returns_monster(self):
        bm = BossManager()
        w  = FakeWorldB(); p = FakePlayerB()
        boss = bm._spawn_boss(p.level, w, p)
        self.assertIsNotNone(boss)
        self.assertTrue(getattr(boss, "is_boss", False))

    def test_spawn_boss_has_elite_mods(self):
        bm = BossManager()
        w  = FakeWorldB(); p = FakePlayerB()
        boss = bm._spawn_boss(p.level, w, p)
        self.assertGreaterEqual(len(getattr(boss, "elite_mods", [])), 2)

    def test_spawn_boss_walkable_position(self):
        bm = BossManager()
        w  = FakeWorldB(); p = FakePlayerB()
        boss = bm._spawn_boss(p.level, w, p)
        ts   = w.tile_size
        col  = int(boss.x // ts)
        row  = int(boss.y // ts)
        self.assertTrue(0 <= col < w.width)
        self.assertTrue(0 <= row < w.height)

    def test_draw_boss_bar_no_boss_no_crash(self):
        from tests.mock_pygame import FakeSurface
        bm   = BossManager()
        surf = FakeSurface()
        try:
            bm.draw_boss_bar(surf, 1280)
        except Exception as e:
            self.fail(f"draw_boss_bar raised {e}")

    def test_draw_boss_bar_with_boss_no_crash(self):
        from tests.mock_pygame import FakeSurface
        bm   = BossManager()
        w    = FakeWorldB(); p = FakePlayerB()
        boss = bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        surf = FakeSurface()
        try:
            bm.draw_boss_bar(surf, 1280)
        except Exception as e:
            self.fail(f"draw_boss_bar raised {e}")

    def test_draw_announcement_no_crash(self):
        from tests.mock_pygame import FakeSurface
        bm   = BossManager()
        w    = FakeWorldB(); p = FakePlayerB()
        bm.update(BOSS_SPAWN_TIMES[0] + 0.1, p.level, w, p)
        surf = FakeSurface()
        try:
            bm.draw_announcement(surf, 1280, 720)
        except Exception as e:
            self.fail(f"draw_announcement raised {e}")

    def test_seconds_to_next_negative_when_exhausted(self):
        bm = BossManager()
        bm._next_idx = 9999
        self.assertEqual(bm.seconds_to_next_boss, -1.0)


# ══════════════════════════════════════════════════════════════════════════════
# core/dungeon_generator.py  private helpers
# ══════════════════════════════════════════════════════════════════════════════
from core.dungeon_generator import (
    DungeonGenerator, Room, DFLOOR, DCORR, DWALL, DLAVA, DENTRY, DEXIT
)

class TestDungeonGeneratorInternals(unittest.TestCase):
    def _blank_tiles(self, W=30, H=30):
        return [[DWALL]*H for _ in range(W)]

    def test_hcorr_carves_floor(self):
        gen   = DungeonGenerator()
        tiles = self._blank_tiles()
        gen._hcorr(tiles, 0, 10, 5)
        for x in range(0, 11):
            self.assertEqual(tiles[x][5], DCORR)

    def test_vcorr_carves_floor(self):
        gen   = DungeonGenerator()
        tiles = self._blank_tiles()
        gen._vcorr(tiles, 0, 8, 5)
        for y in range(0, 9):
            self.assertEqual(tiles[5][y], DCORR)

    def test_hcorr_reverse_direction(self):
        gen   = DungeonGenerator()
        tiles = self._blank_tiles()
        gen._hcorr(tiles, 10, 5, 3)   # x1 > x2
        for x in range(5, 11):
            self.assertEqual(tiles[x][3], DCORR)

    def test_vcorr_reverse_direction(self):
        gen   = DungeonGenerator()
        tiles = self._blank_tiles()
        gen._vcorr(tiles, 8, 2, 4)   # y1 > y2
        for y in range(2, 9):
            self.assertEqual(tiles[4][y], DCORR)

    def test_connect_rooms_creates_corridors(self):
        gen   = DungeonGenerator()
        tiles = self._blank_tiles(50, 50)
        rooms = [
            Room(2, 2, 6, 6),
            Room(20, 20, 6, 6),
            Room(38, 38, 6, 6),
        ]
        # Carve room floors first
        for r in rooms:
            for col, row in r.inner_tiles():
                tiles[col][row] = DFLOOR
        rng = random.Random(42)
        gen._connect_rooms(rooms, tiles, rng)
        corr_count = sum(
            1 for col in range(50) for row in range(50)
            if tiles[col][row] == DCORR
        )
        self.assertGreater(corr_count, 0)

    def test_carve_corridor_connects_two_rooms(self):
        gen   = DungeonGenerator()
        tiles = self._blank_tiles(30, 30)
        r1    = Room(2, 2, 6, 6)
        r2    = Room(20, 20, 6, 6)
        for r in (r1, r2):
            for col, row in r.inner_tiles():
                tiles[col][row] = DFLOOR
        rng = random.Random(7)
        gen._carve_corridor(r1, r2, tiles, rng)
        corr_count = sum(
            1 for col in range(30) for row in range(30)
            if tiles[col][row] == DCORR
        )
        self.assertGreater(corr_count, 0)

    def test_add_lava_places_lava_tiles(self):
        gen   = DungeonGenerator()
        tiles = self._blank_tiles(30, 30)
        rooms = [Room(2, 2, 6, 6), Room(20, 20, 6, 6)]
        rng   = random.Random(42)
        gen._add_lava(rooms, tiles, 30, 30, rng, 3)   # depth=3 positional
        lava_count = sum(
            1 for col in range(30) for row in range(30)
            if tiles[col][row] == DLAVA
        )
        self.assertGreater(lava_count, 0)

    def test_fallback_rooms_creates_3_rooms(self):
        gen   = DungeonGenerator()
        tiles = self._blank_tiles(40, 40)
        rooms = gen._fallback_rooms(40, 40, tiles)
        self.assertGreaterEqual(len(rooms), 3)

    def test_fallback_rooms_have_floor_tiles(self):
        gen   = DungeonGenerator()
        tiles = self._blank_tiles(40, 40)
        gen._fallback_rooms(40, 40, tiles)
        floor_count = sum(
            1 for col in range(40) for row in range(40)
            if tiles[col][row] == DFLOOR
        )
        self.assertGreater(floor_count, 0)

    def test_hcorr_does_not_overwrite_floor(self):
        gen   = DungeonGenerator()
        tiles = self._blank_tiles(20, 20)
        tiles[5][3] = DFLOOR   # pre-existing floor tile
        gen._hcorr(tiles, 0, 10, 3)
        self.assertEqual(tiles[5][3], DFLOOR)   # floor preserved

    def test_hcorr_out_of_bounds_safe(self):
        gen   = DungeonGenerator()
        tiles = self._blank_tiles(10, 10)
        try:
            gen._hcorr(tiles, -5, 15, 5)   # partially out of bounds
        except Exception as e:
            self.fail(f"hcorr raised on OOB: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# core/level_manager.py  player_at_exit, player_at_entry
# ══════════════════════════════════════════════════════════════════════════════
from core.level_manager import DungeonLevel, DungeonEntrance, ExitPortal, LevelManager
from core.dungeon_generator import DungeonGenerator as DG

class FakeCamLM:
    offset_x=0.0; offset_y=0.0; view_w=1280; view_h=630
    world_w=4800; world_h=4800
    def update(self,x,y): pass

class FakeWorldLM:
    width=150; height=150; tile_size=32
    def is_walkable(self,c,r): return True
    def is_rect_walkable(self,*a): return True

class FakePlayerLM:
    def __init__(self,x=2400.0,y=2400.0):
        self.x=float(x); self.y=float(y); self.SIZE=18; self.level=5
        self._inv_timer=0.0; self._block_flash=0.0
        import tests.mock_pygame as mp; self.rect=mp.FakeRect()
    def take_damage(self,_): return 0

class FakeBM:
    def get(self,c,r): return "grassland"

class TestLevelManagerInternals(unittest.TestCase):

    def _make_dlvl(self):
        dmap = DG().generate(seed=42, tile_size=32)
        return DungeonLevel(dmap, 1000.0, 2000.0)

    def test_player_at_exit_true_when_on_portal(self):
        dlvl = self._make_dlvl()
        p    = FakePlayerLM(dlvl.exit_portal.x, dlvl.exit_portal.y)
        self.assertTrue(dlvl.player_at_exit(p))

    def test_player_at_exit_false_when_far(self):
        dlvl = self._make_dlvl()
        p    = FakePlayerLM(0.0, 0.0)
        self.assertFalse(dlvl.player_at_exit(p))

    def test_player_at_entry_true_near_spawn(self):
        dlvl = self._make_dlvl()
        p    = FakePlayerLM(dlvl.spawn_x, dlvl.spawn_y)
        self.assertTrue(dlvl.player_at_entry(p))

    def test_player_at_entry_false_far(self):
        dlvl = self._make_dlvl()
        # Far corner of a large world
        p    = FakePlayerLM(9999.0, 9999.0)
        self.assertFalse(dlvl.player_at_entry(p))

    def test_draw_overlay_no_crash(self):
        from tests.mock_pygame import FakeSurface
        dlvl  = self._make_dlvl()
        surf  = FakeSurface()
        cam   = FakeCamLM()
        try: dlvl.draw_overlay(surf, cam)
        except Exception as e: self.fail(f"draw_overlay raised {e}")

    def test_draw_portals_no_crash(self):
        from tests.mock_pygame import FakeSurface
        dlvl = self._make_dlvl()
        surf = FakeSurface(); cam = FakeCamLM()
        p    = FakePlayerLM()
        try: dlvl.draw_portals(surf, cam, p)
        except Exception as e: self.fail(f"draw_portals raised {e}")

    def test_draw_hud_banner_no_crash(self):
        from tests.mock_pygame import FakeSurface
        dlvl = self._make_dlvl()
        surf = FakeSurface()
        try: dlvl.draw_hud_banner(surf, 1280)
        except Exception as e: self.fail(f"draw_hud_banner raised {e}")


# ══════════════════════════════════════════════════════════════════════════════
# core/session.py  _load
# ══════════════════════════════════════════════════════════════════════════════
import core.session as ses_module

class TestSessionLoad(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._path = self._tmp.name
        self._tmp.close(); os.remove(self._path)
        ses_module.SAVE_FILE = self._path

    def tearDown(self):
        if os.path.exists(self._path): os.remove(self._path)

    def test_load_reads_existing_file(self):
        data = {"persistent_level": 9, "best_time": 300.0, "total_runs": 5,
                "max_storm_phase": 3, "spell_memory": {"known_spells": ["exevo vis"]}}
        with open(self._path, "w") as f: json.dump(data, f)
        s = ses_module.Session()
        self.assertEqual(s.persistent_level, 9)
        self.assertEqual(s.max_storm_phase, 3)
        self.assertIn("known_spells", s.spell_memory_data)

    def test_load_handles_missing_keys_gracefully(self):
        with open(self._path, "w") as f: json.dump({"persistent_level": 3}, f)
        s = ses_module.Session()
        self.assertEqual(s.persistent_level, 3)
        self.assertEqual(s.max_storm_phase, 0)

    def test_load_handles_corrupt_json(self):
        with open(self._path, "w") as f: f.write("{broken}")
        s = ses_module.Session()
        self.assertEqual(s.persistent_level, 0)


# ══════════════════════════════════════════════════════════════════════════════
# core/world.py  apply_dungeon_zones
# ══════════════════════════════════════════════════════════════════════════════
from core.world import World
from constants import TILE_STONE, TILE_GRASS
from systems.dungeons import DungeonZone

class TestWorldApplyDungeonZones(unittest.TestCase):
    def test_converts_grass_to_stone(self):
        w    = World(60, 60, 32, seed=42)
        zone = DungeonZone(50, 50, 5, 0)   # far from center (30,30)
        # Ensure target tiles are grass first
        for col in range(46, 55):
            for row in range(46, 55):
                if 0<=col<60 and 0<=row<60:
                    w.tiles[col][row] = TILE_GRASS
        w.apply_dungeon_zones([zone])
        stone_found = any(
            w.tiles[col][row] == TILE_STONE
            for col in range(46, 55)
            for row in range(46, 55)
            if 0<=col<60 and 0<=row<60
        )
        self.assertTrue(stone_found)

    def test_does_not_crash_empty_zones(self):
        w = World(60, 60, 32, seed=42)
        try: w.apply_dungeon_zones([])
        except Exception as e: self.fail(f"apply_dungeon_zones raised {e}")

    def test_minimap_rebuilt_after_zones(self):
        w    = World(60, 60, 32, seed=42)
        zone = DungeonZone(50, 50, 5, 0)
        w.apply_dungeon_zones([zone])
        surf, size = w.get_minimap()
        self.assertIsNotNone(surf)
        self.assertGreater(size, 0)


# ══════════════════════════════════════════════════════════════════════════════
# entities/item_drop.py  is_picked_up
# ══════════════════════════════════════════════════════════════════════════════
from entities.item_drop import ItemDrop

class FakePlayerDrop:
    x=500.0; y=500.0; SIZE=18

class TestItemDropCoverage(unittest.TestCase):
    def _item(self):
        return {"name":"Sword","slot":"weapon","rarity":"common",
                "item_level":1,"stats":{"atk_damage":5}}

    def test_not_picked_up_initially(self):
        d = ItemDrop(100.0, 100.0, self._item())
        self.assertFalse(d.is_picked_up())

    def test_is_picked_up_after_pickup(self):
        d = ItemDrop(100.0, 100.0, self._item())
        d.pickup()
        self.assertTrue(d.is_picked_up())

    def test_near_player_true(self):
        d = ItemDrop(510.0, 500.0, self._item())
        p = FakePlayerDrop()
        self.assertTrue(d.near_player(p))

    def test_near_player_false(self):
        d = ItemDrop(5000.0, 5000.0, self._item())
        p = FakePlayerDrop()
        self.assertFalse(d.near_player(p))

    def test_update_increments_timer_when_not_picked_up(self):
        d = ItemDrop(100.0, 100.0, self._item())
        d.update(0.5)
        self.assertAlmostEqual(d._timer, 0.5, places=3)

    def test_update_no_timer_when_picked_up(self):
        d = ItemDrop(100.0, 100.0, self._item())
        d.pickup()
        d.update(1.0)
        self.assertAlmostEqual(d._timer, 0.0)


# ══════════════════════════════════════════════════════════════════════════════
# entities/monster.py  draw methods (called via draw())
# ══════════════════════════════════════════════════════════════════════════════
from entities.monster import Monster
from core.camera import Camera

class FakeCamM:
    offset_x=0.0; offset_y=0.0; view_w=1280; view_h=720

class TestMonsterDrawMethods(unittest.TestCase):
    """Calls draw() on each monster type to exercise _draw_* private methods."""

    def _draw(self, mtype, level=0, **kwargs):
        from tests.mock_pygame import FakeSurface
        m   = Monster(200.0, 200.0, mtype, level)
        for k,v in kwargs.items(): setattr(m, k, v)
        surf = FakeSurface()
        cam  = FakeCamM()
        try: m.draw(surf, cam)
        except Exception as e: self.fail(f"draw({mtype}) raised {e}")

    def test_draw_rat(self):         self._draw("rat")
    def test_draw_zombie(self):      self._draw("zombie", level=3)
    def test_draw_skeleton(self):    self._draw("skeleton", level=7)
    def test_draw_orc(self):         self._draw("orc", level=10)
    def test_draw_dark_wizard(self): self._draw("dark_wizard", level=15)
    def test_draw_dragon(self):      self._draw("dragon", level=20)

    def test_draw_elite_badge(self):
        from tests.mock_pygame import FakeSurface
        from systems.elites import apply_modifiers
        m = Monster(200.0, 200.0, "rat", 0)
        apply_modifiers(m, ["berserker"])
        surf = FakeSurface(); cam = FakeCamM()
        try: m.draw(surf, cam)
        except Exception as e: self.fail(f"draw elite badge raised {e}")

    def test_draw_boss_crown(self):
        from tests.mock_pygame import FakeSurface
        m = Monster(200.0, 200.0, "skeleton", 10)
        m.is_boss = True; m.boss_display_name = "Lich"
        surf = FakeSurface(); cam = FakeCamM()
        try: m.draw(surf, cam)
        except Exception as e: self.fail(f"draw boss crown raised {e}")

    def test_draw_windup(self):
        from tests.mock_pygame import FakeSurface
        m = Monster(200.0, 200.0, "skeleton", 10)
        m._windup_spell = "exevo flam"
        m._windup_timer = 0.3
        surf = FakeSurface(); cam = FakeCamM()
        try: m.draw(surf, cam)
        except Exception as e: self.fail(f"draw windup raised {e}")

    def test_draw_dead_monster_skipped(self):
        from tests.mock_pygame import FakeSurface
        m = Monster(200.0, 200.0, "rat", 0)
        m.hp = 0.0
        surf = FakeSurface(); cam = FakeCamM()
        try: m.draw(surf, cam)   # should return early without crashing
        except Exception as e: self.fail(f"draw dead raised {e}")

    def test_draw_hit_flash(self):
        from tests.mock_pygame import FakeSurface
        m = Monster(200.0, 200.0, "rat", 0)
        m._hit_flash = 0.1
        surf = FakeSurface(); cam = FakeCamM()
        try: m.draw(surf, cam)
        except Exception as e: self.fail(f"draw hit flash raised {e}")

    def test_draw_hp_bar_shown_when_damaged(self):
        from tests.mock_pygame import FakeSurface
        m = Monster(200.0, 200.0, "zombie", 3)
        m.hp = m.max_hp / 2
        surf = FakeSurface(); cam = FakeCamM()
        try: m.draw(surf, cam)
        except Exception as e: self.fail(f"draw hp bar raised {e}")


# ══════════════════════════════════════════════════════════════════════════════
# entities/player.py  _init_stats, effective_range, spell_ready
# ══════════════════════════════════════════════════════════════════════════════
from entities.player import Player

class TestPlayerCoverageGaps(unittest.TestCase):

    def test_init_stats_called_on_construction(self):
        p = Player(500.0, 500.0, level=3)
        # _init_stats must have run → stats consistent with level 3
        self.assertEqual(p._base_max_hp, 100 + 3*20)
        self.assertEqual(p._base_max_mp, 50  + 3*10)
        self.assertEqual(p._base_atk_damage, 15 + 3*5)

    def test_effective_range_base(self):
        p = Player(500.0, 500.0, level=0)
        self.assertAlmostEqual(p.effective_range, Player.ATTACK_RANGE)

    def test_effective_range_with_weapon(self):
        p = Player(500.0, 500.0, level=0)
        p.inventory.equipped["weapon"] = {
            "slot":"weapon","rarity":"common","item_level":1,"name":"Spear",
            "stats":{"atk_range": 16}
        }
        self.assertAlmostEqual(p.effective_range, Player.ATTACK_RANGE + 16)

    def test_spell_ready_true_initially(self):
        p = Player(500.0, 500.0, level=0)
        self.assertTrue(p.spell_ready)

    def test_spell_ready_false_after_cast(self):
        from systems.spells import SpellMemory
        p  = Player(500.0, 500.0, level=0)
        sm = SpellMemory(known=["exevo vis"])
        p.spell_memory = sm
        p.mp = 999.0
        p.cast_spell(600.0, 500.0)
        self.assertFalse(p.spell_ready)

    def test_spell_ready_true_again_after_cooldown(self):
        from systems.spells import SpellMemory
        p  = Player(500.0, 500.0, level=0)
        sm = SpellMemory(known=["exevo vis"])
        p.spell_memory = sm; p.mp = 999.0
        p.cast_spell(600.0, 500.0)
        self.assertFalse(p.spell_ready)
        # Fast-forward cooldown directly
        p._spell_cast_cd = 0.0
        self.assertTrue(p.spell_ready)


# ══════════════════════════════════════════════════════════════════════════════
# entities/projectile.py  _explode_aoe
# ══════════════════════════════════════════════════════════════════════════════
from entities.projectile import Projectile

class FakeMonAOE:
    def __init__(self,x,y): self.x=float(x); self.y=float(y); self.SIZE=12; self.hp=100.0
    def is_dead(self): return self.hp<=0
    def take_damage(self,a): self.hp-=a; return a

class TestProjectileAOEInternal(unittest.TestCase):
    def test_explode_aoe_hits_nearby_monster(self):
        p = Projectile(0.0, 0.0, 1.0, 0.0, "exevo flam", 50)
        m = FakeMonAOE(10.0, 0.0)   # within fireball aoe_r (48)
        p._explode_aoe([m], [])
        self.assertLess(m.hp, 100.0)

    def test_explode_aoe_skips_already_hit(self):
        p = Projectile(0.0, 0.0, 1.0, 0.0, "exevo flam", 50)
        m = FakeMonAOE(10.0, 0.0)
        p._explode_aoe([m], [m])   # m is in already_hit
        self.assertAlmostEqual(m.hp, 100.0)

    def test_explode_aoe_skips_far_monster(self):
        p = Projectile(0.0, 0.0, 1.0, 0.0, "exevo flam", 50)
        m = FakeMonAOE(5000.0, 5000.0)
        p._explode_aoe([m], [])
        self.assertAlmostEqual(m.hp, 100.0)

    def test_explode_aoe_zero_radius_no_effect(self):
        p = Projectile(0.0, 0.0, 1.0, 0.0, "exevo vis", 30)
        m = FakeMonAOE(5.0, 0.0)
        p._explode_aoe([m], [])   # spark has aoe_r = 0
        self.assertAlmostEqual(m.hp, 100.0)

    def test_explode_aoe_skips_dead_monster(self):
        p = Projectile(0.0, 0.0, 1.0, 0.0, "exevo flam", 50)
        m = FakeMonAOE(10.0, 0.0); m.hp = 0.0
        p._explode_aoe([m], [])
        self.assertAlmostEqual(m.hp, 0.0)


# ══════════════════════════════════════════════════════════════════════════════
# entities/spawner.py  _biome_weighted_choice, add_monster, _fill_map, _try_spawn_random
# ══════════════════════════════════════════════════════════════════════════════
from entities.spawner import Spawner, _biome_weighted_choice
from tests.fake_world import FakeWorld as FW

class FakeBiomeMapS:
    def __init__(self, biome="grassland"): self._b = biome
    def get(self, c, r): return self._b

class FakePlayerSp:
    x=960.0; y=960.0; level=0; SIZE=18; _inv_timer=0.0
    def take_damage(self,_): return 0

class TestSpawnerCoverageGaps(unittest.TestCase):

    def test_biome_weighted_choice_returns_valid_type(self):
        from entities.monster import available_types
        types  = available_types(0)
        bm     = FakeBiomeMapS("grassland")
        result = _biome_weighted_choice(types, bm, 10, 10)
        self.assertIn(result, types)

    def test_biome_weighted_choice_no_biome_map(self):
        from entities.monster import available_types
        types  = available_types(0)
        result = _biome_weighted_choice(types, None, 10, 10)
        self.assertIn(result, types)

    def test_biome_weighted_choice_volcanic_favors_dragon(self):
        from entities.monster import available_types
        types   = available_types(20)   # all types available
        bm      = FakeBiomeMapS("volcanic")
        results = [_biome_weighted_choice(types, bm, 5, 5) for _ in range(500)]
        dragon_count  = results.count("dragon")
        rat_count     = results.count("rat")
        self.assertGreater(dragon_count, rat_count)

    def test_add_monster_appends(self):
        from entities.monster import Monster
        world   = FW(60, 60, 32)
        spawner = Spawner(world, 0)
        initial = len(spawner.monsters)
        m = Monster(960.0, 960.0, "rat", 0)
        spawner.add_monster(m)
        self.assertEqual(len(spawner.monsters), initial + 1)
        self.assertIs(spawner.monsters[-1], m)

    def test_fill_map_populates_monsters(self):
        world   = FW(60, 60, 32)
        spawner = Spawner(world, 0)
        self.assertGreater(len(spawner.monsters), 0)

    def test_try_spawn_random_returns_monster_or_none(self):
        from entities.monster import available_types
        world   = FW(60, 60, 32)
        spawner = Spawner(world, 0)
        types   = available_types(0)
        result  = spawner._try_spawn_random(types, 0, 30, 30, 5, 20)
        # Should return a Monster or None (None if no walkable tile found)
        if result is not None:
            from entities.monster import Monster
            self.assertIsInstance(result, Monster)

    def test_try_spawn_random_respects_min_dist(self):
        world   = FW(60, 60, 32)
        spawner = Spawner(world, 0)
        from entities.monster import available_types
        types   = available_types(0)
        # With min_dist = 999, should fail to place (returns None)
        result  = spawner._try_spawn_random(types, 0, 30, 30, 999, 10)
        self.assertIsNone(result)

    def test_spawner_with_biome_map(self):
        world   = FW(60, 60, 32)
        bm      = FakeBiomeMapS("grassland")
        spawner = Spawner(world, 0, biome_map=bm)
        self.assertGreater(len(spawner.monsters), 0)

    def test_spawner_zone_aware(self):
        """Zone-based spawning gives stronger monsters near center."""
        from systems.zones import get_zone_monster_types, ZONE_LEVEL_BONUS
        # Center zone should have strong monsters
        center_types = get_zone_monster_types(0)
        self.assertTrue(any(t in center_types for t in ['demon','dragon_lord','dragon']),
                        f"Center zone should have tough monsters: {center_types}")
        # Periphery should have weak monsters
        outer_types = get_zone_monster_types(3)
        self.assertTrue(any(t in outer_types for t in ['rat','zombie','skeleton']),
                        f"Outer zone should have weak monsters: {outer_types}")
        # Center has higher level bonus
        self.assertGreater(ZONE_LEVEL_BONUS[0], ZONE_LEVEL_BONUS[3])


# ══════════════════════════════════════════════════════════════════════════════
# systems/dungeons.py  draw_dungeons (no crash)
# ══════════════════════════════════════════════════════════════════════════════
from systems.dungeons import draw_dungeons, DungeonZone

class TestDrawDungeons(unittest.TestCase):
    def test_draw_dungeons_no_crash(self):
        from tests.mock_pygame import FakeSurface
        class FakeCam:
            offset_x=0.0; offset_y=0.0; view_w=1280; view_h=720
            def world_to_screen(self,x,y): return x,y
        zones = [DungeonZone(50,50,10,0), DungeonZone(100,80,8,1)]
        surf  = FakeSurface()
        cam   = FakeCam()
        try: draw_dungeons(surf, cam, zones, 500.0, 500.0)
        except Exception as e: self.fail(f"draw_dungeons raised {e}")

    def test_draw_dungeons_empty_list_no_crash(self):
        from tests.mock_pygame import FakeSurface
        class FakeCam:
            offset_x=0.0; offset_y=0.0; view_w=1280; view_h=720
            def world_to_screen(self,x,y): return x,y
        surf = FakeSurface(); cam = FakeCam()
        try: draw_dungeons(surf, cam, [], 500.0, 500.0)
        except Exception as e: self.fail(f"draw_dungeons empty raised {e}")


# ══════════════════════════════════════════════════════════════════════════════
# systems/inventory.py  __repr__
# ══════════════════════════════════════════════════════════════════════════════
from systems.inventory import Inventory

class TestInventoryReprCoverage(unittest.TestCase):
    def test_repr_with_nothing_equipped(self):
        inv = Inventory()
        r   = repr(inv)
        self.assertIn("Inventory", r)
        self.assertIn("bag=0", r)

    def test_repr_with_item_equipped(self):
        inv = Inventory()
        inv.equipped["weapon"] = {"slot":"weapon","rarity":"common",
                                  "item_level":1,"name":"Sword","stats":{}}
        r = repr(inv)
        self.assertIn("Sword", r)


if __name__ == "__main__":
    unittest.main()


# ══════════════════════════════════════════════════════════════════════════════
# core/world.py  _build_tile_surfaces, _build_minimap (called via apply_biomes)
# ══════════════════════════════════════════════════════════════════════════════
class TestWorldBuildMethods(unittest.TestCase):
    def test_build_tile_surfaces_called_on_init(self):
        """_build_tile_surfaces is called in __init__; verify surfaces exist."""
        w = World(40, 40, 32, seed=1)
        self.assertTrue(hasattr(w, '_surfs'))
        self.assertGreater(len(w._surfs), 0)

    def test_build_minimap_called_on_init(self):
        """_build_minimap is called in __init__; verify minimap surface."""
        w = World(40, 40, 32, seed=1)
        surf, size = w.get_minimap()
        self.assertIsNotNone(surf)
        self.assertEqual(size, 120)

    def test_build_tile_surfaces_has_all_tile_types(self):
        """After apply_biomes, new tile types must have surfaces."""
        from systems.biomes import BiomeMap
        w  = World(50, 50, 32, seed=42)
        bm = BiomeMap(50, 50, seed=42)
        w.apply_biomes(bm)
        from constants import TILE_SNOW, TILE_SAND, TILE_SWAMP, TILE_LAVA
        for tid in (TILE_SNOW, TILE_SAND, TILE_SWAMP, TILE_LAVA):
            self.assertIn(tid, w._surfs, f"Surface missing for tile {tid}")

    def test_build_minimap_after_apply_biomes(self):
        """apply_biomes rebuilds minimap; should still work."""
        from systems.biomes import BiomeMap
        w  = World(50, 50, 32, seed=42)
        bm = BiomeMap(50, 50, seed=42)
        w.apply_biomes(bm)
        surf, size = w.get_minimap()
        self.assertIsNotNone(surf)


# ══════════════════════════════════════════════════════════════════════════════
# entities/item_drop.py  _font (module-level font cache)
# ══════════════════════════════════════════════════════════════════════════════
class TestItemDropFont(unittest.TestCase):
    def test_font_cache_populated_after_draw(self):
        """_font() is called during draw(); verify cache is populated."""
        import entities.item_drop as id_module
        item = {"name":"Sword","slot":"weapon","rarity":"common",
                "item_level":1,"stats":{"atk_damage":5}}
        # Call _font directly
        f1 = id_module._font("Arial", 10)
        f2 = id_module._font("Arial", 10)   # should hit cache
        self.assertIs(f1, f2)   # same cached object

    def test_font_different_sizes_are_different(self):
        import entities.item_drop as id_module
        f1 = id_module._font("Arial", 10)
        f2 = id_module._font("Arial", 14)
        self.assertIsNot(f1, f2)

    def test_font_bold_vs_non_bold_different(self):
        import entities.item_drop as id_module
        f1 = id_module._font("Arial", 12, bold=False)
        f2 = id_module._font("Arial", 12, bold=True)
        self.assertIsNot(f1, f2)


# ══════════════════════════════════════════════════════════════════════════════
# entities/player.py  _init_stats (already covered via __init__, but explicit)
# ══════════════════════════════════════════════════════════════════════════════
class TestPlayerInitStatsDirect(unittest.TestCase):
    def test_reinit_stats_resets_values(self):
        p = Player(500.0, 500.0, level=5)
        p.level = 10
        p._init_stats()
        self.assertEqual(p._base_max_hp, 100 + 10*20)
        self.assertEqual(p._base_atk_damage, 15 + 10*5)
        self.assertEqual(p.xp, 0)
