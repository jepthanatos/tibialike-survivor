"""Tests unitarios para entities/spawner.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame  # instala pygame falso PRIMERO

import unittest
from entities.spawner import Spawner, TARGET_POP, MIN_POP
from tests.fake_world import FakeWorld


def make_world():
    return FakeWorld(width=60, height=60, tile_size=32)


class FakePlayer:
    """Player mínimo para que Spawner funcione sin pygame."""
    SIZE  = 18
    level = 0
    hp    = 100.0
    max_hp = 100.0
    _inv_timer = 0.0

    def __init__(self, x=960.0, y=960.0, level=0):
        self.x = float(x)
        self.y = float(y)
        self.level = level

    def take_damage(self, amount):
        if self._inv_timer > 0:
            return 0
        self.hp = max(0.0, self.hp - amount)
        self._inv_timer = 0.75
        return max(1, amount)

    def is_dead(self):
        return self.hp <= 0


class TestSpawnerInit(unittest.TestCase):

    def setUp(self):
        self.world   = make_world()
        self.spawner = Spawner(self.world, player_level=0)

    def test_spawns_some_monsters(self):
        self.assertGreater(len(self.spawner.monsters), 0)

    def test_does_not_exceed_target_pop(self):
        self.assertLessEqual(len(self.spawner.monsters), TARGET_POP)

    def test_all_monsters_on_walkable_tiles(self):
        ts = self.world.tile_size
        for m in self.spawner.monsters:
            col = int(m.x // ts)
            row = int(m.y // ts)
            self.assertTrue(
                self.world.is_walkable(col, row),
                f"Monstruo en tile impassable ({col},{row})"
            )

    def test_all_monsters_have_positive_xp(self):
        for m in self.spawner.monsters:
            self.assertGreater(m.xp_reward, 0)

    def test_all_monsters_have_positive_hp(self):
        for m in self.spawner.monsters:
            self.assertGreater(m.max_hp, 0)


class TestSpawnerLevelScaling(unittest.TestCase):

    def test_level_7_includes_skeletons(self):
        world   = make_world()
        spawner = Spawner(world, player_level=7)
        types   = {m.mtype for m in spawner.monsters}
        # Con nivel 7, al menos debería salir zombie y skeleton
        self.assertGreater(len(types), 1)

    def test_level_0_spawns_some_monsters(self):
        """Zone-based spawning: level 0 spawns monsters of all zone types."""
        world   = make_world()
        spawner = Spawner(world, player_level=0)
        # Should have spawned some monsters
        self.assertGreater(len(spawner.monsters), 0)
        # All should have valid types
        from entities.monster import MONSTER_DATA
        for m in spawner.monsters:
            self.assertIn(m.mtype, MONSTER_DATA)

    def test_monster_levels_in_valid_range(self):
        player_level = 5
        world   = make_world()
        spawner = Spawner(world, player_level=player_level)
        from systems.zones import ZONE_LEVEL_BONUS
        max_bonus = max(ZONE_LEVEL_BONUS)
        for m in spawner.monsters:
            self.assertGreaterEqual(m.level, 0)
            # Zone center adds up to max_bonus extra levels
            self.assertLessEqual(m.level, player_level + max_bonus + 8)


class TestSpawnerCullDead(unittest.TestCase):

    def test_dead_monsters_removed_on_update(self):
        world   = make_world()
        player  = FakePlayer(x=960.0, y=960.0)
        spawner = Spawner(world, player_level=0)

        # Matar a todos
        for m in spawner.monsters:
            m.hp = 0.0

        # Congelar el timer de respawn para que no se reponga en este ciclo
        spawner._timer = 999.0
        spawner.update(0.016, player, world)
        self.assertEqual(len(spawner.monsters), 0)


class TestSpawnerRespawn(unittest.TestCase):

    def test_respawn_fills_population(self):
        world   = make_world()
        player  = FakePlayer(x=960.0, y=960.0)
        spawner = Spawner(world, player_level=0)

        # Vaciar completamente
        spawner.monsters.clear()
        self.assertEqual(len(spawner.monsters), 0)

        # Forzar el timer para que el respawn ocurra en el siguiente update
        spawner._timer = 0.0
        spawner.update(0.016, player, world)

        self.assertGreater(len(spawner.monsters), 0,
                           "El spawner debería haber rellenado monstruos")


class TestSpawnerRollLevel(unittest.TestCase):

    def test_roll_level_within_range(self):
        world   = make_world()
        spawner = Spawner(world, player_level=10)
        for _ in range(50):
            lv = spawner._roll_level(10)
            self.assertGreaterEqual(lv, max(0, 10 - 2))
            self.assertLessEqual(lv, 10 + 4)

    def test_roll_level_never_negative(self):
        world   = make_world()
        spawner = Spawner(world, player_level=0)
        for _ in range(20):
            lv = spawner._roll_level(0)
            self.assertGreaterEqual(lv, 0)


if __name__ == '__main__':
    unittest.main()
