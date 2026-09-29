"""Tests unitarios para entities/projectile.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame   # instala pygame falso PRIMERO

import math
import unittest
from entities.projectile import Projectile, Explosion
from systems.spells import SPELL_CATALOGUE


# ── Fake monster for collision tests ──────────────────────────────────────────

class FakeMon:
    def __init__(self, x=0.0, y=0.0, size=12):
        self.x = float(x); self.y = float(y); self.SIZE = size
        self.hp = 100.0; self._hits = []
    def is_dead(self): return self.hp <= 0
    def take_damage(self, amt):
        self.hp -= amt; self._hits.append(amt); return amt


# ── Init ──────────────────────────────────────────────────────────────────────

class TestProjectileInit(unittest.TestCase):

    def _make(self, spell_id="exevo vis"):
        return Projectile(100.0, 200.0, 1.0, 0.0, spell_id, 25)

    def test_starts_alive(self):
        p = self._make()
        self.assertTrue(p.is_alive())

    def test_initial_position(self):
        p = self._make()
        self.assertAlmostEqual(p.x, 100.0)
        self.assertAlmostEqual(p.y, 200.0)

    def test_speed_matches_catalogue(self):
        p = self._make("exevo vis")
        self.assertAlmostEqual(p.speed, SPELL_CATALOGUE["exevo vis"]["speed"])

    def test_radius_matches_catalogue(self):
        p = self._make("exevo vis")
        self.assertEqual(p.radius, SPELL_CATALOGUE["exevo vis"]["radius"])

    def test_pierce_matches_catalogue(self):
        for sid, data in SPELL_CATALOGUE.items():
            p = Projectile(0, 0, 1, 0, sid, 10)
            self.assertEqual(p.pierce, data["pierce"])

    def test_aoe_radius_matches_catalogue(self):
        p = self._make("exevo flam")
        self.assertEqual(p.aoe_r, SPELL_CATALOGUE["exevo flam"]["aoe_radius"])

    def test_owner_default_player(self):
        p = self._make()
        self.assertEqual(p.owner, "player")

    def test_custom_owner(self):
        p = Projectile(0,0,1,0,"exevo vis",10,owner="monster")
        self.assertEqual(p.owner, "monster")


# ── Movement ──────────────────────────────────────────────────────────────────

class TestProjectileMovement(unittest.TestCase):

    def test_moves_in_dx_direction(self):
        p = Projectile(0.0, 0.0, 1.0, 0.0, "exevo vis", 10)
        p.update(0.1, [])
        self.assertGreater(p.x, 0.0)
        self.assertAlmostEqual(p.y, 0.0, places=3)

    def test_moves_in_dy_direction(self):
        p = Projectile(0.0, 0.0, 0.0, 1.0, "exevo vis", 10)
        p.update(0.1, [])
        self.assertGreater(p.y, 0.0)
        self.assertAlmostEqual(p.x, 0.0, places=3)

    def test_diagonal_movement(self):
        inv_rt2 = 1.0 / math.sqrt(2)
        p = Projectile(0.0, 0.0, inv_rt2, inv_rt2, "exevo vis", 10)
        p.update(0.1, [])
        self.assertGreater(p.x, 0.0)
        self.assertGreater(p.y, 0.0)
        self.assertAlmostEqual(p.x, p.y, places=3)

    def test_dies_when_range_exceeded(self):
        p = Projectile(0.0, 0.0, 1.0, 0.0, "exevo vis", 10)
        range_px = SPELL_CATALOGUE["exevo vis"]["range_px"]
        # Advance far beyond range
        for _ in range(500):
            p.update(0.05, [])
            if not p.is_alive():
                break
        self.assertFalse(p.is_alive())

    def test_still_alive_within_range(self):
        p = Projectile(0.0, 0.0, 1.0, 0.0, "exevo vis", 10)
        p.update(0.001, [])   # tiny step
        self.assertTrue(p.is_alive())


# ── Collision ─────────────────────────────────────────────────────────────────

class TestProjectileCollision(unittest.TestCase):

    def test_hits_monster_in_path(self):
        speed = SPELL_CATALOGUE["exevo vis"]["speed"]
        p     = Projectile(0.0, 0.0, 1.0, 0.0, "exevo vis", 20)
        m     = FakeMon(x=speed*0.05, y=0.0, size=12)   # right in the path
        hits  = p.update(0.05, [m])
        self.assertGreater(len(hits), 0)

    def test_does_not_hit_far_monster(self):
        p = Projectile(0.0, 0.0, 1.0, 0.0, "exevo vis", 20)
        m = FakeMon(x=5000.0, y=5000.0)
        hits = p.update(0.05, [m])
        self.assertEqual(len(hits), 0)

    def test_does_not_hit_dead_monster(self):
        speed = SPELL_CATALOGUE["exevo vis"]["speed"]
        p = Projectile(0.0, 0.0, 1.0, 0.0, "exevo vis", 20)
        m = FakeMon(x=speed*0.05, y=0.0, size=12)
        m.hp = 0.0
        hits = p.update(0.05, [m])
        self.assertEqual(hits, [])

    def test_non_pierce_dies_on_hit(self):
        assert not SPELL_CATALOGUE["exevo vis"]["pierce"], "spark should not pierce"
        speed = SPELL_CATALOGUE["exevo vis"]["speed"]
        p     = Projectile(0.0, 0.0, 1.0, 0.0, "exevo vis", 20)
        m     = FakeMon(x=speed*0.05, y=0.0, size=12)
        p.update(0.05, [m])
        self.assertFalse(p.is_alive())

    def test_pierce_stays_alive_after_hit(self):
        # energy_beam pierces
        assert SPELL_CATALOGUE["exevo gran vis"]["pierce"]
        speed = SPELL_CATALOGUE["exevo gran vis"]["speed"]
        p     = Projectile(0.0, 0.0, 1.0, 0.0, "exevo gran vis", 30)
        m     = FakeMon(x=speed*0.05, y=0.0, size=12)
        p.update(0.05, [m])
        self.assertTrue(p.is_alive())

    def test_pierce_does_not_hit_same_monster_twice(self):
        speed = SPELL_CATALOGUE["exevo gran vis"]["speed"]
        p     = Projectile(0.0, 0.0, 1.0, 0.0, "exevo gran vis", 30)
        m     = FakeMon(x=speed*0.05, y=0.0, size=20)
        # Update multiple frames while still overlapping
        for _ in range(5):
            p.update(0.02, [m])
        self.assertEqual(len(m._hits), 1)   # hit only once

    def test_damage_applied_to_monster(self):
        speed = SPELL_CATALOGUE["exevo vis"]["speed"]
        p     = Projectile(0.0, 0.0, 1.0, 0.0, "exevo vis", 50)
        m     = FakeMon(x=speed*0.05, y=0.0, size=15)
        initial_hp = m.hp
        p.update(0.05, [m])
        self.assertLess(m.hp, initial_hp)

    def test_kill_method_deactivates(self):
        p = Projectile(0.0, 0.0, 1.0, 0.0, "exevo vis", 10)
        p.kill()
        self.assertFalse(p.is_alive())


# ── AOE ───────────────────────────────────────────────────────────────────────

class TestProjectileAOE(unittest.TestCase):

    def test_fireball_has_aoe(self):
        self.assertGreater(SPELL_CATALOGUE["exevo flam"]["aoe_radius"], 0)

    def test_aoe_hits_nearby_monster_on_expire(self):
        """When a fireball expires at range, it should AOE nearby monsters."""
        p   = Projectile(0.0, 0.0, 1.0, 0.0, "exevo flam", 50)
        aoe = SPELL_CATALOGUE["exevo flam"]["aoe_radius"]
        m   = FakeMon(x=SPELL_CATALOGUE["exevo flam"]["range_px"] + aoe - 5,
                      y=0.0, size=12)
        # Advance to expiry
        for _ in range(1000):
            p.update(0.05, [m])
            if not p.is_alive():
                break
        # The monster should have taken some damage from AOE
        self.assertLess(m.hp, 100.0)


# ── Explosion ─────────────────────────────────────────────────────────────────

class TestExplosion(unittest.TestCase):

    def test_starts_alive(self):
        e = Explosion(0.0, 0.0, 40, (255, 80, 20))
        self.assertTrue(e.is_alive())

    def test_dies_after_duration(self):
        e = Explosion(0.0, 0.0, 40, (255, 80, 20))
        for _ in range(50):
            e.update(0.02)   # 1 second total
        self.assertFalse(e.is_alive())

    def test_still_alive_briefly(self):
        e = Explosion(0.0, 0.0, 40, (255, 80, 20))
        e.update(0.01)
        self.assertTrue(e.is_alive())


# ── Player cast_spell integration ─────────────────────────────────────────────

class TestPlayerCastSpell(unittest.TestCase):

    def _make_player(self, known=None):
        from entities.player import Player
        from systems.spells import SpellMemory
        p  = Player(500.0, 500.0, level=0)
        sm = SpellMemory(known=known if known is not None else ["exevo vis"])
        p.spell_memory = sm
        p.mp = float(p.max_mp)
        return p

    def test_cast_returns_fire_dict(self):
        p    = self._make_player(["exevo vis"])
        fire = p.cast_spell(600.0, 500.0)
        self.assertIsNotNone(fire)
        self.assertIn("spell_id", fire)
        self.assertEqual(fire["spell_id"], "exevo vis")

    def test_cast_consumes_mp(self):
        p = self._make_player(["exevo vis"])
        mp_before = p.mp
        p.cast_spell(600.0, 500.0)
        self.assertLess(p.mp, mp_before)

    def test_cast_fails_without_mp(self):
        p    = self._make_player(["exevo vis"])
        p.mp = 0.0
        fire = p.cast_spell(600.0, 500.0)
        self.assertIsNone(fire)

    def test_cast_fails_with_no_spells(self):
        p    = self._make_player([])
        fire = p.cast_spell(600.0, 500.0)
        self.assertIsNone(fire)

    def test_cast_on_cooldown_returns_none(self):
        p    = self._make_player(["exevo vis"])
        p.cast_spell(600.0, 500.0)   # first cast
        fire = p.cast_spell(600.0, 500.0)   # immediate second
        self.assertIsNone(fire)

    def test_cast_direction_normalised(self):
        p    = self._make_player(["exevo vis"])
        fire = p.cast_spell(600.0, 500.0)
        if fire:
            norm = (fire['dx']**2 + fire['dy']**2) ** 0.5
            self.assertAlmostEqual(norm, 1.0, places=4)

    def test_cast_increments_magic_level_after_8_casts(self):
        p = self._make_player(["exevo vis"])
        initial_ml = p.spell_memory.magic_level
        for _ in range(8):
            p.mp = float(p.max_mp)
            p._spell_cast_cd = 0
            p.cast_spell(600.0, 500.0)
        self.assertGreater(p.spell_memory.magic_level, initial_ml)

    def test_fire_dict_contains_position(self):
        p    = self._make_player(["exevo vis"])
        fire = p.cast_spell(600.0, 500.0)
        self.assertIn("x", fire)
        self.assertIn("y", fire)
        # Player snaps to tile centre; position is within one tile of spawn
        self.assertAlmostEqual(fire["x"], p.x, places=1)
        self.assertAlmostEqual(fire["y"], p.y, places=1)

    def test_damage_scales_with_magic_level(self):
        p1 = self._make_player(["exevo flam"])
        p1.mp = 999; p1.spell_memory.magic_level = 0
        f1 = p1.cast_spell(600.0, 500.0)

        p2 = self._make_player(["exevo flam"])
        p2.mp = 999; p2.spell_memory.magic_level = 10
        f2 = p2.cast_spell(600.0, 500.0)

        self.assertGreater(f2["damage"], f1["damage"])


# ── observe_spell ─────────────────────────────────────────────────────────────

class TestPlayerObserveSpell(unittest.TestCase):

    def _make_player(self):
        from entities.player import Player
        return Player(500.0, 500.0, level=0)

    def test_observe_within_range_increments(self):
        p = self._make_player()
        # Monster at 100px away (within OBSERVE_RANGE=380)
        p.observe_spell("exevo vis", 530.0, 500.0)
        self.assertEqual(p.spell_memory.observations.get("exevo vis", 0), 1)

    def test_observe_outside_range_does_not_count(self):
        p = self._make_player()
        p.observe_spell("exevo vis", 5000.0, 5000.0)
        self.assertEqual(p.spell_memory.observations.get("exevo vis", 0), 0)

    def test_observe_enough_times_learns(self):
        p      = self._make_player()
        thresh = SPELL_CATALOGUE["exevo vis"]["learn_thresh"]
        learned = False
        for _ in range(thresh):
            # Monster right next to player
            if p.observe_spell("exevo vis", 510.0, 500.0):
                learned = True
        self.assertTrue(learned)
        self.assertIn("exevo vis", p.spell_memory.known_spells)


# ── Spell cycle / select ──────────────────────────────────────────────────────

class TestSpellSelection(unittest.TestCase):

    def _make_player_with_spells(self, spells):
        from entities.player import Player
        from systems.spells import SpellMemory
        p  = Player(500.0, 500.0, level=0)
        p.spell_memory = SpellMemory(known=spells)
        return p

    def test_selected_spell_is_first_by_default(self):
        p = self._make_player_with_spells(["exevo vis", "exevo flam"])
        self.assertEqual(p.selected_spell, "exevo vis")

    def test_cycle_forward(self):
        p = self._make_player_with_spells(["exevo vis", "exevo flam"])
        p.cycle_spell(1)
        self.assertEqual(p.selected_spell, "exevo flam")

    def test_cycle_wraps_around(self):
        p = self._make_player_with_spells(["exevo vis", "exevo flam"])
        p.cycle_spell(1); p.cycle_spell(1)
        self.assertEqual(p.selected_spell, "exevo vis")

    def test_cycle_backward(self):
        p = self._make_player_with_spells(["exevo vis", "exevo flam"])
        p.cycle_spell(-1)
        self.assertEqual(p.selected_spell, "exevo flam")

    def test_select_by_index(self):
        p = self._make_player_with_spells(["exevo vis", "exevo flam", "exevo gran vis"])
        p.select_spell_by_index(2)
        self.assertEqual(p.selected_spell, "exevo gran vis")

    def test_selected_spell_none_when_no_spells(self):
        p = self._make_player_with_spells([])
        self.assertIsNone(p.selected_spell)

    def test_select_index_out_of_range_wraps(self):
        p = self._make_player_with_spells(["exevo vis", "exevo flam"])
        p.select_spell_by_index(99)
        self.assertIn(p.selected_spell, ["exevo vis", "exevo flam"])


if __name__ == '__main__':
    unittest.main()
