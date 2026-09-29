"""
ui/spell_bar.py
Barra de hechizos en la parte izquierda del juego (sobre el HUD).
Muestra: hechizos conocidos, seleccionado activo, cooldown de lanzamiento,
         progreso de observación de hechizos pendientes.
"""
import pygame
import math
from systems.spells import SPELL_CATALOGUE, MONSTER_SPELLS
from constants import C_WHITE, C_GRAY, C_DARK_GRAY, C_PURPLE, C_GREEN, C_ORANGE, C_YELLOW, GAME_H

CELL_W = 52
CELL_H = 52
GAP    = 4
MAX_VISIBLE = 7      # máximo de hechizos en pantalla a la vez

# Colores UI
C_SEL_BORDER  = (220, 200, 80)    # borde del hechizo seleccionado
C_LOCKED_FG   = (80, 80, 90)
C_OBS_BAR     = (80, 170, 255)


class SpellBar:
    def __init__(self, screen_w: int, screen_h: int):
        self.sw = screen_w
        self.sh = screen_h
        self._f_num  = pygame.font.SysFont("Arial", 13, bold=True)
        self._f_name = pygame.font.SysFont("Arial", 10)
        self._f_key  = pygame.font.SysFont("Arial", 11)
        self._f_lbl  = pygame.font.SysFont("Arial", 12, bold=True)
        self._time   = 0.0

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen, player):
        """Draw the spell bar vertically on the left side of the game area."""
        self._time += 0.016

        sm     = player.spell_memory
        known  = sm.known_spells
        sel    = player.selected_spell
        ml     = sm.magic_level

        # Panel header
        hdr = self._f_lbl.render(f"Magia Nv.{ml}", True, C_PURPLE)
        screen.blit(hdr, (6, 6))

        if not known:
            tip = self._f_name.render("Observa monstruos", True, (80, 80, 100))
            screen.blit(tip, (6, 24))
            tip2 = self._f_name.render("para aprender", True, (80, 80, 100))
            screen.blit(tip2, (6, 36))
            self._draw_pending_obs(screen, player, 52)
            return

        # Known spells (numbered 1..N)
        start_y = 26
        for i, sid in enumerate(known[:MAX_VISIBLE]):
            self._draw_spell_cell(screen, player, sid, i, start_y)

        # Pending observations below known spells
        obs_y = start_y + len(known[:MAX_VISIBLE]) * (CELL_H + GAP) + 8
        self._draw_pending_obs(screen, player, obs_y)

    def _draw_spell_cell(self, screen, player, sid: str, idx: int, start_y: int):
        sm    = player.spell_memory
        data  = SPELL_CATALOGUE.get(sid, {})
        color = data.get("color", (180, 180, 180))
        sel   = (player.selected_spell == sid)
        x     = 4
        y     = start_y + idx * (CELL_H + GAP)

        # Background
        bg = (22, 22, 32) if sel else (14, 14, 20)
        pygame.draw.rect(screen, bg, (x, y, CELL_W, CELL_H), border_radius=5)

        # Border
        border_col = C_SEL_BORDER if sel else (45, 45, 60)
        border_w   = 2 if sel else 1
        pygame.draw.rect(screen, border_col, (x, y, CELL_W, CELL_H), border_w, border_radius=5)

        # Color orb
        pulse = 0.8 + 0.2 * math.sin(self._time * 4) if sel else 1.0
        r     = int(13 * pulse)
        glow  = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, 130 if sel else 70), (r+2, r+2), r)
        screen.blit(glow, (x + CELL_W//2 - r - 2, y + 10 - r))
        pygame.draw.circle(screen, color, (x + CELL_W//2, y + 10), 9 if sel else 7)

        # Spell name (truncated)
        name = data.get("incantation", data.get("name", sid))[:12]
        nt   = self._f_name.render(name, True, color if sel else C_GRAY)
        screen.blit(nt, (x + CELL_W//2 - nt.get_width()//2, y + 24))

        # MP cost
        mp_t = self._f_name.render(f"MP:{data.get('mp_cost',0)}", True, (80, 120, 200))
        screen.blit(mp_t, (x + CELL_W//2 - mp_t.get_width()//2, y + 35))

        # Hotkey label
        key_t = self._f_key.render(f"[{idx+1}]", True, C_SEL_BORDER if sel else C_DARK_GRAY)
        screen.blit(key_t, (x + 2, y + 2))

        # Cooldown overlay
        if sel and not player.spell_ready:
            ov = pygame.Surface((CELL_W, CELL_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 110))
            screen.blit(ov, (x, y))

    def _draw_pending_obs(self, screen, player, start_y: int):
        """Shows spells the player has observed but not yet learned."""
        sm      = player.spell_memory
        pending = sm.pending_spells()
        if not pending:
            return

        lbl = self._f_name.render("Observando:", True, (100, 120, 160))
        screen.blit(lbl, (6, start_y))
        y = start_y + 14

        for sid in pending[:4]:
            data    = SPELL_CATALOGUE.get(sid, {})
            obs, th = sm.observation_progress(sid)
            color   = data.get("color", (150, 150, 150))
            name    = data.get("incantation", data.get("name", sid))[:14]
            ml_need = data.get("min_magic_lv", 0)
            ml_ok   = sm.magic_level >= ml_need

            nt = self._f_name.render(name, True, color if ml_ok else C_LOCKED_FG)
            screen.blit(nt, (6, y))

            # Progress bar
            bw = CELL_W - 4
            pygame.draw.rect(screen, C_DARK_GRAY, (6, y+12, bw, 4))
            fw = int(bw * min(1.0, obs / max(1, th)))
            pygame.draw.rect(screen, C_OBS_BAR if ml_ok else C_LOCKED_FG,
                             (6, y+12, fw, 4))
            prog_t = self._f_name.render(f"{obs}/{th}", True, C_GRAY)
            screen.blit(prog_t, (6+bw+2, y+8))

            if not ml_ok:
                req_t = self._f_name.render(f"Nv.M{ml_need}", True, C_ORANGE)
                screen.blit(req_t, (6, y+18))

            y += 35
            if y > GAME_H - 40:
                break
