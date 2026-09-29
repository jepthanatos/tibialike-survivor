"""
ui/pause_menu.py
Menú de pausa ligero: no destruye ni reinicia el juego.
Opciones: Continuar / Menú Principal / Salir
"""
import pygame
import math
from constants import SCREEN_W, SCREEN_H

_BG   = (10, 8, 20, 185)
_SEL  = (255, 220, 80)
_NOR  = (160, 140, 200)
_DIM  = (60, 50, 90)


class PauseMenu:
    OPTIONS = ["Continuar", "Menú Principal", "Salir"]

    def __init__(self):
        self._selected = 0
        self._time     = 0.0
        self._f_title  = pygame.font.SysFont("Arial", 38, bold=True)
        self._f_opt    = pygame.font.SysFont("Arial", 28, bold=True)
        self._f_hint   = pygame.font.SysFont("Arial", 13)

    def run(self, screen: pygame.Surface, clock) -> str:
        """
        Blocks until selection. Returns:
          'resume'  → continue current run
          'menu'    → go to main menu (caller keeps game state or not)
          'quit'    → exit process
        """
        while True:
            dt = clock.tick(60) / 1000.0
            self._time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self._selected = (self._selected - 1) % len(self.OPTIONS)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self._selected = (self._selected + 1) % len(self.OPTIONS)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return self._activate()
                    elif event.key == pygame.K_ESCAPE:
                        return "resume"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    r = self._activate_click(event.pos)
                    if r: return r
                if event.type == pygame.MOUSEMOTION:
                    self._hover(event.pos)

            self._draw(screen)
            pygame.display.flip()

    def _activate(self) -> str:
        label = self.OPTIONS[self._selected]
        return {"Continuar": "resume", "Menú Principal": "menu", "Salir": "quit"}[label]

    def _rects(self):
        rects = []
        for i in range(len(self.OPTIONS)):
            w, h = 280, 46
            x = SCREEN_W // 2 - w // 2
            y = SCREEN_H // 2 - 20 + i * 60
            rects.append(pygame.Rect(x, y, w, h))
        return rects

    def _activate_click(self, pos) -> str | None:
        for i, rect in enumerate(self._rects()):
            if rect.collidepoint(pos):
                self._selected = i
                return self._activate()
        return None

    def _hover(self, pos):
        for i, rect in enumerate(self._rects()):
            if rect.collidepoint(pos):
                self._selected = i

    def _draw(self, screen):
        # Dark overlay
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill(_BG)
        screen.blit(ov, (0, 0))

        # Title
        pulse = 0.9 + 0.1 * math.sin(self._time * 2.5)
        t = self._f_title.render("PAUSA", True, (200, 170, 255))
        t.set_alpha(int(240 * pulse))
        screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, SCREEN_H // 2 - 110))

        # Options
        for i, (label, rect) in enumerate(zip(self.OPTIONS, self._rects())):
            is_sel = (i == self._selected)
            bg_col = (50, 25, 90) if is_sel else (18, 10, 35)
            bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            bg.fill((*bg_col, 200 if is_sel else 100))
            if is_sel:
                pygame.draw.rect(bg, (*_SEL, 220), (0, 0, rect.w, rect.h), 2, border_radius=6)
            screen.blit(bg, rect.topleft)

            col = _SEL if is_sel else _NOR
            text = self._f_opt.render(label, True, col)
            screen.blit(text, (rect.x + rect.w // 2 - text.get_width() // 2,
                                rect.y + rect.h // 2 - text.get_height() // 2))

        hint = self._f_hint.render("↑↓ Navegar  |  ENTER Seleccionar  |  ESC Continuar", True, _DIM)
        screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 28))
