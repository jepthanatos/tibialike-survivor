#!/usr/bin/env python3
"""
run_tests.py
Ejecuta todos los tests unitarios del proyecto.
Uso: python run_tests.py
"""
import sys
import os
import unittest

# Asegurar que el root del proyecto esté en el path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# El mock de pygame DEBE instalarse antes de descubrir/importar tests
import tests.mock_pygame  # noqa: E402

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite  = loader.discover(
        start_dir=os.path.join(ROOT, 'tests'),
        pattern='test_*.py',
        top_level_dir=ROOT,
    )

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    # Exit code 1 si hay fallos (útil para CI)
    sys.exit(0 if result.wasSuccessful() else 1)
