"""
ui/vocation_select.py
Pantalla de selección de vocación estilo Tibia.
Se muestra antes de cada nueva partida.
"""
from __future__ import annotations
import pygame
import math
from constants import SCREEN_W, SCREEN_H

_BG_TOP = (8, 5, 18)
_BG_BOT = (22, 10, 40)
_TITLE  = (220, 190, 255)
_SEL    = (255, 220, 80)
_NOR    = (170, 150, 210)
_DIM    = (70, 60, 100)

VOCATIONS = [
    {
        "id":    "knight",
        "name":  "Knight",
        "color": (220, 80, 50),
        "desc":  "Guerrero cuerpo a cuerpo. Alta vida y defensa.\nHechizos: Berserk, Annihilation, Magic Shield.",
        "stats": "HP: ★★★★★   MP: ★★☆☆☆\nAtaque: ★★★★☆   Magia: ★★☆☆☆",
        "spells": ["exori", "exori gran", "utamo vita"],
        "symbol": "⚔",
    },
    {
        "id":    "paladin",
        "name":  "Paladin",
        "color": (220, 200, 60),
        "desc":  "Experto en distancia y hechizos sagrados.\nHechizos: Conjure Arrow, Divine Caldera, Heal Friend.",
        "stats": "HP: ★★★★☆   MP: ★★★☆☆\nAtaque: ★★★☆☆   Magia: ★★★☆☆",
        "spells": ["exevo con", "exevo gran con", "exura san"],
        "symbol": "🏹",
    },
    {
        "id":    "druid",
        "name":  "Druid",
        "color": (80, 200, 100),
        "desc":  "Magia natural y curativa. Control de área.\nHechizos: Ice Strike, Stone Shower, Great Stone Shower.",
        "stats": "HP: ★★★☆☆   MP: ★★★★☆\nAtaque: ★★☆☆☆   Magia: ★★★★☆",
        "spells": ["exevo frigo", "exevo tera", "exevo gran mas frigo"],
        "symbol": "🌿",
    },
    {
        "id":    "sorcerer",
        "name":  "Sorcerer",
        "color": (100, 140, 255),
        "desc":  "Máximo poder mágico. Hechizos devastadores.\nHechizos: Magic Missile, Great Energy Beam, Fireball.",
        "stats": "HP: ★★☆☆☆   MP: ★★★★★\nAtaque: ★★☆☆☆   Magia: ★★★★★",
        "spells": ["exevo vis", "exevo gran vis", "exevo flam"],
        "symbol": "✦",
    },
]


class VocationSelect:
    def __init__(self):
        self._selected = 0
        self._time     = 0.0
        self._f_title  = pygame.font.SysFont("Arial", 44, bold=True)
        self._f_name   = pygame.font.SysFont("Arial", 30, bold=True)
        self._f_body   = pygame.font.SysFont("Arial", 15)
        self._f_small  = pygame.font.SysFont("Arial", 13)
        self._f_hint   = pygame.font.SysFont("Arial", 13)

        self._bg = pygame.Surface((SCREEN_W, SCREEN_H))
        for y in range(SCREEN_H):
            t = y / SCREEN_H
            col = tuple(int(_BG_TOP[i] + (_BG_BOT[i] - _BG_TOP[i]) * t) for i in range(3))
            pygame.draw.line(self._bg, col, (0, y), (SCREEN_W, y))

    def run(self, screen: pygame.Surface, clock) -> str:
        """Blocks until a vocation is selected. Returns vocation id string."""
        while True:
            dt = clock.tick(60) / 1000.0
            self._time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "sorcerer"
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        self._selected = (self._selected - 1) % len(VOCATIONS)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self._selected = (self._selected + 1) % len(VOCATIONS)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return VOCATIONS[self._selected]["id"]
                    elif event.key == pygame.K_ESCAPE:
                        return "sorcerer"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    r = self._click(event.pos)
                    if r:
                        return r
                if event.type == pygame.MOUSEMOTION:
                    self._hover(event.pos)

            self._draw(screen)
            pygame.display.flip()

    def _card_rects(self):
        n   = len(VOCATIONS)
        cw  = 240; ch = 320
        gap = 28
        total_w = n * cw + (n-1) * gap
        ox = SCREEN_W // 2 - total_w // 2
        oy = SCREEN_H // 2 - ch // 2 + 20
        return [pygame.Rect(ox + i*(cw+gap), oy, cw, ch) for i in range(n)]

    def _click(self, pos) -> str | None:
        for i, rect in enumerate(self._card_rects()):
            if rect.collidepoint(pos):
                if i == self._selected:
                    return VOCATIONS[i]["id"]
                self._selected = i
        return None

    def _hover(self, pos):
        for i, rect in enumerate(self._card_rects()):
            if rect.collidepoint(pos):
                self._selected = i

    def _draw(self, screen):
        screen.blit(self._bg, (0, 0))

        # Title
        pulse = 0.9 + 0.1 * math.sin(self._time * 2.0)
        t = self._f_title.render("Elige tu Vocación", True, _TITLE)
        t.set_alpha(int(240 * pulse))
        screen.blit(t, (SCREEN_W//2 - t.get_width()//2, 38))

        rects = self._card_rects()
        for i, (voc, rect) in enumerate(zip(VOCATIONS, rects)):
            is_sel = (i == self._selected)
            self._draw_card(screen, rect, voc, is_sel)

        # Bottom hint
        hint = self._f_hint.render(
            "←→ Cambiar  |  ENTER Seleccionar", True, _DIM)
        screen.blit(hint, (SCREEN_W//2 - hint.get_width()//2, SCREEN_H - 28))

    def _draw_card(self, screen, rect, voc, is_sel):
        # Background
        alpha = 210 if is_sel else 120
        bg    = (40, 20, 70) if is_sel else (15, 8, 30)
        surf  = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        surf.fill((*bg, alpha))
        col = voc["color"]
        border_col = col if is_sel else tuple(c//2 for c in col)
        bw = 3 if is_sel else 1
        pygame.draw.rect(surf, (*border_col, 240), (0,0,rect.w,rect.h), bw, border_radius=10)

        # Glow behind selected card
        if is_sel:
            glow = pygame.Surface((rect.w+20, rect.h+20), pygame.SRCALPHA)
            pulse = 0.5 + 0.5 * math.sin(self._time * 3.0)
            pygame.draw.rect(glow, (*col, int(40*pulse)),
                             (0, 0, rect.w+20, rect.h+20), border_radius=14)
            screen.blit(glow, (rect.x-10, rect.y-10))

        screen.blit(surf, rect.topleft)

        # Symbol
        sym  = self._f_title.render(voc["symbol"], True, col if is_sel else tuple(c*3//4 for c in col))
        screen.blit(sym, (rect.x + rect.w//2 - sym.get_width()//2, rect.y + 16))

        # Name
        name_col = _SEL if is_sel else _NOR
        nm = self._f_name.render(voc["name"], True, name_col)
        screen.blit(nm, (rect.x + rect.w//2 - nm.get_width()//2, rect.y + 76))

        # Stats
        y = rect.y + 116
        for line in voc["stats"].split("\n"):
            s = self._f_small.render(line, True, (180,160,220) if is_sel else _DIM)
            screen.blit(s, (rect.x + 12, y)); y += 18

        # Description
        y += 6
        for line in voc["desc"].split("\n"):
            s = self._f_small.render(line, True, (200,185,230) if is_sel else (100,90,130))
            screen.blit(s, (rect.x + 10, y)); y += 18

        # Spells list
        y += 8
        sep = self._f_small.render("Hechizos iniciales:", True, col if is_sel else _DIM)
        screen.blit(sep, (rect.x + 10, y)); y += 18
        from systems.spells import SPELL_CATALOGUE
        for sid in voc["spells"]:
            data = SPELL_CATALOGUE.get(sid, {})
            sc = data.get("color", (160,140,200))
            incantat = data.get("incantation", sid)
            spell_s = self._f_small.render(f"  {incantat}", True, sc if is_sel else tuple(c//2 for c in sc))
            screen.blit(spell_s, (rect.x + 10, y)); y += 16

        # "Selected" arrow
        if is_sel:
            ax = rect.x + rect.w//2
            ay = rect.y + rect.h - 14
            off = int(4 * math.sin(self._time * 5))
            pygame.draw.polygon(screen, _SEL, [
                (ax, ay + off), (ax-8, ay-8+off), (ax+8, ay-8+off)])
