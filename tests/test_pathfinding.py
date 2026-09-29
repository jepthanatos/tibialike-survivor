"""Tests unitarios para systems/pathfinding.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from systems.pathfinding import astar
from tests.fake_world import FakeWorld


class TestAstarBasic(unittest.TestCase):

    def setUp(self):
        self.world = FakeWorld(width=20, height=20, tile_size=32)

    def test_same_start_and_goal_returns_empty(self):
        result = astar(self.world, 5, 5, 5, 5)
        self.assertEqual(result, [])

    def test_horizontal_path(self):
        path = astar(self.world, 0, 0, 4, 0)
        self.assertGreater(len(path), 0)
        self.assertEqual(path[-1], (4, 0))

    def test_vertical_path(self):
        path = astar(self.world, 0, 0, 0, 5)
        self.assertGreater(len(path), 0)
        self.assertEqual(path[-1], (0, 5))

    def test_diagonal_path_length(self):
        # En 4-dir A* una diagonal de (0,0)→(3,3) cuesta 6 pasos
        path = astar(self.world, 0, 0, 3, 3)
        self.assertGreaterEqual(len(path), 6)

    def test_path_excludes_start_tile(self):
        path = astar(self.world, 2, 2, 5, 2)
        if path:
            self.assertNotEqual(path[0], (2, 2))

    def test_path_ends_at_goal(self):
        path = astar(self.world, 1, 1, 8, 8)
        self.assertEqual(path[-1], (8, 8))


class TestAstarObstacles(unittest.TestCase):

    def test_detours_around_wall(self):
        # Pared vertical en col=5, filas 0-8 → debe rodearla
        impassable = {(5, r) for r in range(9)}
        world = FakeWorld(width=15, height=15, impassable=impassable)
        path = astar(world, 3, 4, 8, 4)
        # El camino debe existir y evitar la pared
        self.assertGreater(len(path), 0)
        for col, row in path:
            self.assertFalse((col, row) in impassable,
                             f"El path pasa por tile impassable {(col, row)}")

    def test_goal_impassable_finds_neighbour(self):
        impassable = {(5, 5)}
        world = FakeWorld(width=15, height=15, impassable=impassable)
        path = astar(world, 0, 0, 5, 5)
        # Debe encontrar un camino al vecino más cercano de (5,5)
        self.assertGreater(len(path), 0)
        gc, gr = path[-1]
        # El destino final debe ser adyacente al tile impassable original
        self.assertLessEqual(abs(gc - 5) + abs(gr - 5), 1)

    def test_completely_blocked_goal_returns_empty(self):
        # Goal rodeado de tiles impassable en todos los lados
        impassable = {(5, 5), (4, 5), (6, 5), (5, 4), (5, 6)}
        world = FakeWorld(width=10, height=10, impassable=impassable)
        path = astar(world, 0, 0, 5, 5)
        self.assertEqual(path, [])

    def test_max_nodes_limit_returns_empty_on_large_maze(self):
        # Un laberinto tan grande que el límite de nodos se agota
        impassable = {(1, r) for r in range(19)}   # muro casi completo
        world = FakeWorld(width=20, height=20, impassable=impassable)
        # Start izquierda, goal derecha: inalcanzable con max_nodes=5
        path = astar(world, 0, 0, 15, 15, max_nodes=5)
        self.assertEqual(path, [])

    def test_out_of_bounds_start_returns_empty(self):
        world = FakeWorld(width=10, height=10)
        path = astar(world, -1, 0, 5, 5)
        # El start es impassable → sin camino
        self.assertEqual(path, [])


if __name__ == '__main__':
    unittest.main()
