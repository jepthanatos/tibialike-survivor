"""Tests unitarios para core/camera.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from core.camera import Camera


class TestCameraInit(unittest.TestCase):

    def test_initial_offsets_are_zero(self):
        cam = Camera(800, 600, 3000, 3000)
        self.assertEqual(cam.offset_x, 0.0)
        self.assertEqual(cam.offset_y, 0.0)

    def test_stores_dimensions(self):
        cam = Camera(1280, 720, 5000, 5000)
        self.assertEqual(cam.view_w, 1280)
        self.assertEqual(cam.view_h, 720)
        self.assertEqual(cam.world_w, 5000)
        self.assertEqual(cam.world_h, 5000)


class TestCameraUpdate(unittest.TestCase):

    def setUp(self):
        self.cam = Camera(800, 600, 3000, 3000)

    def test_centers_on_target(self):
        self.cam.update(1500, 1500)
        self.assertAlmostEqual(self.cam.offset_x, 1500 - 400)
        self.assertAlmostEqual(self.cam.offset_y, 1500 - 300)

    def test_clamps_to_top_left(self):
        self.cam.update(0, 0)
        self.assertEqual(self.cam.offset_x, 0.0)
        self.assertEqual(self.cam.offset_y, 0.0)

    def test_clamps_to_bottom_right(self):
        self.cam.update(99999, 99999)
        self.assertEqual(self.cam.offset_x, 3000 - 800)
        self.assertEqual(self.cam.offset_y, 3000 - 600)

    def test_partial_clamp_x_only(self):
        self.cam.update(0, 1500)
        self.assertEqual(self.cam.offset_x, 0.0)
        self.assertAlmostEqual(self.cam.offset_y, 1500 - 300)


class TestCameraCoordConversions(unittest.TestCase):

    def setUp(self):
        self.cam = Camera(800, 600, 3000, 3000)
        self.cam.update(1000, 1000)  # offset = (600, 700)

    def test_world_to_screen(self):
        sx, sy = self.cam.world_to_screen(1000, 1000)
        # offset_x = 1000 - 400 = 600 → sx = 1000 - 600 = 400
        self.assertAlmostEqual(sx, 400.0)
        self.assertAlmostEqual(sy, 300.0)

    def test_screen_to_world_roundtrip(self):
        wx, wy = 1234.5, 678.9
        sx, sy = self.cam.world_to_screen(wx, wy)
        rx, ry = self.cam.screen_to_world(sx, sy)
        self.assertAlmostEqual(rx, wx, places=5)
        self.assertAlmostEqual(ry, wy, places=5)

    def test_world_to_screen_at_origin(self):
        sx, sy = self.cam.world_to_screen(0, 0)
        self.assertAlmostEqual(sx, -self.cam.offset_x)
        self.assertAlmostEqual(sy, -self.cam.offset_y)


class TestCameraIsVisible(unittest.TestCase):

    def setUp(self):
        self.cam = Camera(800, 600, 3000, 3000)
        self.cam.update(500, 500)   # offset ≈ (100, 200)

    def test_center_is_visible(self):
        self.assertTrue(self.cam.is_visible(500, 500))

    def test_far_away_not_visible(self):
        self.assertFalse(self.cam.is_visible(5000, 5000))

    def test_margin_respected(self):
        # Un punto 50 px fuera del borde izquierdo visible con margin=64
        sx, _ = self.cam.world_to_screen(self.cam.offset_x - 50, 500)
        # sx debería ser -50, que está dentro del margen 64
        self.assertTrue(self.cam.is_visible(self.cam.offset_x - 50, 500, margin=64))


if __name__ == '__main__':
    unittest.main()


# ── Lerp-specific tests ────────────────────────────────────────────────────────
import math as _math
from core.camera import LERP_SPEED

class TestCameraLerp(unittest.TestCase):

    def _cam(self):
        return Camera(1280, 720, 4800, 4800)

    def test_first_update_is_instant(self):
        cam = self._cam()
        cam.update(2400.0, 2400.0, dt=0.016)
        self.assertAlmostEqual(cam.offset_x, 2400.0 - 640, places=3)
        self.assertAlmostEqual(cam.offset_y, 2400.0 - 360, places=3)

    def test_second_update_lerps_not_jumps(self):
        cam = self._cam()
        cam.update(2400.0, 2400.0, dt=0.016)
        before = cam.offset_x
        cam.update(2400.0 + 32, 2400.0, dt=0.016)
        moved = cam.offset_x - before
        self.assertGreater(moved, 0.0)
        self.assertLess(moved, 32.0)

    def test_lerp_converges_to_target(self):
        cam = self._cam()
        cam.update(2400.0, 2400.0, dt=0.016)
        target_x = (2400.0 + 64) - 640
        for _ in range(300):
            cam.update(2400.0 + 64, 2400.0, dt=0.016)
        self.assertAlmostEqual(cam.offset_x, target_x, delta=0.01)

    def test_snap_teleports_instantly(self):
        cam = self._cam()
        cam.snap(2400.0, 2400.0)
        self.assertAlmostEqual(cam.offset_x, 2400.0 - 640, places=3)
        self.assertAlmostEqual(cam.offset_y, 2400.0 - 360, places=3)

    def test_snap_then_lerp(self):
        cam = self._cam()
        cam.snap(2400.0, 2400.0)
        before = cam.offset_x
        cam.update(2400.0 + 32, 2400.0, dt=0.016)
        moved = cam.offset_x - before
        self.assertGreater(moved, 0.0)
        self.assertLess(moved, 32.0)

    def test_dt_zero_no_movement_after_init(self):
        cam = self._cam()
        cam.update(2400.0, 2400.0, dt=0.016)
        before = cam.offset_x
        cam.update(2400.0 + 32, 2400.0, dt=0.0)
        self.assertAlmostEqual(cam.offset_x, before, places=5)

    def test_lerp_factor_at_60fps_is_reasonable(self):
        factor = 1.0 - _math.exp(-LERP_SPEED * 0.016)
        self.assertGreater(factor, 0.10)
        self.assertLess(factor, 0.30)

    def test_fast_dt_moves_more_than_slow_dt(self):
        cam_fast = self._cam(); cam_fast.snap(2400.0, 2400.0)
        cam_slow = self._cam(); cam_slow.snap(2400.0, 2400.0)
        cam_fast.update(2400.0 + 32, 2400.0, dt=0.1)
        cam_slow.update(2400.0 + 32, 2400.0, dt=0.016)
        self.assertGreater(cam_fast.offset_x, cam_slow.offset_x)

    def test_clamp_at_origin(self):
        cam = self._cam()
        for _ in range(20):
            cam.update(0.0, 0.0, dt=0.016)
        self.assertGreaterEqual(cam.offset_x, 0.0)
        self.assertGreaterEqual(cam.offset_y, 0.0)

    def test_clamp_at_world_edge(self):
        cam = self._cam()
        for _ in range(20):
            cam.update(99999.0, 99999.0, dt=0.016)
        self.assertLessEqual(cam.offset_x, 4800.0 - 1280)
        self.assertLessEqual(cam.offset_y, 4800.0 - 720)

    def test_world_to_screen_correct_after_convergence(self):
        cam = self._cam()
        cam.update(2400.0, 2400.0, dt=0.016)
        for _ in range(60):
            cam.update(2400.0, 2400.0, dt=0.016)
        sx, sy = cam.world_to_screen(2400.0, 2400.0)
        self.assertAlmostEqual(sx, 640, delta=0.1)
        self.assertAlmostEqual(sy, 360, delta=0.1)
