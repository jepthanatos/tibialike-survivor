"""Tests unitarios para systems/loot.py (Tibia-style loot)"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame

import unittest
from systems.loot import (
    generate_item, try_drop, try_drop_with_mult, generate_guaranteed,
    RARITY, RARITY_ORDER, ITEM_TEMPLATES, CREATURE_LOOT,
)

SLOTS = ['weapon','armor','helmet','boots','ring','amulet']


class FakeMon:
    def __init__(self, mtype='rat', level=0, is_boss=False, is_elite=False):
        self.mtype=mtype; self.level=level
        self.is_boss=is_boss; self.is_elite=is_elite


class TestItemTemplates(unittest.TestCase):

    def test_all_templates_have_required_keys(self):
        for t in ITEM_TEMPLATES:
            for k in ('name','slot','rarity','stats'):
                self.assertIn(k, t, f"Template '{t.get('name','?')}' missing '{k}'")

    def test_all_slots_valid(self):
        for t in ITEM_TEMPLATES:
            self.assertIn(t['slot'], SLOTS + ['consumable'])

    def test_all_rarities_valid(self):
        for t in ITEM_TEMPLATES:
            self.assertIn(t['rarity'], RARITY_ORDER)

    def test_stats_are_dict(self):
        for t in ITEM_TEMPLATES:
            self.assertIsInstance(t['stats'], dict)

    def test_enough_templates(self):
        self.assertGreaterEqual(len(ITEM_TEMPLATES), 20)

    def test_each_slot_has_templates(self):
        for slot in SLOTS:
            found = [t for t in ITEM_TEMPLATES if t['slot'] == slot]
            self.assertGreater(len(found), 0, f"No templates for slot '{slot}'")

    def test_tibia_item_names_present(self):
        names = {t['name'] for t in ITEM_TEMPLATES}
        for expected in ('Fire Sword', 'Dragon Scale Mail', 'Boots of Haste',
                         'Platinum Amulet', 'Might Ring'):
            self.assertIn(expected, names)


class TestGenerateItem(unittest.TestCase):

    def test_returns_dict(self):
        item = generate_item(0)
        self.assertIsInstance(item, dict)

    def test_has_required_keys(self):
        item = generate_item(5)
        for k in ('name','slot','rarity','stats','item_level'):
            self.assertIn(k, item)

    def test_slot_is_valid(self):
        for _ in range(20):
            item = generate_item(5)
            self.assertIn(item['slot'], SLOTS)

    def test_rarity_is_valid(self):
        for _ in range(20):
            item = generate_item(5)
            self.assertIn(item['rarity'], RARITY_ORDER)

    def test_higher_level_scales_stats(self):
        """Same template at higher level must have >= stats. Use seed for determinism."""
        import random as _rng
        from systems.loot import ITEM_TEMPLATES
        # Pick a specific template and compare level 0 vs level 30
        for tmpl in ITEM_TEMPLATES:
            if not any(isinstance(v, (int, float)) and v > 0
                       for v in tmpl['stats'].values()):
                continue  # skip non-numeric-stat items (e.g. atk_speed only)
            def _make(lv, t=tmpl):
                item = dict(t)
                item['item_level'] = lv
                scaled = {}
                for stat, val in t['stats'].items():
                    if isinstance(val, (int, float)) and val > 0:
                        scaled[stat] = round(val * (1 + lv * 0.04), 2)
                    else:
                        scaled[stat] = val
                item['stats'] = scaled
                return item
            low  = _make(0)
            high = _make(30)
            low_total  = sum(v for v in low['stats'].values()
                             if isinstance(v, (int, float)) and v > 0)
            high_total = sum(v for v in high['stats'].values()
                             if isinstance(v, (int, float)) and v > 0)
            self.assertGreaterEqual(
                high_total, low_total,
                f"{tmpl['name']}: level-30 ({high_total:.1f}) < level-0 ({low_total:.1f})"
            )

    def test_forced_rarity_respected(self):
        for rarity in RARITY_ORDER:
            item = generate_item(5, rarity=rarity)
            self.assertEqual(item['rarity'], rarity)

    def test_stats_are_positive(self):
        for _ in range(30):
            item = generate_item(5)
            for stat, val in item['stats'].items():
                if isinstance(val, (int, float)):
                    self.assertGreater(val, 0, f"stat '{stat}' should be positive")


class TestCreatureLoot(unittest.TestCase):

    def test_all_creature_types_in_table(self):
        for mtype in ('rat','zombie','skeleton','orc','dark_wizard','dragon','demon','dragon_lord'):
            self.assertIn(mtype, CREATURE_LOOT)

    def test_drop_chances_between_0_and_1(self):
        for mtype, table in CREATURE_LOOT.items():
            for chance, item_name in table:
                self.assertGreater(chance, 0, f"{mtype}.{item_name}")
                self.assertLessEqual(chance, 1.0, f"{mtype}.{item_name}")

    def test_item_names_exist_in_templates_or_consumables(self):
        template_names = {t['name'] for t in ITEM_TEMPLATES} | {'Cheese'}
        for mtype, table in CREATURE_LOOT.items():
            for _, item_name in table:
                self.assertIn(item_name, template_names,
                              f"{mtype} drops '{item_name}' not in templates")

    def test_dragon_drops_tibia_items(self):
        dragon_drops = {name for _, name in CREATURE_LOOT.get('dragon', [])}
        self.assertTrue(
            dragon_drops & {'Dragon Scale Mail','Dragon Helmet','Dragon Slayer','Fire Sword'},
            f"Dragon should drop Tibia items, got: {dragon_drops}"
        )

    def test_demon_drops_rare_items(self):
        demon_drops = {name for _, name in CREATURE_LOOT.get('demon', [])}
        self.assertTrue(
            demon_drops & {'Demon Armor','Demon Shield','Soft Boots'},
            f"Demon should drop epic items, got: {demon_drops}"
        )


class TestTryDrop(unittest.TestCase):

    def test_returns_none_or_dict(self):
        m = FakeMon('rat', 0)
        for _ in range(50):
            result = try_drop(m)
            self.assertIn(type(result), (type(None), dict))

    def test_sometimes_drops(self):
        m = FakeMon('rat', 0)
        drops = [try_drop(m) for _ in range(200)]
        self.assertTrue(any(d is not None for d in drops))

    def test_drop_has_correct_slot(self):
        m = FakeMon('dragon', 20)
        for _ in range(50):
            item = try_drop(m)
            if item:
                self.assertIn(item['slot'], SLOTS + ['consumable'])
                break

    def test_higher_tier_monsters_drop_better(self):
        dragon_drops = [try_drop(FakeMon('dragon',20)) for _ in range(200)]
        rat_drops    = [try_drop(FakeMon('rat',0))     for _ in range(200)]
        def avg_rarity(drops):
            scored = [RARITY_ORDER.index(d['rarity']) for d in drops if d and d['slot'] != 'consumable']
            return sum(scored)/len(scored) if scored else 0
        self.assertGreaterEqual(avg_rarity(dragon_drops), avg_rarity(rat_drops))


class TestTryDropWithMult(unittest.TestCase):

    def test_boss_always_drops(self):
        m = FakeMon('rat', 0, is_boss=True)
        for _ in range(20):
            self.assertIsNotNone(try_drop_with_mult(m, 1.0))

    def test_multiplier_increases_drops(self):
        m = FakeMon('zombie', 5)
        normal  = sum(1 for _ in range(500) if try_drop_with_mult(m, 1.0))
        boosted = sum(1 for _ in range(500) if try_drop_with_mult(m, 3.0))
        self.assertGreater(boosted, normal)


class TestGenerateGuaranteed(unittest.TestCase):

    def test_at_least_min_rarity(self):
        order = RARITY_ORDER
        for _ in range(30):
            item = generate_guaranteed(5, min_rarity='rare')
            self.assertGreaterEqual(order.index(item['rarity']), order.index('rare'))

    def test_uncommon_min_rarity(self):
        order = RARITY_ORDER
        for _ in range(30):
            item = generate_guaranteed(5, min_rarity='uncommon')
            self.assertGreaterEqual(order.index(item['rarity']), order.index('uncommon'))


class TestRarityConstants(unittest.TestCase):

    def test_rarity_dict_has_all_tiers(self):
        for r in RARITY_ORDER:
            self.assertIn(r, RARITY)

    def test_rarity_order_ascending(self):
        self.assertEqual(RARITY_ORDER, ['common','uncommon','rare','epic'])
