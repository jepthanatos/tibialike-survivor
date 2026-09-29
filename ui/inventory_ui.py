"""
ui/inventory_ui.py
Panel de inventario: equipamiento + bolsa.  Tecla I para abrir/cerrar.
"""
import pygame
from systems.loot      import RARITY
from systems.inventory import SLOTS
from systems.inventory import MAX_BAG_SIZE
from constants import *

# ── Layout ────────────────────────────────────────────────────────────────────
PANEL_W = 660
PANEL_H = 440
SLOT_W  = 270
BAG_COLS = 4
BAG_ROWS = 5
CELL_SZ  = 72   # px por celda de bolsa

SLOT_LABELS = {
    'weapon': '⚔  Weapon',
    'armor':  '🛡  Armor',
    'helmet': '🪖  Helmet',
    'shield': '🔰  Shield',
    'ring':   '💍  Ring',
    'amulet': '📿  Amulet',
}


class InventoryUI:
    def __init__(self, screen_w: int, screen_h: int):
        self.sw = screen_w
        self.sh = screen_h

        self._f_title  = pygame.font.SysFont("Arial", 22, bold=True)
        self._f_label  = pygame.font.SysFont("Arial", 15, bold=True)
        self._f_body   = pygame.font.SysFont("Arial", 13)
        self._f_small  = pygame.font.SysFont("Arial", 11)
        self._f_hint   = pygame.font.SysFont("Arial", 13)

        # Overlay semi-transparente (precalculado)
        self._overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 155))

        self._hover_item: dict | None = None   # para tooltip
        self._hover_rect: pygame.Rect | None = None

    # ── Rects de referencia ───────────────────────────────────────────────────

    def _panel_rect(self) -> pygame.Rect:
        px = (self.sw - PANEL_W) // 2
        py = (self.sh - PANEL_H) // 2
        return pygame.Rect(px, py, PANEL_W, PANEL_H)

    def _equip_slot_rect(self, panel: pygame.Rect, idx: int) -> pygame.Rect:
        x = panel.x + 10
        y = panel.y + 55 + idx * 54
        return pygame.Rect(x, y, SLOT_W, 48)

    def _bag_cell_rect(self, panel: pygame.Rect, col: int, row: int) -> pygame.Rect:
        bx = panel.x + SLOT_W + 22
        by = panel.y + 55
        return pygame.Rect(bx + col * CELL_SZ, by + row * CELL_SZ, CELL_SZ, CELL_SZ)

    # ── Click handling ────────────────────────────────────────────────────────

    def handle_click(self, mx: int, my: int, inventory) -> str | None:
        """
        Procesa un clic del ratón.
        Devuelve un mensaje de notificación o None.
        """
        panel = self._panel_rect()

        # Clic en ranura de equipo → desequipar
        for idx, slot in enumerate(SLOTS):
            r = self._equip_slot_rect(panel, idx)
            if r.collidepoint(mx, my):
                item = inventory.equipped.get(slot)
                if item:
                    ok = inventory.unequip(slot)
                    return f"Unequipped {item['name']}" if ok else "Bag full!"
                return None

        # Clic en celda de bolsa → equipar
        for row in range(BAG_ROWS):
            for col in range(BAG_COLS):
                r   = self._bag_cell_rect(panel, col, row)
                idx = row * BAG_COLS + col
                if r.collidepoint(mx, my) and idx < len(inventory.bag):
                    item  = inventory.bag[idx]
                    ok, _ = inventory.equip(item)
                    return f"Equipped {item['name']}" if ok else "Bag full!"

        return None

    # ── Hover tracking ────────────────────────────────────────────────────────

    def update_hover(self, mx: int, my: int, inventory):
        panel = self._panel_rect()
        self._hover_item = None

        for idx, slot in enumerate(SLOTS):
            r = self._equip_slot_rect(panel, idx)
            if r.collidepoint(mx, my):
                self._hover_item = inventory.equipped.get(slot)
                self._hover_rect = r
                return

        for row in range(BAG_ROWS):
            for col in range(BAG_COLS):
                r   = self._bag_cell_rect(panel, col, row)
                idx = row * BAG_COLS + col
                if r.collidepoint(mx, my) and idx < len(inventory.bag):
                    self._hover_item = inventory.bag[idx]
                    self._hover_rect = r
                    return

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen, inventory, player):
        screen.blit(self._overlay, (0, 0))

        panel = self._panel_rect()
        pygame.draw.rect(screen, (18, 18, 22), panel, border_radius=10)
        pygame.draw.rect(screen, (80, 80, 90), panel, 2, border_radius=10)

        # Título
        title = self._f_title.render("INVENTORY  [I / ESC to close]", True, C_WHITE)
        screen.blit(title, (panel.x + (PANEL_W - title.get_width()) // 2, panel.y + 12))

        # Separador vertical
        sx = panel.x + SLOT_W + 16
        pygame.draw.line(screen, (70, 70, 80), (sx, panel.y + 45), (sx, panel.y + PANEL_H - 8))

        self._draw_equipment(screen, panel, inventory, player)
        self._draw_bag(screen, panel, inventory)
        if self._hover_item:
            self._draw_tooltip(screen, self._hover_item, self._hover_rect)

        # Hint footer
        hint = self._f_hint.render(
            "Click equipped slot to unequip  |  Click bag item to equip",
            True, (100, 100, 110))
        screen.blit(hint, (panel.x + (PANEL_W - hint.get_width()) // 2,
                           panel.y + PANEL_H - 20))

    def _draw_equipment(self, screen, panel, inventory, player):
        lbl = self._f_label.render("EQUIPMENT", True, C_YELLOW)
        screen.blit(lbl, (panel.x + 10, panel.y + 35))

        for idx, slot in enumerate(SLOTS):
            r    = self._equip_slot_rect(panel, idx)
            item = inventory.equipped.get(slot)

            bg = (30, 30, 36) if item else (22, 22, 28)
            pygame.draw.rect(screen, bg, r, border_radius=5)

            border_col = RARITY[item['rarity']]['color'] if item else (55, 55, 65)
            pygame.draw.rect(screen, border_col, r, 1, border_radius=5)

            # Slot label
            sl = self._f_small.render(SLOT_LABELS.get(slot, slot), True, C_GRAY)
            screen.blit(sl, (r.x + 6, r.y + 5))

            if item:
                col  = RARITY[item['rarity']]['color']
                name = self._f_body.render(item['name'], True, col)
                screen.blit(name, (r.x + 6, r.y + 22))

                # Stat resumido
                stats_str = self._short_stats(item['stats'])
                sv = self._f_small.render(stats_str, True, C_GRAY)
                screen.blit(sv, (r.x + 6, r.y + 35))
            else:
                empty = self._f_body.render("—  empty  —", True, (55, 55, 65))
                screen.blit(empty, (r.x + 6, r.y + 22))

        # Resumen de stats del jugador
        all_s  = inventory.all_stats
        sy_off = panel.y + 55 + len(SLOTS) * 54 + 6
        pieces = []
        if all_s.get('atk_damage'):  pieces.append(f"ATK +{int(all_s['atk_damage'])}")
        if all_s.get('defense'):     pieces.append(f"DEF {int(all_s['defense'])}")
        if all_s.get('max_hp'):      pieces.append(f"HP +{int(all_s['max_hp'])}")
        if pieces and sy_off < panel.y + PANEL_H - 25:
            sv = self._f_small.render("Total: " + "  ".join(pieces), True, C_GREEN)
            screen.blit(sv, (panel.x + 10, sy_off))

    def _draw_bag(self, screen, panel, inventory):
        bag_title = self._f_label.render(
            f"BAG  {len(inventory.bag)}/{MAX_BAG_SIZE}", True, C_YELLOW)
        bx = panel.x + SLOT_W + 22
        screen.blit(bag_title, (bx, panel.y + 35))

        for row in range(BAG_ROWS):
            for col in range(BAG_COLS):
                r   = self._bag_cell_rect(panel, col, row)
                idx = row * BAG_COLS + col

                if idx < len(inventory.bag):
                    item      = inventory.bag[idx]
                    color     = RARITY[item['rarity']]['color']
                    bg        = (28, 28, 36)
                    pygame.draw.rect(screen, bg, r, border_radius=4)
                    pygame.draw.rect(screen, color, r, 1, border_radius=4)

                    # Letra de slot
                    lt   = {'weapon':'W','armor':'A','helmet':'H',
                            'shield':'S','ring':'R','amulet':'M'}.get(item['slot'], '?')
                    ltc  = self._f_label.render(lt, True, color)
                    screen.blit(ltc, (r.x + (CELL_SZ - ltc.get_width()) // 2,
                                     r.y + 8))
                    # Nombre corto
                    short = item['name'][:9]
                    ns    = self._f_small.render(short, True, C_WHITE)
                    screen.blit(ns, (r.x + (CELL_SZ - ns.get_width()) // 2,
                                    r.y + 32))
                    # Nivel
                    lvs = self._f_small.render(f"i{item['item_level']}", True, C_GRAY)
                    screen.blit(lvs, (r.x + (CELL_SZ - lvs.get_width()) // 2,
                                     r.y + 46))
                else:
                    pygame.draw.rect(screen, (18, 18, 22), r, border_radius=4)
                    pygame.draw.rect(screen, (38, 38, 48), r, 1, border_radius=4)

    def _draw_tooltip(self, screen, item: dict, anchor: pygame.Rect):
        color    = RARITY[item['rarity']]['color']
        lines    = [
            (item['name'],       color,  self._f_label),
            (item['rarity'].capitalize(), C_GRAY, self._f_small),
            (f"Slot: {item['slot'].capitalize()}  |  iLv {item['item_level']}",
             C_GRAY, self._f_small),
            ("", C_GRAY, self._f_small),
        ]
        for stat, val in item['stats'].items():
            if stat in ('block_chance', 'xp_bonus', 'atk_speed', 'hp_regen'):
                lines.append((f"  {stat}: +{val*100:.1f}%", C_WHITE, self._f_body))
            else:
                lines.append((f"  {stat}: +{int(val)}", C_WHITE, self._f_body))

        tw = max((ln[2].size(ln[0])[0] for ln in lines if ln[0]), default=120) + 16
        th = sum(max(ln[2].size(ln[0])[1], 14) for ln in lines) + 16

        tx = min(anchor.x, self.sw - tw - 8)
        ty = anchor.y - th - 4
        if ty < 0:
            ty = anchor.y + anchor.height + 4

        pygame.draw.rect(screen, (12, 12, 16), (tx, ty, tw, th), border_radius=6)
        pygame.draw.rect(screen, color,        (tx, ty, tw, th), 1, border_radius=6)

        cy = ty + 8
        for text, col, font in lines:
            if text:
                surf = font.render(text, True, col)
                screen.blit(surf, (tx + 8, cy))
                cy += surf.get_height() + 2
            else:
                cy += 6

    @staticmethod
    def _short_stats(stats: dict) -> str:
        parts = []
        for k, v in list(stats.items())[:3]:
            if k in ('block_chance', 'xp_bonus', 'atk_speed', 'hp_regen'):
                parts.append(f"{k[:4]}+{v*100:.0f}%")
            else:
                short = {'atk_damage': 'ATK', 'max_hp': 'HP',
                         'defense': 'DEF', 'mp_bonus': 'MP',
                         'atk_range': 'RNG'}.get(k, k[:3])
                parts.append(f"{short}+{int(v)}")
        return "  ".join(parts)
