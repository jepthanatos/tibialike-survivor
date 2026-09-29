"""Tests unitarios para core/session.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import tempfile
import unittest

# Parchear SAVE_FILE antes de importar Session
import core.session as session_module


class TestSessionFresh(unittest.TestCase):
    """Session sin fichero previo."""

    def setUp(self):
        self._tmp  = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self._path = self._tmp.name
        self._tmp.close()
        os.remove(self._path)                   # que no exista
        session_module.SAVE_FILE = self._path
        self.session = session_module.Session()

    def tearDown(self):
        if os.path.exists(self._path):
            os.remove(self._path)

    def test_initial_level_is_zero(self):
        self.assertEqual(self.session.persistent_level, 0)

    def test_initial_best_time_is_zero(self):
        self.assertEqual(self.session.best_time, 0.0)

    def test_initial_runs_is_zero(self):
        self.assertEqual(self.session.total_runs, 0)


class TestSessionSave(unittest.TestCase):
    """Lógica de actualización al guardar."""

    def setUp(self):
        self._tmp  = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self._path = self._tmp.name
        self._tmp.close()
        os.remove(self._path)
        session_module.SAVE_FILE = self._path
        self.session = session_module.Session()

    def tearDown(self):
        if os.path.exists(self._path):
            os.remove(self._path)

    def test_save_increments_run_count(self):
        self.session.save(0, 10.0)
        self.assertEqual(self.session.total_runs, 1)
        self.session.save(0, 5.0)
        self.assertEqual(self.session.total_runs, 2)

    def test_save_updates_persistent_level_when_higher(self):
        self.session.save(10, 100.0)
        self.assertEqual(self.session.persistent_level, 10)

    def test_save_keeps_persistent_level_when_lower(self):
        self.session.save(15, 100.0)
        self.session.save(5, 50.0)
        self.assertEqual(self.session.persistent_level, 15)

    def test_save_updates_best_time_when_higher(self):
        self.session.save(0, 300.0)
        self.assertAlmostEqual(self.session.best_time, 300.0, places=1)

    def test_save_keeps_best_time_when_lower(self):
        self.session.save(0, 500.0)
        self.session.save(0, 200.0)
        self.assertAlmostEqual(self.session.best_time, 500.0, places=1)

    def test_save_writes_json_file(self):
        self.session.save(7, 120.0)
        self.assertTrue(os.path.exists(self._path))
        with open(self._path) as f:
            data = json.load(f)
        self.assertEqual(data['persistent_level'], 7)
        self.assertEqual(data['total_runs'], 1)

    def test_save_then_reload_persists_data(self):
        self.session.save(12, 250.0)
        # Nueva instancia cargando el mismo fichero
        session2 = session_module.Session()
        self.assertEqual(session2.persistent_level, 12)
        self.assertEqual(session2.total_runs, 1)
        self.assertAlmostEqual(session2.best_time, 250.0, places=1)


class TestSessionCorruptFile(unittest.TestCase):
    """Session con fichero corrupto: debe arrancar con valores por defecto."""

    def setUp(self):
        self._tmp  = tempfile.NamedTemporaryFile(suffix='.json',
                                                  delete=False, mode='w')
        self._path = self._tmp.name
        self._tmp.write("NOT VALID JSON !!!")
        self._tmp.close()
        session_module.SAVE_FILE = self._path
        self.session = session_module.Session()

    def tearDown(self):
        if os.path.exists(self._path):
            os.remove(self._path)

    def test_corrupt_file_gives_defaults(self):
        self.assertEqual(self.session.persistent_level, 0)
        self.assertEqual(self.session.total_runs, 0)


if __name__ == '__main__':
    unittest.main()


class TestSessionStormPhase(unittest.TestCase):
    """Verifica que max_storm_phase se guarda y carga correctamente."""

    def setUp(self):
        self._tmp  = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self._path = self._tmp.name
        self._tmp.close()
        os.remove(self._path)
        session_module.SAVE_FILE = self._path
        self.session = session_module.Session()

    def tearDown(self):
        if os.path.exists(self._path):
            os.remove(self._path)

    def test_storm_phase_starts_at_zero(self):
        self.assertEqual(self.session.max_storm_phase, 0)

    def test_save_updates_storm_phase(self):
        self.session.save(0, 100.0, storm_phase=3)
        self.assertEqual(self.session.max_storm_phase, 3)

    def test_save_keeps_higher_storm_phase(self):
        self.session.save(0, 100.0, storm_phase=4)
        self.session.save(0, 50.0,  storm_phase=2)
        self.assertEqual(self.session.max_storm_phase, 4)

    def test_save_and_reload_storm_phase(self):
        self.session.save(5, 200.0, storm_phase=3)
        session2 = session_module.Session()
        self.assertEqual(session2.max_storm_phase, 3)

    def test_save_without_storm_phase_defaults_to_zero(self):
        self.session.save(0, 10.0)   # sin storm_phase
        self.assertEqual(self.session.max_storm_phase, 0)


class TestSessionSpellMemory(unittest.TestCase):
    """Verifica que spell_memory se persiste correctamente."""

    def setUp(self):
        self._tmp  = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self._path = self._tmp.name
        self._tmp.close()
        os.remove(self._path)
        session_module.SAVE_FILE = self._path
        self.session = session_module.Session()

    def tearDown(self):
        if os.path.exists(self._path):
            os.remove(self._path)

    def test_spell_memory_data_empty_initially(self):
        self.assertEqual(self.session.spell_memory_data, {})

    def test_save_persists_spell_memory(self):
        from systems.spells import SpellMemory
        sm = SpellMemory(known=["exevo vis", "exevo flam"])
        sm.magic_level = 5
        self.session.save(3, 100.0, spell_memory=sm)
        session2 = session_module.Session()
        self.assertEqual(session2.spell_memory_data.get("magic_level"), 5)
        self.assertIn("exevo vis", session2.spell_memory_data.get("known_spells", []))

    def test_save_without_spell_memory_keeps_existing(self):
        from systems.spells import SpellMemory
        sm = SpellMemory(known=["exevo vis"])
        self.session.save(0, 50.0, spell_memory=sm)
        self.session.save(1, 80.0)   # no spell_memory arg
        # spell_memory_data should still have the previously saved value
        self.assertIn("known_spells", self.session.spell_memory_data)
