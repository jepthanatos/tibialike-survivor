"""
mock_pygame.py
Instala un módulo pygame falso en sys.modules ANTES de que cualquier
módulo del juego lo importe. Basta con hacer:

    import tests.mock_pygame   # al inicio del test

"""
import sys


# ── Tipos de datos básicos ────────────────────────────────────────────────────

class FakeRect:
    """Emula pygame.Rect con lo mínimo que usan los módulos del juego."""
    def __init__(self, x=0, y=0, w=0, h=0):
        self.x = x; self.y = y
        self.w = w; self.h = h
        self.width = w; self.height = h

    @property
    def center(self):
        return (self.x + self.w // 2, self.y + self.h // 2)

    @center.setter
    def center(self, value):
        self.x = value[0] - self.w // 2
        self.y = value[1] - self.h // 2

    @property
    def topleft(self):
        return (self.x, self.y)

    @property
    def centerx(self):
        return self.x + self.w // 2

    @property
    def centery(self):
        return self.y + self.h // 2

    def collidepoint(self, *args):
        # Accept (x, y) or ((x, y),) like real pygame.Rect
        if len(args) == 2:
            px, py = args[0], args[1]
        else:
            pos = args[0]
            px, py = pos[0], pos[1]
        return (self.x <= px < self.x + self.w and
                self.y <= py < self.y + self.h)


class FakeSurface:
    """Emula pygame.Surface (ignora todo el drawing)."""
    def __init__(self, *args, **kwargs):
        self._data = {}

    def fill(self, *a, **kw): pass
    def blit(self, *a, **kw): pass
    def set_at(self, *a, **kw): pass
    def get_at(self, *a): return (0, 0, 0, 255)
    def copy(self): return FakeSurface()
    def get_width(self): return 1280
    def get_height(self): return 720
    def get_size(self): return (1280, 720)
    def set_alpha(self, *a): pass


class FakeFont:
    def render(self, text, antialias, color, *a):
        s = FakeSurface()
        return s

    def size(self, text):
        return (len(text) * 8, 16)


class _FakeFontModule:
    @staticmethod
    def SysFont(*a, **kw):
        return FakeFont()

    @staticmethod
    def Font(*a, **kw):
        return FakeFont()

    @staticmethod
    def init(): pass


class _FakeDraw:
    @staticmethod
    def circle(*a, **kw): pass

    @staticmethod
    def rect(*a, **kw): pass

    @staticmethod
    def ellipse(*a, **kw): pass

    @staticmethod
    def line(*a, **kw): pass

    @staticmethod
    def polygon(*a, **kw): pass

    @staticmethod
    def arc(*a, **kw): pass


class _FakeDisplay:
    @staticmethod
    def set_mode(*a, **kw): return FakeSurface()

    @staticmethod
    def set_caption(*a): pass

    @staticmethod
    def flip(): pass


class _FakeEvent:
    @staticmethod
    def get(): return []


class _FakeClock:
    def tick(self, fps=60): return 16
    def get_fps(self): return 60.0


# ── Módulo pygame falso ───────────────────────────────────────────────────────

class _FakePygame:
    # Tipos
    Rect    = FakeRect
    Surface = FakeSurface

    # Sub-módulos
    draw    = _FakeDraw
    font    = _FakeFontModule
    display = _FakeDisplay
    event   = _FakeEvent

    # Flags
    SRCALPHA    = 65536
    QUIT        = 256
    KEYDOWN     = 768
    KEYUP       = 769
    MOUSEBUTTONDOWN = 1025

    # Teclas (valores arbitrarios únicos)
    K_w     = 119; K_s     = 115; K_a = 97; K_d = 100
    K_UP    = 273; K_DOWN  = 274; K_LEFT = 276; K_RIGHT = 275
    K_ESCAPE = 27; K_r     = 114; K_SPACE = 32
    K_RETURN = 13; K_i = 105; K_e = 101; K_q = 113; K_f = 102
    K_TAB = 9; K_y = 121; K_n = 110; K_SLASH = 47
    K_COMMA = 44; K_PERIOD = 46; K_RCTRL = 305; K_RSHIFT = 303
    K_KP1=257;K_KP2=258;K_KP3=259;K_KP4=260;K_KP5=261;K_KP6=262;K_KP7=263
    K_1=49;K_2=50;K_3=51;K_4=52;K_5=53;K_6=54;K_7=55

    @staticmethod
    def init(): pass

    @staticmethod
    def quit(): pass

    @staticmethod
    def key_get_pressed():
        return {}

    # pygame.time.Clock accesible como atributo
    class time:
        Clock = _FakeClock


# Instalar en sys.modules
sys.modules['pygame'] = _FakePygame()


class FakeStorm:
    """Fake Storm object with all attributes the HUD/renderer expects."""
    phase_reached     = 1
    state             = "waiting"
    phase_name        = "Fase 1"
    phase_number      = 1
    close_warning     = False
    timer             = 60.0
    radius            = 2000.0
    next_radius       = 1500.0
    _base_radius      = 2400.0
    center_x          = 2400.0
    center_y          = 2400.0
    closing_progress  = 0.0
    current_dps       = 0.0

    def player_inside(self, x, y):
        import math
        return math.hypot(x - self.center_x, y - self.center_y) <= self.radius

    def distance_outside(self, x, y):
        import math
        d = math.hypot(x - self.center_x, y - self.center_y)
        return max(0.0, d - self.radius)
