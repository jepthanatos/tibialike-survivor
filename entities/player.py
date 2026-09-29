import pygame
import math
import random
from constants import *
from systems.inventory import Inventory
from systems.spells import SpellMemory, SPELL_CATALOGUE, OBSERVE_RANGE
from systems.skills import Skills

# Tibia movement speeds (seconds per tile step)
WALK_DELAY = 0.18   # normal ground
FAST_DELAY = 0.12   # with speed boots etc.



# ── Tibia XP formula ──────────────────────────────────────────────────────────
def _tibia_xp_cumulative(lv: int) -> int:
    """Total XP needed to reach level `lv` from level 1."""
    if lv <= 1: return 0
    return (50 * (lv**3 - 5*lv**2 + 8*lv - 4)) // 3

def tibia_xp_for_next_level(lv: int) -> int:
    """XP needed to advance from level `lv` to `lv+1`."""
    return max(100, _tibia_xp_cumulative(lv+1) - _tibia_xp_cumulative(lv))


# ── Monster XP table (Tibia classic values) ───────────────────────────────────
MONSTER_XP = {
    "rat":         20,
    "zombie":      50,
    "skeleton":    35,
    "orc":        115,
    "dark_wizard": 385,
    "dragon":    4000,
    "demon":     6000,
    "dragon_lord":7200,
    "cyclops":900, "bear":100, "wolf":18,
    "fire_devil":200, "troll":55, "vampire":1200,
}


class Player:
    SIZE          = 18
    SPEED         = 132.0           # kept for compatibility (unused in tile movement)
    ATTACK_RANGE  = 72.0
    ATTACK_CONE   = math.radians(115)
    BASE_COOLDOWN = 0.48

    OUTFITS = [
        ((60, 120, 200), (30, 60, 120),  (90, 60, 30)),    # Knight
        ((200, 80, 40),  (120, 40, 20),  (200, 180, 50)),  # Paladin
        ((40, 160, 60),  (20, 90, 30),   (80, 50, 20)),    # Druid
        ((180, 60, 200), (90, 30, 120),  (200, 200, 80)),  # Sorcerer
    ]

    VOCATIONS = ["knight", "paladin", "druid", "sorcerer"]
    VOCATION_NAMES = {
        "knight":   "Knight",
        "paladin":  "Paladin",
        "druid":    "Druid",
        "sorcerer": "Sorcerer",
    }

    # Direction vectors (col, row) for 4-directional movement
    DIR_VECTORS = {
        'right': ( 1,  0),
        'left':  (-1,  0),
        'down':  ( 0,  1),
        'up':    ( 0, -1),
    }
    DIR_ANGLES = {
        'right': 0.0,
        'left':  math.pi,
        'down':  math.pi / 2,
        'up':   -math.pi / 2,
    }

    def __init__(self, x, y, level=0, spell_memory=None, outfit_idx=0, vocation='sorcerer', skills=None):
        self.x     = float(x)
        self.y     = float(y)
        self.level = level
        self._outfit     = self.OUTFITS[outfit_idx % len(self.OUTFITS)]
        self._outfit_idx = outfit_idx
        self.vocation    = vocation

        self.inventory    = Inventory()
        self.spell_memory = spell_memory if spell_memory else SpellMemory(vocation=vocation)
        self.skills       = skills if skills else Skills(vocation=vocation)

        self._init_stats()

        self.direction      = 0.0          # radians, for arc drawing
        self._facing        = 'right'       # last pressed direction
        self._move_timer    = 0.0           # time until next step allowed
        self._step_anim     = 0.0           # walk animation counter
        self._atk_timer     = 0.0
        self._atk_anim      = 0.0
        self._atk_angle     = 0.0
        self._inv_timer     = 0.0
        self._block_flash   = 0.0
        self._spell_cast_cd = 0.0

        # Tile-based position tracking
        self._tile_size = TILE_SIZE
        self._snap_to_tile()

        self.attack_cooldown     = self.BASE_COOLDOWN
        self._selected_spell_idx = 0

        self.rect = pygame.Rect(int(x - self.SIZE), int(y - self.SIZE),
                                self.SIZE * 2, self.SIZE * 2)

    def _snap_to_tile(self):
        """Snap position to nearest tile centre."""
        ts = self._tile_size
        col = round((self.x - ts/2) / ts)
        row = round((self.y - ts/2) / ts)
        self.x = col * ts + ts / 2
        self.y = row * ts + ts / 2

    def _tile_pos(self):
        ts = self._tile_size
        return int(self.x // ts), int(self.y // ts)

    def _init_stats(self):
        lv = self.level
        self._base_max_hp      = 100 + lv * 20
        self._base_max_mp      = 50  + lv * 10
        self._base_atk_damage  = 15  + lv * 5
        self.max_xp            = tibia_xp_for_next_level(lv)
        self.xp                = 0
        self.hp                = float(self._base_max_hp)
        self.mp                = float(self._base_max_mp)

    @property
    def max_hp(self):           return self._base_max_hp  + int(self.inventory.stat('max_hp'))
    @property
    def max_mp(self):           return self._base_max_mp  + int(self.inventory.stat('mp_bonus'))
    @property
    def attack_damage(self):    return self._base_atk_damage + int(self.inventory.stat('atk_damage'))
    @property
    def effective_range(self):  return self.ATTACK_RANGE + self.inventory.stat('atk_range')
    @property
    def defense(self):          return int(self.inventory.stat('defense'))
    @property
    def block_chance(self):
        base = self.inventory.stat('block_chance')
        return min(0.60, base + self.skills.shielding_bonus())
    @property
    def hp_regen(self):         return self.inventory.stat('hp_regen')
    @property
    def xp_bonus(self):         return self.inventory.stat('xp_bonus')
    @property
    def atk_speed_bonus(self):  return min(0.60, self.inventory.stat('atk_speed'))
    @property
    def effective_cooldown(self): return max(0.15, self.BASE_COOLDOWN*(1.0-self.atk_speed_bonus))
    @property
    def walk_delay(self) -> float:
        """Time between tile steps. Boots/speed items reduce this."""
        spd_bonus = min(0.5, self.inventory.stat('atk_speed'))  # reuse atk_speed as move speed
        return max(0.08, WALK_DELAY * (1.0 - spd_bonus * 0.6))

    @property
    def selected_spell(self):
        spells = self.spell_memory.known_spells
        return spells[self._selected_spell_idx % len(spells)] if spells else None

    def cycle_spell(self, direction: int = 1):
        n = len(self.spell_memory.known_spells)
        if n > 0:
            self._selected_spell_idx = (self._selected_spell_idx + direction) % n

    def select_spell_by_index(self, idx: int):
        n = len(self.spell_memory.known_spells)
        if n > 0:
            self._selected_spell_idx = idx % n

    def cast_spell(self, target_wx, target_wy):
        sid = self.selected_spell
        if not sid or self._spell_cast_cd > 0:
            return None
        data = SPELL_CATALOGUE[sid]
        if self.mp < data['mp_cost']:
            return None
        self.mp             = max(0.0, self.mp - data['mp_cost'])
        self._spell_cast_cd = 0.55
        dx = target_wx - self.x; dy = target_wy - self.y
        dist = math.hypot(dx, dy)
        if dist < 1: dx, dy = 1.0, 0.0
        else: dx /= dist; dy /= dist
        self.spell_memory.on_spell_cast()
        _sk_up = self.skills.gain_magic()
        if _sk_up: self._skill_levelup = ("magic", self.skills.levels["magic"])
        dmg = data['damage'] + self.spell_memory.magic_level * 4 + self.skills.magic_bonus()
        return {'spell_id': sid, 'x': self.x, 'y': self.y, 'dx': dx, 'dy': dy,
                'damage': dmg, 'owner': 'player'}

    def observe_spell(self, spell_id, mx, my):
        if math.hypot(self.x - mx, self.y - my) > OBSERVE_RANGE:
            return False
        return self.spell_memory.observe(spell_id)

    def gain_xp(self, amount):
        effective = int(amount * (1.0 + self.xp_bonus))
        self.xp  += effective
        if self.xp >= self.max_xp:
            self.xp              -= self.max_xp
            self.level           += 1
            # Tibia-style HP/MP gain per level per vocation
            _hp_gain = {"knight":15,"paladin":10,"druid":8,"sorcerer":8}.get(self.vocation,10)
            _mp_gain = {"knight":5,"paladin":15,"druid":30,"sorcerer":30}.get(self.vocation,10)
            _atk_gain= {"knight":4,"paladin":3,"druid":2,"sorcerer":2}.get(self.vocation,3)
            self._base_max_hp     += _hp_gain
            self.hp               = min(self.hp + _hp_gain, self.max_hp)
            self._base_max_mp     += _mp_gain
            self._base_atk_damage += _atk_gain
            self.max_xp           = tibia_xp_for_next_level(self.level)
            return True
        return False

    def take_damage(self, amount):
        if self._inv_timer > 0:
            return 0
        if self.block_chance > 0 and random.random() < self.block_chance:
            self._block_flash = 0.28; self._inv_timer = 0.35
            _sk_up = self.skills.gain_shielding()
            if _sk_up: self._skill_levelup = ("shielding", self.skills.levels["shielding"])
            return 0
        actual = max(1, amount - self.defense)
        self.hp         = max(0.0, self.hp - actual)
        self._inv_timer = 0.75
        return actual

    def is_dead(self):
        return self.hp <= 0

    @property
    def attack_ready(self):
        return self._atk_timer <= 0

    @property
    def attack_cooldown_progress(self):
        cd = self.effective_cooldown
        return min(1.0, max(0.0, 1.0 - self._atk_timer / cd)) if cd > 0 else 1.0

    @property
    def spell_ready(self):
        return self._spell_cast_cd <= 0

    def attack(self, target_wx, target_wy, monsters):
        if self._atk_timer > 0:
            return []
        self._atk_timer      = self.effective_cooldown
        self.attack_cooldown = self.effective_cooldown
        dx = target_wx - self.x; dy = target_wy - self.y
        angle = math.atan2(dy, dx) if abs(dx)+abs(dy) > 1 else self._atk_angle
        self._atk_angle = angle; self._atk_anim = 0.22; self.direction = angle
        hits = []; hc = self.ATTACK_CONE/2; eff = self.effective_range
        for m in monsters:
            if m.is_dead(): continue
            mdx = m.x-self.x; mdy = m.y-self.y; dist = math.hypot(mdx, mdy)
            if dist > eff + m.SIZE: continue
            ma   = math.atan2(mdy, mdx)
            diff = abs(math.atan2(math.sin(ma-angle), math.cos(ma-angle)))
            if diff <= hc:
                # Skill bonus from weapon type
                weapon = self.inventory.equipped.get("weapon")
                wtype  = weapon.get("weapon_type", "sword") if weapon else "sword"
                skill_bonus = self.skills.melee_bonus(wtype)
                dmg = max(1, self.attack_damage + skill_bonus + random.randint(-3, 6))
                m.take_damage(dmg)
                _sk_up = self.skills.gain_melee(wtype)
                if _sk_up: self._skill_levelup = (wtype, self.skills.levels[wtype])
                hits.append((m, dmg))
        return hits

    # ── Tile-based update ─────────────────────────────────────────────────────
    def update(self, keys, dt, world):
        if self._atk_timer   > 0: self._atk_timer   -= dt
        if self._atk_anim    > 0: self._atk_anim    -= dt
        if self._inv_timer   > 0: self._inv_timer   -= dt
        if self._block_flash > 0: self._block_flash -= dt
        if self._spell_cast_cd > 0: self._spell_cast_cd -= dt
        if self._move_timer  > 0: self._move_timer  -= dt
        if self._step_anim   > 0: self._step_anim   -= dt

        if self.hp_regen > 0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + self.hp_regen * dt)
        if self.mp < self.max_mp:
            self.mp = min(self.max_mp, self.mp + 2.5 * dt)

        # Determine intended direction from keys (priority: last pressed)
        # Classic Tibia: 4-directional only
        move_dir = None
        if   keys[pygame.K_UP]    or keys[pygame.K_w]: move_dir = 'up'
        elif keys[pygame.K_DOWN]  or keys[pygame.K_s]: move_dir = 'down'
        elif keys[pygame.K_LEFT]  or keys[pygame.K_a]: move_dir = 'left'
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]: move_dir = 'right'

        if move_dir is not None:
            self._facing   = move_dir
            self.direction = self.DIR_ANGLES[move_dir]

            # Only step if movement timer expired
            if self._move_timer <= 0:
                dc, dr = self.DIR_VECTORS[move_dir]
                ts     = self._tile_size
                col, row = self._tile_pos()
                ncol = col + dc
                nrow = row + dr
                if world.is_walkable(ncol, nrow):
                    self.x = ncol * ts + ts / 2
                    self.y = nrow * ts + ts / 2
                    self._move_timer = self.walk_delay
                    self._step_anim  = 0.15   # for leg animation

        self.rect.center = (int(self.x), int(self.y))

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self, screen, camera):
        from ui.tibia_sprites import draw_humanoid
        sx = int(self.x - camera.offset_x)
        sy = int(self.y - camera.offset_y)
        if not (-80 <= sx <= camera.view_w+80 and -80 <= sy <= camera.view_h+80):
            return

        if self._atk_anim > 0:
            self._draw_arc(screen, sx, sy, 1.0 - self._atk_anim/0.22)

        outfit_col, legs_col, hair_col = self._outfit
        hit_flash = self._inv_timer > 0 and int(self._inv_timer*14)%2 == 0

        # Walk animation: slight vertical bob
        bob = int(math.sin(self._step_anim * math.pi / 0.15) * 2) if self._step_anim > 0 else 0

        from ui.tibia_sprites import draw_player_sprite
        draw_player_sprite(screen, sx, sy, self._outfit_idx,
                           outfit_col, legs_col, hair_col,
                           direction=self.direction, hit_flash=hit_flash, bob=bob)

        # "Tú" label
        f   = pygame.font.SysFont("Arial", 9, bold=True)
        lbl = f.render("Tú", True, (255, 255, 100))
        screen.blit(lbl, (sx - lbl.get_width()//2, sy - 58))

        if self.spell_memory.magic_level > 0:
            fm = pygame.font.SysFont("Arial", 10, bold=True)
            ml = fm.render(f"✦{self.spell_memory.magic_level}", True, C_PURPLE)
            screen.blit(ml, (sx - ml.get_width()//2, sy - 70))

        if self.block_chance > 0:
            pygame.draw.circle(screen, (100, 150, 255), (sx+14, sy-30), 5)
            pygame.draw.circle(screen, (200, 220, 255), (sx+14, sy-30), 3)

    def _draw_arc(self, screen, sx, sy, progress):
        radius = int(self.effective_range); half = self.ATTACK_CONE/2
        size   = radius*2+12
        arc_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        alpha = int(190*(1.0-progress)); cx = cy = size//2
        pts = [(cx, cy)]
        for i in range(15):
            a = self._atk_angle-half+self.ATTACK_CONE*i/14
            pts.append((int(cx+math.cos(a)*radius), int(cy+math.sin(a)*radius)))
        pygame.draw.polygon(arc_surf, (*C_YELLOW, alpha), pts)
        pygame.draw.polygon(arc_surf, (*C_ORANGE, min(255,alpha+80)), pts, 2)
        screen.blit(arc_surf, (sx-cx, sy-cy))
