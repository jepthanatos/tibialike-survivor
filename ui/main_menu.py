"""
ui/main_menu.py
═══════════════════════════════════════════════════════════════
Menú principal del juego.
Opciones: Nueva Partida / Continuar / Borrar Save / Salir
"""
from __future__ import annotations
import pygame
import math
import os
from constants import SCREEN_W, SCREEN_H, C_WHITE, C_GRAY, C_RED, C_YELLOW, C_GREEN

SAVE_FILE = "save.json"

_BG_TOP    = (10,  5, 20)
_BG_BOT    = (25, 10, 45)
_TITLE_COL = (200, 160, 255)
_SEL_COL   = (255, 220,  80)
_NOR_COL   = (160, 140, 200)
_DIM_COL   = ( 80,  70, 110)
_DANGER    = (220,  60,  60)

OPTIONS_BASE     = ["Nueva Partida", "Continuar",   "Salir"]
OPTIONS_SAVE     = ["Nueva Partida", "Continuar",   "Borrar Progreso", "Salir"]
# When no save: Continuar is grayed out


class MainMenu:
    """
    Renders and handles input for the main menu.
    Call `run(screen, clock)` — blocks until an option is chosen.
    Returns one of: "new", "continue", "delete", "quit"
    """

    def __init__(self):
        self._time     = 0.0
        self._selected = 0
        self._confirm_delete = False   # confirmation step before deleting

        self._f_title  = pygame.font.SysFont("Arial", 62, bold=True)
        self._f_sub    = pygame.font.SysFont("Arial", 18)
        self._f_opt    = pygame.font.SysFont("Arial", 32, bold=True)
        self._f_hint   = pygame.font.SysFont("Arial", 14)
        self._f_save   = pygame.font.SysFont("Arial", 15)

        # Build gradient background surface once
        self._bg = pygame.Surface((SCREEN_W, SCREEN_H))
        for y in range(SCREEN_H):
            t   = y / SCREEN_H
            col = tuple(int(_BG_TOP[i] + (_BG_BOT[i] - _BG_TOP[i]) * t) for i in range(3))
            pygame.draw.line(self._bg, col, (0, y), (SCREEN_W, y))

        # Star field (static)
        import random
        rng         = random.Random(42)
        self._stars = [(rng.randint(0, SCREEN_W), rng.randint(0, SCREEN_H),
                        rng.randint(1, 3)) for _ in range(120)]

    # ── Public ────────────────────────────────────────────────────────────────

    def run(self, screen: pygame.Surface, clock) -> str:
        """Block until user selects an option. Returns action string."""
        while True:
            dt = clock.tick(60) / 1000.0
            self._time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    result = self._handle_key(event.key)
                    if result:
                        return result
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    result = self._handle_click(event.pos)
                    if result:
                        return result
                if event.type == pygame.MOUSEMOTION:
                    self._handle_hover(event.pos)

            self._draw(screen)
            pygame.display.flip()

    # ── Input ─────────────────────────────────────────────────────────────────

    def _options(self) -> list[str]:
        return OPTIONS_SAVE if self._save_exists() else OPTIONS_BASE

    def _save_exists(self) -> bool:
        return os.path.exists(SAVE_FILE)

    def _handle_key(self, key) -> str | None:
        opts = self._options()

        if self._confirm_delete:
            if key == pygame.K_y:
                self._delete_save()
                self._confirm_delete = False
                self._selected = 0
                return None
            else:
                self._confirm_delete = False
            return None

        if key in (pygame.K_UP, pygame.K_w):
            self._selected = (self._selected - 1) % len(opts)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self._selected = (self._selected + 1) % len(opts)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            return self._activate(self._selected)
        elif key == pygame.K_ESCAPE:
            return "quit"
        return None

    def _handle_click(self, pos) -> str | None:
        if self._confirm_delete:
            self._confirm_delete = False
            return None
        opts   = self._options()
        rects  = self._option_rects(opts)
        for i, rect in enumerate(rects):
            if rect.collidepoint(pos):
                return self._activate(i)
        return None

    def _handle_hover(self, pos):
        opts  = self._options()
        rects = self._option_rects(opts)
        for i, rect in enumerate(rects):
            if rect.collidepoint(pos):
                self._selected = i

    def _activate(self, idx) -> str | None:
        opts = self._options()
        if idx >= len(opts):
            return None
        label = opts[idx]

        if label == "Continuar" and not self._save_exists():
            return None   # grayed out

        if label == "Borrar Progreso":
            self._confirm_delete = True
            return None

        mapping = {
            "Nueva Partida": "new",
            "Continuar":     "continue",
            "Salir":         "quit",
        }
        return mapping.get(label)

    def _delete_save(self):
        try:
            if os.path.exists(SAVE_FILE):
                os.remove(SAVE_FILE)
            hist = "stats_history.json"
            if os.path.exists(hist):
                os.remove(hist)
        except Exception:
            pass

    # ── Layout ────────────────────────────────────────────────────────────────

    def _option_rects(self, opts) -> list[pygame.Rect]:
        rects = []
        start_y = SCREEN_H // 2 - 20
        for i in range(len(opts)):
            w, h = 320, 52
            x    = SCREEN_W // 2 - w // 2
            y    = start_y + i * 68
            rects.append(pygame.Rect(x, y, w, h))
        return rects

    # ── Draw ──────────────────────────────────────────────────────────────────

    def _draw(self, screen: pygame.Surface):
        screen.blit(self._bg, (0, 0))
        self._draw_stars(screen)
        self._draw_title(screen)
        self._draw_options(screen)
        if self._confirm_delete:
            self._draw_confirm(screen)
        self._draw_save_info(screen)
        self._draw_hint(screen)

    def _draw_stars(self, screen):
        pulse = 0.6 + 0.4 * math.sin(self._time * 1.2)
        for x, y, r in self._stars:
            alpha = int(120 + 100 * pulse)
            s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, (200, 200, 255, alpha), (r+1, r+1), r)
            screen.blit(s, (x - r - 1, y - r - 1))

    def _draw_title(self, screen):
        pulse  = 0.85 + 0.15 * math.sin(self._time * 2.0)
        # Shadow
        shadow = self._f_title.render("TIBIA SURVIVOR", True, (40, 10, 80))
        sx     = SCREEN_W // 2 - shadow.get_width() // 2
        screen.blit(shadow, (sx + 3, 83))
        # Main title
        title = self._f_title.render("TIBIA SURVIVOR", True, _TITLE_COL)
        title.set_alpha(int(240 * pulse))
        screen.blit(title, (sx, 80))
        # Subtitle
        sub = self._f_sub.render("Sobrevive el mayor tiempo posible", True, _DIM_COL)
        screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 155))

    def _draw_options(self, screen):
        opts  = self._options()
        rects = self._option_rects(opts)

        for i, (opt, rect) in enumerate(zip(opts, rects)):
            is_sel      = (i == self._selected)
            is_disabled = (opt == "Continuar" and not self._save_exists())
            is_danger   = (opt == "Borrar Progreso")

            # Background pill
            bg_alpha = 180 if is_sel else 80
            bg_col   = (60, 30, 100) if is_sel else (20, 10, 40)
            bg_surf  = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            bg_surf.fill((*bg_col, bg_alpha))
            if is_sel:
                pygame.draw.rect(bg_surf, (*_SEL_COL, 200), (0, 0, rect.w, rect.h), 2, border_radius=8)
            screen.blit(bg_surf, rect.topleft)
            pygame.draw.rect(screen, (50, 30, 80), rect, 1, border_radius=8)

            # Text
            if is_disabled:
                col = _DIM_COL
            elif is_danger:
                col = _DANGER if is_sel else (180, 60, 60)
            elif is_sel:
                col = _SEL_COL
            else:
                col = _NOR_COL

            text  = self._f_opt.render(opt, True, col)
            tx    = rect.x + rect.w // 2 - text.get_width() // 2
            ty    = rect.y + rect.h // 2 - text.get_height() // 2
            screen.blit(text, (tx, ty))

            # Disabled hint
            if is_disabled:
                hint = self._f_hint.render("(sin guardado)", True, _DIM_COL)
                screen.blit(hint, (tx + text.get_width() + 8, ty + 8))

            # Arrow indicator
            if is_sel and not is_disabled:
                ax = rect.x - 24
                ay = rect.y + rect.h // 2
                pulse_off = int(6 * math.sin(self._time * 5))
                pygame.draw.polygon(screen, _SEL_COL, [
                    (ax + pulse_off, ay),
                    (ax - 8 + pulse_off, ay - 8),
                    (ax - 8 + pulse_off, ay + 8),
                ])

    def _draw_confirm(self, screen):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        screen.blit(ov, (0, 0))

        bw, bh = 500, 180
        bx     = SCREEN_W // 2 - bw // 2
        by     = SCREEN_H // 2 - bh // 2
        pygame.draw.rect(screen, (30, 10, 50), (bx, by, bw, bh), border_radius=12)
        pygame.draw.rect(screen, _DANGER,      (bx, by, bw, bh), 2, border_radius=12)

        f1 = pygame.font.SysFont("Arial", 22, bold=True)
        f2 = pygame.font.SysFont("Arial", 16)
        t1 = f1.render("⚠  ¿Borrar todo el progreso?", True, _DANGER)
        t2 = f2.render("Se eliminarán el nivel, hechizos y estadísticas.", True, C_GRAY)
        t3 = f2.render("Pulsa  Y  para confirmar  |  cualquier otra tecla para cancelar", True, C_WHITE)
        screen.blit(t1, (SCREEN_W//2 - t1.get_width()//2, by + 30))
        screen.blit(t2, (SCREEN_W//2 - t2.get_width()//2, by + 72))
        screen.blit(t3, (SCREEN_W//2 - t3.get_width()//2, by + 110))

    def _draw_save_info(self, screen):
        if not self._save_exists():
            return
        try:
            import json
            with open(SAVE_FILE) as f:
                d = json.load(f)
            lv      = d.get("persistent_level", 0)
            runs    = d.get("total_runs", 0)
            best_s  = d.get("best_time", 0.0)
            m, s    = int(best_s)//60, int(best_s)%60
            phase   = d.get("max_storm_phase", 0)
            known   = len(d.get("spell_memory", {}).get("known_spells", []))
            text    = (f"Guardado:  Nivel {lv}  |  {runs} partidas  |  "
                       f"Mejor {m:02d}:{s:02d}  |  Fase tormenta {phase}  |  "
                       f"{known} hechizos")
            t = self._f_save.render(text, True, (120, 100, 160))
            screen.blit(t, (SCREEN_W//2 - t.get_width()//2, SCREEN_H - 70))
        except Exception:
            pass

    def _draw_hint(self, screen):
        hint = self._f_hint.render(
            "↑↓ Navegar  |  ENTER Seleccionar  |  ESC Salir",
            True, (60, 50, 90))
        screen.blit(hint, (SCREEN_W//2 - hint.get_width()//2, SCREEN_H - 30))
