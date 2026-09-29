"""
ui/monster_tooltip.py
Tooltip minimalista: nombre + nivel + barra HP.
Sólo 2-3 líneas para no afectar el rendimiento con muchos enemigos.
"""
from __future__ import annotations
import pygame
import math
from constants import SCREEN_W, GAME_H

HOVER_RADIUS = 28.0
_UPDATE_INTERVAL = 0.08   # refrescar hover cada 80ms, no cada frame

_BG    = (12, 10, 22, 200)
_BORD  = (80, 60, 120)
_NAME  = (220, 200, 255)
_GRAY  = (140, 130, 160)


class MonsterTooltip:
    def __init__(self):
        self._f_name = pygame.font.SysFont("Arial", 13, bold=True)
        self._f_body = pygame.font.SysFont("Arial", 11)
        self._target  = None
        self._alpha   = 0.0
        self._tick    = 0.0   # throttle timer

    def update(self, dt: float, mx: int, my: int,
               monsters: list, camera) -> None:
        self._tick -= dt
        if self._tick > 0:
            # Don't recalculate every frame — only fade
            if self._target and not self._target.is_dead():
                self._alpha = min(1.0, self._alpha + dt * 6)
            else:
                self._alpha = max(0.0, self._alpha - dt * 8)
            return
        self._tick = _UPDATE_INTERVAL

        best = None; best_d = HOVER_RADIUS
        for m in monsters:
            if m.is_dead(): continue
            sx = m.x - camera.offset_x
            sy = m.y - camera.offset_y
            d  = math.hypot(mx - sx, my - sy)
            if d < best_d:
                best_d = d; best = m

        self._target = best
        self._alpha  = min(1.0, self._alpha + dt*6) if best else max(0.0, self._alpha - dt*8)

    def draw(self, screen: pygame.Surface, mx: int, my: int) -> None:
        if self._alpha < 0.05 or self._target is None:
            return
        m = self._target
        if m.is_dead():
            return

        # Build compact tooltip
        badge = " ☠" if getattr(m,"is_boss",False) else (" ★" if getattr(m,"is_elite",False) else "")
        name_str = f"{m.name}{badge}  Nv.{m.level}"
        hp_pct   = max(0.0, m.hp / m.max_hp) if m.max_hp > 0 else 0.0
        hp_str   = f"HP {int(m.hp):,}/{m.max_hp:,}"

        name_s = self._f_name.render(name_str, True, _NAME)
        hp_s   = self._f_body.render(hp_str, True,
                    (80,210,80) if hp_pct>0.6 else (255,160,40) if hp_pct>0.25 else (220,50,50))

        pad = 7
        w   = max(name_s.get_width(), hp_s.get_width()) + pad*2
        h   = name_s.get_height() + hp_s.get_height() + pad*2 + 6  # +6 for hp bar

        tx = mx + 14
        ty = my - h - 6
        if tx + w > SCREEN_W - 4: tx = mx - w - 14
        if ty < 4: ty = my + 20
        if ty + h > GAME_H - 4: ty = GAME_H - h - 4

        # Background
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill(_BG)
        pygame.draw.rect(surf, _BORD, (0, 0, w, h), 1, border_radius=4)
        surf.set_alpha(int(self._alpha * 240))
        screen.blit(surf, (tx, ty))

        # Text
        a = int(self._alpha * 240)
        name_s.set_alpha(a); hp_s.set_alpha(a)
        screen.blit(name_s, (tx+pad, ty+pad))

        # HP bar
        bar_y = ty + pad + name_s.get_height() + 3
        bar_w = w - pad*2
        pygame.draw.rect(screen, (40,0,0),     (tx+pad, bar_y, bar_w, 5))
        pygame.draw.rect(screen, (180,50,50),  (tx+pad, bar_y, int(bar_w*hp_pct), 5))

        screen.blit(hp_s, (tx+pad, bar_y+7))
