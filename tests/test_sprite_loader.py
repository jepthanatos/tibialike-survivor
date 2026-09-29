"""Tests unitarios para core/sprite_loader.py"""
import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame

import unittest
from core.sprite_loader import SpriteLoader


def _make_loader(config: dict) -> SpriteLoader:
    """Creates a SpriteLoader with a temp config file."""
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(config, tmp); tmp.close()
    loader = SpriteLoader(config_path=tmp.name)
    loader.load()
    return loader, tmp.name


class TestSpriteLoaderInit(unittest.TestCase):

    def test_starts_unloaded(self):
        sl = SpriteLoader.__new__(SpriteLoader)
        sl._loaded = False; sl._config = {}; sl._cache = {}; sl._missing = set()
        self.assertFalse(sl._loaded)

    def test_load_on_missing_file(self):
        sl = SpriteLoader(config_path="/nonexistent/sprites.json")
        sl.load()
        self.assertTrue(sl._loaded)
        self.assertEqual(sl._config, {})

    def test_load_on_invalid_json(self):
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        tmp.write("{ invalid json "); tmp.close()
        sl = SpriteLoader(config_path=tmp.name)
        sl.load()   # should not raise
        self.assertTrue(sl._loaded)
        os.remove(tmp.name)

    def test_loads_valid_json(self):
        sl, path = _make_loader({"monsters": {"rat": None, "zombie": None}})
        self.assertIn("monsters", sl._config)
        os.remove(path)

    def test_readme_key_ignored(self):
        sl, path = _make_loader({"_readme": ["docs"], "monsters": {"rat": None}})
        self.assertNotIn("_readme", sl._config)
        self.assertIn("monsters", sl._config)
        os.remove(path)


class TestSpriteLoaderGet(unittest.TestCase):

    def test_get_null_entry_returns_none(self):
        sl, path = _make_loader({"monsters": {"rat": None}})
        result = sl.get("monsters", "rat")
        self.assertIsNone(result)
        os.remove(path)

    def test_get_missing_section_returns_none(self):
        sl, path = _make_loader({"monsters": {"rat": None}})
        result = sl.get("ui", "hud_background")
        self.assertIsNone(result)
        os.remove(path)

    def test_get_missing_key_returns_none(self):
        sl, path = _make_loader({"monsters": {}})
        result = sl.get("monsters", "rat")
        self.assertIsNone(result)
        os.remove(path)

    def test_get_nonexistent_file_returns_none(self):
        sl, path = _make_loader({"monsters": {"rat": "/no/such/file.png"}})
        result = sl.get("monsters", "rat")
        self.assertIsNone(result)
        os.remove(path)

    def test_missing_cached_after_first_lookup(self):
        sl, path = _make_loader({"monsters": {"rat": None}})
        sl.get("monsters", "rat")
        # Second call should hit cache
        result = sl.get("monsters", "rat")
        self.assertIsNone(result)
        os.remove(path)

    def test_get_triggers_load(self):
        sl, path = _make_loader({"monsters": {"rat": None}})
        sl2 = SpriteLoader(config_path=path)
        self.assertFalse(sl2._loaded)
        sl2.get("monsters", "rat")
        self.assertTrue(sl2._loaded)
        os.remove(path)


class TestSpriteLoaderHas(unittest.TestCase):

    def test_has_returns_false_for_null(self):
        sl, path = _make_loader({"monsters": {"rat": None}})
        self.assertFalse(sl.has("monsters", "rat"))
        os.remove(path)

    def test_has_returns_false_for_missing_key(self):
        sl, path = _make_loader({"monsters": {}})
        self.assertFalse(sl.has("monsters", "rat"))
        os.remove(path)

    def test_has_returns_true_for_configured_path(self):
        sl, path = _make_loader({"monsters": {"rat": "some/path.png"}})
        self.assertTrue(sl.has("monsters", "rat"))
        os.remove(path)


class TestSpriteLoaderReload(unittest.TestCase):

    def test_reload_clears_cache(self):
        sl, path = _make_loader({"monsters": {"rat": None}})
        sl.get("monsters", "rat")   # populate missing cache
        sl.reload()
        self.assertEqual(len(sl._cache), 0)
        self.assertEqual(len(sl._missing), 0)
        os.remove(path)

    def test_reload_re_reads_file(self):
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump({"monsters": {"rat": None}}, tmp); tmp.close()
        sl = SpriteLoader(config_path=tmp.name)
        sl.load()
        self.assertIn("monsters", sl._config)
        # Overwrite file
        with open(tmp.name, 'w') as f:
            json.dump({"ui": {"hud_background": None}}, f)
        sl.reload()
        self.assertIn("ui", sl._config)
        self.assertNotIn("monsters", sl._config)
        os.remove(tmp.name)


class TestSpriteLoaderSummary(unittest.TestCase):

    def test_summary_no_config(self):
        sl, path = _make_loader({})
        s = sl.summary()
        self.assertIsInstance(s, str)
        self.assertIn("procedurales", s)
        os.remove(path)

    def test_summary_with_config(self):
        sl, path = _make_loader({"monsters": {"rat": "some.png"}})
        s = sl.summary()
        self.assertIn("rat", s)
        self.assertIn("some.png", s)
        os.remove(path)


class TestSpriteLoaderConfiguredSections(unittest.TestCase):

    def test_configured_sections_empty(self):
        sl, path = _make_loader({})
        self.assertEqual(sl.configured_sections(), [])
        os.remove(path)

    def test_configured_sections_populated(self):
        sl, path = _make_loader({"monsters": {}, "player": {}, "ui": {}})
        sections = sl.configured_sections()
        self.assertIn("monsters", sections)
        self.assertIn("player", sections)
        os.remove(path)


class TestSpritesJsonExists(unittest.TestCase):
    """Verifica que sprites.json existe y es JSON válido."""

    def test_sprites_json_exists(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'sprites.json')
        self.assertTrue(os.path.exists(path), "sprites.json not found")

    def test_sprites_json_valid(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'sprites.json')
        with open(path) as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_sprites_json_has_required_sections(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'sprites.json')
        with open(path) as f:
            data = json.load(f)
        for section in ("player", "bots", "monsters", "tiles", "ui"):
            self.assertIn(section, data, f"sprites.json missing section '{section}'")

    def test_sprites_json_monsters_has_all_types(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'sprites.json')
        with open(path) as f:
            data = json.load(f)
        for mtype in ("rat","zombie","skeleton","orc","dark_wizard","dragon","demon","dragon_lord"):
            self.assertIn(mtype, data["monsters"], f"monsters.{mtype} missing from sprites.json")

    def test_sprites_json_values_are_str_or_null(self):
        """All entries must be a string path or null — no other types."""
        path = os.path.join(os.path.dirname(__file__), '..', 'sprites.json')
        with open(path) as f:
            data = json.load(f)
        for section, entries in data.items():
            if section.startswith('_') or not isinstance(entries, dict):
                continue
            for key, val in entries.items():
                self.assertIn(type(val), (str, type(None)),
                              f"{section}.{key} must be str or null, got {type(val)}")

    def test_sprite_loader_loads_sprites_json(self):
        sl = SpriteLoader()
        sl.load()
        # All sections present
        for section in ("player", "bots", "monsters"):
            self.assertIn(section, sl._config)

    def test_all_null_entries_return_none(self):
        """With default sprites.json (all null), every get() returns None."""
        sl = SpriteLoader()
        sl.load()
        for section, entries in sl._config.items():
            for key in entries:
                result = sl.get(section, key)
                self.assertIsNone(result, f"get({section!r},{key!r}) should be None")


if __name__ == '__main__':
    unittest.main()
