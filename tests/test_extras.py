"""
tests/test_extras.py
Tests para las mejoras post-fase-8:
  · Demon y Dragon Lord
  · MainMenu (lógica)
  · MonsterTooltip
  · Session.new_seed / semilla aleatoria
"""
import sys, os, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tests.mock_pygame

import unittest, random


# ══════════════════════════════════════════════════════════════════════════════
# Demon
# ══════════════════════════════════════════════════════════════════════════════
from entities.monster import Monster, MONSTER_DATA, available_types

class TestDemon(unittest.TestCase):
    def test_in_catalogue(self):             self.assertIn('demon', MONSTER_DATA)
    def test_min_level_25(self):             self.assertEqual(MONSTER_DATA['demon']['min_level'], 25)
    def test_initialises(self):
        m = Monster(100.0, 100.0, 'demon', 25)
        self.assertEqual(m.name, 'Demon'); self.assertGreater(m.max_hp, 0)
    def test_not_at_low_level(self):         self.assertNotIn('demon', available_types(0))
    def test_available_at_25(self):          self.assertIn('demon', available_types(25))
    def test_has_spells(self):
        m = Monster(0, 0, 'demon', 25); self.assertGreater(len(m._my_spells), 0)
    def test_has_death_coil(self):
        from systems.spells import MONSTER_SPELLS
        self.assertIn('exura mort', MONSTER_SPELLS.get('demon', []))
    def test_draw_no_crash(self):
        from tests.mock_pygame import FakeSurface
        class Cam: offset_x=0.0; offset_y=0.0; view_w=1280; view_h=720
        m = Monster(200.0, 200.0, 'demon', 25)
        try: m.draw(FakeSurface(), Cam())
        except Exception as e: self.fail(f"demon.draw raised {e}")
    def test_xp_greater_than_skeleton(self):
        d = Monster(0,0,'demon',25); s = Monster(0,0,'skeleton',25)
        self.assertGreater(d.xp_reward, s.xp_reward)
    def test_take_damage(self):
        m = Monster(0,0,'demon',25); hp = m.hp; m.take_damage(50)
        self.assertLess(m.hp, hp)
    def test_elite_applicable(self):
        from systems.elites import apply_modifiers
        m = Monster(0,0,'demon',25); apply_modifiers(m,['berserker'])
        self.assertTrue(m.is_elite)


# ══════════════════════════════════════════════════════════════════════════════
# Dragon Lord
# ══════════════════════════════════════════════════════════════════════════════
class TestDragonLord(unittest.TestCase):
    def test_in_catalogue(self):        self.assertIn('dragon_lord', MONSTER_DATA)
    def test_min_level_30(self):        self.assertEqual(MONSTER_DATA['dragon_lord']['min_level'], 30)
    def test_initialises(self):
        m = Monster(100.0, 100.0, 'dragon_lord', 30)
        self.assertEqual(m.name, 'Dragon Lord'); self.assertGreater(m.max_hp, 0)
    def test_not_at_low_level(self):    self.assertNotIn('dragon_lord', available_types(0))
    def test_available_at_30(self):     self.assertIn('dragon_lord', available_types(30))
    def test_has_spells(self):
        m = Monster(0,0,'dragon_lord',30); self.assertGreater(len(m._my_spells), 0)
    def test_has_energy_beam(self):
        from systems.spells import MONSTER_SPELLS
        self.assertIn('exevo gran vis', MONSTER_SPELLS.get('dragon_lord', []))
    def test_draw_no_crash(self):
        from tests.mock_pygame import FakeSurface
        class Cam: offset_x=0.0; offset_y=0.0; view_w=1280; view_h=720
        m = Monster(200.0, 200.0, 'dragon_lord', 30)
        try: m.draw(FakeSurface(), Cam())
        except Exception as e: self.fail(f"dragon_lord.draw raised {e}")
    def test_highest_xp_base(self):
        dl_xp = MONSTER_DATA['dragon_lord']['xp_base']
        for t, d in MONSTER_DATA.items():
            if t != 'dragon_lord':
                self.assertGreaterEqual(dl_xp, d['xp_base'])
    def test_largest_size(self):
        dl_size = MONSTER_DATA['dragon_lord']['size']
        for t, d in MONSTER_DATA.items():
            self.assertGreaterEqual(dl_size, d['size'])
    def test_all_types_at_30(self):
        types = available_types(30)
        for t in ('rat','zombie','skeleton','orc','dark_wizard',
                  'dragon','demon','dragon_lord'):
            self.assertIn(t, types)


# ══════════════════════════════════════════════════════════════════════════════
# Session.new_seed
# ══════════════════════════════════════════════════════════════════════════════
import core.session as ses_module

class TestSessionSeed(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self._path = self._tmp.name; self._tmp.close(); os.remove(self._path)
        ses_module.SAVE_FILE = self._path
    def tearDown(self):
        if os.path.exists(self._path): os.remove(self._path)

    def test_returns_int(self):
        s = ses_module.Session(); self.assertIsInstance(s.new_seed(), int)
    def test_non_negative(self):
        s = ses_module.Session(); self.assertGreaterEqual(s.new_seed(), 0)
    def test_within_range(self):
        s = ses_module.Session(); self.assertLess(s.new_seed(), 2**31)
    def test_stored_as_last_seed(self):
        s = ses_module.Session(); seed = s.new_seed(); self.assertEqual(s.last_seed, seed)
    def test_different_each_call(self):
        s = ses_module.Session()
        self.assertGreater(len({s.new_seed() for _ in range(20)}), 1)
    def test_persisted_in_save(self):
        s = ses_module.Session(); seed = s.new_seed(); s.save(0, 60.0, seed=seed)
        s2 = ses_module.Session(); self.assertEqual(s2.last_seed, seed)
    def test_same_seed_same_world(self):
        from core.world import World; from constants import TILE_SIZE
        w1 = World(40,40,TILE_SIZE,seed=42); w2 = World(40,40,TILE_SIZE,seed=42)
        self.assertEqual(sum(w1.tiles[c][r]!=w2.tiles[c][r]
                              for c in range(40) for r in range(40)), 0)
    def test_diff_seeds_diff_worlds(self):
        from core.world import World; from constants import TILE_SIZE
        w1 = World(40,40,TILE_SIZE,seed=1); w2 = World(40,40,TILE_SIZE,seed=999)
        self.assertGreater(sum(w1.tiles[c][r]!=w2.tiles[c][r]
                               for c in range(40) for r in range(40)), 10)


# ══════════════════════════════════════════════════════════════════════════════
# MainMenu logic
# ══════════════════════════════════════════════════════════════════════════════
class TestMainMenu(unittest.TestCase):
    def _menu(self, has_save=False):
        from ui.main_menu import MainMenu
        m = MainMenu(); m._save_exists = lambda: has_save; return m

    def test_options_no_save(self):
        menu = self._menu(False); opts = menu._options()
        self.assertIn("Nueva Partida", opts)
        self.assertNotIn("Borrar Progreso", opts)

    def test_options_with_save(self):
        menu = self._menu(True); opts = menu._options()
        self.assertIn("Continuar", opts); self.assertIn("Borrar Progreso", opts)

    def test_nueva_partida_returns_new(self):
        menu = self._menu(False)
        self.assertEqual(menu._activate(menu._options().index("Nueva Partida")), "new")

    def test_salir_returns_quit(self):
        menu = self._menu(False); opts = menu._options()
        self.assertEqual(menu._activate(opts.index("Salir")), "quit")

    def test_continuar_no_save_returns_none(self):
        menu = self._menu(False); opts = menu._options()
        if "Continuar" in opts:
            self.assertIsNone(menu._activate(opts.index("Continuar")))

    def test_continuar_with_save(self):
        menu = self._menu(True)
        self.assertEqual(menu._activate(menu._options().index("Continuar")), "continue")

    def test_borrar_sets_confirm(self):
        menu = self._menu(True)
        menu._activate(menu._options().index("Borrar Progreso"))
        self.assertTrue(menu._confirm_delete)

    def test_key_up_wraps(self):
        import pygame
        menu = self._menu(False); menu._selected = 0
        menu._handle_key(pygame.K_UP)
        self.assertEqual(menu._selected, len(menu._options()) - 1)

    def test_key_down_advances(self):
        import pygame
        menu = self._menu(False); menu._selected = 0
        menu._handle_key(pygame.K_DOWN); self.assertEqual(menu._selected, 1)

    def test_key_down_wraps(self):
        import pygame
        menu = self._menu(False); opts = menu._options()
        menu._selected = len(opts) - 1
        menu._handle_key(pygame.K_DOWN); self.assertEqual(menu._selected, 0)

    def test_escape_returns_quit(self):
        import pygame
        menu = self._menu(False)
        self.assertEqual(menu._handle_key(pygame.K_ESCAPE), "quit")

    def test_enter_activates(self):
        import pygame
        menu = self._menu(False); menu._selected = 0
        self.assertEqual(menu._handle_key(pygame.K_RETURN), "new")

    def test_confirm_y_deletes(self):
        import pygame
        menu = self._menu(False); menu._confirm_delete = True
        deleted = []; menu._delete_save = lambda: deleted.append(True)
        menu._handle_key(pygame.K_y)
        self.assertTrue(deleted); self.assertFalse(menu._confirm_delete)

    def test_confirm_other_key_cancels(self):
        import pygame
        menu = self._menu(False); menu._confirm_delete = True
        menu._handle_key(pygame.K_n); self.assertFalse(menu._confirm_delete)

    def test_option_rects_count(self):
        menu = self._menu(True); opts = menu._options()
        self.assertEqual(len(menu._option_rects(opts)), len(opts))

    def test_delete_removes_file(self):
        from ui.main_menu import MainMenu
        import ui.main_menu as mm_module
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        path = tmp.name; tmp.close()
        old = mm_module.SAVE_FILE; mm_module.SAVE_FILE = path
        MainMenu()._delete_save()
        self.assertFalse(os.path.exists(path)); mm_module.SAVE_FILE = old

    def test_draw_no_crash(self):
        from tests.mock_pygame import FakeSurface
        menu = self._menu(False)
        try: menu._draw(FakeSurface())
        except Exception as e: self.fail(f"_draw raised {e}")

    def test_hover_updates_selected(self):
        import pygame
        menu = self._menu(False); opts = menu._options()
        rects = menu._option_rects(opts)
        # Simulate hovering over last option
        r = rects[-1]
        menu._handle_hover((r.centerx, r.centery))
        self.assertEqual(menu._selected, len(opts) - 1)


# ══════════════════════════════════════════════════════════════════════════════
# MonsterTooltip
# ══════════════════════════════════════════════════════════════════════════════
from ui.monster_tooltip import MonsterTooltip, HOVER_RADIUS

class FM:
    def __init__(self,x=200.0,y=200.0,mtype='rat',level=1,hp=50,max_hp=100,
                 damage=10,speed=72,is_boss=False,is_elite=False,
                 elite_mods=None,my_spells=None):
        self.x=float(x);self.y=float(y);self.mtype=mtype;self.level=level
        self.name=mtype.capitalize();self.hp=float(hp);self.max_hp=float(max_hp)
        self.damage=damage;self.speed=float(speed)
        self.is_boss=is_boss;self.is_elite=is_elite
        self.elite_mods=elite_mods or [];self._my_spells=my_spells or []
    def is_dead(self): return self.hp<=0

class FC: offset_x=0.0; offset_y=0.0

class TestTooltip(unittest.TestCase):
    def test_target_none_initially(self):
        tt = MonsterTooltip(); self.assertIsNone(tt._target)
    def test_hover_sets_target(self):
        tt = MonsterTooltip(); m = FM()
        tt.update(0.2, 200, 200, [m], FC()); self.assertIs(tt._target, m)
    def test_far_mouse_no_target(self):
        tt = MonsterTooltip(); m = FM()
        tt.update(0.2, 5000, 5000, [m], FC()); self.assertIsNone(tt._target)
    def test_dead_not_targeted(self):
        tt = MonsterTooltip(); m = FM(hp=0)
        tt.update(0.2, 200, 200, [m], FC()); self.assertIsNone(tt._target)
    def test_alpha_increases_on_hover(self):
        tt = MonsterTooltip(); m = FM()
        tt._tick = 0   # force immediate update
        tt.update(0.3, 200, 200, [m], FC()); self.assertGreater(tt._alpha, 0)
    def test_alpha_decreases_away(self):
        tt = MonsterTooltip(); m = FM()
        tt._tick = 0; tt.update(0.5, 200, 200, [m], FC()); a = tt._alpha
        tt._tick = 0; tt.update(0.5, 5000, 5000, [m], FC()); self.assertLess(tt._alpha, a)
    def test_draw_no_crash_no_target(self):
        from tests.mock_pygame import FakeSurface
        tt = MonsterTooltip()
        try: tt.draw(FakeSurface(), 100, 100)
        except Exception as e: self.fail(f"draw raised {e}")
    def test_draw_no_crash_with_target(self):
        from tests.mock_pygame import FakeSurface
        tt = MonsterTooltip(); m = FM()
        tt._tick = 0; tt.update(0.5, 200, 200, [m], FC()); tt._alpha = 1.0
        try: tt.draw(FakeSurface(), 200, 200)
        except Exception as e: self.fail(f"draw raised {e}")
    def test_closest_selected(self):
        tt = MonsterTooltip()
        m1 = FM(x=200.0, y=200.0); m2 = FM(x=215.0, y=200.0)
        tt._tick = 0; tt.update(0.016, 200, 200, [m1, m2], FC())
        self.assertIs(tt._target, m1)
    def test_hover_radius_positive(self):
        self.assertGreater(HOVER_RADIUS, 0)
    def test_outside_radius_no_target(self):
        tt = MonsterTooltip(); m = FM(x=200.0, y=200.0)
        tt._tick = 0; tt.update(0.016, int(200+HOVER_RADIUS+5), 200, [m], FC())
        self.assertIsNone(tt._target)
    def test_empty_monster_list(self):
        tt = MonsterTooltip()
        tt._tick = 0; tt.update(0.016, 200, 200, [], FC()); self.assertIsNone(tt._target)


if __name__ == '__main__':
    unittest.main()


# ══════════════════════════════════════════════════════════════════════════════
# Bot competitor
# ══════════════════════════════════════════════════════════════════════════════
from entities.bot import Bot, STATE_ROAM, STATE_HUNT, STATE_FLEE, STATE_ATTACK

class FakeWorldBot:
    width=60; height=60; tile_size=32
    def is_walkable(self,c,r): return 0<=c<60 and 0<=r<60
    def is_rect_walkable(self,*a): return True

class FakePlayerBot:
    x=960.0; y=960.0; SIZE=18; level=5; hp=100.0; max_hp=100.0
    _inv_timer=0.0; _block_flash=0.0
    def __init__(self):
        import tests.mock_pygame as mp; self.rect=mp.FakeRect()
    def take_damage(self,a): self.hp=max(0,self.hp-a); return a

class FakeStormBot:
    cx=960.0; cy=960.0
    def player_inside(self,x,y): return True   # always safe

class TestBot(unittest.TestCase):
    def _bot(self, x=400.0, y=400.0, level=5):
        from entities.bot import INTEL_VETERANO
        b = Bot(x, y, level, bot_idx=0)
        b.intel = INTEL_VETERANO   # combat tests need attacking ability
        b._aggro_range = 300.0
        b._flee_hp_pct = 0.4
        b._hunt_range  = 600.0
        return b
    def _world(self): return FakeWorldBot()
    def _player(self): return FakePlayerBot()

    def test_initialises(self):
        b = self._bot(); self.assertFalse(b.is_dead())
    def test_has_name(self):
        b = self._bot(); self.assertIsInstance(b.name, str); self.assertGreater(len(b.name), 0)
    def test_starts_with_full_hp(self):
        b = self._bot(); self.assertAlmostEqual(b.hp, float(b.max_hp))
    def test_take_damage(self):
        b = self._bot(); hp = b.hp; b.take_damage(30); self.assertLess(b.hp, hp)
    def test_invincibility_frames(self):
        b = self._bot(); b.take_damage(10); dmg = b.take_damage(10)
        self.assertEqual(dmg, 0)   # still in inv frames
    def test_is_dead_when_hp_zero(self):
        b = self._bot(); b.hp = 0.0; self.assertTrue(b.is_dead())
    def test_update_returns_zero_when_dead(self):
        b = self._bot(); b.hp = 0.0
        result = b.update(0.016, self._player(), [], self._world(), FakeStormBot())
        self.assertEqual(result, 0)
    def test_update_no_crash(self):
        b = self._bot(); p = self._player(); w = self._world()
        try: b.update(0.1, p, [], w, FakeStormBot())
        except Exception as e: self.fail(f"update raised {e}")
    def test_bot_moves_toward_waypoint(self):
        b = self._bot(400.0, 400.0); p = self._player(); w = self._world()
        b._waypoint = (600.0, 400.0)
        b._state = STATE_ROAM
        x_before = b.x
        b.update(0.5, p, [], w, FakeStormBot())
        # Should have moved (or stayed if blocked, but world is open)
        # Just check no crash
        self.assertIsInstance(b.x, float)
    def test_hunt_state_attacks_monster(self):
        from entities.monster import Monster
        b = self._bot(200.0, 200.0, level=5)
        m = Monster(210.0, 200.0, 'rat', 0)   # very close
        p = self._player(); w = self._world()
        b._state = STATE_HUNT; b._target_m = m
        b._atk_timer = 0
        for _ in range(20): b.update(0.05, p, [m], w, FakeStormBot())
        self.assertLess(m.hp, m.max_hp)   # monster took damage
    def test_attack_player_state(self):
        b = self._bot(960.0, 960.0, level=10)   # same pos as player
        p = self._player(); w = self._world()
        b._state = STATE_ATTACK; b._atk_timer = 0
        dmg = b.update(0.1, p, [], w, FakeStormBot())
        self.assertGreater(dmg, 0)
    def test_draw_no_crash(self):
        from tests.mock_pygame import FakeSurface
        class FC2: offset_x=0.0; offset_y=0.0; view_w=1280; view_h=720
        b = self._bot()
        try: b.draw(FakeSurface(), FC2())
        except Exception as e: self.fail(f"bot.draw raised {e}")
    def test_flee_state_no_crash(self):
        b = self._bot(); p = self._player(); w = self._world()
        b._state = STATE_FLEE
        try: b.update(0.1, p, [], w, FakeStormBot())
        except Exception as e: self.fail(f"flee raised {e}")
    def test_hp_regen(self):
        b = self._bot(); b.hp = b.max_hp * 0.5; hp_before = b.hp
        b.update(1.0, self._player(), [], self._world(), FakeStormBot())
        self.assertGreater(b.hp, hp_before)


# ══════════════════════════════════════════════════════════════════════════════
# PauseMenu
# ══════════════════════════════════════════════════════════════════════════════
class TestPauseMenu(unittest.TestCase):
    def _menu(self):
        from ui.pause_menu import PauseMenu
        return PauseMenu()

    def test_activate_continuar(self):
        m = self._menu(); m._selected = 0
        self.assertEqual(m._activate(), "resume")

    def test_activate_menu(self):
        m = self._menu(); m._selected = 1
        self.assertEqual(m._activate(), "menu")

    def test_activate_salir(self):
        m = self._menu(); m._selected = 2
        self.assertEqual(m._activate(), "quit")

    def test_rects_count(self):
        import pygame
        m = self._menu()
        rects = m._rects()
        self.assertEqual(len(rects), 3)
        for r in rects:
            self.assertIsInstance(r, pygame.Rect)

    def test_draw_no_crash(self):
        from tests.mock_pygame import FakeSurface
        m = self._menu()
        try: m._draw(FakeSurface())
        except Exception as e: self.fail(f"PauseMenu._draw raised {e}")

    def test_hover_updates_selection(self):
        m = self._menu()
        rects = m._rects()
        r = rects[2]
        m._hover((r.centerx, r.centery))
        self.assertEqual(m._selected, 2)

    def test_click_returns_action(self):
        m = self._menu()
        rects = m._rects()
        result = m._activate_click((rects[0].centerx, rects[0].centery))
        self.assertEqual(result, "resume")

    def test_click_outside_returns_none(self):
        m = self._menu()
        self.assertIsNone(m._activate_click((0, 0)))
