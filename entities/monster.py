import pygame
import math
import random
from constants import *
from systems.pathfinding import astar
from systems.spells import SPELL_CATALOGUE, MONSTER_SPELLS, OBSERVE_RANGE

# ── Monster catalogue ─────────────────────────────────────────────────────────
MONSTER_DATA = {
    'rat': dict(
        name='Rat',         min_level=0,
        base_hp=15,         hp_lv=3,
        base_dmg=3,         dmg_lv=1,
        speed=72.0,         atk_range=17.0,   atk_cd=1.2,
        aggro=10,           xp_base=5,        xp_lv=2,
        size=10,
        color=(142,102,62), outline=(100,70,40),
    ),
    'zombie': dict(
        name='Zombie',      min_level=3,
        base_hp=32,         hp_lv=6,
        base_dmg=8,         dmg_lv=2,
        speed=46.0,         atk_range=20.0,   atk_cd=1.8,
        aggro=12,           xp_base=14,       xp_lv=3,
        size=13,
        color=(58,132,58),  outline=(38,100,38),
    ),
    'skeleton': dict(
        name='Skeleton',    min_level=7,
        base_hp=55,         hp_lv=8,
        base_dmg=15,        dmg_lv=3,
        speed=62.0,         atk_range=22.0,   atk_cd=1.5,
        aggro=14,           xp_base=28,       xp_lv=5,
        size=12,
        color=(212,210,195),outline=(155,150,138),
    ),
    # ── Phase 5: new monsters ─────────────────────────────────────────────
    'orc': dict(
        name='Orc',         min_level=10,
        base_hp=95,         hp_lv=12,
        base_dmg=22,        dmg_lv=4,
        speed=58.0,         atk_range=24.0,   atk_cd=1.6,
        aggro=13,           xp_base=48,       xp_lv=8,
        size=15,
        color=(60,145,50),  outline=(35,100,30),
    ),
    'dark_wizard': dict(
        name='Dark Wizard',  min_level=15,
        base_hp=72,          hp_lv=10,
        base_dmg=30,         dmg_lv=6,
        speed=44.0,          atk_range=18.0,   atk_cd=2.2,
        aggro=16,            xp_base=75,       xp_lv=12,
        size=12,
        color=(140,60,210),  outline=(90,30,150),
    ),
    'dragon': dict(
        name='Dragon',      min_level=20,
        base_hp=200,        hp_lv=20,
        base_dmg=40,        dmg_lv=8,
        speed=50.0,         atk_range=30.0,   atk_cd=2.0,
        aggro=18,           xp_base=150,      xp_lv=18,
        size=20,
        color=(200,80,30),  outline=(140,45,15),
    ),
    # ── Cyclops ────────────────────────────────────────────────────────────
    'cyclops': dict(
        name='Cyclops',     min_level=13,
        base_hp=140,        hp_lv=15,
        base_dmg=28,        dmg_lv=5,
        speed=52.0,         atk_range=26.0,   atk_cd=1.8,
        aggro=14,           xp_base=150,      xp_lv=12,
        size=16,
        color=(90,120,60),  outline=(55,80,35),
    ),
    'bear': dict(
        name='Bear',        min_level=5,
        base_hp=70,         hp_lv=9,
        base_dmg=16,        dmg_lv=3,
        speed=60.0,         atk_range=20.0,   atk_cd=1.4,
        aggro=11,           xp_base=60,       xp_lv=7,
        size=14,
        color=(130,90,55),  outline=(90,60,35),
    ),
    'wolf': dict(
        name='Wolf',        min_level=2,
        base_hp=25,         hp_lv=4,
        base_dmg=7,         dmg_lv=2,
        speed=90.0,         atk_range=18.0,   atk_cd=1.0,
        aggro=13,           xp_base=18,       xp_lv=3,
        size=11,
        color=(80,80,85),   outline=(50,50,55),
    ),
    'fire_devil': dict(
        name='Fire Devil',  min_level=17,
        base_hp=110,        hp_lv=14,
        base_dmg=38,        dmg_lv=7,
        speed=66.0,         atk_range=24.0,   atk_cd=1.5,
        aggro=17,           xp_base=145,      xp_lv=14,
        size=14,
        color=(255,80,20),  outline=(200,40,0),
    ),
    'troll': dict(
        name='Troll',       min_level=4,
        base_hp=50,         hp_lv=7,
        base_dmg=12,        dmg_lv=2,
        speed=48.0,         atk_range=22.0,   atk_cd=1.6,
        aggro=10,           xp_base=40,       xp_lv=5,
        size=14,
        color=(100,140,70), outline=(65,95,45),
    ),
    'vampire': dict(
        name='Vampire',     min_level=18,
        base_hp=160,        hp_lv=18,
        base_dmg=45,        dmg_lv=9,
        speed=70.0,         atk_range=22.0,   atk_cd=1.4,
        aggro=16,           xp_base=220,      xp_lv=20,
        size=14,
        color=(100,20,150), outline=(65,10,100),
    ),
}

def available_types(player_level):
    return [k for k, v in MONSTER_DATA.items() if player_level >= v['min_level']] or ['rat']


# ── Monster class ─────────────────────────────────────────────────────────────
class Monster:
    PATH_INTERVAL   = 0.55
    WANDER_INTERVAL = 2.2
    SPELL_CD_BASE   = 4.5
    SPELL_RANGE_PX  = 320.0
    WINDUP_TIME     = 0.65

    def __init__(self, x, y, mtype, level):
        self.x     = float(x)
        self.y     = float(y)
        self.mtype = mtype
        self.level = level

        d = MONSTER_DATA[mtype]
        self.name       = d['name']
        self.SIZE       = d['size']
        self.color      = d['color']
        self.outline    = d['outline']
        self.speed      = d['speed']
        self.atk_range  = d['atk_range']
        self.atk_cd     = d['atk_cd']
        self.aggro_r    = d['aggro']

        self.max_hp     = d['base_hp'] + d['hp_lv'] * level
        self.hp         = float(self.max_hp)
        self.damage     = d['base_dmg'] + d['dmg_lv'] * level
        self.xp_reward  = d['xp_base'] + d['xp_lv'] * level

        self._path          = []
        self._path_timer    = random.uniform(0, self.PATH_INTERVAL)
        self._atk_timer     = random.uniform(0, self.atk_cd)
        self._aggroed       = False
        self._wander_target = None
        self._wander_timer  = 0.0
        self._hit_flash     = 0.0

        # Elite / boss tags (set externally by elites.apply_modifiers)
        self.is_elite      = False
        self.is_boss       = False
        self.elite_mods: list = []
        self.elite_regen   = 0.0

        # Intelligence tier: 0=simple 1=normal 2=tactical
        _INTEL = {
            "rat":0,"zombie":0,"skeleton":0,"troll":0,"wolf":0,"bear":0,
            "orc":1,"cyclops":1,"dark_wizard":1,"fire_devil":1,"vampire":1,
            "dragon":2,"demon":2,"dragon_lord":2,
        }
        self.intel = _INTEL.get(mtype, 1)
        # Simple: smaller aggro range — less perceptive
        if self.intel == 0:
            self.aggro_r = max(4, self.aggro_r - 4)
        # Tactical: flee when HP < 28%
        self._flee_hp_pct = {0: 0.0, 1: 0.0, 2: 0.28}[self.intel]

        # Spell system
        available   = MONSTER_SPELLS.get(mtype, [])
        max_spells  = 1 if level < 5 else 2
        self._my_spells: list[str] = (
            random.sample(available, min(len(available), max_spells))
            if available else []
        )
        # Dark wizard & dragon always cast spells
        if mtype == 'dark_wizard':
            self._my_spells = ['exevo mas vis', 'exura mort']
        elif mtype == 'dragon':
            self._my_spells = ['exevo flam', 'exevo gran mas flam']

        self._spell_cd     = random.uniform(2.0, self.SPELL_CD_BASE)
        self._windup_spell: str | None = None
        self._windup_timer = 0.0
        self._windup_dir   = (0.0, 0.0)

        self.rect = pygame.Rect(int(x - self.SIZE), int(y - self.SIZE),
                                self.SIZE * 2, self.SIZE * 2)

    def is_dead(self):
        return self.hp <= 0

    def take_damage(self, amount):
        self.hp         = max(0.0, self.hp - amount)
        self._hit_flash = 0.14
        # Learning fields — safe defaults if __init__ patch not applied
        if not hasattr(self, '_hit_streak'):
            self._hit_streak = 0; self._lateral_mode = False
            self._lateral_timer = 0.0; self._lateral_angle = 0.0
            self._times_hurt_by_melee = 0; self._preferred_range = None
        # Learning: track consecutive hits
        self._hit_streak += 1
        if self._hit_streak >= 3 and not self._lateral_mode:
            self._lateral_mode  = True
            self._lateral_timer = 2.5 + random.random() * 1.5
            self._lateral_angle = random.uniform(0, math.tau)
            self._hit_streak    = 0
        # Spellcasters: remember melee attacks, prefer more distance
        if self._my_spells:
            self._times_hurt_by_melee += 1
            if self._times_hurt_by_melee >= 2 and self._preferred_range is None:
                self._preferred_range = self.SPELL_RANGE_PX * 0.85
        return amount

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self, dt, player, world):
        if self.is_dead():
            return 0, None

        self._path_timer -= dt
        self._atk_timer  -= dt
        if self._hit_flash > 0:
            self._hit_flash -= dt

        # Elite HP regen
        if self.elite_regen > 0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + self.elite_regen * dt)

        # ── Learning: ensure fields exist (backward-compat) ──────────────
        if not hasattr(self, '_hit_streak'):
            self._hit_streak = 0; self._lateral_mode = False
            self._lateral_timer = 0.0; self._lateral_angle = 0.0
            self._times_hurt_by_melee = 0; self._preferred_range = None
            intel = getattr(self, 'intel', 1)
            self._flee_hp_pct = {0:0.0, 1:0.0, 2:0.28}.get(intel, 0.0)

        # Learning decay: lateral mode times out
        if self._lateral_timer > 0:
            self._lateral_timer -= dt
        else:
            self._lateral_mode = False

        ts     = world.tile_size
        mc, mr = int(self.x // ts), int(self.y // ts)
        pc, pr = int(player.x  // ts), int(player.y  // ts)
        tile_dist  = abs(mc - pc) + abs(mr - pr)
        pixel_dist = math.hypot(self.x - player.x, self.y - player.y)

        if tile_dist <= self.aggro_r:
            self._aggroed = True
        elif tile_dist > self.aggro_r * 2.2:
            self._aggroed = False

        if self._path_timer <= 0:
            self._path_timer = self.PATH_INTERVAL
            if self._aggroed:
                self._path = astar(world, mc, mr, pc, pr, max_nodes=380)
            else:
                self._wander_timer -= self.PATH_INTERVAL
                if self._wander_timer <= 0 or not self._wander_target:
                    self._wander_timer = self.WANDER_INTERVAL
                    for _ in range(15):
                        wc = mc + random.randint(-8, 8)
                        wr = mr + random.randint(-8, 8)
                        if world.is_walkable(wc, wr):
                            self._wander_target = (wc, wr)
                            break
                if self._wander_target:
                    wc, wr = self._wander_target
                    self._path = astar(world, mc, mr, wc, wr, max_nodes=160)

        # ── Intelligence-driven movement ─────────────────────────────────
        _hp_pct = self.hp / max(1, self.max_hp)
        _flee_active = (self.intel == 2 and _hp_pct < self._flee_hp_pct
                        and self._aggroed)

        if _flee_active:
            # Tactical: flee from player when low HP
            _ddx = self.x - player.x; _ddy = self.y - player.y
            _dp  = math.hypot(_ddx, _ddy)
            if _dp > 0:
                self.x += (_ddx/_dp) * self.speed * 1.2 * dt
                self.y += (_ddy/_dp) * self.speed * 1.2 * dt
        elif (self.intel >= 1 and self._my_spells and self._aggroed
              and pixel_dist > 0):
            # Normal/Tactical with spells: maintain optimal range
            _optimal = self.SPELL_RANGE_PX * 0.75
            if pixel_dist < _optimal * 0.6:
                # Back off to cast
                _ddx = self.x - player.x; _ddy = self.y - player.y
                _dp  = math.hypot(_ddx, _ddy)
                if _dp > 0:
                    self.x += (_ddx/_dp) * self.speed * 0.5 * dt
                    self.y += (_ddy/_dp) * self.speed * 0.5 * dt
            elif self._path:
                nc, nr   = self._path[0]
                target_x = nc * ts + ts // 2
                target_y = nr * ts + ts // 2
                ddx      = target_x - self.x
                ddy      = target_y - self.y
                dist_wp  = math.hypot(ddx, ddy)
                if dist_wp < 3:
                    self.x = float(target_x); self.y = float(target_y)
                    self._path.pop(0)
                else:
                    self.x += (ddx / dist_wp) * self.speed * dt
                    self.y += (ddy / dist_wp) * self.speed * dt
        elif self._path:
            nc, nr   = self._path[0]
            target_x = nc * ts + ts // 2
            target_y = nr * ts + ts // 2
            ddx      = target_x - self.x
            ddy      = target_y - self.y
            dist_wp  = math.hypot(ddx, ddy)
            if dist_wp < 3:
                self.x = float(target_x)
                self.y = float(target_y)
                self._path.pop(0)
            else:
                self.x += (ddx / dist_wp) * self.speed * dt
                self.y += (ddy / dist_wp) * self.speed * dt

        self.rect.center = (int(self.x), int(self.y))

        # Melee
        melee_dmg = 0
        if pixel_dist <= self.atk_range + player.SIZE and self._atk_timer <= 0:
            self._atk_timer = self.atk_cd
            raw = max(1, self.damage + random.randint(-1, 2))
            melee_dmg = player.take_damage(raw)
            if melee_dmg > 0:
                self._hit_streak = 0  # reset: monster is landing hits, no need to dodge

        # Spell
        spell_event = None
        if self._windup_spell:
            self._windup_timer -= dt
            if self._windup_timer <= 0:
                sid = self._windup_spell
                self._windup_spell = None
                dx, dy = self._windup_dir
                spell_event = {'spell_id': sid, 'x': self.x, 'y': self.y,
                               'dx': dx, 'dy': dy}
                self._spell_cd = self.SPELL_CD_BASE + random.uniform(-1.0, 1.5)
        else:
            self._spell_cd -= dt
            if (self._spell_cd <= 0 and self._aggroed
                    and self._my_spells
                    and pixel_dist <= self.SPELL_RANGE_PX):
                sid = random.choice(self._my_spells)
                ddx = player.x - self.x
                ddy = player.y - self.y
                dist = math.hypot(ddx, ddy)
                if dist > 0:
                    self._windup_spell = sid
                    self._windup_timer = self.WINDUP_TIME
                    self._windup_dir   = (ddx / dist, ddy / dist)

        return melee_dmg, spell_event

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self, screen, camera):
        if self.is_dead():
            return
        sx = int(self.x - camera.offset_x)
        sy = int(self.y - camera.offset_y)
        if not (-80 <= sx <= camera.view_w + 80 and
                -80 <= sy <= camera.view_h + 80):
            return

        col = (255, 255, 255) if self._hit_flash > 0 else self.color

        # Shadow
        pygame.draw.ellipse(screen, (0, 0, 0),
                            (sx - self.SIZE, sy + self.SIZE - 4,
                             self.SIZE * 2, 8))

        # Sprite by type
        if self.mtype == 'rat':          self._draw_rat(screen, sx, sy, col)
        elif self.mtype == 'zombie':     self._draw_zombie(screen, sx, sy, col)
        elif self.mtype == 'orc':        self._draw_orc(screen, sx, sy, col)
        elif self.mtype == 'dark_wizard':self._draw_dark_wizard(screen, sx, sy, col)
        elif self.mtype == 'dragon':     self._draw_dragon(screen, sx, sy, col)
        elif self.mtype == 'cyclops':    self._draw_cyclops(screen, sx, sy, col)
        elif self.mtype == 'bear':       self._draw_bear(screen, sx, sy, col)
        elif self.mtype == 'wolf':       self._draw_wolf(screen, sx, sy, col)
        elif self.mtype == 'fire_devil': self._draw_fire_devil(screen, sx, sy, col)
        elif self.mtype == 'troll':      self._draw_troll(screen, sx, sy, col)
        elif self.mtype == 'vampire':    self._draw_vampire(screen, sx, sy, col)
        else:                            self._draw_skeleton(screen, sx, sy, col)

        # ── Tibia-style HP bar (only when monster has taken damage) ──────────
        if self.hp < self.max_hp:
            # Tibia shows a thin red bar above the creature, 1px black border
            bar_w = max(20, self.SIZE * 2 + 4)
            bx    = sx - bar_w // 2
            by    = sy - self.SIZE - 8
            bar_h = 4
            # Black border
            pygame.draw.rect(screen, (0, 0, 0), (bx - 1, by - 1, bar_w + 2, bar_h + 2))
            # Dark red background (empty)
            pygame.draw.rect(screen, (80, 0, 0), (bx, by, bar_w, bar_h))
            # Bright red fill (current HP)
            hp_pct = max(0.0, self.hp) / self.max_hp
            fill_w = int(bar_w * hp_pct)
            if fill_w > 0:
                # Colour shifts: green when full, yellow mid, red low (like Tibia)
                if hp_pct > 0.6:
                    bar_col = (100, 200,  40)   # green
                elif hp_pct > 0.3:
                    bar_col = (220, 180,  20)   # yellow
                else:
                    bar_col = (220,  40,  20)   # red
                if self.is_boss:
                    bar_col = (200, 100, 255)   # purple for bosses
                pygame.draw.rect(screen, bar_col, (bx, by, fill_w, bar_h))

        # Elite / boss crown badge
        if self.is_boss:
            self._draw_boss_crown(screen, sx, sy)
        elif self.is_elite:
            self._draw_elite_badge(screen, sx, sy)

        # Windup
        if self._windup_spell:
            self._draw_windup(screen, sx, sy)

    # ── Sprite helpers ────────────────────────────────────────────────────────

    def _draw_rat(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'rat', col, self._hit_flash > 0)

    def _draw_zombie(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'zombie', col, self._hit_flash > 0)

    def _draw_skeleton(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'skeleton', col, self._hit_flash > 0)

    def _draw_orc(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'orc', col, self._hit_flash > 0)

    def _draw_dark_wizard(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'dark_wizard', col, self._hit_flash > 0)

    def _draw_dragon(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'dragon', col, self._hit_flash > 0, size=self.SIZE)


    def _draw_cyclops(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'cyclops', col, self._hit_flash > 0)

    def _draw_bear(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'bear', col, self._hit_flash > 0)

    def _draw_wolf(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'wolf', col, self._hit_flash > 0)

    def _draw_fire_devil(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'fire_devil', col, self._hit_flash > 0)

    def _draw_troll(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'troll', col, self._hit_flash > 0)

    def _draw_vampire(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'vampire', col, self._hit_flash > 0)

    def _draw_demon(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'demon', col, self._hit_flash > 0)

    def _draw_dragon_lord(self, screen, sx, sy, col):
        from ui.tibia_sprites import draw_monster
        draw_monster(screen, sx, sy, 'dragon_lord', col, self._hit_flash > 0)

    def _draw_elite_badge(self, screen, sx, sy):
        from systems.elites import MODIFIERS
        if not self.elite_mods:
            return
        color = MODIFIERS[self.elite_mods[0]]["color"]
        bx = sx - self.SIZE
        by = sy - self.SIZE - 14
        pygame.draw.rect(screen, (10,10,10), (bx, by, self.SIZE*2, 10), border_radius=3)
        pygame.draw.rect(screen, color,      (bx, by, self.SIZE*2, 10), 1, border_radius=3)
        f = pygame.font.SysFont("Arial", 9, bold=True)
        tag = self.elite_mods[0].capitalize()[:8]
        t = f.render(tag, True, color)
        screen.blit(t, (sx - t.get_width()//2, by + 1))

    def _draw_boss_crown(self, screen, sx, sy):
        # Crown above boss
        cy = sy - self.SIZE - 18
        pts = [(sx-10, cy+8), (sx-10, cy), (sx-5, cy+5),
               (sx, cy-2), (sx+5, cy+5), (sx+10, cy), (sx+10, cy+8)]
        pygame.draw.polygon(screen, (220, 180, 20), pts)
        pygame.draw.polygon(screen, (255, 220, 60), pts, 1)
        for gem_x in [sx-5, sx, sx+5]:
            pygame.draw.circle(screen, (255, 60, 60), (gem_x, cy+4), 2)

    def _draw_windup(self, screen, sx, sy):
        sid   = self._windup_spell
        prog  = 1.0 - self._windup_timer / self.WINDUP_TIME
        data  = SPELL_CATALOGUE.get(sid, {})
        color = data.get("color", (200,200,200))
        r     = int(4 + 9 * prog)
        alpha = int(100 + 155 * prog)
        pulse = int(180 + 75 * math.sin(prog * math.pi * 6))
        surf  = pygame.Surface((r*2+6, r*2+6), pygame.SRCALPHA)
        cx    = r + 3
        pygame.draw.circle(surf, (*color, alpha), (cx, cx), r)
        pygame.draw.circle(surf, (255,255,255,pulse), (cx,cx), max(1,r//2))
        screen.blit(surf, (sx-cx, sy-self.SIZE-r-6))
        f   = pygame.font.SysFont("Arial", 10)
        lbl = f.render(data.get("name","?")[:6], True, color)
        screen.blit(lbl, (sx-lbl.get_width()//2, sy-self.SIZE-r-20))

# ── Demon & Dragon Lord (appended in update 1) ────────────────────────────────
MONSTER_DATA['demon'] = dict(
    name='Demon',       min_level=25,
    base_hp=340,        hp_lv=28,
    base_dmg=58,        dmg_lv=9,
    speed=55.0,         atk_range=26.0,   atk_cd=1.8,
    aggro=20,           xp_base=240,      xp_lv=22,
    size=18,
    color=(160, 20, 20), outline=(100, 10, 10),
)
MONSTER_DATA['dragon_lord'] = dict(
    name='Dragon Lord', min_level=30,
    base_hp=480,        hp_lv=35,
    base_dmg=72,        dmg_lv=12,
    speed=48.0,         atk_range=34.0,   atk_cd=2.2,
    aggro=22,           xp_base=380,      xp_lv=30,
    size=24,
    color=(180, 60, 180), outline=(120, 30, 120),
)

def _draw_demon(self, screen, sx, sy, col):
    import pygame, math
    s = self.SIZE
    # Muscular humanoid body
    pygame.draw.rect(screen, self.outline, (sx-s//2-2, sy-s+2, s+4, int(s*1.9)))
    pygame.draw.rect(screen, col,          (sx-s//2-1, sy-s+3, s+2, int(s*1.9)-2))
    # Head
    pygame.draw.circle(screen, self.outline, (sx, sy-s+2), s//2+2)
    pygame.draw.circle(screen, col,          (sx, sy-s+2), s//2)
    # Horns
    hc = (220, 80, 80)
    pygame.draw.polygon(screen, hc, [(sx-6, sy-s-2), (sx-10, sy-s-14), (sx-3, sy-s+2)])
    pygame.draw.polygon(screen, hc, [(sx+6, sy-s-2), (sx+10, sy-s-14), (sx+3, sy-s+2)])
    # Glowing eyes
    pygame.draw.circle(screen, (255, 50,  50), (sx-4, sy-s), 3)
    pygame.draw.circle(screen, (255, 200, 50), (sx-4, sy-s), 1)
    pygame.draw.circle(screen, (255, 50,  50), (sx+4, sy-s), 3)
    pygame.draw.circle(screen, (255, 200, 50), (sx+4, sy-s), 1)
    # Wings (dark)
    wc = tuple(max(0, c-40) for c in col)
    pygame.draw.polygon(screen, wc, [(sx-s, sy-4), (sx-s*2-4, sy-s*2), (sx-s//2, sy+s)])
    pygame.draw.polygon(screen, wc, [(sx+s, sy-4), (sx+s*2+4, sy-s*2), (sx+s//2, sy+s)])

def _draw_dragon_lord(self, screen, sx, sy, col):
    import pygame
    s = self.SIZE
    # Massive body
    pygame.draw.ellipse(screen, self.outline, (sx-s, sy-s//2, s*2+2, int(s*1.8)+2))
    pygame.draw.ellipse(screen, col,          (sx-s+1, sy-s//2+1, s*2, int(s*1.8)))
    # Armoured head
    pygame.draw.circle(screen, self.outline, (sx, sy-s+4), s//2+3)
    pygame.draw.circle(screen, col,          (sx, sy-s+4), s//2+1)
    # Crown of spikes
    for i, angle in enumerate(range(-60, 70, 30)):
        import math
        a = math.radians(angle - 90)
        ex = sx + int(math.cos(a) * (s//2+6))
        ey = (sy - s + 4) + int(math.sin(a) * (s//2+6))
        pygame.draw.line(screen, (200, 150, 230), (sx, sy-s+4), (ex, ey), 2)
    # Glowing purple eyes
    pygame.draw.circle(screen, (230, 80, 230), (sx-5, sy-s+2), 3)
    pygame.draw.circle(screen, (255, 200, 255), (sx-5, sy-s+2), 1)
    pygame.draw.circle(screen, (230, 80, 230), (sx+5, sy-s+2), 3)
    pygame.draw.circle(screen, (255, 200, 255), (sx+5, sy-s+2), 1)
    # Large wings
    wc = tuple(max(0, c-50) for c in col)
    pygame.draw.polygon(screen, wc, [(sx-s, sy-6), (sx-s*3, sy-s*2), (sx-s//2, sy+s//2)])
    pygame.draw.polygon(screen, wc, [(sx+s, sy-6), (sx+s*3, sy-s*2), (sx+s//2, sy+s//2)])

# Monkey-patch draw methods onto Monster class
Monster._draw_demon       = _draw_demon
Monster._draw_dragon_lord = _draw_dragon_lord

# Patch draw() to handle new types
_orig_draw = Monster.draw
def _patched_draw(self, screen, camera):
    # Use parent logic but handle new types
    if self.is_dead(): return
    sx = int(self.x - camera.offset_x)
    sy = int(self.y - camera.offset_y)
    if not (-80 <= sx <= camera.view_w + 80 and -80 <= sy <= camera.view_h + 80):
        return
    import pygame
    col = (255, 255, 255) if self._hit_flash > 0 else self.color
    pygame.draw.ellipse(screen, (0,0,0), (sx-self.SIZE, sy+self.SIZE-4, self.SIZE*2, 8))
    if   self.mtype == 'rat':          self._draw_rat(screen, sx, sy, col)
    elif self.mtype == 'zombie':       self._draw_zombie(screen, sx, sy, col)
    elif self.mtype == 'orc':         self._draw_orc(screen, sx, sy, col)
    elif self.mtype == 'dark_wizard': self._draw_dark_wizard(screen, sx, sy, col)
    elif self.mtype == 'dragon':      self._draw_dragon(screen, sx, sy, col)
    elif self.mtype == 'demon':       self._draw_demon(screen, sx, sy, col)
    elif self.mtype == 'dragon_lord': self._draw_dragon_lord(screen, sx, sy, col)
    elif self.mtype == 'cyclops':     self._draw_cyclops(screen, sx, sy, col)
    elif self.mtype == 'bear':        self._draw_bear(screen, sx, sy, col)
    elif self.mtype == 'wolf':        self._draw_wolf(screen, sx, sy, col)
    elif self.mtype == 'fire_devil':  self._draw_fire_devil(screen, sx, sy, col)
    elif self.mtype == 'troll':       self._draw_troll(screen, sx, sy, col)
    elif self.mtype == 'vampire':     self._draw_vampire(screen, sx, sy, col)
    else:                             self._draw_skeleton(screen, sx, sy, col)
    if self.hp < self.max_hp:
        bw=self.SIZE*2+6; bx=sx-bw//2; by=sy-self.SIZE-9
        bar_col=(255,180,30) if self.is_boss else (210,50,50)
        pygame.draw.rect(screen,(60,0,0),(bx,by,bw,5))
        pygame.draw.rect(screen,bar_col,(bx,by,int(bw*max(0,self.hp)/self.max_hp),5))
    if self.is_boss:         self._draw_boss_crown(screen, sx, sy)
    elif self.is_elite:      self._draw_elite_badge(screen, sx, sy)
    if self._windup_spell:   self._draw_windup(screen, sx, sy)

Monster.draw = _patched_draw
