"""Tests para bugs corregidos: spells de monstruos, vocation select, cobertura."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame
import unittest
from systems.spells import SPELL_CATALOGUE, MONSTER_SPELLS, VOCATION_SPELLS
from entities.monster import MONSTER_DATA
from entities.player import MONSTER_XP
from systems.loot import CREATURE_LOOT
from systems.zones import ZONE_MONSTER_TYPES


class TestMonsterSpellIDs(unittest.TestCase):

    def test_all_monster_spells_in_catalogue(self):
        for mtype, spells in MONSTER_SPELLS.items():
            for sid in spells:
                self.assertIn(sid, SPELL_CATALOGUE,
                    f"MONSTER_SPELLS['{mtype}'] usa spell desconocido '{sid}'")

    def test_no_old_spell_ids(self):
        old_ids = {"poison_bolt","decay_wave","fireball","energy_beam",
                   "death_coil","spark","bone_shard"}
        for mtype, spells in MONSTER_SPELLS.items():
            for sid in spells:
                self.assertNotIn(sid, old_ids,
                    f"'{mtype}' usa ID antiguo '{sid}'")

    def test_dark_wizard_spells_valid(self):
        spells = MONSTER_SPELLS.get("dark_wizard", [])
        self.assertTrue(len(spells) > 0, "dark_wizard should have spells")
        for sid in spells:
            self.assertIn(sid, SPELL_CATALOGUE)

    def test_dragon_spells_valid(self):
        spells = MONSTER_SPELLS.get("dragon", [])
        self.assertTrue(len(spells) > 0, "dragon should have spells")
        for sid in spells:
            self.assertIn(sid, SPELL_CATALOGUE)

    def test_new_monsters_have_spell_entries(self):
        for mtype in ["wolf","troll","bear","cyclops","fire_devil","vampire"]:
            self.assertIn(mtype, MONSTER_SPELLS,
                f"New monster '{mtype}' missing from MONSTER_SPELLS")
            for sid in MONSTER_SPELLS[mtype]:
                self.assertIn(sid, SPELL_CATALOGUE,
                    f"'{mtype}' uses unknown spell '{sid}'")

    def test_projectile_creation_safe(self):
        from entities.projectile import Projectile
        for mtype, spells in MONSTER_SPELLS.items():
            for sid in spells:
                data = SPELL_CATALOGUE.get(sid, {})
                dmg = data.get("damage", 0)
                if dmg > 0:
                    p = Projectile(100,100,1.0,0.0,sid,int(dmg*0.6),owner='monster')
                    self.assertIsNotNone(p)


class TestVocationSelectInMain(unittest.TestCase):

    def _main_src(self):
        return open(os.path.join(os.path.dirname(__file__),'..','main.py')).read()

    def test_voc_screen_instantiated(self):
        self.assertIn('VocationSelect()', self._main_src())

    def test_voc_screen_run_called_on_new_game(self):
        count = self._main_src().count("voc_screen.run(screen, clock)")
        self.assertGreaterEqual(count, 3,
            f"voc_screen.run only called {count} times, need >=3")

    def test_vocation_select_spells_valid(self):
        from ui.vocation_select import VOCATIONS
        for voc_data in VOCATIONS:
            for sid in voc_data["spells"]:
                self.assertIn(sid, SPELL_CATALOGUE,
                    f"VocationSelect '{voc_data['id']}' uses unknown spell '{sid}'")


class TestAllMonstersHaveLoot(unittest.TestCase):

    def test_all_monsters_have_loot_table(self):
        for mtype in MONSTER_DATA:
            self.assertIn(mtype, CREATURE_LOOT,
                f"No loot table for '{mtype}'")

    def test_loot_chances_valid(self):
        for mtype, drops in CREATURE_LOOT.items():
            for chance, name in drops:
                self.assertGreater(chance, 0.0)
                self.assertLessEqual(chance, 1.0)

    def test_loot_item_names_exist(self):
        from systems.loot import ITEM_TEMPLATES
        valid = {t["name"] for t in ITEM_TEMPLATES} | {"Cheese"}
        for mtype, drops in CREATURE_LOOT.items():
            for _, name in drops:
                self.assertIn(name, valid,
                    f"'{mtype}' has unknown item '{name}'")


class TestAllMonstersHaveXP(unittest.TestCase):

    def test_all_monsters_in_xp_table(self):
        for mtype in MONSTER_DATA:
            self.assertIn(mtype, MONSTER_XP,
                f"No MONSTER_XP for '{mtype}'")

    def test_xp_positive(self):
        for mtype, xp in MONSTER_XP.items():
            self.assertGreater(xp, 0)

    def test_danger_scaling(self):
        self.assertGreater(MONSTER_XP["demon"],   MONSTER_XP["dragon"])
        self.assertGreater(MONSTER_XP["dragon"],  MONSTER_XP["vampire"])
        self.assertGreater(MONSTER_XP["vampire"], MONSTER_XP["cyclops"])
        self.assertGreater(MONSTER_XP["cyclops"], MONSTER_XP["orc"])
        self.assertGreater(MONSTER_XP["orc"],     MONSTER_XP["rat"])

    def test_level_scaling_formula(self):
        base = MONSTER_XP["rat"]
        lv0  = max(1, int(base * (1 + 0  * 0.04)))
        lv10 = max(1, int(base * (1 + 10 * 0.04)))
        self.assertGreater(lv10, lv0)


class TestZoneMonsterValidity(unittest.TestCase):

    def test_zone_types_all_valid(self):
        valid = set(MONSTER_DATA.keys())
        for z, types in enumerate(ZONE_MONSTER_TYPES):
            for mtype in types:
                self.assertIn(mtype, valid,
                    f"Zone {z} has unknown monster '{mtype}'")

    def test_center_has_tough_monsters(self):
        tough = {"demon","dragon_lord","dragon","vampire"}
        self.assertTrue(any(t in tough for t in ZONE_MONSTER_TYPES[0]))

    def test_periphery_has_weak_monsters(self):
        weak = {"rat","wolf","zombie","skeleton","troll","bear"}
        self.assertTrue(any(t in weak for t in ZONE_MONSTER_TYPES[3]))


class TestSpellIDGlobalConsistency(unittest.TestCase):

    def test_vocation_spells_all_in_catalogue(self):
        for voc, spells in VOCATION_SPELLS.items():
            for sid in spells:
                self.assertIn(sid, SPELL_CATALOGUE,
                    f"VOCATION_SPELLS['{voc}'] uses unknown '{sid}'")

    def test_tibia_incantations(self):
        prefixes = ("exori","exevo","exura","utamo")
        for sid, data in SPELL_CATALOGUE.items():
            inc = data.get("incantation","")
            self.assertTrue(any(inc.startswith(p) for p in prefixes),
                f"'{sid}' has invalid incantation '{inc}'")

    def test_catalogue_has_sufficient_spells(self):
        self.assertGreaterEqual(len(SPELL_CATALOGUE), 15)


if __name__ == "__main__":
    unittest.main()
