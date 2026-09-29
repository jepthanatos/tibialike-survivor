"""Tests unitarios para systems/skills.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame

import unittest
from systems.skills import Skills, xp_for_level, ALL_SKILLS, SKILL_NAMES


class TestXpForLevel(unittest.TestCase):
    def test_level_1_positive(self):
        self.assertGreater(xp_for_level(1), 0)
    def test_higher_level_more_xp(self):
        self.assertGreater(xp_for_level(20), xp_for_level(10))
    def test_level_10_is_50_times_10_pow_1_6(self):
        import math
        expected = max(1, int(50 * (10 ** 1.6)))
        self.assertEqual(xp_for_level(10), expected)
    def test_returns_int(self):
        self.assertIsInstance(xp_for_level(5), int)


class TestSkillsInit(unittest.TestCase):
    def test_all_skills_present(self):
        sk = Skills()
        for s in ALL_SKILLS:
            self.assertIn(s, sk.levels)
            self.assertIn(s, sk.xp)

    def test_default_level_10(self):
        sk = Skills(vocation="paladin")
        # non-primary skills stay at 10 (paladin bonus: distance, shielding)
        self.assertEqual(sk.levels["sword"], 10)

    def test_knight_sword_bonus(self):
        sk = Skills(vocation="knight")
        self.assertGreater(sk.levels["sword"], 10)

    def test_sorcerer_magic_bonus(self):
        sk = Skills(vocation="sorcerer")
        self.assertGreater(sk.levels["magic"], 10)

    def test_druid_magic_bonus(self):
        sk = Skills(vocation="druid")
        self.assertGreater(sk.levels["magic"], 10)

    def test_paladin_distance_bonus(self):
        sk = Skills(vocation="paladin")
        self.assertGreater(sk.levels["distance"], 10)

    def test_unknown_vocation_no_crash(self):
        sk = Skills(vocation="wizard")
        self.assertEqual(sk.levels["sword"], 10)


class TestSkillsGain(unittest.TestCase):
    def _sk(self):
        return Skills(vocation="sorcerer")  # no sword bonus

    def test_gain_increases_xp(self):
        sk = self._sk()
        sk.gain("sword", 5.0)
        self.assertAlmostEqual(sk.xp["sword"], 5.0)

    def test_gain_levels_up_eventually(self):
        sk = self._sk()
        needed = xp_for_level(sk.levels["sword"])
        leveled = False
        for _ in range(needed + 5):
            if sk.gain("sword", 1.0):
                leveled = True; break
        self.assertTrue(leveled)

    def test_xp_carries_over_on_level_up(self):
        sk = self._sk()
        needed = xp_for_level(sk.levels["sword"])
        sk.gain("sword", needed + 3.0)
        self.assertAlmostEqual(sk.xp["sword"], 3.0, delta=1.0)

    def test_gain_unknown_skill_returns_false(self):
        sk = self._sk()
        result = sk.gain("unknown_skill")
        self.assertFalse(result)

    def test_gain_melee(self):
        sk = self._sk()
        sk.gain_melee("sword")
        self.assertGreater(sk.xp["sword"], 0)

    def test_gain_shielding_adds_double(self):
        sk = self._sk()
        sk.gain_shielding()
        self.assertAlmostEqual(sk.xp["shielding"], 2.0)

    def test_gain_distance(self):
        sk = self._sk()
        sk.gain_distance()
        self.assertGreater(sk.xp["distance"], 0)

    def test_gain_magic(self):
        sk = self._sk()
        sk.gain_magic()
        self.assertGreater(sk.xp["magic"], 0)


class TestSkillsBonuses(unittest.TestCase):
    def test_melee_bonus_zero_at_level_10(self):
        sk = Skills(vocation="sorcerer")
        self.assertEqual(sk.melee_bonus("sword"), 0)

    def test_melee_bonus_positive_above_10(self):
        sk = Skills(vocation="sorcerer")
        sk.levels["sword"] = 20
        self.assertGreater(sk.melee_bonus("sword"), 0)

    def test_distance_bonus_zero_at_level_10(self):
        sk = Skills(vocation="sorcerer")
        self.assertEqual(sk.distance_bonus(), 0)

    def test_magic_bonus_zero_at_base_level(self):
        # Use knight which has no magic bonus, so starts at exactly level 10
        sk = Skills(vocation="knight")
        self.assertEqual(sk.magic_bonus(), 0)

    def test_shielding_bonus_zero_at_level_10(self):
        sk = Skills()
        self.assertAlmostEqual(sk.shielding_bonus(), 0.0)

    def test_shielding_bonus_capped_at_30_percent(self):
        sk = Skills()
        sk.levels["shielding"] = 999
        self.assertLessEqual(sk.shielding_bonus(), 0.30)

    def test_bonuses_increase_with_level(self):
        sk = Skills(vocation="sorcerer")
        sk.levels["magic"] = 10; b10 = sk.magic_bonus()
        sk.levels["magic"] = 20; b20 = sk.magic_bonus()
        self.assertGreater(b20, b10)


class TestSkillsPrimarySkill(unittest.TestCase):
    def test_knight_primary_sword(self):
        sk = Skills(vocation="knight")
        self.assertEqual(sk.primary_skill(), "sword")

    def test_paladin_primary_distance(self):
        sk = Skills(vocation="paladin")
        self.assertEqual(sk.primary_skill(), "distance")

    def test_sorcerer_primary_magic(self):
        sk = Skills(vocation="sorcerer")
        self.assertEqual(sk.primary_skill(), "magic")

    def test_druid_primary_magic(self):
        sk = Skills(vocation="druid")
        self.assertEqual(sk.primary_skill(), "magic")

    def test_unknown_defaults_to_sword(self):
        sk = Skills(vocation="unknown")
        self.assertEqual(sk.primary_skill(), "sword")


class TestSkillsProgress(unittest.TestCase):
    def test_progress_zero_at_start(self):
        sk = Skills(vocation="sorcerer")
        self.assertAlmostEqual(sk.progress("sword"), 0.0)

    def test_progress_increases_with_xp(self):
        sk = Skills(vocation="sorcerer")
        sk.gain("sword", 10.0)
        self.assertGreater(sk.progress("sword"), 0.0)

    def test_progress_caps_at_1(self):
        sk = Skills(vocation="sorcerer")
        sk.xp["sword"] = xp_for_level(sk.levels["sword"]) * 2
        self.assertLessEqual(sk.progress("sword"), 1.0)

    def test_progress_unknown_skill(self):
        sk = Skills()
        self.assertAlmostEqual(sk.progress("nonexistent"), 0.0)


class TestSkillsSerialization(unittest.TestCase):
    def test_to_dict_has_required_keys(self):
        sk = Skills(vocation="knight")
        d = sk.to_dict()
        self.assertIn("vocation", d)
        self.assertIn("levels", d)
        self.assertIn("xp", d)

    def test_from_dict_restores_levels(self):
        sk = Skills(vocation="knight")
        sk.levels["sword"] = 25
        sk2 = Skills.from_dict(sk.to_dict())
        self.assertEqual(sk2.levels["sword"], 25)

    def test_from_dict_restores_vocation(self):
        sk = Skills(vocation="druid")
        sk2 = Skills.from_dict(sk.to_dict())
        self.assertEqual(sk2.vocation, "druid")

    def test_from_dict_restores_xp(self):
        sk = Skills()
        sk.xp["magic"] = 42.5
        sk2 = Skills.from_dict(sk.to_dict())
        self.assertAlmostEqual(sk2.xp["magic"], 42.5, places=1)

    def test_from_empty_dict_no_crash(self):
        sk = Skills.from_dict({})
        self.assertIsInstance(sk, Skills)

    def test_repr_contains_vocation(self):
        sk = Skills(vocation="paladin")
        r = repr(sk)
        self.assertIn("paladin", r)


class TestSkillsAllSkillNames(unittest.TestCase):
    def test_all_skills_have_names(self):
        for s in ALL_SKILLS:
            self.assertIn(s, SKILL_NAMES)

    def test_names_are_strings(self):
        for s, name in SKILL_NAMES.items():
            self.assertIsInstance(name, str)
            self.assertGreater(len(name), 0)


if __name__ == "__main__":
    unittest.main()
