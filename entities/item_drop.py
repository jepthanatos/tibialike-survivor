"""
entities/item_drop.py
Item caído en el suelo: visual, animación y pickup.
"""
import pygame
import math
from systems.loot import RARITY

PICKUP_RADIUS = 38.0   # px hasta el centro del item

SLOT_LETTER = {
    'weapon': 'W', 'armor': 'A', 'helmet': 'H',
    'shield': 'S', 'ring': 'R', 'amulet': 'M',
}

_fonts: dict = {}

def _font(name, size, bold=False):
    key = (name, size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont(name, size, bold=bold)
    return _fonts[key]


class ItemDrop:
    def __init__(self, x: float, y: float, item: dict):
        self.x    = float(x)
        self.y    = float(y)
        self.item = item
        self._timer     = 0.0
        self._picked_up = False

    # ── Estado ────────────────────────────────────────────────────────────────

    def is_picked_up(self) -> bool:
        return self._picked_up

    def pickup(self):
        self._picked_up = True

    def near_player(self, player) -> bool:
        return math.hypot(self.x - player.x, self.y - player.y) <= PICKUP_RADIUS

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float):
        if not self._picked_up:
            self._timer += dt

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen, camera, player):
        if self._picked_up:
            return

        sx = int(self.x - camera.offset_x)
        sy = int(self.y - camera.offset_y)

        if not (-50 <= sx <= camera.view_w + 50 and
                -50 <= sy <= camera.view_h + 50):
            return

        bob      = int(math.sin(self._timer * 3.2) * 3)
        sy_draw  = sy + bob
        color    = RARITY[self.item['rarity']]['color']
        slot     = self.item['slot']
        letter   = SLOT_LETTER.get(slot, '?')
        nearby   = self.near_player(player)

        # ── Glow ──────────────────────────────────────────────────────────
        pulse = int(55 + 35 * math.sin(self._timer * 2.8))
        glow  = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, pulse), (15, 15), 13)
        screen.blit(glow, (sx - 15, sy_draw - 15))

        # ── Orb ───────────────────────────────────────────────────────────
        pygame.draw.circle(screen, (20, 20, 20), (sx, sy_draw), 9)
        pygame.draw.circle(screen, color,        (sx, sy_draw), 8)
        # Glint
        glint = tuple(min(255, c + 80) for c in color)
        pygame.draw.circle(screen, glint, (sx - 2, sy_draw - 2), 3)

        # ── Slot letter ───────────────────────────────────────────────────
        f = _font("Arial", 10, bold=True)
        lt = f.render(letter, True, (255, 255, 255))
        screen.blit(lt, (sx - lt.get_width() // 2, sy_draw - lt.get_height() // 2))

        # ── Name + hint when player is nearby ─────────────────────────────
        if nearby:
            nf      = _font("Arial", 13)
            name_s  = nf.render(self.item['name'], True, color)
            hint_s  = nf.render("[F] Pick up", True, (200, 200, 200))
            nx      = sx - name_s.get_width() // 2
            screen.blit(name_s, (nx, sy_draw - 30))
            screen.blit(hint_s, (sx - hint_s.get_width() // 2, sy_draw - 16))
