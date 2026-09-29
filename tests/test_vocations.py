"""Tests unitarios para vocaciones, hechizos Tibia y VocationSelect."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame

import unittest
from systems.spells import (
    SPELL_CATALOGUE, VOCATION_SPELLS, MONSTER_SPELLS, SpellMemory
)


class TestTibiaSpellNames(unittest.TestCase):
    """Verifica que todos los hechizos tienen incantaciones reales de Tibia."""

    VALID_PREFIXES = ("exori", "exevo", "exura", "utamo")

    def test_all_have_incantation(self):
        for sid, data in SPELL_CATALOGUE.items():
            self.assertIn("incantation", data, f"{sid} missing incantation")

    def test_incantations_look_like_tibia(self):
        for sid, data in SPELL_CATALOGUE.items():
            inc = data["incantation"]
            self.assertTrue(
                any(inc.startswith(p) for p in self.VALID_PREFIXES),
                f"'{inc}' doesn't start with a valid Tibia prefix"
            )

    def test_all_have_display_name(self):
        for sid, data in SPELL_CATALOGUE.items():
            self.assertIn("name", data)
            self.assertGreater(len(data["name"]), 0)

    def test_all_have_color(self):
        for sid, data in SPELL_CATALOGUE.items():
            self.assertIn("color", data)
            col = data["color"]
            self.assertEqual(len(col), 3)
            for c in col:
                self.assertGreaterEqual(c, 0)
                self.assertLessEqual(c, 255)

    def test_all_have_vocations_list(self):
        for sid, data in SPELL_CATALOGUE.items():
            self.assertIn("vocations", data)
            self.assertIsInstance(data["vocations"], list)
            self.assertGreater(len(data["vocations"]), 0)

    def test_unique_incantations(self):
        incantations = [d["incantation"] for d in SPELL_CATALOGUE.values()]
        self.assertEqual(len(incantations), len(set(incantations)),
                         "Duplicate incantations found")


class TestVocationSpells(unittest.TestCase):
    """Verifica que cada vocación tiene hechizos correctamente asignados."""

    VOCATIONS = ["knight", "paladin", "druid", "sorcerer"]

    def test_all_vocations_have_spells(self):
        for voc in self.VOCATIONS:
            spells = VOCATION_SPELLS.get(voc, [])
            self.assertGreater(len(spells), 0, f"{voc} has no spells")

    def test_knight_has_exori(self):
        self.assertIn("exori", VOCATION_SPELLS["knight"])

    def test_knight_has_exori_gran(self):
        self.assertIn("exori gran", VOCATION_SPELLS["knight"])

    def test_paladin_has_conjure_arrow(self):
        self.assertIn("exevo con", VOCATION_SPELLS["paladin"])

    def test_druid_has_ice_strike(self):
        self.assertIn("exevo frigo", VOCATION_SPELLS["druid"])

    def test_sorcerer_has_magic_missile(self):
        self.assertIn("exevo vis", VOCATION_SPELLS["sorcerer"])

    def test_sorcerer_has_fireball(self):
        self.assertIn("exevo flam", VOCATION_SPELLS["sorcerer"])

    def test_vocation_spells_all_in_catalogue(self):
        for voc, spells in VOCATION_SPELLS.items():
            for sid in spells:
                self.assertIn(sid, SPELL_CATALOGUE,
                              f"Vocation '{voc}' references unknown spell '{sid}'")

    def test_vocations_have_different_spells(self):
        knight_set   = set(VOCATION_SPELLS["knight"])
        sorcerer_set = set(VOCATION_SPELLS["sorcerer"])
        self.assertFalse(knight_set == sorcerer_set,
                         "Knight and sorcerer should have different spells")

    def test_knight_spells_are_knight_only_or_shared(self):
        for sid in VOCATION_SPELLS["knight"]:
            data = SPELL_CATALOGUE[sid]
            self.assertIn("knight", data["vocations"])

    def test_sorcerer_spells_have_high_damage(self):
        sorcerer_damage = [
            SPELL_CATALOGUE[s]["damage"]
            for s in VOCATION_SPELLS["sorcerer"]
            if SPELL_CATALOGUE[s]["damage"] > 0
        ]
        self.assertTrue(any(d >= 100 for d in sorcerer_damage),
                        "Sorcerer should have at least one high-damage spell (>=100)")


class TestMonsterSpells(unittest.TestCase):
    """Verifica las tablas de hechizos de monstruos."""

    def test_all_monster_types_present(self):
        for mtype in ["rat","zombie","skeleton","orc","dark_wizard",
                      "dragon","demon","dragon_lord"]:
            self.assertIn(mtype, MONSTER_SPELLS)

    def test_dragon_has_fireball(self):
        self.assertIn("exevo flam", MONSTER_SPELLS["dragon"])

    def test_demon_has_death_strike(self):
        self.assertIn("exura mort", MONSTER_SPELLS["demon"])

    def test_dragon_lord_has_energy_beam(self):
        self.assertIn("exevo gran vis", MONSTER_SPELLS["dragon_lord"])

    def test_rat_has_no_spells(self):
        self.assertEqual(MONSTER_SPELLS["rat"], [])

    def test_all_monster_spell_ids_valid(self):
        for mtype, spells in MONSTER_SPELLS.items():
            for sid in spells:
                self.assertIn(sid, SPELL_CATALOGUE,
                              f"Monster '{mtype}' references unknown spell '{sid}'")


class TestSpellMemoryVocation(unittest.TestCase):
    def test_default_vocation_sorcerer(self):
        sm = SpellMemory()
        self.assertEqual(sm.vocation, "sorcerer")

    def test_custom_vocation_stored(self):
        sm = SpellMemory(vocation="knight")
        self.assertEqual(sm.vocation, "knight")

    def test_vocation_spells_method(self):
        sm = SpellMemory(vocation="druid")
        voc_spells = sm.vocation_spells()
        self.assertIn("exevo frigo", voc_spells)

    def test_to_dict_saves_vocation(self):
        sm = SpellMemory(vocation="paladin")
        d  = sm.to_dict()
        self.assertEqual(d["vocation"], "paladin")

    def test_from_dict_restores_vocation(self):
        sm = SpellMemory(vocation="druid")
        sm2 = SpellMemory.from_dict(sm.to_dict())
        self.assertEqual(sm2.vocation, "druid")

    def test_repr_contains_vocation(self):
        sm = SpellMemory(vocation="knight")
        self.assertIn("knight", repr(sm))

    def test_observe_learns_spell_at_threshold(self):
        sm = SpellMemory(vocation="sorcerer")
        data  = SPELL_CATALOGUE["exevo vis"]
        thresh = data["learn_thresh"]
        sm.magic_level = data["min_magic_lv"]
        learned = False
        for _ in range(thresh + 5):
            if sm.observe("exevo vis"):
                learned = True; break
        self.assertTrue(learned)

    def test_observe_requires_min_magic_level(self):
        sm = SpellMemory(vocation="sorcerer")
        sm.magic_level = 0
        # exevo gran mas vis needs magic level 12
        for _ in range(20):
            sm.observe("exevo gran mas vis")
        self.assertNotIn("exevo gran mas vis", sm.known_spells)


class TestVocationSelect(unittest.TestCase):
    def test_four_vocations(self):
        from ui.vocation_select import VOCATIONS
        self.assertEqual(len(VOCATIONS), 4)

    def test_vocation_ids_correct(self):
        from ui.vocation_select import VOCATIONS
        ids = {v["id"] for v in VOCATIONS}
        self.assertEqual(ids, {"knight","paladin","druid","sorcerer"})

    def test_all_have_spells_in_catalogue(self):
        from ui.vocation_select import VOCATIONS
        for voc in VOCATIONS:
            for sid in voc["spells"]:
                self.assertIn(sid, SPELL_CATALOGUE,
                              f"VocationSelect {voc['id']} refs unknown spell {sid}")

    def test_all_have_symbol(self):
        from ui.vocation_select import VOCATIONS
        for voc in VOCATIONS:
            self.assertIn("symbol", voc)
            self.assertGreater(len(voc["symbol"]), 0)

    def test_instantiates_without_crash(self):
        from ui.vocation_select import VocationSelect
        vs = VocationSelect()
        self.assertIsInstance(vs, VocationSelect)

    def test_card_rects_count(self):
        from ui.vocation_select import VocationSelect, VOCATIONS
        import pygame
        vs   = VocationSelect()
        rects = vs._card_rects()
        self.assertEqual(len(rects), len(VOCATIONS))
        for r in rects:
            self.assertIsInstance(r, pygame.Rect)

    def test_click_sets_selected(self):
        from ui.vocation_select import VocationSelect
        vs   = VocationSelect()
        rects = vs._card_rects()
        vs._click((rects[2].centerx, rects[2].centery))
        self.assertEqual(vs._selected, 2)

    def test_draw_no_crash(self):
        from ui.vocation_select import VocationSelect
        from tests.mock_pygame import FakeSurface
        vs = VocationSelect()
        try:
            vs._draw(FakeSurface())
        except Exception as e:
            self.fail(f"VocationSelect._draw raised {e}")


if __name__ == "__main__":
    unittest.main()
