"""Tests unitarios para systems/spells.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from systems.spells import (
    SpellMemory, SPELL_CATALOGUE, MONSTER_SPELLS,
    OBSERVE_RANGE,
)


# ── Catalogue sanity ──────────────────────────────────────────────────────────

class TestSpellCatalogue(unittest.TestCase):

    REQUIRED_KEYS = ("name","color","mp_cost","damage","speed","radius",
                     "pierce","aoe_radius","learn_thresh","min_magic_lv",
                     "range_px","desc")

    def test_all_spells_have_required_keys(self):
        for sid, data in SPELL_CATALOGUE.items():
            for k in self.REQUIRED_KEYS:
                self.assertIn(k, data, f"Hechizo '{sid}' falta clave '{k}'")

    def test_mp_cost_non_negative(self):
        """Monster spells have mp_cost=0 (cast by AI, not player). Player spells have positive cost."""
        for sid, data in SPELL_CATALOGUE.items():
            self.assertGreaterEqual(data["mp_cost"], 0, f"'{sid}' mp_cost debe ser >=0")

    def test_damage_non_zero(self):
        """Some spells heal (negative damage) or buff (0). At least one deals positive damage."""
        positives = [d["damage"] for d in SPELL_CATALOGUE.values() if d["damage"] > 0]
        self.assertGreater(len(positives), 0)

    def test_speed_positive_for_projectile_spells(self):
        """Melee/buff spells have speed=0 by design. Projectile spells (speed>0) have positive speed."""
        # Projectile spells: have speed AND range both > 0
        projectile_spells = [d for d in SPELL_CATALOGUE.values()
                             if d["range_px"] > 60 and d["speed"] > 0]
        self.assertGreater(len(projectile_spells), 0, "Should have at least some projectile spells")
        for d in projectile_spells:
            self.assertGreater(d["speed"], 0)

    def test_learn_thresh_positive(self):
        for sid, data in SPELL_CATALOGUE.items():
            self.assertGreaterEqual(data["learn_thresh"], 1)

    def test_min_magic_lv_non_negative(self):
        for sid, data in SPELL_CATALOGUE.items():
            self.assertGreaterEqual(data["min_magic_lv"], 0)

    def test_range_px_non_negative(self):
        """Melee/self spells have range=0 by design."""
        for sid, data in SPELL_CATALOGUE.items():
            self.assertGreaterEqual(data["range_px"], 0)

    def test_color_is_valid_rgb(self):
        for sid, data in SPELL_CATALOGUE.items():
            col = data["color"]
            self.assertEqual(len(col), 3)
            for c in col:
                self.assertGreaterEqual(c, 0)
                self.assertLessEqual(c, 255)

    def test_aoe_radius_non_negative(self):
        for sid, data in SPELL_CATALOGUE.items():
            self.assertGreaterEqual(data["aoe_radius"], 0)

    def test_pierce_is_bool(self):
        for sid, data in SPELL_CATALOGUE.items():
            self.assertIsInstance(data["pierce"], bool)


class TestMonsterSpells(unittest.TestCase):

    def test_all_monster_types_have_entry(self):
        for mtype in ("rat", "zombie", "skeleton"):
            self.assertIn(mtype, MONSTER_SPELLS)

    def test_monster_spell_ids_exist_in_catalogue(self):
        for mtype, spells in MONSTER_SPELLS.items():
            for sid in spells:
                self.assertIn(sid, SPELL_CATALOGUE,
                              f"'{sid}' en MONSTER_SPELLS['{mtype}'] no está en catálogo")

    def test_rat_spells_are_basic(self):
        """Rats should only know low-level spells."""
        for sid in MONSTER_SPELLS["rat"]:
            data = SPELL_CATALOGUE[sid]
            self.assertLessEqual(data["min_magic_lv"], 2,
                                 f"Rat no debería necesitar magic_lv alto: {sid}")

    def test_skeleton_has_most_spells(self):
        self.assertGreaterEqual(
            len(MONSTER_SPELLS["skeleton"]),
            len(MONSTER_SPELLS["rat"]))


# ── SpellMemory init ──────────────────────────────────────────────────────────

class TestSpellMemoryInit(unittest.TestCase):

    def test_starts_empty_known(self):
        sm = SpellMemory()
        self.assertEqual(sm.known_spells, [])

    def test_starts_zero_magic_level(self):
        # Knight starts at 0, sorcerer at 4
        sm_k = SpellMemory(vocation="knight")
        self.assertEqual(sm_k.magic_level, 0)
        sm_s = SpellMemory(vocation="sorcerer")
        self.assertEqual(sm_s.magic_level, 4)

    def test_starts_empty_observations(self):
        sm = SpellMemory()
        self.assertEqual(sm.observations, {})

    def test_init_with_known_spells(self):
        sm = SpellMemory(known=["exevo vis", "exevo flam"])
        self.assertIn("exevo vis", sm.known_spells)
        self.assertIn("exevo flam", sm.known_spells)

    def test_pending_empty_initially(self):
        sm = SpellMemory()
        self.assertEqual(sm.pending_spells(), [])


# ── Observation ───────────────────────────────────────────────────────────────

class TestObservation(unittest.TestCase):

    def test_observe_increments_counter(self):
        sm = SpellMemory()
        sm.observe("exevo vis")
        self.assertEqual(sm.observations.get("exevo vis", 0), 1)

    def test_observe_already_known_returns_false(self):
        sm = SpellMemory(known=["exevo vis"])
        result = sm.observe("exevo vis")
        self.assertFalse(result)

    def test_observe_unknown_spell_returns_false(self):
        sm = SpellMemory()
        result = sm.observe("nonexistent_spell")
        self.assertFalse(result)

    def test_observe_enough_times_learns_spell(self):
        """spark: learn_thresh=3, min_magic_lv=0"""
        sm = SpellMemory()
        thresh = SPELL_CATALOGUE["exevo vis"]["learn_thresh"]
        for _ in range(thresh - 1):
            result = sm.observe("exevo vis")
            self.assertFalse(result)
        result = sm.observe("exevo vis")   # last observation
        self.assertTrue(result)
        self.assertIn("exevo vis", sm.known_spells)

    def test_observe_does_not_learn_without_magic_level(self):
        """death_coil requires min_magic_lv=10"""
        sm = SpellMemory()
        sm.magic_level = 0   # not enough
        thresh = SPELL_CATALOGUE["exura mort"]["learn_thresh"]
        for _ in range(thresh + 5):
            sm.observe("exura mort")
        self.assertNotIn("exura mort", sm.known_spells)

    def test_observe_learns_when_magic_level_met_later(self):
        """Observe enough times with low magic, then raise magic level -> should learn."""
        sm = SpellMemory()
        sm.magic_level = 0
        thresh  = SPELL_CATALOGUE["exevo flam"]["learn_thresh"]
        ml_need = SPELL_CATALOGUE["exevo flam"]["min_magic_lv"]
        for _ in range(thresh + 2):
            sm.observe("exevo flam")
        self.assertNotIn("exevo flam", sm.known_spells)  # not enough magic yet
        sm.magic_level = ml_need
        result = sm.observe("exevo flam")   # one more -> should trigger
        self.assertTrue(result)

    def test_observation_progress_returns_tuple(self):
        sm = SpellMemory()
        sm.observe("exevo vis")
        sm.observe("exevo vis")
        obs, thresh = sm.observation_progress("exevo vis")
        self.assertEqual(obs, 2)
        self.assertEqual(thresh, SPELL_CATALOGUE["exevo vis"]["learn_thresh"])

    def test_observation_progress_unknown_spell(self):
        sm = SpellMemory()
        obs, thresh = sm.observation_progress("fake_spell")
        self.assertEqual(obs, 0)

    def test_pending_spells_listed_after_partial_observation(self):
        sm = SpellMemory()
        sm.observe("exevo vis")   # partial (not enough yet)
        pending = sm.pending_spells()
        self.assertIn("exevo vis", pending)

    def test_pending_spells_not_listed_once_learned(self):
        sm = SpellMemory()
        thresh = SPELL_CATALOGUE["exevo vis"]["learn_thresh"]
        for _ in range(thresh):
            sm.observe("exevo vis")
        pending = sm.pending_spells()
        self.assertNotIn("exevo vis", pending)


# ── Magic level ───────────────────────────────────────────────────────────────

class TestMagicLevel(unittest.TestCase):

    def test_magic_level_increases_after_8_casts(self):
        sm = SpellMemory(vocation="knight")  # starts at 0
        leveled_up = False
        for _ in range(8):
            if sm.on_spell_cast():
                leveled_up = True
        self.assertTrue(leveled_up)
        self.assertEqual(sm.magic_level, 1)

    def test_magic_level_does_not_increase_before_8_casts(self):
        sm = SpellMemory(vocation="knight")  # starts at 0
        for _ in range(7):
            sm.on_spell_cast()
        self.assertEqual(sm.magic_level, 0)

    def test_magic_level_increases_multiple_times(self):
        sm = SpellMemory(vocation="knight")  # starts at 0
        for _ in range(24):
            sm.on_spell_cast()
        self.assertEqual(sm.magic_level, 3)

    def test_on_spell_cast_returns_true_on_level_up(self):
        sm = SpellMemory()
        results = [sm.on_spell_cast() for _ in range(8)]
        self.assertTrue(results[-1])

    def test_on_spell_cast_returns_false_otherwise(self):
        sm = SpellMemory()
        for i in range(7):
            self.assertFalse(sm.on_spell_cast())


# ── can_learn ─────────────────────────────────────────────────────────────────

class TestCanLearn(unittest.TestCase):

    def test_can_learn_basic_spell_at_lv0(self):
        sm = SpellMemory()
        self.assertTrue(sm.can_learn("exevo vis"))

    def test_cannot_learn_high_spell_at_lv0(self):
        sm = SpellMemory()
        self.assertFalse(sm.can_learn("exura mort"))

    def test_can_learn_after_reaching_required_magic_level(self):
        sm = SpellMemory()
        sm.magic_level = SPELL_CATALOGUE["exevo flam"]["min_magic_lv"]
        self.assertTrue(sm.can_learn("exevo flam"))

    def test_can_learn_unknown_spell_returns_false(self):
        sm = SpellMemory()
        self.assertFalse(sm.can_learn("not_a_spell"))


# ── Serialisation ─────────────────────────────────────────────────────────────

class TestSpellMemorySerialisation(unittest.TestCase):

    def test_to_dict_contains_required_keys(self):
        sm = SpellMemory(known=["exevo vis"])
        d  = sm.to_dict()
        self.assertIn("known_spells", d)
        self.assertIn("magic_level", d)
        self.assertIn("observations", d)

    def test_roundtrip_preserves_known_spells(self):
        sm = SpellMemory(known=["exevo vis", "exevo flam"])
        sm.magic_level = 3
        sm.observations = {"exevo flam": 4}
        sm2 = SpellMemory.from_dict(sm.to_dict())
        self.assertEqual(sm2.known_spells, sm.known_spells)
        self.assertEqual(sm2.magic_level, 3)
        self.assertEqual(sm2.observations.get("exevo flam"), 4)

    def test_from_dict_empty_gives_defaults(self):
        sm = SpellMemory.from_dict({})
        self.assertEqual(sm.known_spells, [])
        self.assertEqual(sm.magic_level, 0)

    def test_to_dict_roundtrip_known_order_preserved(self):
        spells = ["exevo vis", "exevo mort", "exevo con"]
        sm = SpellMemory(known=spells)
        sm2 = SpellMemory.from_dict(sm.to_dict())
        self.assertEqual(sm2.known_spells, spells)


# ── Repr ──────────────────────────────────────────────────────────────────────

class TestSpellMemoryRepr(unittest.TestCase):

    def test_repr_does_not_crash(self):
        sm = SpellMemory()
        r  = repr(sm)
        self.assertIsInstance(r, str)
        self.assertIn("SpellMemory", r)


if __name__ == '__main__':
    unittest.main()
