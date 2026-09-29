import pygame
import math
from constants import *
from systems.loot      import RARITY
from systems.inventory import SLOTS
from systems.storm import STATE_WAITING, STATE_CLOSING, STATE_DONE

_SLOT_LETTER = {'weapon':'W','armor':'A','helmet':'H','boots':'B','ring':'R','amulet':'M'}


class HUD:
    def __init__(self, screen_w, screen_h):
        self.sw = screen_w
        self.sh = screen_h
        self._f_lg = pygame.font.SysFont("Arial", 22, bold=True)
        self._f_md = pygame.font.SysFont("Arial", 16)
        self._f_sm = pygame.font.SysFont("Arial", 13)
        self._f_xs = pygame.font.SysFont("Arial", 11)
        self._f_storm = pygame.font.SysFont("Arial", 14, bold=True)

        # Tibia-style HUD: dark brown/wood panel
        self._bg = pygame.Surface((screen_w, HUD_H))
        self._bg.fill((40, 28, 12))            # dark brown base
        pygame.draw.line(self._bg, (100, 70, 20), (0, 0), (screen_w, 0), 2)  # gold top border
        pygame.draw.line(self._bg, (20, 12, 4),   (0, 1), (screen_w, 1), 1)  # shadow
        self._pulse = 0.0

    # ── Main draw ─────────────────────────────────────────────────────────────
    def draw(self, screen, player, elapsed, monster_count, storm=None):
        hy = GAME_H
        screen.blit(self._bg, (0, hy))
        self._pulse += 0.07

        # HP / MP / XP bars
        self._bar(screen, 10, hy+8,  195, 22, player.hp, player.max_hp, C_HP_BAR, C_HP_BG, "HP")
        self._bar(screen, 10, hy+34, 195, 22, player.mp, player.max_mp, C_MP_BAR, C_MP_BG, "MP")
        self._bar(screen, 10, hy+60, 195, 14, player.xp, player.max_xp, C_XP_BAR, C_XP_BG, "XP")

        # Level + vocation
        voc_name = getattr(player, 'vocation', 'player').capitalize()
        lv = self._f_lg.render(f"Lv.{player.level}", True, C_YELLOW)
        vc = self._f_xs.render(voc_name, True, C_GRAY)
        screen.blit(lv, (214, hy + 6))
        screen.blit(vc, (214, hy + 26))

        # ATK cooldown
        if player.attack_ready:
            screen.blit(self._f_sm.render("ATK READY", True, C_GREEN), (214, hy+38))
        else:
            screen.blit(self._f_sm.render("ATK CD", True, C_ORANGE), (214, hy+38))
            pygame.draw.rect(screen, C_DARK_GRAY, (214, hy+52, 82, 5))
            fw = int(82 * player.attack_cooldown_progress)
            pygame.draw.rect(screen, C_ORANGE, (214, hy+52, fw, 5))

        # Stats
        stat_txt = f"ATK {player.attack_damage}"
        if player.defense:   stat_txt += f"  DEF {player.defense}"
        if player.hp_regen:  stat_txt += f"  REG {player.hp_regen:.1f}/s"
        screen.blit(self._f_xs.render(stat_txt, True, C_GRAY), (214, hy+60))

        # Timer (centre)
        mins, secs = int(elapsed)//60, int(elapsed)%60
        t = self._f_lg.render(f"{mins:02d}:{secs:02d}", True, C_WHITE)
        screen.blit(t, (self.sw//2 - t.get_width()//2, hy+8))

        # Enemy count
        mc = self._f_md.render(f"Enemies: {monster_count}", True, C_GRAY)
        screen.blit(mc, (self.sw//2 - mc.get_width()//2, hy+34))

        # Storm panel
        if storm is not None:
            self._draw_storm_panel(screen, storm, hy)

        # Quick equip bar
        self._draw_quick_equip(screen, player, hy)

        # Hint
        hint = self._f_xs.render(
            "WASD: Mover  |  Click: Atacar  |  F: Recoger  |  I: Inventario  |  R: Reiniciar  |  ESC: Salir",
            True, (70, 70, 70))
        screen.blit(hint, (self.sw - hint.get_width() - 6, hy + HUD_H - 16))

    # ── Storm panel ───────────────────────────────────────────────────────────
    def _draw_storm_panel(self, screen, storm, hy):
        px = self.sw // 2 - 60
        py = hy + 52

        state = storm.state
        phase = storm.phase_name

        if state == STATE_DONE:
            pulse_alpha = int(180 + 70 * math.sin(self._pulse * 0.7))
            col = (min(255, 220 + 35), 50, 50, pulse_alpha)
            label = self._f_storm.render("⚠  COLAPSO", True, C_STORM_DANGER)
        elif state == STATE_WAITING:
            t   = storm.timer
            col = C_STORM_SAFE if t > 15 else C_STORM_DANGER
            label = self._f_storm.render(
                f"✔ {phase}  |  Cierra en {int(t)}s", True, col)
        else:   # CLOSING
            prog  = storm.closing_progress
            pulse = int(200 + 55 * math.sin(self._pulse * 0.5))
            label = self._f_storm.render(
                f"▶ {phase}  CERRANDO", True, (pulse, 80, 220))

        screen.blit(label, (px, py))

        # Barra de progreso del cierre
        if state == STATE_CLOSING:
            bw = 160; bh = 5
            bx = px
            by = py + 20
            pygame.draw.rect(screen, C_DARK_GRAY, (bx, by, bw, bh))
            pygame.draw.rect(screen, C_STORM_EDGE,
                             (bx, by, int(bw * storm.closing_progress), bh))
            pygame.draw.rect(screen, C_GRAY, (bx, by, bw, bh), 1)

        # DPS indicator
        dps_s = self._f_xs.render(f"DPS tormenta: {storm.current_dps:.0f}", True, (140, 80, 180))
        screen.blit(dps_s, (px, py + 28))

    # ── Quick equip bar ───────────────────────────────────────────────────────
    def _draw_quick_equip(self, screen, player, hy):
        inv = player.inventory
        sz  = 34; gap = 4
        total = len(SLOTS) * (sz + gap) - gap
        sx = self.sw - total - 130
        sy = hy + (HUD_H - sz) // 2

        for i, slot in enumerate(SLOTS):
            x    = sx + i * (sz + gap)
            item = inv.equipped.get(slot)
            bg   = (28, 28, 36) if item else (18, 18, 22)
            pygame.draw.rect(screen, bg, (x, sy, sz, sz), border_radius=4)
            border = RARITY[item['rarity']]['color'] if item else (50, 50, 60)
            pygame.draw.rect(screen, border, (x, sy, sz, sz), 1, border_radius=4)
            letter = _SLOT_LETTER[slot]
            lt = self._f_sm.render(letter, True, border if item else (50, 50, 60))
            screen.blit(lt, (x+(sz-lt.get_width())//2, sy+(sz-lt.get_height())//2))

        lbl = self._f_xs.render("[I] inventario", True, (70, 70, 80))
        screen.blit(lbl, (sx + total//2 - lbl.get_width()//2, sy - 14))

    # ── Minimap ───────────────────────────────────────────────────────────────
    def draw_minimap(self, screen, world, player, monsters, storm=None, bots=None):
        mm_surf, MM = world.get_minimap()
        mm   = mm_surf.copy()
        ww   = world.width  * world.tile_size
        wh   = world.height * world.tile_size

        # Zone rings on minimap (concentric danger zones)
        from systems.zones import ZONE_THRESHOLDS, ZONE_COLORS
        cen_mm = MM // 2
        map_r  = min(ww, wh) // 2
        for i, threshold in enumerate(ZONE_THRESHOLDS):
            ring_r = int(threshold * map_r * MM / min(ww, wh))
            if ring_r > 0:
                col = ZONE_COLORS[i]
                ring_surf = pygame.Surface((MM, MM), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (*col, 35), (cen_mm, cen_mm), ring_r)
                pygame.draw.circle(ring_surf, (*col, 80), (cen_mm, cen_mm), ring_r, 1)
                mm.blit(ring_surf, (0,0))

        # Storm ring on minimap
        if storm is not None:
            cx_mm = int(storm.center_x * MM / ww)
            cy_mm = int(storm.center_y * MM / wh)
            r_mm  = int(storm.radius   * MM / min(ww, wh))
            if r_mm > 0:
                pygame.draw.circle(mm, C_STORM_EDGE, (cx_mm, cy_mm), r_mm, 1)
            # Next zone ring
            nr_mm = int(storm.next_radius * MM / min(ww, wh))
            if 0 < nr_mm < r_mm:
                pygame.draw.circle(mm, C_STORM_NEXT, (cx_mm, cy_mm), nr_mm, 1)

        for m in monsters:
            mx = int(m.x * MM / ww); my = int(m.y * MM / wh)
            if 0 <= mx < MM and 0 <= my < MM:
                mm.set_at((mx, my), (220, 50, 50))

        px = max(0, min(MM-1, int(player.x * MM / ww)))
        py = max(0, min(MM-1, int(player.y * MM / wh)))
        pygame.draw.circle(mm, (255, 255, 255), (px, py), 2)

        # Bot dots: yellow squares
        _bot_colors = [(255,200,0),(255,140,0),(255,80,0),(200,255,0)]
        for i, bot in enumerate(bots or []):
            if bot.is_dead(): continue
            bx = int(bot.x * MM / ww); by = int(bot.y * MM / wh)
            if 0 <= bx < MM-1 and 0 <= by < MM-1:
                col = _bot_colors[i % len(_bot_colors)]
                pygame.draw.rect(mm, col, (bx-1, by-1, 3, 3))

        pygame.draw.rect(mm, (150, 150, 150), (0, 0, MM, MM), 1)
        screen.blit(mm, (self.sw - MM - 8, 8))

    # ── Bar helper ────────────────────────────────────────────────────────────
    def _bar(self, screen, x, y, w, h, val, maxv, fill, bg, label):
        # Tibia-style sunken bar with raised border
        pygame.draw.rect(screen, (0, 0, 0),      (x-1, y-1, w+2, h+2))  # outer black border
        pygame.draw.rect(screen, bg,              (x, y, w, h))           # empty background
        if maxv > 0:
            fw = int(w * max(0.0, val) / maxv)
            if fw > 0:
                pygame.draw.rect(screen, fill,   (x, y, fw, h))
                # Thin highlight strip on top (Tibia's shiny bar look)
                hi = tuple(min(255, c+50) for c in fill)
                pygame.draw.rect(screen, hi,     (x, y, fw, max(1, h//3)))
        # Sunken border: dark top/left, lighter bottom/right
        pygame.draw.line(screen, (0,0,0),        (x,   y),   (x+w, y),   1)
        pygame.draw.line(screen, (0,0,0),        (x,   y),   (x,   y+h), 1)
        pygame.draw.line(screen, (100, 70, 20),  (x,   y+h), (x+w, y+h), 1)
        pygame.draw.line(screen, (100, 70, 20),  (x+w, y),   (x+w, y+h), 1)
        # Label text
        txt = self._f_sm.render(f"{label}: {int(val)}/{int(maxv)}", True, C_WHITE)
        screen.blit(txt, (x+4, y+(h-txt.get_height())//2))

    # ── Biome badge ───────────────────────────────────────────────────────────
    def draw_biome_badge(self, screen, biome_name: str):
        """Small biome name indicator in the HUD centre-right area."""
        from systems.biomes import BIOMES
        bd    = BIOMES.get(biome_name, BIOMES["grassland"])
        color = bd["color"]
        icon  = bd["icon"]
        name  = bd["name"]
        hy    = GAME_H
        text  = self._f_sm.render(f"{icon}  {name}", True, color)
        sx    = self.sw // 2 + 80
        sy    = hy + 52
        # small background
        import pygame
        bg = pygame.Surface((text.get_width()+12, text.get_height()+4), pygame.SRCALPHA)
        bg.fill((10,10,20,180))
        screen.blit(bg, (sx-6, sy-2))
        screen.blit(text, (sx, sy))

    # ── Skills HUD ────────────────────────────────────────────────────────────
    def draw_skills(self, screen, player):
        """Compact skills display in bottom-right corner of the HUD bar."""
        import pygame
        from systems.skills import SKILL_NAMES, xp_for_level
        sk = getattr(player, 'skills', None)
        if sk is None:
            return

        # Position: bottom-right of HUD bar
        hy = GAME_H
        x  = self.sw - 220
        y  = hy + 8

        # Primary skill (largest display)
        primary = sk.primary_skill()
        lv      = sk.levels[primary]
        xp      = sk.xp[primary]
        req     = xp_for_level(lv)
        pct     = min(1.0, xp / req) if req > 0 else 1.0
        name    = SKILL_NAMES.get(primary, primary)

        # Background
        bg = pygame.Surface((210, HUD_H - 10), pygame.SRCALPHA)
        bg.fill((8, 8, 20, 160))
        screen.blit(bg, (x - 4, y - 2))

        # Primary skill name + level
        lbl = self._f_sm.render(f"{name}  {lv}", True, (100, 200, 255))
        screen.blit(lbl, (x, y))

        # XP bar
        bw, bh = 140, 6
        pygame.draw.rect(screen, (20, 20, 40), (x, y + 14, bw, bh))
        pygame.draw.rect(screen, (80, 180, 255), (x, y + 14, int(bw * pct), bh))
        pygame.draw.rect(screen, (50, 80, 120), (x, y + 14, bw, bh), 1)

        xp_lbl = self._f_xs.render(f"{int(xp)}/{req} xp", True, (120, 130, 160))
        screen.blit(xp_lbl, (x + bw + 4, y + 12))

        # Secondary skills compact row
        y2 = y + 26
        other = [(s, sk.levels[s]) for s in sk.levels if s != primary][:4]
        col_w = 48
        for i, (skill, level) in enumerate(other):
            short = SKILL_NAMES.get(skill, skill)[:3]
            s = self._f_xs.render(f"{short}{level}", True, (140, 140, 160))
            screen.blit(s, (x + i * col_w, y2))

    # ── Zone indicator ────────────────────────────────────────────────────────
    def draw_zone_indicator(self, screen, player_x, player_y, map_w, map_h):
        """Shows current danger zone in bottom HUD bar."""
        import pygame
        from systems.zones import get_zone, get_zone_name, get_zone_color
        map_cx = (map_w // 2) * TILE_SIZE
        map_cy = (map_h // 2) * TILE_SIZE
        map_r  = min(map_w, map_h) // 2 * TILE_SIZE
        zone   = get_zone(player_x, player_y, map_cx, map_cy, map_r)
        name   = get_zone_name(zone)
        color  = get_zone_color(zone)
        hy     = GAME_H
        # Background pill
        label  = self._f_sm.render(f"Zona: {name}", True, color)
        bx     = self.sw // 2 - label.get_width() // 2 - 6
        by     = hy + HUD_H // 2 - label.get_height() // 2 - 2
        bg     = pygame.Surface((label.get_width() + 12, label.get_height() + 4), pygame.SRCALPHA)
        bg.fill((*color, 35))
        screen.blit(bg, (bx, by))
        pygame.draw.rect(screen, (*color, 120), (bx, by, bg.get_width(), bg.get_height()), 1, border_radius=4)
        screen.blit(label, (bx + 6, by + 2))
