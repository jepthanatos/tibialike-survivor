"""Tests unitarios para systems/storm.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import math
import unittest
from systems.storm import (
    Storm, PHASE_DATA,
    STATE_WAITING, STATE_CLOSING, STATE_DONE,
    CLOSE_WARNING_AT,
)

MAP_W = 4800.0
MAP_H = 4800.0
CX    = MAP_W / 2
CY    = MAP_H / 2


def make_storm():
    return Storm(MAP_W, MAP_H)


# ── Init ──────────────────────────────────────────────────────────────────────

class TestStormInit(unittest.TestCase):

    def test_starts_in_waiting_state(self):
        s = make_storm()
        self.assertEqual(s.state, STATE_WAITING)

    def test_initial_radius_covers_most_of_map(self):
        s = make_storm()
        half = min(MAP_W, MAP_H) / 2
        self.assertGreater(s.radius, half * 0.80)
        self.assertLessEqual(s.radius, half)

    def test_initial_phase_name_is_first(self):
        s = make_storm()
        self.assertEqual(s.phase_name, PHASE_DATA[0][0])

    def test_center_starts_at_map_center(self):
        s = make_storm()
        self.assertAlmostEqual(s.center_x, CX, delta=1)
        self.assertAlmostEqual(s.center_y, CY, delta=1)

    def test_initial_dps_is_first_phase(self):
        s = make_storm()
        self.assertAlmostEqual(s.current_dps, PHASE_DATA[0][4])

    def test_phase_reached_starts_at_zero(self):
        s = make_storm()
        self.assertEqual(s.phase_reached, 0)

    def test_timer_positive_on_init(self):
        s = make_storm()
        self.assertGreater(s.timer, 0)


# ── player_inside ─────────────────────────────────────────────────────────────

class TestPlayerInside(unittest.TestCase):

    def test_center_is_inside(self):
        s = make_storm()
        self.assertTrue(s.player_inside(CX, CY))

    def test_far_corner_is_outside(self):
        s = make_storm()
        self.assertFalse(s.player_inside(0.0, 0.0))

    def test_just_inside_edge(self):
        s = make_storm()
        r = s.radius
        # Un punto a r-1 del centro
        self.assertTrue(s.player_inside(CX + r - 1, CY))

    def test_just_outside_edge(self):
        s = make_storm()
        r = s.radius
        self.assertFalse(s.player_inside(CX + r + 1, CY))

    def test_diagnonal_inside(self):
        s = make_storm()
        r = s.radius * 0.7
        px = CX + r * math.cos(math.radians(45))
        py = CY + r * math.sin(math.radians(45))
        self.assertTrue(s.player_inside(px, py))


# ── distance_outside ──────────────────────────────────────────────────────────

class TestDistanceOutside(unittest.TestCase):

    def test_inside_returns_zero(self):
        s = make_storm()
        self.assertEqual(s.distance_outside(CX, CY), 0.0)

    def test_outside_returns_positive(self):
        s = make_storm()
        self.assertGreater(s.distance_outside(0.0, 0.0), 0.0)

    def test_distance_matches_geometry(self):
        s = make_storm()
        far = CX + s.radius + 200.0
        expected = abs(math.hypot(far - s.center_x, CY - s.center_y) - s.radius)
        result   = s.distance_outside(far, CY)
        self.assertAlmostEqual(result, expected, delta=1.0)


# ── Damage (player outside) ────────────────────────────────────────────────────

class TestStormDamage(unittest.TestCase):

    def test_no_damage_when_inside(self):
        s = make_storm()
        dmg = s.update(0.5, CX, CY)
        self.assertEqual(dmg, 0.0)

    def test_damage_when_outside(self):
        s = make_storm()
        total = 0.0
        # Simular 5 segundos fuera de la tormenta
        for _ in range(100):
            total += s.update(0.05, 0.0, 0.0)
        self.assertGreater(total, 0.0)

    def test_damage_resets_accumulator_when_inside(self):
        s = make_storm()
        s.update(0.1, 0.0, 0.0)  # acumular un poco
        dmg = s.update(0.1, CX, CY)   # entrar a la zona segura
        self.assertEqual(dmg, 0.0)
        # El siguiente frame fuera no debe arrastrar daño anterior
        # (acumulador se reinicia)
        dmg2 = s.update(0.001, 0.0, 0.0)
        self.assertEqual(dmg2, 0.0)   # demasiado poco para disparar

    def test_damage_increases_with_later_phases(self):
        """DPS de fases posteriores debe ser mayor."""
        s = make_storm()
        dps_first = s.current_dps
        # Avanzar a la última fase a la fuerza
        s._phase_idx = len(PHASE_DATA) - 1
        s._state     = STATE_DONE
        dps_last     = s.current_dps
        self.assertGreater(dps_last, dps_first)

    def test_done_state_still_deals_damage(self):
        s = make_storm()
        s._state = STATE_DONE
        total = sum(s.update(0.05, 0.0, 0.0) for _ in range(50))
        self.assertGreater(total, 0.0)


# ── State transitions ─────────────────────────────────────────────────────────

class TestStormStateTransitions(unittest.TestCase):

    def _fast_forward_waiting(self, s):
        """Avanza la tormenta hasta que el estado cambia de WAITING."""
        for _ in range(100_000):   # up to 10000s at dt=0.1
            s.update(0.1, CX, CY)
            if s.state != STATE_WAITING:
                return
        raise AssertionError("La tormenta no salió de WAITING en tiempo razonable")

    def test_transitions_to_closing(self):
        s = make_storm()
        self._fast_forward_waiting(s)
        self.assertEqual(s.state, STATE_CLOSING)

    def test_radius_decreases_while_closing(self):
        s = make_storm()
        self._fast_forward_waiting(s)
        r_before = s.radius
        for _ in range(200):
            s.update(0.1, CX, CY)
        self.assertLess(s.radius, r_before)

    def test_radius_never_below_target(self):
        s = make_storm()
        # Correr todas las fases
        for _ in range(20000):
            s.update(0.1, CX, CY)
            if s.state == STATE_DONE:
                break
        # Radio mínimo: fracción de la última fase
        min_frac = PHASE_DATA[-1][3]
        min_r    = s._base_radius * min_frac
        self.assertGreaterEqual(s.radius, min_r * 0.99)

    def test_transitions_back_to_waiting_after_close(self):
        s = make_storm()
        self._fast_forward_waiting(s)
        # Avanzar el cierre completo
        for _ in range(10000):
            s.update(0.1, CX, CY)
            if s.state == STATE_WAITING:
                return
            if s.state == STATE_DONE:
                return  # aceptable si pasamos por todas las fases
        self.assertIn(s.state, (STATE_WAITING, STATE_DONE))

    def test_eventually_reaches_done(self):
        s = make_storm()
        for _ in range(50000):
            s.update(0.5, CX, CY)
            if s.state == STATE_DONE:
                return
        self.fail("La tormenta no llegó a DONE en tiempo razonable")

    def test_phase_reached_increments(self):
        s = make_storm()
        self._fast_forward_waiting(s)
        for _ in range(20000):  # up to 2000s — covers all phase wait times
            s.update(0.1, CX, CY)
            if s.state == STATE_WAITING and s._phase_idx > 0:
                break
        self.assertGreater(s.phase_reached, 0)


# ── HUD properties ────────────────────────────────────────────────────────────

class TestStormProperties(unittest.TestCase):

    def test_phase_number_starts_at_one(self):
        s = make_storm()
        self.assertEqual(s.phase_number, 1)

    def test_timer_non_negative(self):
        s = make_storm()
        for _ in range(100):
            s.update(0.05, CX, CY)
            self.assertGreaterEqual(s.timer, 0.0)

    def test_closing_progress_is_zero_when_waiting(self):
        s = make_storm()
        self.assertAlmostEqual(s.closing_progress, 0.0)

    def test_closing_progress_increases_while_closing(self):
        s = make_storm()
        # Force into closing
        s._start_closing()
        prog_before = s.closing_progress
        for _ in range(10):
            s.update(0.5, CX, CY)
        self.assertGreater(s.closing_progress, prog_before)

    def test_closing_progress_between_0_and_1(self):
        s = make_storm()
        s._start_closing()
        for _ in range(500):
            s.update(0.1, CX, CY)
            p = s.closing_progress
            self.assertGreaterEqual(p, 0.0)
            self.assertLessEqual(p, 1.0)
            if s.state != STATE_CLOSING:
                break

    def test_next_radius_less_than_current_radius(self):
        s = make_storm()
        self.assertLess(s.next_radius, s.radius)

    def test_phase_name_changes_after_phase_advance(self):
        s = make_storm()
        first_name = s.phase_name
        # Avanzar dos fases manualmente
        s._phase_idx = 1
        s._state     = STATE_WAITING
        s._timer     = PHASE_DATA[1][1]
        second_name  = s.phase_name
        self.assertNotEqual(first_name, second_name)

    def test_done_state_phase_name(self):
        s = make_storm()
        s._state = STATE_DONE
        self.assertIn("COLAPSO", s.phase_name.upper())

    def test_close_warning_triggers_near_threshold(self):
        s = make_storm()
        s._timer = CLOSE_WARNING_AT - 0.5
        self.assertTrue(s.close_warning)

    def test_close_warning_false_early_in_wait(self):
        s = make_storm()
        s._timer = CLOSE_WARNING_AT + 10
        self.assertFalse(s.close_warning)

    def test_close_warning_false_during_closing(self):
        s = make_storm()
        s._state = STATE_CLOSING
        s._timer = 1.0
        self.assertFalse(s.close_warning)


# ── PHASE_DATA sanity ─────────────────────────────────────────────────────────

class TestPhaseDataIntegrity(unittest.TestCase):

    def test_all_phases_have_five_fields(self):
        for i, pd in enumerate(PHASE_DATA):
            self.assertEqual(len(pd), 5, f"Phase {i} no tiene 5 campos")

    def test_wait_and_close_times_positive(self):
        for pd in PHASE_DATA:
            self.assertGreater(pd[1], 0, "wait_s debe ser > 0")
            self.assertGreater(pd[2], 0, "close_s debe ser > 0")

    def test_target_fractions_between_0_and_1(self):
        for pd in PHASE_DATA:
            self.assertGreater(pd[3], 0.0)
            self.assertLess(pd[3], 1.0)

    def test_target_fractions_decrease_each_phase(self):
        fracs = [pd[3] for pd in PHASE_DATA]
        for i in range(len(fracs) - 1):
            self.assertGreater(fracs[i], fracs[i+1],
                               "Cada fase debe tener radio objetivo menor")

    def test_dps_increases_each_phase(self):
        dps_vals = [pd[4] for pd in PHASE_DATA]
        for i in range(len(dps_vals) - 1):
            self.assertLess(dps_vals[i], dps_vals[i+1],
                            "El DPS debe crecer en cada fase")

    def test_dps_values_positive(self):
        for pd in PHASE_DATA:
            self.assertGreater(pd[4], 0)


# ── Repr ──────────────────────────────────────────────────────────────────────

class TestStormRepr(unittest.TestCase):

    def test_repr_does_not_crash(self):
        s = make_storm()
        r = repr(s)
        self.assertIsInstance(r, str)
        self.assertIn("Storm", r)


if __name__ == '__main__':
    unittest.main()
