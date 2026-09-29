"""Tests unitarios para entities/player.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame  # instala pygame falso PRIMERO

import math
import unittest
from entities.player import Player
from tests.fake_world import FakeWorld


def make_player(level=0, x=500.0, y=500.0):
    return Player(x, y, level=level)


class TestPlayerInitStats(unittest.TestCase):

    def test_level0_max_hp(self):
        p = make_player(0)
        self.assertEqual(p.max_hp, 100)

    def test_level5_max_hp(self):
        p = make_player(5)
        self.assertEqual(p.max_hp, 100 + 5 * 20)

    def test_level0_max_mp(self):
        p = make_player(0)
        self.assertEqual(p.max_mp, 50)

    def test_level0_attack_damage(self):
        p = make_player(0)
        self.assertEqual(p.attack_damage, 15)

    def test_level10_attack_damage(self):
        p = make_player(10)
        self.assertEqual(p.attack_damage, 15 + 10 * 5)

    def test_hp_starts_full(self):
        p = make_player(3)
        self.assertAlmostEqual(p.hp, p.max_hp)

    def test_xp_starts_at_zero(self):
        p = make_player(0)
        self.assertEqual(p.xp, 0)

    def test_initial_level_stored(self):
        p = make_player(7)
        self.assertEqual(p.level, 7)


class TestPlayerTakeDamage(unittest.TestCase):

    def test_damage_reduces_hp(self):
        p = make_player(0)
        initial = p.hp
        p.take_damage(20)
        self.assertLess(p.hp, initial)

    def test_damage_clamps_hp_to_zero(self):
        p = make_player(0)
        p.take_damage(9999)
        self.assertEqual(p.hp, 0.0)

    def test_damage_returns_zero_during_invincibility(self):
        p = make_player(0)
        p.take_damage(10)    # activa inv_timer
        result = p.take_damage(10)
        self.assertEqual(result, 0)

    def test_damage_returns_actual_amount(self):
        p = make_player(0)
        result = p.take_damage(30)
        self.assertEqual(result, 30)

    def test_minimum_damage_is_one(self):
        p = make_player(0)
        result = p.take_damage(0)
        self.assertEqual(result, 1)

    def test_invincibility_timer_activates(self):
        p = make_player(0)
        p.take_damage(5)
        self.assertGreater(p._inv_timer, 0)


class TestPlayerDead(unittest.TestCase):

    def test_not_dead_when_alive(self):
        p = make_player(0)
        self.assertFalse(p.is_dead())

    def test_dead_when_hp_zero(self):
        p = make_player(0)
        p.hp = 0.0
        self.assertTrue(p.is_dead())

    def test_dead_after_lethal_damage(self):
        p = make_player(0)
        p.take_damage(9999)
        self.assertTrue(p.is_dead())


class TestPlayerLevelUp(unittest.TestCase):

    def test_gain_xp_no_levelup(self):
        p = make_player(0)
        result = p.gain_xp(10)
        self.assertFalse(result)
        self.assertEqual(p.level, 0)

    def test_gain_xp_triggers_levelup(self):
        p = make_player(0)
        result = p.gain_xp(p.max_xp)
        self.assertTrue(result)
        self.assertEqual(p.level, 1)

    def test_levelup_increases_max_hp(self):
        p = make_player(0)
        old_max = p.max_hp
        p.gain_xp(p.max_xp)
        # HP gain is vocation-specific (knight=15, others 8-15)
        self.assertGreater(p.max_hp, old_max,
                           "Max HP should increase on level up")

    def test_levelup_increases_attack_damage(self):
        p = make_player(0)
        p.gain_xp(p.max_xp)
        # Attack damage increase is vocation-specific
        self.assertGreater(p.attack_damage, 15 + 0 * 5)

    def test_levelup_updates_max_xp(self):
        from entities.player import tibia_xp_for_next_level
        p = make_player(0)
        p.gain_xp(p.max_xp)
        self.assertEqual(p.max_xp, tibia_xp_for_next_level(p.level))

    def test_xp_remainder_carries_over(self):
        p = make_player(0)
        threshold = p.max_xp
        p.gain_xp(threshold + 5)
        self.assertEqual(p.xp, 5)

    def test_levelup_restores_partial_hp(self):
        p = make_player(0)
        p.hp = 10.0
        p.gain_xp(p.max_xp)
        self.assertGreater(p.hp, 10.0)


class TestPlayerAttackCooldown(unittest.TestCase):

    def test_attack_ready_initially(self):
        p = make_player(0)
        self.assertTrue(p.attack_ready)

    def test_attack_not_ready_after_swing(self):
        p = make_player(0)
        p.attack(600.0, 500.0, [])
        self.assertFalse(p.attack_ready)

    def test_cooldown_progress_zero_after_swing(self):
        p = make_player(0)
        p.attack(600.0, 500.0, [])
        self.assertAlmostEqual(p.attack_cooldown_progress, 0.0, places=1)

    def test_cooldown_progress_one_when_ready(self):
        p = make_player(0)
        self.assertAlmostEqual(p.attack_cooldown_progress, 1.0)

    def test_no_hit_during_cooldown(self):
        p = make_player(0)
        p.attack(600.0, 500.0, [])
        hits = p.attack(600.0, 500.0, [])
        self.assertEqual(hits, [])


class TestPlayerAttackHit(unittest.TestCase):
    """Comprueba que el cono de ataque acierta / falla correctamente."""

    def _make_fake_monster(self, x, y):
        """Monster mínimo para test de hit detection."""
        class FakeMon:
            def __init__(self, mx, my):
                self.x = float(mx); self.y = float(my)
                self.SIZE = 12; self._hp = 100
                self.hp = 100.0
            def is_dead(self): return self._hp <= 0
            def take_damage(self, amt):
                self._hp -= amt; self.hp = self._hp
                return amt
        return FakeMon(x, y)

    def test_monster_directly_ahead_is_hit(self):
        p = make_player(level=0, x=500.0, y=500.0)
        # Monstruo a la derecha, dentro del rango
        m = self._make_fake_monster(560.0, 500.0)
        hits = p.attack(560.0, 500.0, [m])
        self.assertEqual(len(hits), 1)

    def test_monster_too_far_is_not_hit(self):
        p = make_player(level=0, x=500.0, y=500.0)
        m = self._make_fake_monster(900.0, 500.0)   # muy lejos
        hits = p.attack(900.0, 500.0, [m])
        self.assertEqual(len(hits), 0)

    def test_dead_monster_not_hit(self):
        p = make_player(level=0, x=500.0, y=500.0)
        m = self._make_fake_monster(550.0, 500.0)
        m._hp = 0   # ya muerto
        hits = p.attack(550.0, 500.0, [m])
        self.assertEqual(len(hits), 0)


class TestPlayerMovement(unittest.TestCase):
    """Verifica colisión con tiles y límites del mapa."""

    def _keys_only(self, *active_keys):
        """Devuelve un dict de teclas donde solo active_keys están presionadas."""
        import tests.mock_pygame as mp
        pg = mp._FakePygame
        all_keys = [pg.K_w, pg.K_s, pg.K_a, pg.K_d,
                    pg.K_UP, pg.K_DOWN, pg.K_LEFT, pg.K_RIGHT]
        return {k: (k in active_keys) for k in all_keys}

    def test_player_moves_right(self):
        import tests.mock_pygame as mp
        world = FakeWorld(width=50, height=50, tile_size=32)
        p = make_player(x=800.0, y=800.0)
        keys = self._keys_only(mp._FakePygame.K_d)
        initial_x = p.x
        p.update(keys, 0.1, world)
        self.assertGreater(p.x, initial_x)

    def test_player_blocked_by_impassable_tile(self):
        import tests.mock_pygame as mp
        # Tile (26,25) impassable, player starts at tile (25,25)
        world = FakeWorld(width=50, height=50, tile_size=32,
                          impassable={(26, 25)})
        ts = 32
        p = make_player(x=25*ts + ts//2, y=25*ts + ts//2)
        keys = self._keys_only(mp._FakePygame.K_d)
        for _ in range(30):
            p.update(keys, 0.05, world)
        # Should stay at tile 25 (x = 25*32+16 = 816)
        self.assertLessEqual(p.x, 26 * ts + ts//2)   # did not cross to tile 26

    def test_player_clamped_to_world_bounds(self):
        import tests.mock_pygame as mp
        world = FakeWorld(width=10, height=10, tile_size=32)
        ts = 32
        p = make_player(x=2*ts + ts//2, y=5*ts + ts//2)
        keys = self._keys_only(mp._FakePygame.K_a)
        for _ in range(100):
            p.update(keys, 0.1, world)
        # Should not go to col < 0
        self.assertGreaterEqual(p.x, ts // 2)


if __name__ == '__main__':
    unittest.main()
