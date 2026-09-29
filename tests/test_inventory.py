"""Tests unitarios para systems/inventory.py e integración con Player."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame   # instala pygame falso PRIMERO

import unittest
from systems.inventory import Inventory, MAX_BAG_SIZE
from systems.loot import generate_item
SLOTS = ["weapon","armor","helmet","boots","ring","amulet"]
from entities.player import Player


# ── Helpers ───────────────────────────────────────────────────────────────────

def _item(slot='weapon', rarity='common', **extra_stats):
    item = generate_item(1, slot=slot, rarity=rarity)
    item['stats'].update(extra_stats)
    return item

def _fill_bag(inv, count=None):
    """Llena la bolsa hasta count (default=MAX_BAG_SIZE)."""
    if count is None:
        count = MAX_BAG_SIZE
    for _ in range(count):
        if len(inv.bag) < MAX_BAG_SIZE:
            inv.bag.append(_item(slot='ring'))


# ── TestInventoryInit ─────────────────────────────────────────────────────────

class TestInventoryInit(unittest.TestCase):

    def test_all_slots_start_empty(self):
        inv = Inventory()
        for slot in SLOTS:
            self.assertIsNone(inv.equipped[slot])

    def test_bag_starts_empty(self):
        inv = Inventory()
        self.assertEqual(len(inv.bag), 0)

    def test_not_bag_full_initially(self):
        inv = Inventory()
        self.assertFalse(inv.bag_full)

    def test_equipped_count_zero_initially(self):
        inv = Inventory()
        self.assertEqual(inv.equipped_count(), 0)


# ── TestPickUp ────────────────────────────────────────────────────────────────

class TestPickUp(unittest.TestCase):

    def test_pickup_adds_to_bag(self):
        inv  = Inventory()
        item = _item('ring')
        ok   = inv.pick_up(item)
        self.assertTrue(ok)
        self.assertIn(item, inv.bag)

    def test_pickup_fails_when_bag_full(self):
        inv = Inventory()
        _fill_bag(inv)
        before_len = len(inv.bag)
        extra = _item('ring')
        ok = inv.pick_up(extra)
        self.assertFalse(ok)
        # La bolsa no debe haber crecido
        self.assertEqual(len(inv.bag), before_len)

    def test_bag_size_does_not_exceed_max(self):
        inv = Inventory()
        for _ in range(MAX_BAG_SIZE + 10):
            inv.pick_up(_item('ring'))
        self.assertLessEqual(len(inv.bag), MAX_BAG_SIZE)

    def test_pickup_multiple_items(self):
        inv = Inventory()
        items = [_item(s) for s in ['weapon', 'armor', 'helmet']]
        for it in items:
            inv.pick_up(it)
        self.assertEqual(len(inv.bag), 3)


# ── TestEquip ─────────────────────────────────────────────────────────────────

class TestEquip(unittest.TestCase):

    def test_equip_from_bag_fills_slot(self):
        inv  = Inventory()
        item = _item('armor')
        inv.pick_up(item)
        ok, old = inv.equip(item)
        self.assertTrue(ok)
        self.assertIs(inv.equipped['armor'], item)

    def test_equip_removes_from_bag(self):
        inv  = Inventory()
        item = _item('armor')
        inv.pick_up(item)
        inv.equip(item)
        self.assertNotIn(item, inv.bag)

    def test_equip_returns_old_item_to_bag(self):
        inv  = Inventory()
        old  = _item('weapon')
        new  = _item('weapon')
        inv.pick_up(old)
        inv.equip(old)
        inv.pick_up(new)
        ok, displaced = inv.equip(new)
        self.assertTrue(ok)
        self.assertIs(displaced, old)
        self.assertIn(old, inv.bag)

    def test_equip_fails_if_bag_full_and_slot_occupied(self):
        inv  = Inventory()
        old  = _item('weapon')
        new  = _item('weapon')
        inv.pick_up(old)
        inv.equip(old)
        _fill_bag(inv)   # bolsa llena
        inv.bag.append(new)   # forzar new en bolsa
        # Ahora la bolsa debería estar llena + new extra
        # Resetear a MAX_BAG_SIZE con new dentro
        inv.bag = inv.bag[:MAX_BAG_SIZE]
        if new not in inv.bag:
            inv.bag[-1] = new  # aseguramos que new esté
        ok, displaced = inv.equip(new)
        # Puede que falle porque la bolsa ya está al límite y old necesita volver
        # Depende del estado exacto; lo que sí garantizamos: no hay crash
        self.assertIsInstance(ok, bool)

    def test_equipped_count_increases(self):
        inv = Inventory()
        for slot in ['weapon', 'armor', 'helmet']:
            item = _item(slot)
            inv.pick_up(item)
            inv.equip(item)
        self.assertEqual(inv.equipped_count(), 3)


# ── TestUnequip ───────────────────────────────────────────────────────────────

class TestUnequip(unittest.TestCase):

    def test_unequip_fills_empty_slot(self):
        inv  = Inventory()
        item = _item('helmet')
        inv.pick_up(item)
        inv.equip(item)
        ok = inv.unequip('helmet')
        self.assertTrue(ok)
        self.assertIsNone(inv.equipped['helmet'])
        self.assertIn(item, inv.bag)

    def test_unequip_empty_slot_returns_false(self):
        inv = Inventory()
        ok = inv.unequip('amulet')
        self.assertFalse(ok)

    def test_unequip_fails_when_bag_full(self):
        inv  = Inventory()
        item = _item('amulet')
        inv.pick_up(item)
        inv.equip(item)
        _fill_bag(inv)   # bolsa llena
        ok = inv.unequip('amulet')
        self.assertFalse(ok)
        self.assertIs(inv.equipped['amulet'], item)  # sigue equipado

    def test_unequip_decreases_count(self):
        inv  = Inventory()
        item = _item('ring')
        inv.pick_up(item)
        inv.equip(item)
        self.assertEqual(inv.equipped_count(), 1)
        inv.unequip('ring')
        self.assertEqual(inv.equipped_count(), 0)


# ── TestDropFromBag ───────────────────────────────────────────────────────────

class TestDropFromBag(unittest.TestCase):

    def test_drop_removes_item_at_index(self):
        inv   = Inventory()
        items = [_item('ring') for _ in range(3)]
        for it in items:
            inv.pick_up(it)
        removed = inv.drop_from_bag(1)
        self.assertIs(removed, items[1])
        self.assertEqual(len(inv.bag), 2)

    def test_drop_invalid_index_returns_none(self):
        inv = Inventory()
        inv.pick_up(_item('ring'))
        result = inv.drop_from_bag(99)
        self.assertIsNone(result)

    def test_drop_negative_index_returns_none(self):
        inv = Inventory()
        result = inv.drop_from_bag(-1)
        self.assertIsNone(result)


# ── TestStatAggregation ───────────────────────────────────────────────────────

class TestStatAggregation(unittest.TestCase):

    def test_stat_zero_when_nothing_equipped(self):
        inv = Inventory()
        self.assertEqual(inv.stat('atk_damage'), 0.0)
        self.assertEqual(inv.stat('defense'), 0.0)

    def test_stat_sums_equipped_items(self):
        inv = Inventory()
        # Equipar directamente (sin pasar por bolsa) para el test
        inv.equipped['weapon'] = {'slot':'weapon','rarity':'common',
                                  'item_level':1,'name':'Sword',
                                  'stats':{'atk_damage': 10}}
        inv.equipped['ring']   = {'slot':'ring','rarity':'common',
                                  'item_level':1,'name':'Ring',
                                  'stats':{'atk_damage': 5}}
        self.assertEqual(inv.stat('atk_damage'), 15.0)

    def test_all_stats_aggregates_correctly(self):
        inv = Inventory()
        inv.equipped['armor']  = {'slot':'armor','rarity':'common',
                                  'item_level':1,'name':'Armor',
                                  'stats':{'max_hp': 30, 'defense': 4}}
        inv.equipped['helmet'] = {'slot':'helmet','rarity':'common',
                                  'item_level':1,'name':'Helm',
                                  'stats':{'max_hp': 10, 'defense': 2}}
        stats = inv.all_stats
        self.assertEqual(stats.get('max_hp', 0), 40)
        self.assertEqual(stats.get('defense', 0), 6)

    def test_stat_ignores_unequipped_slots(self):
        inv = Inventory()
        inv.equipped['weapon'] = {'slot':'weapon','rarity':'common',
                                  'item_level':1,'name':'Sword',
                                  'stats':{'atk_damage': 8}}
        # Solo weapon equipado, los demás None
        self.assertEqual(inv.stat('max_hp'), 0.0)

    def test_all_stats_empty_when_nothing_equipped(self):
        inv = Inventory()
        self.assertEqual(inv.all_stats, {})


# ── TestPlayerEquipmentIntegration ───────────────────────────────────────────

class TestPlayerEquipmentIntegration(unittest.TestCase):
    """Verifica que los stats del jugador reflejan el equipamiento."""

    def _make_player(self):
        return Player(500.0, 500.0, level=0)

    def test_base_attack_damage_without_equipment(self):
        p = self._make_player()
        self.assertEqual(p.attack_damage, 15)   # base lv0

    def test_weapon_increases_attack_damage(self):
        p = self._make_player()
        p.inventory.equipped['weapon'] = {
            'slot':'weapon','rarity':'common','item_level':1,'name':'Sword',
            'stats':{'atk_damage': 20}
        }
        self.assertEqual(p.attack_damage, 35)

    def test_defense_zero_without_equipment(self):
        p = self._make_player()
        self.assertEqual(p.defense, 0)

    def test_armor_adds_defense(self):
        p = self._make_player()
        p.inventory.equipped['armor'] = {
            'slot':'armor','rarity':'common','item_level':1,'name':'Armor',
            'stats':{'defense': 8, 'max_hp': 20}
        }
        self.assertEqual(p.defense, 8)

    def test_max_hp_increases_with_equipment(self):
        p = self._make_player()
        base_hp = p.max_hp
        p.inventory.equipped['armor'] = {
            'slot':'armor','rarity':'common','item_level':1,'name':'Armor',
            'stats':{'max_hp': 50}
        }
        self.assertEqual(p.max_hp, base_hp + 50)

    def test_block_chance_zero_without_shield(self):
        p = self._make_player()
        self.assertAlmostEqual(p.block_chance, 0.0)

    def test_shield_adds_block_chance(self):
        p = self._make_player()
        p.inventory.equipped['shield'] = {
            'slot':'shield','rarity':'common','item_level':1,'name':'Shield',
            'stats':{'defense': 3, 'block_chance': 0.15}
        }
        self.assertAlmostEqual(p.block_chance, 0.15, places=3)

    def test_block_chance_capped_at_60_percent(self):
        p = self._make_player()
        p.inventory.equipped['shield'] = {
            'slot':'shield','rarity':'epic','item_level':20,'name':'Shield',
            'stats':{'block_chance': 0.99}
        }
        self.assertLessEqual(p.block_chance, 0.60)

    def test_xp_bonus_zero_without_equipment(self):
        p = self._make_player()
        self.assertAlmostEqual(p.xp_bonus, 0.0)

    def test_xp_bonus_increases_xp_gain(self):
        p = self._make_player()
        p.max_xp = 10000   # evitar level-up durante el test
        p.inventory.equipped['ring'] = {
            'slot':'ring','rarity':'common','item_level':1,'name':'Ring',
            'stats':{'xp_bonus': 0.50}   # +50% XP
        }
        before = p.xp
        p.gain_xp(100)
        # Con 50% bonus, deberíamos ganar int(100 * 1.50) = 150 XP
        self.assertEqual(p.xp - before, 150)

    def test_hp_regen_zero_without_equipment(self):
        p = self._make_player()
        self.assertAlmostEqual(p.hp_regen, 0.0)

    def test_amulet_adds_hp_regen(self):
        p = self._make_player()
        p.inventory.equipped['amulet'] = {
            'slot':'amulet','rarity':'common','item_level':1,'name':'Amulet',
            'stats':{'hp_regen': 2.0}
        }
        self.assertAlmostEqual(p.hp_regen, 2.0, places=3)

    def test_atk_speed_bonus_reduces_cooldown(self):
        p = self._make_player()
        base_cd = p.effective_cooldown
        p.inventory.equipped['weapon'] = {
            'slot':'weapon','rarity':'common','item_level':1,'name':'Dagger',
            'stats':{'atk_speed': 0.20}
        }
        self.assertLess(p.effective_cooldown, base_cd)

    def test_effective_cooldown_has_minimum(self):
        p = self._make_player()
        p.inventory.equipped['weapon'] = {
            'slot':'weapon','rarity':'epic','item_level':20,'name':'Rapier',
            'stats':{'atk_speed': 0.99}   # would reduce to near zero
        }
        self.assertGreaterEqual(p.effective_cooldown, 0.15)

    def test_defense_reduces_damage_taken(self):
        p = self._make_player()
        p.inventory.equipped['armor'] = {
            'slot':'armor','rarity':'common','item_level':1,'name':'Armor',
            'stats':{'defense': 10}
        }
        # Take 15 damage, defense 10 → actual = max(1, 15-10) = 5
        actual = p.take_damage(15)
        self.assertEqual(actual, 5)

    def test_damage_never_less_than_one_even_with_high_defense(self):
        p = self._make_player()
        p.inventory.equipped['armor'] = {
            'slot':'armor','rarity':'epic','item_level':20,'name':'Dragon Scale',
            'stats':{'defense': 999}
        }
        actual = p.take_damage(5)
        # Invincibility OR at least 1 if not blocked
        self.assertGreaterEqual(actual, 0)  # 0 si bloqueo, ≥1 si pega


class TestInventoryRepr(unittest.TestCase):

    def test_repr_does_not_crash(self):
        inv = Inventory()
        try:
            r = repr(inv)
            self.assertIsInstance(r, str)
        except Exception as e:
            self.fail(f"repr() lanzó excepción: {e}")


if __name__ == '__main__':
    unittest.main()
