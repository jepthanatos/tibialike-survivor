"""Tests unitarios para systems/stats.py y systems/lifetime_stats.py"""
import sys, os, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame
from tests.mock_pygame import FakeStorm

import unittest
from systems.stats          import RunStats, RARITY_ORDER
from systems.lifetime_stats import LifetimeStats, RANKING_KEYS, TOP_N
import systems.lifetime_stats as lt_module


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_run(**overrides) -> dict:
    """Minimal run dict for testing LifetimeStats."""
    base = {
        "date":                 "2025-01-01T00:00:00",
        "elapsed_s":            120.0,
        "level_reached":        5,
        "storm_phase":          2,
        "time_in_storm_s":      15.0,
        "dungeon_count":        1,
        "kills":                {"rat": 10, "zombie": 5},
        "total_kills":          15,
        "elite_kills":          2,
        "boss_kills":           0,
        "melee_hits":           30,
        "melee_damage_dealt":   600,
        "spell_damage_dealt":   {"exevo vis": 200},
        "total_spell_damage":   200,
        "total_damage_dealt":   800,
        "spells_cast":          {"exevo vis": 8},
        "spells_cast_total":    8,
        "spells_learned":       ["exevo vis"],
        "damage_received":      120,
        "storm_damage":         20,
        "damage_blocked":       30,
        "times_hit":            12,
        "xp_earned":            450,
        "mp_spent":             80,
        "items_found":          3,
        "items_equipped_peak":  2,
        "best_gear_rarity":     "uncommon",
        "distance_walked_km":   0.5,
    }
    base.update(overrides)
    return base


class FakeMonster:
    def __init__(self, mtype="rat", is_boss=False, is_elite=False):
        self.mtype    = mtype
        self.is_boss  = is_boss
        self.is_elite = is_elite
        self.xp_reward= 10


class FakePlayer:
    def __init__(self):
        self.level = 3

# FakeStorm imported from tests.mock_pygame


# ══════════════════════════════════════════════════════════════════════════════
# RunStats
# ══════════════════════════════════════════════════════════════════════════════

class TestRunStatsInit(unittest.TestCase):

    def test_starts_empty(self):
        r = RunStats()
        self.assertEqual(r.total_kills, 0)
        self.assertEqual(r.elapsed_s, 0.0)
        self.assertEqual(r.level_reached, 0)
        self.assertEqual(r.kills, {})
        self.assertEqual(r.spells_cast, {})

    def test_reset_clears_all(self):
        r = RunStats()
        r.on_kill(FakeMonster("rat"))
        r.on_melee_hit(50)
        r.reset()
        self.assertEqual(r.total_kills, 0)
        self.assertEqual(r.melee_damage_dealt, 0)


class TestRunStatsKills(unittest.TestCase):

    def test_on_kill_increments_type(self):
        r = RunStats()
        r.on_kill(FakeMonster("rat"))
        r.on_kill(FakeMonster("rat"))
        r.on_kill(FakeMonster("zombie"))
        self.assertEqual(r.kills["rat"], 2)
        self.assertEqual(r.kills["zombie"], 1)

    def test_total_kills_sum(self):
        r = RunStats()
        for _ in range(5): r.on_kill(FakeMonster("rat"))
        for _ in range(3): r.on_kill(FakeMonster("zombie"))
        self.assertEqual(r.total_kills, 8)

    def test_elite_kill_increments_elite_counter(self):
        r = RunStats()
        r.on_kill(FakeMonster("skeleton", is_elite=True))
        self.assertEqual(r.elite_kills, 1)
        self.assertEqual(r.total_kills, 1)

    def test_boss_kill_increments_boss_counter(self):
        r = RunStats()
        r.on_kill(FakeMonster("skeleton", is_boss=True))
        self.assertEqual(r.boss_kills, 1)
        self.assertEqual(r.elite_kills, 0)

    def test_most_killed_type(self):
        r = RunStats()
        for _ in range(7): r.on_kill(FakeMonster("rat"))
        for _ in range(3): r.on_kill(FakeMonster("zombie"))
        self.assertEqual(r.most_killed_type, "rat")


class TestRunStatsDamage(unittest.TestCase):

    def test_melee_hit_accumulates(self):
        r = RunStats()
        r.on_melee_hit(30)
        r.on_melee_hit(45)
        self.assertEqual(r.melee_damage_dealt, 75)
        self.assertEqual(r.melee_hits, 2)

    def test_spell_hit_by_id(self):
        r = RunStats()
        r.on_spell_hit("exevo vis", 80)
        r.on_spell_hit("exevo vis", 60)
        r.on_spell_hit("exevo flam", 200)
        self.assertEqual(r.spell_damage_dealt["exevo vis"], 140)
        self.assertEqual(r.spell_damage_dealt["exevo flam"], 200)

    def test_total_spell_damage(self):
        r = RunStats()
        r.on_spell_hit("exevo vis", 100)
        r.on_spell_hit("exevo flam", 250)
        self.assertEqual(r.total_spell_damage, 350)

    def test_total_damage_dealt(self):
        r = RunStats()
        r.on_melee_hit(100)
        r.on_spell_hit("exevo vis", 200)
        self.assertEqual(r.total_damage_dealt, 300)

    def test_damage_received_accumulates(self):
        r = RunStats()
        r.on_damage_received(20)
        r.on_damage_received(30, "storm")
        self.assertEqual(r.damage_received, 50)
        self.assertEqual(r.storm_damage, 30)
        self.assertEqual(r.times_hit, 2)

    def test_zero_damage_not_counted(self):
        r = RunStats()
        r.on_damage_received(0)
        self.assertEqual(r.times_hit, 0)

    def test_damage_blocked(self):
        r = RunStats()
        r.on_damage_blocked(15)
        r.on_damage_blocked(20)
        self.assertEqual(r.damage_blocked, 35)


class TestRunStatsSpells(unittest.TestCase):

    def test_spell_cast_tracked(self):
        r = RunStats()
        r.on_spell_cast("exevo vis", 6)
        r.on_spell_cast("exevo vis", 6)
        r.on_spell_cast("exevo flam", 22)
        self.assertEqual(r.spells_cast["exevo vis"], 2)
        self.assertEqual(r.spells_cast["exevo flam"], 1)

    def test_mp_spent_accumulates(self):
        r = RunStats()
        r.on_spell_cast("exevo vis", 6)
        r.on_spell_cast("exevo flam", 22)
        self.assertEqual(r.mp_spent, 28)

    def test_total_spells_cast(self):
        r = RunStats()
        r.on_spell_cast("exevo vis", 6)
        r.on_spell_cast("exevo vis", 6)
        self.assertEqual(r.total_spells_cast, 2)

    def test_favourite_spell_most_cast(self):
        r = RunStats()
        for _ in range(5): r.on_spell_cast("exevo vis", 6)
        for _ in range(2): r.on_spell_cast("exevo flam", 22)
        self.assertEqual(r.favourite_spell, "exevo vis")

    def test_favourite_spell_none_when_no_casts(self):
        r = RunStats()
        self.assertIsNone(r.favourite_spell)

    def test_spell_learned_stored(self):
        r = RunStats()
        r.on_spell_learned("exevo vis")
        r.on_spell_learned("exevo flam")
        self.assertIn("exevo vis", r.spells_learned)
        self.assertIn("exevo flam", r.spells_learned)

    def test_spell_learned_no_duplicates(self):
        r = RunStats()
        r.on_spell_learned("exevo vis")
        r.on_spell_learned("exevo vis")
        self.assertEqual(r.spells_learned.count("exevo vis"), 1)


class TestRunStatsItems(unittest.TestCase):

    def test_items_found_increments(self):
        r = RunStats()
        r.on_item_found({"rarity": "common"})
        r.on_item_found({"rarity": "rare"})
        self.assertEqual(r.items_found, 2)

    def test_best_rarity_updated(self):
        r = RunStats()
        r.on_item_found({"rarity": "common"})
        r.on_item_found({"rarity": "epic"})
        self.assertEqual(r.best_gear_rarity, "epic")

    def test_best_rarity_not_downgraded(self):
        r = RunStats()
        r.on_item_found({"rarity": "rare"})
        r.on_item_found({"rarity": "common"})
        self.assertEqual(r.best_gear_rarity, "rare")

    def test_equipped_peak_updates(self):
        r = RunStats()
        r.on_item_equipped_check(3)
        r.on_item_equipped_check(1)
        r.on_item_equipped_check(5)
        self.assertEqual(r.items_equipped_peak, 5)


class TestRunStatsMovement(unittest.TestCase):

    def test_distance_accumulates(self):
        r = RunStats()
        r.on_player_moved(0.0, 0.0)
        r.on_player_moved(100.0, 0.0)
        r.on_player_moved(100.0, 50.0)
        self.assertAlmostEqual(r.distance_walked_px, 150.0)

    def test_first_move_no_distance(self):
        r = RunStats()
        r.on_player_moved(500.0, 500.0)
        self.assertEqual(r.distance_walked_px, 0.0)

    def test_km_walked_conversion(self):
        r = RunStats()
        r.distance_walked_px = 32_000  # = 1 km
        self.assertAlmostEqual(r.km_walked, 1.0, places=5)


class TestRunStatsDungeon(unittest.TestCase):

    def test_dungeon_count_unique(self):
        r = RunStats()
        r.on_dungeon_entered(0)
        r.on_dungeon_entered(0)
        r.on_dungeon_entered(1)
        self.assertEqual(r.dungeon_count, 2)


class TestRunStatsStorm(unittest.TestCase):

    def test_time_in_storm_accumulates_when_outside(self):
        r = RunStats()
        r.on_storm_tick(0.5, in_storm=True)
        r.on_storm_tick(0.5, in_storm=True)
        self.assertAlmostEqual(r.time_in_storm_s, 1.0)

    def test_time_not_accumulated_when_inside_safe(self):
        r = RunStats()
        r.on_storm_tick(1.0, in_storm=False)
        self.assertAlmostEqual(r.time_in_storm_s, 0.0)


class TestRunStatsFinalise(unittest.TestCase):

    def test_finalise_snapshots_level(self):
        r = RunStats()
        p = FakePlayer(); s = FakeStorm()
        r.finalise(p, s)
        self.assertEqual(r.level_reached, 3)

    def test_finalise_snapshots_storm_phase(self):
        r = RunStats()
        p = FakePlayer(); s = FakeStorm()
        r.finalise(p, s)
        self.assertEqual(r.storm_phase, s.phase_reached)


class TestRunStatsToDict(unittest.TestCase):

    def test_to_dict_has_required_keys(self):
        r = RunStats()
        d = r.to_dict()
        for key in ("elapsed_s","level_reached","total_kills","total_damage_dealt",
                    "xp_earned","items_found","distance_walked_km","storm_phase"):
            self.assertIn(key, d, f"Missing key: {key}")

    def test_to_dict_date_present(self):
        r = RunStats()
        d = r.to_dict()
        self.assertIn("date", d)
        self.assertIsInstance(d["date"], str)

    def test_to_dict_values_correct(self):
        r = RunStats()
        r.on_melee_hit(100)
        r.on_spell_hit("exevo vis", 50)
        d = r.to_dict()
        self.assertEqual(d["melee_damage_dealt"], 100)
        self.assertEqual(d["total_spell_damage"], 50)
        self.assertEqual(d["total_damage_dealt"], 150)


# ══════════════════════════════════════════════════════════════════════════════
# LifetimeStats
# ══════════════════════════════════════════════════════════════════════════════

class TestLifetimeStatsBase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._path = self._tmp.name
        self._tmp.close()
        os.remove(self._path)
        lt_module.HISTORY_FILE = self._path
        self.lt = LifetimeStats()

    def tearDown(self):
        if os.path.exists(self._path):
            os.remove(self._path)


class TestLifetimeStatsInit(TestLifetimeStatsBase):

    def test_empty_initially(self):
        self.assertEqual(self.lt.runs, [])
        self.assertEqual(self.lt.totals, {})
        self.assertEqual(self.lt.records, {})

    def test_total_runs_zero(self):
        self.assertEqual(self.lt.total_runs(), 0)


class TestLifetimeStatsRegister(TestLifetimeStatsBase):

    def test_register_adds_run(self):
        self.lt.register_run(_make_run())
        self.assertEqual(len(self.lt.runs), 1)

    def test_total_runs_increments(self):
        self.lt.register_run(_make_run())
        self.lt.register_run(_make_run())
        self.assertEqual(self.lt.total_runs(), 2)

    def test_register_persists_to_file(self):
        self.lt.register_run(_make_run(level_reached=8))
        lt2 = LifetimeStats()
        self.assertEqual(lt2.total_runs(), 1)
        self.assertEqual(lt2.runs[0]["level_reached"], 8)

    def test_max_runs_stored_respected(self):
        from systems.lifetime_stats import MAX_RUNS_STORED
        for _ in range(MAX_RUNS_STORED + 5):
            self.lt.register_run(_make_run())
        self.assertLessEqual(len(self.lt.runs), MAX_RUNS_STORED)


class TestLifetimeTotals(TestLifetimeStatsBase):

    def test_totals_accumulate_kills(self):
        self.lt.register_run(_make_run(total_kills=10))
        self.lt.register_run(_make_run(total_kills=15))
        self.assertEqual(self.lt.totals["total_kills"], 25)

    def test_totals_accumulate_xp(self):
        self.lt.register_run(_make_run(xp_earned=500))
        self.lt.register_run(_make_run(xp_earned=300))
        self.assertEqual(self.lt.totals["xp_earned"], 800)

    def test_totals_accumulate_elapsed(self):
        self.lt.register_run(_make_run(elapsed_s=100.0))
        self.lt.register_run(_make_run(elapsed_s=200.0))
        self.assertAlmostEqual(self.lt.totals["elapsed_s"], 300.0)

    def test_totals_kill_breakdown_by_type(self):
        self.lt.register_run(_make_run(kills={"rat":10,"zombie":5}))
        self.lt.register_run(_make_run(kills={"rat":3,"skeleton":8}))
        self.assertEqual(self.lt.totals["kills_rat"], 13)
        self.assertEqual(self.lt.totals["kills_zombie"], 5)
        self.assertEqual(self.lt.totals["kills_skeleton"], 8)

    def test_totals_spells_learned_union(self):
        self.lt.register_run(_make_run(spells_learned=["exevo vis"]))
        self.lt.register_run(_make_run(spells_learned=["exevo flam","exevo vis"]))
        learned = self.lt.totals["spells_learned_ever"]
        self.assertIn("exevo vis", learned)
        self.assertIn("exevo flam", learned)
        self.assertEqual(learned.count("exevo vis"), 1)   # no duplicates

    def test_average_kills_per_run(self):
        self.lt.register_run(_make_run(total_kills=10))
        self.lt.register_run(_make_run(total_kills=20))
        avg = self.lt.average("total_kills")
        self.assertAlmostEqual(avg, 15.0)


class TestLifetimeRecords(TestLifetimeStatsBase):

    def test_records_update_on_new_high(self):
        self.lt.register_run(_make_run(level_reached=10))
        self.lt.register_run(_make_run(level_reached=5))
        self.assertEqual(self.lt.records["highest_level"], 10)

    def test_records_not_lowered(self):
        self.lt.register_run(_make_run(total_kills=50))
        self.lt.register_run(_make_run(total_kills=20))
        self.assertEqual(self.lt.records["most_kills_run"], 50)

    def test_longest_run_record(self):
        self.lt.register_run(_make_run(elapsed_s=300.0))
        self.lt.register_run(_make_run(elapsed_s=100.0))
        self.assertAlmostEqual(self.lt.records["longest_run_s"], 300.0)

    def test_boss_kill_record(self):
        self.lt.register_run(_make_run(boss_kills=3))
        self.assertEqual(self.lt.records["most_bosses_run"], 3)

    def test_storm_phase_record(self):
        self.lt.register_run(_make_run(storm_phase=4))
        self.lt.register_run(_make_run(storm_phase=2))
        self.assertEqual(self.lt.records["highest_storm_phase"], 4)


class TestLifetimeRankings(TestLifetimeStatsBase):

    def _populate(self, n=5):
        for i in range(n):
            self.lt.register_run(_make_run(
                elapsed_s=float(i*60),
                level_reached=i,
                total_kills=i*10,
            ))

    def test_ranking_returns_list(self):
        self._populate(3)
        result = self.lt.ranking("survival")
        self.assertIsInstance(result, list)

    def test_ranking_sorted_descending(self):
        self._populate(5)
        result = self.lt.ranking("survival")
        times  = [r["elapsed_s"] for r in result]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_ranking_respects_top_n(self):
        self._populate(TOP_N + 3)
        result = self.lt.ranking("level")
        self.assertLessEqual(len(result), TOP_N)

    def test_ranking_empty_when_no_runs(self):
        result = self.lt.ranking("kills")
        self.assertEqual(result, [])

    def test_all_rankings_keys(self):
        self._populate(3)
        all_r = self.lt.all_rankings()
        for k, _, _ in RANKING_KEYS:
            self.assertIn(k, all_r)

    def test_ranking_levels_correct(self):
        self._populate(5)
        result = self.lt.ranking("level")
        levels = [r["level_reached"] for r in result]
        self.assertEqual(levels, sorted(levels, reverse=True))

    def test_damage_ranking_sorted(self):
        for dmg in [100, 500, 300, 800, 200]:
            self.lt.register_run(_make_run(total_damage_dealt=dmg))
        result = self.lt.ranking("damage")
        vals   = [r["total_damage_dealt"] for r in result]
        self.assertEqual(vals, sorted(vals, reverse=True))


class TestLifetimeHelpers(TestLifetimeStatsBase):

    def test_total_playtime_str_format(self):
        self.lt.register_run(_make_run(elapsed_s=90.0))
        s = self.lt.total_playtime_str()
        self.assertIn(":", s)

    def test_run_summary_line(self):
        r = _make_run(elapsed_s=120, level_reached=5, total_kills=15, total_damage_dealt=800)
        line = LifetimeStats.run_summary_line(r)
        self.assertIsInstance(line, str)
        self.assertIn("Lv5", line)
        self.assertIn("15k", line)


class TestRankingKeyIntegrity(unittest.TestCase):

    def test_all_ranking_keys_have_three_fields(self):
        for item in RANKING_KEYS:
            self.assertEqual(len(item), 3, f"Bad entry: {item}")

    def test_ranking_keys_non_empty(self):
        self.assertGreater(len(RANKING_KEYS), 0)

    def test_ranking_labels_are_strings(self):
        for key, field, label in RANKING_KEYS:
            self.assertIsInstance(label, str)
            self.assertGreater(len(label), 0)


if __name__ == "__main__":
    unittest.main()
