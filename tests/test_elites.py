"""Tests unitarios para systems/elites.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame

import unittest
from systems.elites import (
    MODIFIERS, MODIFIER_KEYS, ELITE_CHANCE,
    roll_elite, roll_boss_mods, apply_modifiers, elite_badge_color,
)
from entities.monster import Monster


def _mon(mtype='rat', level=0):
    return Monster(200.0, 200.0, mtype, level)


class TestModifierCatalogue(unittest.TestCase):

    REQUIRED = ("name","color","hp_mult","dmg_mult","spd_mult","xp_mult","regen_ps","desc")

    def test_all_modifiers_have_required_keys(self):
        for mid, data in MODIFIERS.items():
            for k in self.REQUIRED:
                self.assertIn(k, data, f"Modifier '{mid}' missing '{k}'")

    def test_hp_mult_positive(self):
        for mid, d in MODIFIERS.items():
            self.assertGreater(d["hp_mult"], 0, mid)

    def test_dmg_mult_positive(self):
        for mid, d in MODIFIERS.items():
            self.assertGreater(d["dmg_mult"], 0, mid)

    def test_spd_mult_positive(self):
        for mid, d in MODIFIERS.items():
            self.assertGreater(d["spd_mult"], 0, mid)

    def test_xp_mult_at_least_one(self):
        for mid, d in MODIFIERS.items():
            self.assertGreaterEqual(d["xp_mult"], 1.0, mid)

    def test_regen_ps_non_negative(self):
        for mid, d in MODIFIERS.items():
            self.assertGreaterEqual(d["regen_ps"], 0.0, mid)

    def test_color_is_valid_rgb(self):
        for mid, d in MODIFIERS.items():
            col = d["color"]
            self.assertEqual(len(col), 3)
            for c in col:
                self.assertGreaterEqual(c, 0)
                self.assertLessEqual(c, 255)

    def test_modifier_keys_list_matches_dict(self):
        self.assertEqual(set(MODIFIER_KEYS), set(MODIFIERS.keys()))


class TestRollElite(unittest.TestCase):

    def test_returns_list(self):
        result = roll_elite()
        self.assertIsInstance(result, list)

    def test_all_ids_in_catalogue(self):
        for _ in range(50):
            mods = roll_elite()
            for mid in mods:
                self.assertIn(mid, MODIFIERS)

    def test_max_2_mods(self):
        for _ in range(100):
            mods = roll_elite()
            self.assertLessEqual(len(mods), 2)

    def test_no_duplicates_in_result(self):
        for _ in range(100):
            mods = roll_elite()
            self.assertEqual(len(mods), len(set(mods)))

    def test_sometimes_returns_empty(self):
        """With ELITE_CHANCE < 1, some rolls should be empty."""
        results = [roll_elite() for _ in range(200)]
        empties = sum(1 for r in results if len(r) == 0)
        self.assertGreater(empties, 0)

    def test_sometimes_returns_non_empty(self):
        results = [roll_elite() for _ in range(200)]
        non_empty = sum(1 for r in results if len(r) > 0)
        self.assertGreater(non_empty, 0)


class TestRollBossMods(unittest.TestCase):

    def test_returns_2_to_3_mods(self):
        for _ in range(30):
            mods = roll_boss_mods()
            self.assertGreaterEqual(len(mods), 2)
            self.assertLessEqual(len(mods), 3)

    def test_all_ids_in_catalogue(self):
        for _ in range(30):
            for mid in roll_boss_mods():
                self.assertIn(mid, MODIFIERS)

    def test_no_duplicates(self):
        for _ in range(30):
            mods = roll_boss_mods()
            self.assertEqual(len(mods), len(set(mods)))


class TestApplyModifiers(unittest.TestCase):

    def test_empty_mods_sets_is_elite_false(self):
        m = _mon('rat', 0)
        apply_modifiers(m, [])
        self.assertFalse(m.is_elite)

    def test_non_empty_mods_sets_is_elite_true(self):
        m = _mon('rat', 0)
        apply_modifiers(m, ['berserker'])
        self.assertTrue(m.is_elite)

    def test_mods_stored_on_monster(self):
        m = _mon('rat', 0)
        apply_modifiers(m, ['swift', 'armored'])
        self.assertIn('swift', m.elite_mods)
        self.assertIn('armored', m.elite_mods)

    def test_hp_increases_with_armored(self):
        m = _mon('rat', 0)
        base_hp = m.max_hp
        apply_modifiers(m, ['armored'])
        self.assertGreater(m.max_hp, base_hp)

    def test_speed_increases_with_swift(self):
        m = _mon('rat', 0)
        base_speed = m.speed
        apply_modifiers(m, ['swift'])
        self.assertGreater(m.speed, base_speed)

    def test_speed_decreases_with_armored(self):
        m = _mon('rat', 0)
        base_speed = m.speed
        apply_modifiers(m, ['armored'])
        self.assertLess(m.speed, base_speed)

    def test_xp_reward_increases_with_elite(self):
        m = _mon('rat', 0)
        base_xp = m.xp_reward
        apply_modifiers(m, ['berserker'])
        self.assertGreater(m.xp_reward, base_xp)

    def test_hp_equals_max_hp_after_apply(self):
        m = _mon('rat', 0)
        apply_modifiers(m, ['armored'])
        self.assertAlmostEqual(m.hp, float(m.max_hp))

    def test_regen_set_for_regenerating(self):
        m = _mon('rat', 0)
        apply_modifiers(m, ['regenerating'])
        self.assertGreater(m.elite_regen, 0.0)

    def test_regen_zero_for_non_regen_modifier(self):
        m = _mon('rat', 0)
        apply_modifiers(m, ['berserker'])
        self.assertEqual(m.elite_regen, 0.0)

    def test_giant_increases_size(self):
        m = _mon('rat', 0)
        base_size = m.SIZE
        apply_modifiers(m, ['giant'])
        self.assertGreater(m.SIZE, base_size)

    def test_multiple_mods_stack_hp(self):
        m1 = _mon('rat', 0)
        m2 = _mon('rat', 0)
        apply_modifiers(m1, ['armored'])
        apply_modifiers(m2, ['armored', 'regenerating'])
        self.assertGreater(m2.max_hp, m1.max_hp)

    def test_damage_increases_with_berserker(self):
        m = _mon('rat', 0)
        base_dmg = m.damage
        apply_modifiers(m, ['berserker'])
        self.assertGreater(m.damage, base_dmg)

    def test_max_hp_at_least_one(self):
        m = _mon('rat', 0)
        apply_modifiers(m, ['swift'])   # swift reduces nothing below 1
        self.assertGreaterEqual(m.max_hp, 1)

    def test_damage_at_least_one(self):
        m = _mon('rat', 0)
        apply_modifiers(m, ['swift'])
        self.assertGreaterEqual(m.damage, 1)


class TestEliteBadgeColor(unittest.TestCase):

    def test_empty_mods_returns_gray(self):
        col = elite_badge_color([])
        self.assertIsInstance(col, tuple)
        self.assertEqual(len(col), 3)

    def test_returns_first_mod_color(self):
        col = elite_badge_color(['berserker'])
        self.assertEqual(col, MODIFIERS['berserker']['color'])

    def test_with_multiple_mods_returns_first(self):
        col = elite_badge_color(['swift', 'armored'])
        self.assertEqual(col, MODIFIERS['swift']['color'])


class TestNewMonsterTypes(unittest.TestCase):
    """Verify the 3 new Phase 5 monster types init correctly."""

    def test_orc_initialises(self):
        m = Monster(100.0, 100.0, 'orc', level=10)
        self.assertEqual(m.name, 'Orc')
        self.assertGreater(m.max_hp, 0)

    def test_dark_wizard_initialises(self):
        m = Monster(100.0, 100.0, 'dark_wizard', level=15)
        self.assertEqual(m.name, 'Dark Wizard')
        self.assertGreater(m.xp_reward, 0)

    def test_dragon_initialises(self):
        m = Monster(100.0, 100.0, 'dragon', level=20)
        self.assertEqual(m.name, 'Dragon')
        self.assertGreater(m.SIZE, 0)

    def test_orc_min_level_10(self):
        from entities.monster import MONSTER_DATA
        self.assertEqual(MONSTER_DATA['orc']['min_level'], 10)

    def test_dark_wizard_min_level_15(self):
        from entities.monster import MONSTER_DATA
        self.assertEqual(MONSTER_DATA['dark_wizard']['min_level'], 15)

    def test_dragon_min_level_20(self):
        from entities.monster import MONSTER_DATA
        self.assertEqual(MONSTER_DATA['dragon']['min_level'], 20)

    def test_available_types_at_level_0_excludes_new(self):
        from entities.monster import available_types
        types = available_types(0)
        self.assertNotIn('orc', types)
        self.assertNotIn('dark_wizard', types)
        self.assertNotIn('dragon', types)

    def test_available_types_at_level_20_includes_all(self):
        from entities.monster import available_types
        types = available_types(20)
        for t in ('rat','zombie','skeleton','orc','dark_wizard','dragon'):
            self.assertIn(t, types)

    def test_orc_has_higher_hp_than_skeleton_same_level(self):
        orc = Monster(0,0,'orc',10)
        ske = Monster(0,0,'skeleton',10)
        self.assertGreater(orc.max_hp, ske.max_hp)

    def test_dragon_has_high_xp(self):
        from entities.monster import MONSTER_DATA
        xps = {k: v['xp_base'] for k, v in MONSTER_DATA.items()}
        # Dragon should have higher xp than skeletons/zombies/rats
        self.assertGreater(xps['dragon'], xps['skeleton'])
        self.assertGreater(xps['dragon'], xps['zombie'])

    def test_dark_wizard_has_spells(self):
        m = Monster(0,0,'dark_wizard',15)
        self.assertGreater(len(m._my_spells), 0)

    def test_dragon_has_spells(self):
        m = Monster(0,0,'dragon',20)
        self.assertGreater(len(m._my_spells), 0)

    def test_elite_can_be_applied_to_new_types(self):
        for mtype in ('orc','dark_wizard','dragon'):
            m = Monster(0,0,mtype,10)
            apply_modifiers(m, ['berserker'])
            self.assertTrue(m.is_elite)


if __name__ == '__main__':
    unittest.main()
