"""Tests unitarios para entities/monster.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame  # instala pygame falso PRIMERO

import unittest
from entities.monster import Monster, MONSTER_DATA, available_types


def make_monster(mtype='rat', level=0, x=200.0, y=200.0):
    return Monster(x, y, mtype, level)


class TestMonsterInitRat(unittest.TestCase):

    def setUp(self):
        self.m = make_monster('rat', level=0)
        self.d = MONSTER_DATA['rat']

    def test_name(self):
        self.assertEqual(self.m.name, 'Rat')

    def test_hp_formula(self):
        expected = self.d['base_hp'] + self.d['hp_lv'] * 0
        self.assertAlmostEqual(self.m.max_hp, expected)

    def test_hp_starts_full(self):
        self.assertAlmostEqual(self.m.hp, self.m.max_hp)

    def test_damage_formula(self):
        expected = self.d['base_dmg'] + self.d['dmg_lv'] * 0
        self.assertEqual(self.m.damage, expected)

    def test_xp_reward_formula(self):
        expected = self.d['xp_base'] + self.d['xp_lv'] * 0
        self.assertEqual(self.m.xp_reward, expected)

    def test_speed(self):
        self.assertAlmostEqual(self.m.speed, self.d['speed'])


class TestMonsterInitZombie(unittest.TestCase):

    def setUp(self):
        self.m = make_monster('zombie', level=5)
        self.d = MONSTER_DATA['zombie']

    def test_hp_scales_with_level(self):
        expected = self.d['base_hp'] + self.d['hp_lv'] * 5
        self.assertAlmostEqual(self.m.max_hp, expected)

    def test_xp_scales_with_level(self):
        expected = self.d['xp_base'] + self.d['xp_lv'] * 5
        self.assertEqual(self.m.xp_reward, expected)


class TestMonsterInitSkeleton(unittest.TestCase):

    def test_skeleton_min_level_in_data(self):
        self.assertEqual(MONSTER_DATA['skeleton']['min_level'], 7)

    def test_skeleton_damage_scales(self):
        d = MONSTER_DATA['skeleton']
        m = make_monster('skeleton', level=10)
        expected = d['base_dmg'] + d['dmg_lv'] * 10
        self.assertEqual(m.damage, expected)


class TestMonsterDamage(unittest.TestCase):

    def test_take_damage_reduces_hp(self):
        m = make_monster('rat', 0)
        initial = m.hp
        m.take_damage(5)
        self.assertLess(m.hp, initial)

    def test_take_damage_clamps_to_zero(self):
        m = make_monster('rat', 0)
        m.take_damage(9999)
        self.assertEqual(m.hp, 0.0)

    def test_take_damage_activates_hit_flash(self):
        m = make_monster('rat', 0)
        m.take_damage(1)
        self.assertGreater(m._hit_flash, 0)

    def test_take_damage_returns_amount(self):
        m = make_monster('rat', 0)
        result = m.take_damage(8)
        self.assertEqual(result, 8)


class TestMonsterIsDead(unittest.TestCase):

    def test_not_dead_initially(self):
        m = make_monster('rat', 0)
        self.assertFalse(m.is_dead())

    def test_dead_when_hp_zero(self):
        m = make_monster('rat', 0)
        m.hp = 0.0
        self.assertTrue(m.is_dead())

    def test_dead_after_lethal_damage(self):
        m = make_monster('zombie', 0)
        m.take_damage(9999)
        self.assertTrue(m.is_dead())


class TestAvailableTypes(unittest.TestCase):

    def test_level_0_returns_only_rat(self):
        types = available_types(0)
        self.assertIn('rat', types)
        self.assertNotIn('zombie', types)
        self.assertNotIn('skeleton', types)

    def test_level_3_includes_zombie(self):
        types = available_types(3)
        self.assertIn('rat', types)
        self.assertIn('zombie', types)
        self.assertNotIn('skeleton', types)

    def test_level_7_includes_all(self):
        types = available_types(7)
        self.assertIn('rat', types)
        self.assertIn('zombie', types)
        self.assertIn('skeleton', types)

    def test_level_2_excludes_zombie(self):
        types = available_types(2)
        self.assertNotIn('zombie', types)

    def test_returns_at_least_one_type_always(self):
        types = available_types(-99)   # nivel imposible
        self.assertGreater(len(types), 0)

    def test_returns_list_not_empty_for_high_level(self):
        types = available_types(100)
        self.assertGreaterEqual(len(types), 3)


class TestMonsterXpScaling(unittest.TestCase):

    def test_higher_level_more_xp(self):
        m0 = make_monster('rat', 0)
        m5 = make_monster('rat', 5)
        self.assertGreater(m5.xp_reward, m0.xp_reward)

    def test_skeleton_more_xp_than_rat_same_level(self):
        rat = make_monster('rat', 0)
        ske = make_monster('skeleton', 0)
        self.assertGreater(ske.xp_reward, rat.xp_reward)


if __name__ == '__main__':
    unittest.main()
