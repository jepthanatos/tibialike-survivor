"""
ui/biome_ui.py
══════════════════════════════════════════════════════════════════
Efectos visuales de bioma:
  · Overlay de tinte ambiental semitransparente (sobre el mundo)
  · Banner con nombre del bioma al entrar en una zona nueva
  · Efectos de partículas ligeros (nieve, arena, ceniza)
"""
from __future__ import annotations
import pygame
import math
import random
from systems.biomes import BIOMES
from constants import SCREEN_W, GAME_H

_PARTICLE_LIMIT = 80


class BiomeUI:
    def __init__(self, view_w: int, view_h: int):
        self.vw = view_w
        self.vh = view_h

        self._tint_surf = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        self._current_biome = "grassland"
        self._banner_text   = ""
        self._banner_timer  = 0.0
        self._banner_alpha  = 0

        self._f_banner = pygame.font.SysFont("Arial", 28, bold=True)
        self._f_desc   = pygame.font.SysFont("Arial", 14)

        # Particles: list of [x, y, vx, vy, life, max_life, color, size]
        self._particles: list = []
        self._particle_timer = 0.0
        self._time = 0.0

    # ── Called each frame ─────────────────────────────────────────────────────

    def update(self, dt: float, biome_name: str):
        self._time += dt
        self._banner_timer = max(0.0, self._banner_timer - dt)

        # Detect biome change → show banner
        if biome_name != self._current_biome:
            self._current_biome = biome_name
            bd = BIOMES.get(biome_name, BIOMES["grassland"])
            self._banner_text  = f"{bd['icon']}  {bd['name']}"
            self._banner_timer = 3.5
            self._particles.clear()

        # Spawn particles
        self._particle_timer -= dt
        if self._particle_timer <= 0 and len(self._particles) < _PARTICLE_LIMIT:
            self._particle_timer = self._spawn_interval(biome_name)
            self._spawn_particle(biome_name)

        # Update particles
        for p in self._particles[:]:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
            if p[4] <= 0 or p[1] > self.vh + 20:
                self._particles.remove(p)

    def draw(self, screen: pygame.Surface, biome_name: str):
        bd = BIOMES.get(biome_name, BIOMES["grassland"])
        tint = bd.get("ambient_tint")

        # Ambient tint
        if tint and len(tint) == 4:
            self._tint_surf.fill(tint)
            screen.blit(self._tint_surf, (0, 0))

        # Particles
        for p in self._particles:
            x, y, _, _, life, max_life, color, size = p
            alpha = int(200 * (life / max_life))
            ps = pygame.Surface((size*2+2, size*2+2), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*color, alpha), (size+1, size+1), size)
            screen.blit(ps, (int(x)-size, int(y)-size))

        # Lava glow on screen edges (volcanic biome)
        if biome_name == "volcanic":
            pulse = int(40 + 20 * math.sin(self._time * 2.2))
            glow  = pygame.Surface((self.vw, self.vh), pygame.SRCALPHA)
            for t in range(8, 0, -1):
                a = int(pulse * (t / 8) ** 2)
                pygame.draw.rect(glow, (220, 60, 10, a),
                                 (t, t, self.vw-t*2, self.vh-t*2), 1)
            screen.blit(glow, (0, 0))

        # Biome banner
        if self._banner_timer > 0:
            self._draw_banner(screen, bd)

    def _draw_banner(self, screen: pygame.Surface, bd: dict):
        frac  = min(1.0, self._banner_timer / 0.6)
        alpha = int(255 * frac)

        # Background pill
        text_s  = self._f_banner.render(self._banner_text, True, (255, 255, 255))
        desc_s  = self._f_desc.render(bd["description"], True, (200, 200, 200))
        pw      = max(text_s.get_width(), desc_s.get_width()) + 40
        ph      = text_s.get_height() + desc_s.get_height() + 20
        px      = (self.vw - pw) // 2
        py      = self.vh // 4 - ph // 2

        bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        bg.fill((10, 10, 20, int(180 * frac)))
        pygame.draw.rect(bg, (*bd["color"][:3], alpha), (0, 0, pw, ph), 2,
                         border_radius=8)
        screen.blit(bg, (px, py))

        text_s.set_alpha(alpha)
        desc_s.set_alpha(alpha)
        screen.blit(text_s, (px + pw//2 - text_s.get_width()//2, py + 8))
        screen.blit(desc_s, (px + pw//2 - desc_s.get_width()//2,
                             py + 8 + text_s.get_height() + 4))

    # ── Particle system ───────────────────────────────────────────────────────

    def _spawn_interval(self, biome: str) -> float:
        return {
            "snowfield": 0.08,
            "desert":    0.12,
            "volcanic":  0.10,
            "swamp":     0.18,
        }.get(biome, 9999.0)   # no particles for grassland

    def _spawn_particle(self, biome: str):
        x  = random.uniform(0, self.vw)
        y  = -5.0

        if biome == "snowfield":
            self._particles.append([
                x, y,
                random.uniform(-12, 12),    # vx (wind drift)
                random.uniform(25, 55),     # vy (falling speed)
                random.uniform(2.0, 4.5),   # life
                4.5,                        # max_life
                (220, 235, 255),            # color
                random.randint(1, 3),       # size
            ])

        elif biome == "desert":
            # Sand grains drifting sideways
            self._particles.append([
                x, random.uniform(0, self.vh),
                random.uniform(20, 60),     # wind rightward
                random.uniform(-5, 5),
                random.uniform(1.0, 2.5),
                2.5,
                (200, 180, 100),
                1,
            ])

        elif biome == "volcanic":
            # Ash flakes falling slowly
            self._particles.append([
                x, y,
                random.uniform(-8, 8),
                random.uniform(15, 35),
                random.uniform(3.0, 6.0),
                6.0,
                (80, 70, 70),
                random.randint(1, 2),
            ])

        elif biome == "swamp":
            # Bubbles rising from ground
            self._particles.append([
                random.uniform(0, self.vw),
                float(self.vh),
                random.uniform(-4, 4),
                random.uniform(-20, -8),   # rising
                random.uniform(1.5, 3.0),
                3.0,
                (60, 120, 50),
                random.randint(2, 4),
            ])
