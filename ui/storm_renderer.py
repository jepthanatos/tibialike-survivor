"""
ui/storm_renderer.py
Renderizado visual de la tormenta:
  · Niebla semitransparente fuera del círculo seguro
  · Anillo de borde luminoso con pulso animado
  · Anillo azul punteado del siguiente círculo (durante WAITING)
  · Viñeta roja en bordes de pantalla cuando el jugador está fuera
  · Indicador de dirección hacia el centro si el jugador está fuera
"""
import pygame
import math
from systems.storm import STATE_CLOSING, STATE_DONE, STATE_WAITING
from constants import (
    C_STORM_FOG, C_STORM_EDGE, C_STORM_NEXT,
    C_STORM_DANGER, C_WHITE, C_YELLOW,
)

# Grosor del glow del borde (píxeles)
EDGE_RINGS   = 8
# Grosor del anillo del siguiente círculo
NEXT_RINGS   = 3
# Alfa base del fog exterior
FOG_ALPHA    = 155
# Tamaño del indicador de flecha
ARROW_SIZE   = 18


class StormRenderer:
    def __init__(self, view_w: int, view_h: int):
        self.vw = view_w
        self.vh = view_h
        self._fog_surf = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        self._vig_surf = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        self._build_vignette()
        self._time = 0.0

    def _build_vignette(self):
        """Superficie fija de viñeta roja en los bordes (se muestra solo fuera)."""
        self._vig_surf.fill((0, 0, 0, 0))
        for i in range(28):
            alpha = int(100 * (i / 28) ** 2)
            t = 28 - i
            pygame.draw.rect(
                self._vig_surf, (200, 30, 30, alpha),
                (t, t, self.vw - t * 2, self.vh - t * 2), 1
            )

    # ── Draw público ──────────────────────────────────────────────────────────

    def draw(self, screen, camera, storm, player_x: float, player_y: float):
        self._time += 0.016   # proxy de dt para pulsos

        cx_s, cy_s = camera.world_to_screen(storm.center_x, storm.center_y)
        r          = int(storm.radius)
        pulse      = 0.5 + 0.5 * math.sin(self._time * 2.8)

        # ── 1. Fog exterior ───────────────────────────────────────────────
        self._fog_surf.fill((*C_STORM_FOG, FOG_ALPHA))
        # Borrar el círculo seguro (transparencia total)
        if r > 0:
            pygame.draw.circle(self._fog_surf, (0, 0, 0, 0),
                               (int(cx_s), int(cy_s)), r)
        screen.blit(self._fog_surf, (0, 0))

        # ── 2. Anillo de borde con glow ───────────────────────────────────
        base_alpha = int(160 + 80 * pulse)
        for i in range(EDGE_RINGS, 0, -1):
            alpha = int(base_alpha * (i / EDGE_RINGS) ** 1.5)
            color = (*C_STORM_EDGE, alpha)
            # Dibujar sobre el fog: hacemos un ring en la posición adecuada
            glow_surf = pygame.Surface((self.vw, self.vh), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, color, (int(cx_s), int(cy_s)),
                               r + i, 1)
            screen.blit(glow_surf, (0, 0))

        # ── 3. Anillo del siguiente círculo (durante WAITING) ─────────────
        if storm.state == STATE_WAITING and storm.phase_number <= 5:
            nr = int(storm.next_radius)
            if nr > 0 and nr < r:
                ncx_s, ncy_s = camera.world_to_screen(storm.center_x, storm.center_y)
                for i in range(NEXT_RINGS):
                    alpha = int(100 + 80 * pulse) if i == 0 else 60
                    next_surf = pygame.Surface((self.vw, self.vh), pygame.SRCALPHA)
                    pygame.draw.circle(next_surf, (*C_STORM_NEXT, alpha),
                                       (int(ncx_s), int(ncy_s)), nr + i, 1)
                    screen.blit(next_surf, (0, 0))

                # Label punteado en el anillo
                lbl_f = pygame.font.SysFont("Arial", 11)
                lbl   = lbl_f.render("próxima zona", True, C_STORM_NEXT)
                lx    = int(ncx_s) - lbl.get_width() // 2
                ly    = int(ncy_s) - nr - 18
                if 0 <= lx <= self.vw and 0 <= ly <= self.vh:
                    screen.blit(lbl, (lx, ly))

        # ── 4. Indicador de dirección cuando el jugador está fuera ────────
        if not storm.player_inside(player_x, player_y):
            self._draw_direction_arrow(screen, camera, storm,
                                       player_x, player_y, pulse)
            screen.blit(self._vig_surf, (0, 0))

    # ── Flecha de dirección ───────────────────────────────────────────────────

    def _draw_direction_arrow(self, screen, camera, storm,
                              px, py, pulse):
        """Dibuja una flecha en el borde de la pantalla apuntando al centro."""
        dx = storm.center_x - px
        dy = storm.center_y - py
        angle = math.atan2(dy, dx)

        # Punto en el borde de la pantalla en esa dirección
        mid_x = self.vw / 2
        mid_y = self.vh / 2
        margin = 48

        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Clamp al borde del viewport con margen
        if abs(cos_a) > 1e-6:
            tx = mid_x + (self.vw / 2 - margin) * (1 if cos_a > 0 else -1)
            ty = mid_y + (tx - mid_x) * sin_a / cos_a
        else:
            tx = mid_x
            ty = mid_y + (self.vh / 2 - margin) * (1 if sin_a > 0 else -1)

        ty = max(margin, min(self.vh - margin, ty))
        tx = max(margin, min(self.vw - margin, tx))

        # Triángulo de flecha
        tip  = (int(tx + cos_a * ARROW_SIZE), int(ty + sin_a * ARROW_SIZE))
        perp = (-sin_a, cos_a)
        sz   = ARROW_SIZE * 0.55
        bl   = (int(tx - perp[0] * sz), int(ty - perp[1] * sz))
        br   = (int(tx + perp[0] * sz), int(ty + perp[1] * sz))

        alpha = int(180 + 60 * pulse)
        arrow_surf = pygame.Surface((self.vw, self.vh), pygame.SRCALPHA)
        pygame.draw.polygon(arrow_surf, (*C_STORM_DANGER, alpha), [tip, bl, br])
        pygame.draw.polygon(arrow_surf, (255, 255, 255, 200), [tip, bl, br], 1)
        screen.blit(arrow_surf, (0, 0))

        # Distancia al borde de la zona segura
        dist = storm.distance_outside(px, py)
        df   = pygame.font.SysFont("Arial", 12, bold=True)
        ds   = df.render(f"{int(dist)} px", True, C_STORM_DANGER)
        screen.blit(ds, (int(tx) - ds.get_width() // 2 + int(cos_a * 28),
                         int(ty) - ds.get_height() // 2 + int(sin_a * 28)))
