"""
systems/boss.py
Sistema de jefes: spawneo periódico, seguimiento del jefe activo,
barra de HP en pantalla y loot garantizado al morir.
"""
from __future__ import annotations
import math
import random
import pygame

from systems.elites import roll_boss_mods, apply_modifiers, MODIFIERS
from systems.loot import generate_item

# ── Jefe activo global ────────────────────────────────────────────────────────

# Tiempo entre aparición de jefes (segundos desde el inicio de la partida)
BOSS_SPAWN_TIMES = [90, 180, 280, 400, 540]  # se puede extender
BOSS_TYPES = {
    "orc_warchief": {
        "base_type":  "orc",
        "name":       "Orc Warchief",
        "color":      (50, 160, 40),
        "size":       22,
        "hp_base":    420,
        "dmg_base":   42,
        "speed":      68.0,
        "xp_base":    280,
        "min_level":  10,
    },
    "lich": {
        "base_type":  "dark_wizard",
        "name":       "Lich",
        "color":      (140, 50, 220),
        "size":       18,
        "hp_base":    380,
        "dmg_base":   55,
        "speed":      52.0,
        "xp_base":    320,
        "min_level":  15,
    },
    "ancient_dragon": {
        "base_type":  "dragon",
        "name":       "Ancient Dragon",
        "color":      (200, 80, 30),
        "size":       28,
        "hp_base":    650,
        "dmg_base":   70,
        "speed":      58.0,
        "xp_base":    500,
        "min_level":  20,
    },
}


class BossManager:
    """Manages boss spawn timing, active boss tracking and on-screen UI."""

    def __init__(self):
        self.active_boss = None          # Monster instance
        self.boss_name   = ""
        self._next_idx   = 0            # index into BOSS_SPAWN_TIMES
        self._elapsed    = 0.0
        self._announced  = False
        self._announce_timer = 0.0

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float, player_level: int,
               world, player) -> "Monster | None":
        """
        Returns a new boss Monster if one should be spawned this frame,
        else None.  Clears dead active boss.
        """
        self._elapsed += dt

        if self._announce_timer > 0:
            self._announce_timer -= dt

        # Clear dead boss
        if self.active_boss is not None and self.active_boss.is_dead():
            self.active_boss = None
            self.boss_name   = ""

        # Don't spawn another if one is already alive
        if self.active_boss is not None:
            return None

        # Check spawn schedule
        if self._next_idx >= len(BOSS_SPAWN_TIMES):
            return None
        if self._elapsed < BOSS_SPAWN_TIMES[self._next_idx]:
            return None

        self._next_idx += 1

        boss = self._spawn_boss(player_level, world, player)
        if boss:
            self.active_boss     = boss
            self.boss_name       = boss.boss_display_name
            self._announced      = True
            self._announce_timer = 5.0   # seconds the announcement shows
        return boss

    # ── Spawn ─────────────────────────────────────────────────────────────────

    def _spawn_boss(self, player_level: int, world, player):
        from entities.monster import Monster

        # Pick an appropriate boss type
        eligible = [k for k, v in BOSS_TYPES.items()
                    if player_level >= v["min_level"]]
        if not eligible:
            eligible = list(BOSS_TYPES.keys())

        btype_id = random.choice(eligible)
        bdata    = BOSS_TYPES[btype_id]

        # Find a spawn position: 25-45 tiles from player, walkable
        ts = world.tile_size
        pc = int(player.x // ts)
        pr = int(player.y // ts)
        W, H = world.width, world.height

        for _ in range(60):
            angle = random.uniform(0, math.tau)
            dist  = random.randint(25, 45)
            col   = int(pc + math.cos(angle) * dist)
            row   = int(pr + math.sin(angle) * dist)
            if 5 <= col < W-5 and 5 <= row < H-5 and world.is_walkable(col, row):
                break
        else:
            col = max(5, min(W-5, pc + 30))
            row = max(5, min(H-5, pr + 30))

        x = col * ts + ts // 2
        y = row * ts + ts // 2

        # Create as a regular monster of the closest matching type,
        # then override stats
        base_type = bdata["base_type"]
        # Map to existing catalogue types for pathfinding/drawing
        _type_map = {
            "orc":         "skeleton",
            "dark_wizard": "skeleton",
            "dragon":      "skeleton",
        }
        mtype_for_ai = _type_map.get(base_type, "skeleton")

        boss = Monster(x, y, mtype_for_ai, player_level)

        # Override stats with boss values
        scale = 1.0 + player_level * 0.08
        boss.max_hp    = int(bdata["hp_base"]  * scale)
        boss.hp        = float(boss.max_hp)
        boss.damage    = int(bdata["dmg_base"] * scale)
        boss.speed     = bdata["speed"]
        boss.xp_reward = int(bdata["xp_base"]  * scale)
        boss.aggro_r   = 25
        boss.SIZE      = bdata["size"]
        boss.color     = bdata["color"]
        boss.outline   = tuple(max(0, c - 30) for c in bdata["color"])

        # Apply elite mods on top
        apply_modifiers(boss, roll_boss_mods())

        # Boss-specific tags
        boss.is_boss              = True
        boss.boss_display_name    = bdata["name"]
        boss.boss_type_id         = btype_id
        boss.guaranteed_loot_rarity = "rare"   # minimum rarity on death

        return boss

    # ── On boss death ─────────────────────────────────────────────────────────

    def on_boss_death(self, boss) -> list[dict]:
        """Generate guaranteed loot drops for the boss. Returns list of item dicts."""
        level = boss.level
        drops = [
            generate_item(level, rarity="rare"),
            generate_item(level, rarity=random.choice(["rare", "epic"])),
        ]
        return drops

    # ── UI ────────────────────────────────────────────────────────────────────

    def draw_boss_bar(self, screen: pygame.Surface, screen_w: int):
        """Draw boss HP bar at top-centre of screen when a boss is alive."""
        boss = self.active_boss
        if boss is None or boss.is_dead():
            return

        bw   = 420
        bh   = 24
        bx   = (screen_w - bw) // 2
        by   = 8
        frac = max(0.0, boss.hp / boss.max_hp)

        # Background
        pygame.draw.rect(screen, (20, 8, 8), (bx - 4, by - 4, bw + 8, bh + 8),
                         border_radius=6)
        pygame.draw.rect(screen, (50, 10, 10), (bx, by, bw, bh), border_radius=4)

        # HP fill with gradient-ish colour
        hp_color = (
            int(200 + 55 * (1-frac)),
            int(20 + 40 * frac),
            20
        )
        pygame.draw.rect(screen, hp_color, (bx, by, int(bw * frac), bh),
                         border_radius=4)

        # Border glow
        pygame.draw.rect(screen, (220, 80, 40), (bx, by, bw, bh), 2,
                         border_radius=4)

        # Name + HP text
        font_big = pygame.font.SysFont("Arial", 16, bold=True)
        font_sm  = pygame.font.SysFont("Arial", 12)
        name_surf = font_big.render(f"☠  {boss.boss_display_name}", True, (255, 200, 150))
        hp_surf   = font_sm.render(f"{int(boss.hp)} / {boss.max_hp}", True, (200, 200, 200))

        screen.blit(name_surf, (bx + bw // 2 - name_surf.get_width() // 2,
                                by + bh // 2 - name_surf.get_height() // 2))
        screen.blit(hp_surf, (bx + bw - hp_surf.get_width() - 6,
                               by + bh + 2))

        # Mod badges
        if hasattr(boss, "elite_mods"):
            xoff = bx
            for mid in boss.elite_mods:
                col  = MODIFIERS[mid]["color"]
                badge = font_sm.render(MODIFIERS[mid]["name"], True, col)
                screen.blit(badge, (xoff, by + bh + 2))
                xoff += badge.get_width() + 8

    def draw_announcement(self, screen: pygame.Surface, screen_w: int, screen_h: int):
        """Flashing warning when a boss first appears."""
        if self._announce_timer <= 0:
            return
        frac  = self._announce_timer / 5.0
        alpha = int(255 * min(1.0, frac * 2))
        font  = pygame.font.SysFont("Arial", 42, bold=True)
        surf  = font.render(f"☠  {self.boss_name}  ha aparecido  ☠", True, (255, 100, 50))
        surf.set_alpha(alpha)
        screen.blit(surf, (screen_w // 2 - surf.get_width() // 2, screen_h // 3))

    @property
    def announcement_active(self) -> bool:
        return self._announce_timer > 0

    @property
    def seconds_to_next_boss(self) -> float:
        if self._next_idx >= len(BOSS_SPAWN_TIMES):
            return -1.0
        return max(0.0, BOSS_SPAWN_TIMES[self._next_idx] - self._elapsed)
