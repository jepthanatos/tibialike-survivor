"""
entities/projectile.py
Proyectil mágico: movimiento, colisión con monstruos, AOE, pierce y efectos visuales.
"""
from __future__ import annotations
import pygame
import math
import random
from systems.spells import SPELL_CATALOGUE
from constants import C_WHITE, C_YELLOW


class Projectile:
    """Un proyectil disparado por el jugador."""

    def __init__(self, x: float, y: float, dx: float, dy: float,
                 spell_id: str, damage: int, owner: str = "player"):
        self.x        = float(x)
        self.y        = float(y)
        self.dx       = dx   # normalizado
        self.dy       = dy
        self.spell_id = spell_id
        self.damage   = damage
        self.owner    = owner

        data           = SPELL_CATALOGUE[spell_id]
        self.speed     = data["speed"]
        self.radius    = data["radius"]
        self.color     = data["color"]
        self.pierce    = data["pierce"]
        self.aoe_r     = data["aoe_radius"]
        self.range_px  = data["range_px"]

        self._dist_travelled = 0.0
        self._alive          = True
        self._hit_set: set   = set()   # monster ids already hit (pierce)
        self._trail: list    = []      # (x, y, age)
        self._anim           = 0.0    # time alive for pulse effects

    # ── State ─────────────────────────────────────────────────────────────

    def is_alive(self) -> bool:
        return self._alive

    def kill(self):
        self._alive = False

    # ── Update ────────────────────────────────────────────────────────────

    def update(self, dt: float, monsters: list) -> list[tuple]:
        """
        Returns list of (monster, damage_dealt) for hits this frame.
        """
        if not self._alive:
            return []

        self._anim += dt

        # Move
        step = self.speed * dt
        self.x              += self.dx * step
        self.y              += self.dy * step
        self._dist_travelled += step

        # Trail
        self._trail.append([self.x, self.y, 0.0])
        for t in self._trail:
            t[2] += dt
        self._trail = [t for t in self._trail if t[2] < 0.22]

        # Range expired
        if self._dist_travelled >= self.range_px:
            self._explode_aoe(monsters, [])
            self.kill()
            return []

        # Collision
        hits = []
        for m in monsters:
            if m.is_dead():
                continue
            if id(m) in self._hit_set:
                continue
            dist = math.hypot(m.x - self.x, m.y - self.y)
            if dist <= self.radius + m.SIZE:
                self._hit_set.add(id(m))
                dmg = max(1, self.damage + random.randint(-3, 5))
                m.take_damage(dmg)
                hits.append((m, dmg))
                if not self.pierce:
                    self._explode_aoe(monsters, [m])
                    self.kill()
                    return hits

        return hits

    def _explode_aoe(self, monsters: list, already_hit: list):
        if self.aoe_r <= 0:
            return
        for m in monsters:
            if m.is_dead() or m in already_hit:
                continue
            if math.hypot(m.x - self.x, m.y - self.y) <= self.aoe_r + m.SIZE:
                dmg = max(1, self.damage // 2 + random.randint(-2, 3))
                m.take_damage(dmg)

    # ── Draw ──────────────────────────────────────────────────────────────

    def draw(self, screen, camera):
        if not self._alive:
            return

        sx = int(self.x - camera.offset_x)
        sy = int(self.y - camera.offset_y)

        if not (-80 <= sx <= camera.view_w + 80 and
                -80 <= sy <= camera.view_h + 80):
            return

        # Trail
        trail_surf = pygame.Surface(
            (camera.view_w, camera.view_h), pygame.SRCALPHA)
        for tx, ty, age in self._trail:
            tsx  = int(tx - camera.offset_x)
            tsy  = int(ty - camera.offset_y)
            frac = max(0.0, 1.0 - age / 0.22)
            r    = max(1, int(self.radius * frac * 0.65))
            a    = int(160 * frac)
            c    = (*self.color, a)
            pygame.draw.circle(trail_surf, c, (tsx, tsy), r)
        screen.blit(trail_surf, (0, 0))

        # AOE preview ring (when about to expire near range)
        if self.aoe_r > 0:
            remaining_frac = 1.0 - self._dist_travelled / self.range_px
            if remaining_frac < 0.25:
                aoe_surf = pygame.Surface(
                    (camera.view_w, camera.view_h), pygame.SRCALPHA)
                a = int(60 * remaining_frac / 0.25)
                pygame.draw.circle(aoe_surf, (*self.color, a),
                                   (sx, sy), self.aoe_r, 2)
                screen.blit(aoe_surf, (0, 0))

        # Core glow
        pulse = 0.85 + 0.15 * math.sin(self._anim * 14)
        glr   = max(1, int(self.radius * 1.6 * pulse))
        glow  = pygame.Surface((glr * 2 + 4, glr * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.color, 80), (glr + 2, glr + 2), glr)
        screen.blit(glow, (sx - glr - 2, sy - glr - 2))

        # Core orb
        pygame.draw.circle(screen, (10, 10, 10), (sx, sy), self.radius + 1)
        pygame.draw.circle(screen, self.color, (sx, sy), self.radius)
        bright = tuple(min(255, c + 90) for c in self.color)
        pygame.draw.circle(screen, bright, (sx - 1, sy - 1), max(1, self.radius // 2))


# ── AOE explosion visual (spawned when a fireball-type hits) ──────────────────

class Explosion:
    """Efecto visual de explosión AOE, sin lógica de daño."""

    def __init__(self, x: float, y: float, radius: int, color: tuple):
        self.x      = float(x)
        self.y      = float(y)
        self.max_r  = radius
        self.color  = color
        self._life  = 0.38
        self._age   = 0.0
        self._alive = True

    def update(self, dt: float):
        self._age  += dt
        self._life -= dt
        if self._life <= 0:
            self._alive = False

    def is_alive(self) -> bool:
        return self._alive

    def draw(self, screen, camera):
        if not self._alive:
            return
        sx    = int(self.x - camera.offset_x)
        sy    = int(self.y - camera.offset_y)
        frac  = min(1.0, self._age / 0.38)
        r     = max(2, int(self.max_r * (frac ** 0.5)))
        alpha = int(210 * (1.0 - frac))
        surf  = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        cx    = r + 4
        pygame.draw.circle(surf, (*self.color, alpha), (cx, cx), r)
        pygame.draw.circle(surf, (255, 240, 200, alpha // 2), (cx, cx), r, 2)
        screen.blit(surf, (sx - cx, sy - cx))
