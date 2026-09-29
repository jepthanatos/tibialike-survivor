"""
ui/stats_ui.py
══════════════════════════════════════════════════════════════
Tres pantallas:

  StatsOverlay   → panel in-game (tecla TAB), estadísticas de la partida actual
  RunSummaryUI   → pantalla de Game Over ampliada con resumen completo
  RankingsUI     → visor de rankings históricos (tecla TAB en Game Over)

Navegación en Game Over:
  R              → reiniciar
  TAB            → ciclar entre: Resumen run | Rankings | Histórico totales
  ESC            → salir
"""
from __future__ import annotations
import pygame
import math
from typing import Any

from systems.stats         import RunStats, RARITY_ORDER
from systems.lifetime_stats import LifetimeStats, RANKING_KEYS, _fmt_time
from systems.spells        import SPELL_CATALOGUE
from constants import (
    SCREEN_W, SCREEN_H, GAME_H, HUD_H,
    C_WHITE, C_GRAY, C_BLACK, C_YELLOW, C_GREEN, C_RED, C_CYAN,
    C_ORANGE, C_PURPLE, C_DARK_GRAY, C_STORM_EDGE,
)

# Colour palette for stats panels
_BG        = (10, 10, 18)
_PANEL_BG  = (16, 16, 28)
_BORDER    = (60, 60, 90)
_HDR       = (200, 170, 255)
_VAL       = (230, 230, 230)
_GOOD      = (80, 220, 100)
_WARN      = (255, 180, 40)
_GOLD      = (255, 210, 40)
_RARITY_C  = {
    "common":   (180, 180, 180),
    "uncommon": (55,  210,  80),
    "rare":     (80,  135, 245),
    "epic":     (210,  65, 245),
}

_MTYPE_COLOR = {
    "rat":         (142, 102,  62),
    "zombie":      ( 58, 132,  58),
    "skeleton":    (212, 210, 195),
    "orc":         ( 60, 145,  50),
    "dark_wizard": (140,  60, 210),
    "dragon":      (200,  80,  30),
}


def _font(size, bold=False):
    return pygame.font.SysFont("Arial", size, bold=bold)


def _render(font, text, color):
    return font.render(str(text), True, color)


def _bar(surface, x, y, w, h, frac, fill_col, bg_col=(30, 30, 40)):
    pygame.draw.rect(surface, bg_col, (x, y, w, h))
    if frac > 0:
        pygame.draw.rect(surface, fill_col, (x, y, int(w * min(1.0, frac)), h))
    pygame.draw.rect(surface, _BORDER, (x, y, w, h), 1)


def _section(surface, font, x, y, title):
    t = font.render(title, True, _HDR)
    surface.blit(t, (x, y))
    pygame.draw.line(surface, _BORDER, (x, y + t.get_height() + 1),
                     (x + 280, y + t.get_height() + 1))
    return y + t.get_height() + 4


# ── In-game overlay (Tab key) ─────────────────────────────────────────────────

class StatsOverlay:
    """Semi-transparent panel showing current-run stats while playing."""

    W = 420
    H = GAME_H

    def __init__(self):
        self._surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self._f_h  = _font(14, bold=True)
        self._f_b  = _font(13)
        self._f_s  = _font(11)
        self._time  = 0.0

    def draw(self, screen, run: RunStats, elapsed: float, player=None):
        self._time += 0.016
        if player is not None:
            self._player_skills = getattr(player, "skills", None)
        surf = self._surf
        surf.fill((8, 8, 20, 210))
        pygame.draw.rect(surf, _BORDER, (0, 0, self.W, self.H), 1)

        fh, fb, fs = self._f_h, self._f_b, self._f_s
        x, y = 10, 8

        # Title
        t = fh.render("⚔  ESTADÍSTICAS  [TAB cerrar]", True, _HDR)
        surf.blit(t, (self.W//2 - t.get_width()//2, y))
        y += t.get_height() + 6

        # ── Run info ──
        y = _section(surf, fh, x, y, "PARTIDA")
        rows = [
            ("Tiempo",   _fmt_time(elapsed)),
            ("Nivel",    run.level_reached or "—"),
            ("XP ganada", f"{run.xp_earned:,}"),
            ("Km recorridos", f"{run.km_walked:.2f}"),
            ("Fase tormenta", run.storm_phase or "—"),
            ("Tiempo en tormenta", _fmt_time(run.time_in_storm_s)),
            ("Mazmorras visitadas", run.dungeon_count),
        ]
        for label, val in rows:
            surf.blit(fs.render(label, True, _GRAY), (x + 4, y))
            surf.blit(fs.render(str(val), True, _VAL), (self.W - 130, y))
            y += 15

        y += 4
        # ── Kills ──
        y = _section(surf, fh, x, y, "BAJAS")
        surf.blit(fb.render(f"Total: {run.total_kills}", True, _GOLD), (x+4, y)); y += 17
        for mtype, count in sorted(run.kills.items(), key=lambda i: -i[1]):
            col = _MTYPE_COLOR.get(mtype, _VAL)
            surf.blit(fs.render(mtype.capitalize(), True, col), (x+8, y))
            surf.blit(fs.render(str(count), True, _VAL), (self.W-130, y))
            y += 14
        surf.blit(fs.render(f"Élites:  {run.elite_kills}", True, _WARN), (x+8, y)); y += 14
        surf.blit(fs.render(f"Jefes:   {run.boss_kills}", True, (255,120,40)), (x+8, y)); y += 16

        # ── Damage ──
        y = _section(surf, fh, x, y, "DAÑO INFLIGIDO")
        surf.blit(fs.render(f"Cuerpo a cuerpo: {run.melee_damage_dealt:,}", True, _VAL), (x+4, y)); y += 14
        surf.blit(fs.render(f"Hechizos:        {run.total_spell_damage:,}", True, C_PURPLE), (x+4, y)); y += 14
        surf.blit(fs.render(f"TOTAL:           {run.total_damage_dealt:,}", True, _GOLD), (x+4, y)); y += 16

        # ── Damage received ──
        y = _section(surf, fh, x, y, "DAÑO RECIBIDO")
        rows2 = [
            ("Monstruos",   run.damage_received - run.storm_damage),
            ("Tormenta",    run.storm_damage),
            ("Bloqueado",   run.damage_blocked),
            ("Veces golpeado", run.times_hit),
        ]
        for label, val in rows2:
            surf.blit(fs.render(label, True, _GRAY), (x+4, y))
            surf.blit(fs.render(f"{val:,}", True, _VAL), (self.W-130, y))
            y += 14
        y += 4

        # ── Skills ──
        from systems.skills import SKILL_NAMES, xp_for_level
        player_sk = getattr(self, '_player_skills', None)
        if player_sk is not None:
            y = _section(surf, fh, x, y, "SKILLS")
            bar_w = 110
            for skill, lv in player_sk.levels.items():
                xp  = player_sk.xp[skill]
                req = xp_for_level(lv)
                pct = min(1.0, xp / req) if req > 0 else 1.0
                nm_s = fs.render(SKILL_NAMES.get(skill, skill), True, _GRAY)
                lv_s = fs.render(str(lv), True, _GOLD)
                surf.blit(nm_s, (x+4, y))
                surf.blit(lv_s, (self.W - 130, y))
                bx = self.W - 110
                pygame.draw.rect(surf, (30, 30, 50),     (bx, y+3, bar_w, 7))
                pygame.draw.rect(surf, (80, 180, 255), (bx, y+3, int(bar_w*pct), 7))
                y += 14
            y += 4

        # ── Spells ──
        if run.spells_cast:
            y = _section(surf, fh, x, y, "HECHIZOS")
            for sid, cnt in sorted(run.spells_cast.items(), key=lambda i: -i[1]):
                data  = SPELL_CATALOGUE.get(sid, {})
                col   = data.get("color", _VAL)
                name  = data.get("name", sid)
                dmg   = run.spell_damage_dealt.get(sid, 0)
                surf.blit(fs.render(f"{name[:12]}", True, col), (x+4, y))
                surf.blit(fs.render(f"{cnt}× {dmg:,}dmg", True, _VAL), (self.W-155, y))
                y += 14

        # ── Items ──
        y += 4
        y = _section(surf, fh, x, y, "OBJETOS")
        surf.blit(fs.render(f"Encontrados:    {run.items_found}", True, _VAL), (x+4, y)); y += 14
        col_r = _RARITY_C.get(run.best_gear_rarity, _VAL)
        surf.blit(fs.render(f"Mejor rareza:   {run.best_gear_rarity.capitalize()}", True, col_r), (x+4, y)); y += 14

        # TAB hint at bottom
        hint = fs.render("TAB → cerrar", True, (60, 60, 80))
        surf.blit(hint, (self.W//2 - hint.get_width()//2, self.H - 18))

        screen.blit(surf, (SCREEN_W - self.W, 0))


_GRAY = (140, 140, 140)


# ── End-of-run summary ────────────────────────────────────────────────────────

# TAB pages in game-over screen
PAGE_SUMMARY  = 0
PAGE_RANKINGS = 1
PAGE_TOTALS   = 2
PAGE_HISTORY  = 3
PAGE_NAMES    = ["Resumen", "Rankings", "Totales vida", "Historial"]


class GameOverStats:
    """
    Full-screen stat view on game over.
    Replaces the old simple game-over screen.
    Pages cycled with TAB.
    """

    def __init__(self, screen_w, screen_h):
        self.sw = screen_w
        self.sh = screen_h
        self.page = PAGE_SUMMARY

        self._f_big  = _font(62, bold=True)
        self._f_hdr  = _font(22, bold=True)
        self._f_mid  = _font(17)
        self._f_body = _font(14)
        self._f_sm   = _font(12)

        self._scroll   = 0     # for history page
        self._rank_idx = 0     # selected ranking category

        # Build opaque background once
        self._bg = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        self._bg.fill((0, 0, 10, 195))

    def next_page(self):
        self.page = (self.page + 1) % 4
        self._scroll = 0

    def scroll(self, direction: int):
        self._scroll = max(0, self._scroll + direction * 22)

    def cycle_ranking(self, direction: int = 1):
        self._rank_idx = (self._rank_idx + direction) % len(RANKING_KEYS)

    def set_bots(self, bots):
        """Pass the bot list for ranking display."""
        self._bots = list(bots)

    def draw(self, screen, run: RunStats, lifetime: LifetimeStats, player, storm):
        screen.blit(self._bg, (0, 0))

        # ── Battle Royale ranking panel (always visible, bottom-left) ─────
        bots_ref = getattr(self, '_bots', [])
        if bots_ref:
            _all  = sorted(bots_ref + [player], key=lambda e: -getattr(e,'level',0))
            _lh   = 22 if len(_all) <= 8 else 14   # line height
            panel_h = 28 + len(_all) * _lh
            panel_y = max(8, self.sh - panel_h - 8)
            panel_bg = pygame.Surface((290, panel_h), pygame.SRCALPHA)
            panel_bg.fill((0, 0, 0, 170))
            screen.blit(panel_bg, (8, panel_y))
            fhdr = self._f_sm.render("RANKING FINAL", True, (220, 200, 60))
            screen.blit(fhdr, (16, panel_y + 4))
            medals = ["🥇","🥈","🥉","4°","5°"]
            for rank, entity in enumerate(_all):
                is_player = entity is player
                lv   = getattr(entity,'level', 0)
                dead = getattr(entity,'hp', 1) <= 0
                voc  = getattr(entity,'vocation','bot').capitalize() if is_player \
                       else f"Bot {getattr(entity,'_bot_idx',rank)+1}"
                col  = (255,220,60) if rank==0 else \
                       ((200,200,200) if is_player else (140,140,160))
                if dead: col = (80, 80, 80)
                medal = medals[rank] if rank < len(medals) else f"{rank+1}°"
                _f    = self._f_sm if _lh >= 18 else pygame.font.SysFont("Arial", 9)
                txt   = _f.render(f"{medal} Lv{lv} {voc[:9]}{' ☠' if dead else ''}", True, col)
                screen.blit(txt, (16, panel_y + 26 + rank * _lh))

        # Header strip
        pygame.draw.rect(screen, (20, 10, 35), (0, 0, self.sw, 62))
        pygame.draw.line(screen, _BORDER, (0, 62), (self.sw, 62))

        # YOU DIED
        died = self._f_big.render("YOU DIED", True, C_RED)
        screen.blit(died, (self.sw//2 - died.get_width()//2, -2))

        # Page tabs
        tab_w = self.sw // 4
        for i, name in enumerate(PAGE_NAMES):
            tx     = i * tab_w
            is_sel = (i == self.page)
            bg     = (40, 20, 70) if is_sel else (18, 10, 30)
            pygame.draw.rect(screen, bg, (tx, 64, tab_w, 26))
            pygame.draw.rect(screen, _BORDER if not is_sel else _HDR,
                             (tx, 64, tab_w, 26), 1)
            tsurf = self._f_sm.render(name, True, _HDR if is_sel else _GRAY)
            screen.blit(tsurf, (tx + tab_w//2 - tsurf.get_width()//2, 71))

        # Page body (below tabs)
        body_y = 96
        if self.page == PAGE_SUMMARY:
            self._draw_summary(screen, run, lifetime, player, storm, body_y)
        elif self.page == PAGE_RANKINGS:
            self._draw_rankings(screen, lifetime, body_y)
        elif self.page == PAGE_TOTALS:
            self._draw_totals(screen, lifetime, body_y)
        else:
            self._draw_history(screen, lifetime, body_y)

        # Bottom hint
        hint = self._f_sm.render(
            "R: Reiniciar  |  TAB: Cambiar página  |  ESC: Salir"
            + ("  |  ←→: Cambiar ranking" if self.page == PAGE_RANKINGS else "")
            + ("  |  ↑↓: Scroll" if self.page == PAGE_HISTORY else ""),
            True, (70, 70, 90))
        screen.blit(hint, (self.sw//2 - hint.get_width()//2, self.sh - 20))

    # ── Summary page ─────────────────────────────────────────────────────────
    def _draw_summary(self, screen, run: RunStats, lifetime: LifetimeStats, player, storm, y0):
        col_w = self.sw // 3
        fh, fb, fs = self._f_hdr, self._f_body, self._f_sm

        def kv(surface, x, y, label, val, col=_VAL):
            surface.blit(fs.render(label, True, _GRAY), (x, y))
            surface.blit(fb.render(str(val), True, col), (x + 190, y))
            return y + 18

        # ── Col 1: Run summary ──
        x1, y = 20, y0 + 6
        t = fh.render("RESUMEN", True, _HDR)
        screen.blit(t, (x1, y)); y += t.get_height() + 6
        m, s = int(run.elapsed_s)//60, int(run.elapsed_s)%60
        y = kv(screen, x1, y, "Tiempo",         f"{m:02d}:{s:02d}", _GOLD)
        y = kv(screen, x1, y, "Nivel final",    player.level,       C_YELLOW)
        y = kv(screen, x1, y, "XP ganada",      f"{run.xp_earned:,}")
        y = kv(screen, x1, y, "Fase tormenta",  run.storm_phase,    C_STORM_EDGE)
        y = kv(screen, x1, y, "En tormenta",    _fmt_time(run.time_in_storm_s), _WARN)
        y = kv(screen, x1, y, "Mazmorras",      run.dungeon_count)
        y = kv(screen, x1, y, "Km recorridos",  f"{run.km_walked:.2f} km")
        y += 8
        t2 = fh.render("BAJAS", True, _HDR); screen.blit(t2, (x1, y)); y += t2.get_height() + 4
        y = kv(screen, x1, y, "Total kills",    run.total_kills, _GOLD)
        for mtype, cnt in sorted(run.kills.items(), key=lambda i: -i[1]):
            col = _MTYPE_COLOR.get(mtype, _VAL)
            y = kv(screen, x1, y, f"  {mtype.capitalize()}", cnt, col)
        y = kv(screen, x1, y, "Élites",         run.elite_kills, _WARN)
        y = kv(screen, x1, y, "Jefes",          run.boss_kills,  (255,120,40))

        # ── Col 2: Damage ──
        x2, y2 = col_w + 10, y0 + 6
        t = fh.render("DAÑO INFLIGIDO", True, _HDR); screen.blit(t, (x2, y2)); y2 += t.get_height() + 6
        y2 = kv(screen, x2, y2, "Cuerpo a cuerpo", f"{run.melee_damage_dealt:,}")
        y2 = kv(screen, x2, y2, "Hechizos (total)", f"{run.total_spell_damage:,}", C_PURPLE)
        y2 = kv(screen, x2, y2, "TOTAL",            f"{run.total_damage_dealt:,}", _GOLD)

        if run.spells_cast:
            y2 += 8
            t2 = fh.render("HECHIZOS", True, _HDR); screen.blit(t2, (x2, y2)); y2 += t2.get_height() + 4
            for sid, cnt in sorted(run.spells_cast.items(), key=lambda i: -i[1]):
                data = SPELL_CATALOGUE.get(sid, {})
                dmg  = run.spell_damage_dealt.get(sid, 0)
                col  = data.get("color", _VAL)
                name = data.get("name", sid)
                screen.blit(fs.render(f"✦ {name}", True, col), (x2, y2))
                screen.blit(fs.render(f"{cnt}× castings  {dmg:,} dmg", True, _VAL), (x2+165, y2))
                y2 += 16
            y2 = kv(screen, x2, y2, "MP gastado", f"{run.mp_spent:,}", (80,120,220))

        if run.spells_learned:
            y2 += 6
            t3 = fh.render("APRENDIDOS", True, _HDR); screen.blit(t3, (x2, y2)); y2 += t3.get_height() + 4
            for sid in run.spells_learned:
                data = SPELL_CATALOGUE.get(sid, {})
                col  = data.get("color", _VAL)
                screen.blit(fs.render(f"  {data.get('name',sid)}", True, col), (x2, y2))
                y2 += 14

        # ── Col 3: Received & items ──
        x3, y3 = col_w * 2 + 10, y0 + 6
        t = fh.render("DAÑO RECIBIDO", True, _HDR); screen.blit(t, (x3, y3)); y3 += t.get_height() + 6
        y3 = kv(screen, x3, y3, "Monstruos",   f"{run.damage_received - run.storm_damage:,}", C_RED)
        y3 = kv(screen, x3, y3, "Tormenta",    f"{run.storm_damage:,}",    C_STORM_EDGE)
        y3 = kv(screen, x3, y3, "Bloqueado",   f"{run.damage_blocked:,}",  _GOOD)
        y3 = kv(screen, x3, y3, "Veces golpeado", run.times_hit)
        y3 += 10
        t2 = fh.render("OBJETOS", True, _HDR); screen.blit(t2, (x3, y3)); y3 += t2.get_height() + 4
        y3 = kv(screen, x3, y3, "Encontrados",  run.items_found)
        y3 = kv(screen, x3, y3, "Max equipados", run.items_equipped_peak)
        col_r = _RARITY_C.get(run.best_gear_rarity, _VAL)
        y3 = kv(screen, x3, y3, "Mejor rareza",
                run.best_gear_rarity.capitalize(), col_r)

        # Records broken?
        y3 += 14
        t3 = fh.render("NUEVOS RÉCORDS", True, _HDR); screen.blit(t3, (x3, y3)); y3 += t3.get_height() + 4
        checks = [
            (run.elapsed_s      > lifetime.records.get("longest_run_s", 0),      "⭐  Mejor supervivencia"),
            (run.level_reached  > lifetime.records.get("highest_level", 0),      "⭐  Nivel más alto"),
            (run.total_kills    > lifetime.records.get("most_kills_run", 0),      "⭐  Más kills en una run"),
            (run.total_damage_dealt > lifetime.records.get("most_damage_dealt_run",0), "⭐  Más daño infligido"),
            (run.boss_kills     > lifetime.records.get("most_bosses_run", 0),     "⭐  Más jefes derrotados"),
        ]
        any_record = False
        for cond, label in checks:
            if cond:
                screen.blit(fb.render(label, True, _GOLD), (x3, y3)); y3 += 18
                any_record = True
        if not any_record:
            screen.blit(fs.render("(sin nuevos récords)", True, _GRAY), (x3, y3))

    # ── Rankings page ─────────────────────────────────────────────────────────
    def _draw_rankings(self, screen, lifetime: LifetimeStats, y0):
        fh, fb, fs = self._f_hdr, self._f_body, self._f_sm
        rkeys      = RANKING_KEYS

        # Category selector tabs (horizontal)
        cat_w = self.sw // len(rkeys)
        for i, (key, field, label) in enumerate(rkeys):
            tx     = i * cat_w
            is_sel = (i == self._rank_idx)
            bg     = (40, 20, 70) if is_sel else (14, 8, 25)
            pygame.draw.rect(screen, bg, (tx, y0, cat_w, 24))
            pygame.draw.rect(screen, _BORDER if not is_sel else _HDR,
                             (tx, y0, cat_w, 24), 1)
            lbl = fs.render(label[:14], True, _HDR if is_sel else _GRAY)
            screen.blit(lbl, (tx + cat_w//2 - lbl.get_width()//2, y0 + 5))

        y = y0 + 34
        _, field, label = rkeys[self._rank_idx]
        title_s = fh.render(f"TOP {10}  —  {label}", True, _HDR)
        screen.blit(title_s, (self.sw//2 - title_s.get_width()//2, y)); y += title_s.get_height() + 8

        entries = lifetime.ranking(rkeys[self._rank_idx][0])
        if not entries:
            screen.blit(fb.render("Sin datos aún. ¡Juega más partidas!", True, _GRAY),
                        (self.sw//2 - 200, y))
            return

        # Table header
        cols = [("Pos", 50), ("Fecha", 160), ("Tiempo", 90),
                ("Nivel", 70), ("Kills", 70), (label[:14], 120)]
        cx   = 30
        for col_name, cw in cols:
            screen.blit(fs.render(col_name, True, _HDR), (cx, y))
            cx += cw
        y += 18
        pygame.draw.line(screen, _BORDER, (20, y), (self.sw-20, y))
        y += 4

        for rank, run in enumerate(entries, 1):
            row_col = _GOLD if rank == 1 else (_WARN if rank <= 3 else _VAL)
            cx = 30
            cells = [
                str(rank),
                run.get("date","?")[:10],
                _fmt_time(run.get("elapsed_s", 0)),
                str(run.get("level_reached", 0)),
                str(run.get("total_kills", 0)),
                self._fmt_field(field, run.get(field, 0)),
            ]
            for ci, (cell, (col_name, cw)) in enumerate(zip(cells, cols)):
                col = _GOLD if (ci == 5 and rank == 1) else row_col
                screen.blit(fs.render(cell, True, col), (cx, y))
                cx += cw

            # Mini kill bar
            if run.get("total_kills", 0) > 0:
                bar_x = self.sw - 200
                max_kills = entries[0].get("total_kills", 1)
                frac = run.get("total_kills", 0) / max(1, max_kills)
                _bar(screen, bar_x, y+2, 180, 10, frac, _GOOD)
            y += 22
            if y > self.sh - 50: break

    # ── Totals page ──────────────────────────────────────────────────────────
    def _draw_totals(self, screen, lifetime: LifetimeStats, y0):
        fh, fb, fs = self._f_hdr, self._f_body, self._f_sm
        t = lifetime.totals
        col_w = self.sw // 2

        def kv(x, y, label, val, col=_VAL):
            screen.blit(fs.render(label, True, _GRAY), (x, y))
            screen.blit(fb.render(str(val), True, col), (x + 220, y))
            return y + 18

        x1, y = 20, y0 + 6
        h = fh.render("VIDA COMPLETA", True, _HDR); screen.blit(h, (x1, y)); y += h.get_height() + 6
        y = kv(x1, y, "Partidas jugadas",  lifetime.total_runs(), _GOLD)
        y = kv(x1, y, "Tiempo total",      lifetime.total_playtime_str(), C_YELLOW)
        y = kv(x1, y, "Kills totales",     f"{t.get('total_kills',0):,}")
        y = kv(x1, y, "Élites totales",    f"{t.get('elite_kills',0):,}", _WARN)
        y = kv(x1, y, "Jefes totales",     f"{t.get('boss_kills',0):,}", (255,120,40))
        y = kv(x1, y, "Daño infligido",    f"{t.get('total_damage_dealt',0):,}")
        y = kv(x1, y, "Daño recibido",     f"{t.get('damage_received',0):,}", C_RED)
        y = kv(x1, y, "Daño bloqueado",    f"{t.get('damage_blocked',0):,}", _GOOD)
        y = kv(x1, y, "XP total",          f"{t.get('xp_earned',0):,}", _GOOD)
        y = kv(x1, y, "MP gastado",        f"{t.get('mp_spent',0):,}", (80,120,220))
        y = kv(x1, y, "Objetos hallados",  f"{t.get('items_found',0):,}")
        y = kv(x1, y, "Hechizos lanzados", f"{t.get('spells_cast_total',0):,}", C_PURPLE)
        y = kv(x1, y, "Km recorridos",     f"{t.get('distance_walked_km',0):.1f} km")

        # Kill breakdown by type
        y += 8
        h2 = fh.render("KILLS POR TIPO", True, _HDR); screen.blit(h2, (x1, y)); y += h2.get_height() + 4
        mtypes = ["rat","zombie","skeleton","orc","dark_wizard","dragon"]
        max_k  = max((t.get(f"kills_{mt}", 0) for mt in mtypes), default=1)
        for mt in mtypes:
            count = t.get(f"kills_{mt}", 0)
            col   = _MTYPE_COLOR.get(mt, _VAL)
            screen.blit(fs.render(mt.capitalize(), True, col), (x1+4, y))
            screen.blit(fs.render(str(count), True, _VAL), (x1+180, y))
            _bar(screen, x1+220, y+2, 130, 10, count/max(1,max_k), col)
            y += 16

        # Records
        x2, y2 = col_w + 10, y0 + 6
        h3 = fh.render("RÉCORDS ABSOLUTOS", True, _HDR); screen.blit(h3, (x2, y2)); y2 += h3.get_height() + 6
        recs = [
            ("Mejor supervivencia",  "longest_run_s",         True),
            ("Nivel más alto",       "highest_level",          False),
            ("Más kills en una run", "most_kills_run",         False),
            ("Más daño en una run",  "most_damage_dealt_run",  False),
            ("Más jefes en una run", "most_bosses_run",         False),
            ("Más élites en una run","most_elites_run",         False),
            ("Más XP en una run",    "most_xp_run",             False),
            ("Más hechizos",         "most_spells_cast_run",    False),
            ("Mayor distancia",      "furthest_walked_km",      True),
            ("Fase tormenta max",    "highest_storm_phase",     False),
            ("Objetos en una run",   "most_items_found_run",    False),
        ]
        for label, key, is_time in recs:
            val = lifetime.records.get(key, 0)
            fmt = _fmt_time(val) if is_time and not "km" in key else (
                  f"{val:.2f} km" if "km" in key else f"{int(val):,}")
            y2 = kv(x2, y2, label, fmt, _GOLD)

        # Spells learned ever
        learned_ever = t.get("spells_learned_ever", [])
        if learned_ever:
            y2 += 8
            h4 = fh.render("HECHIZOS APRENDIDOS (total vida)", True, _HDR)
            screen.blit(h4, (x2, y2)); y2 += h4.get_height() + 4
            for sid in learned_ever:
                data = SPELL_CATALOGUE.get(sid, {})
                col  = data.get("color", _VAL)
                screen.blit(fs.render(f"  ✦ {data.get('name',sid)}", True, col), (x2, y2))
                y2 += 14

        # Averages
        if lifetime.total_runs() > 1:
            y2 += 8
            h5 = fh.render("MEDIAS POR PARTIDA", True, _HDR)
            screen.blit(h5, (x2, y2)); y2 += h5.get_height() + 4
            avgs = [
                ("Tiempo medio",    _fmt_time(lifetime.average("elapsed_s"))),
                ("Kills medias",    f"{lifetime.average('total_kills'):.0f}"),
                ("Daño medio",      f"{lifetime.average('total_damage_dealt'):,.0f}"),
                ("XP media",        f"{lifetime.average('xp_earned'):,.0f}"),
            ]
            for label, val in avgs:
                y2 = kv(x2, y2, label, val, C_CYAN)

    # ── History page ─────────────────────────────────────────────────────────
    def _draw_history(self, screen, lifetime: LifetimeStats, y0):
        fh, fb, fs = self._f_hdr, self._f_body, self._f_sm
        runs       = list(reversed(lifetime.runs))   # newest first

        h = fh.render(f"HISTORIAL  ({len(runs)} partidas, más recientes primero)", True, _HDR)
        screen.blit(h, (self.sw//2 - h.get_width()//2, y0 + 2))

        # Column headers
        hdr_y = y0 + h.get_height() + 8
        headers = [("Fecha", 130), ("Tiempo", 80), ("Nivel", 55),
                   ("Kills", 55), ("Élites", 55), ("Jefes", 55),
                   ("Daño", 90), ("XP", 90), ("Fase ☁", 55), ("Km", 65)]
        cx = 14
        for col_name, cw in headers:
            screen.blit(fs.render(col_name, True, _HDR), (cx, hdr_y))
            cx += cw
        pygame.draw.line(screen, _BORDER, (8, hdr_y + 16), (self.sw - 8, hdr_y + 16))

        y     = hdr_y + 20
        start = self._scroll // 20
        for rank, run in enumerate(runs[start:], start + 1):
            if y > self.sh - 40:
                break
            row_bg = (20, 14, 35) if rank % 2 == 0 else (14, 10, 24)
            pygame.draw.rect(screen, row_bg, (8, y - 2, self.sw - 16, 20))

            cells = [
                run.get("date","?")[:10],
                _fmt_time(run.get("elapsed_s",0)),
                str(run.get("level_reached",0)),
                str(run.get("total_kills",0)),
                str(run.get("elite_kills",0)),
                str(run.get("boss_kills",0)),
                f"{run.get('total_damage_dealt',0):,}",
                f"{run.get('xp_earned',0):,}",
                str(run.get("storm_phase",0)),
                f"{run.get('distance_walked_km',0):.2f}",
            ]
            cx = 14
            for cell, (col_name, cw) in zip(cells, headers):
                col = _GOLD if col_name == "Nivel" else _VAL
                screen.blit(fs.render(cell, True, col), (cx, y))
                cx += cw
            y += 20

        if not runs:
            screen.blit(fb.render("Sin historial aún.", True, _GRAY),
                        (self.sw//2 - 100, y0 + 60))

    # ── Format field value for ranking table ─────────────────────────────────
    @staticmethod
    def _fmt_field(field: str, val) -> str:
        if field == "elapsed_s":
            return _fmt_time(val)
        if field == "distance_walked_km":
            return f"{float(val):.2f} km"
        return f"{int(val):,}"
