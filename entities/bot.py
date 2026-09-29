"""
entities/bot.py
═══════════════════════════════════════════════════════════════
Bot competidor con 5 niveles de inteligencia:

  NOVATO   — vaga sin rumbo, solo huye de la tormenta
  APRENDIZ — caza monstruos fáciles, no ataca al jugador
  VETERANO — caza monstruos, ataca jugador si tiene ventaja
  EXPERTO  — ataca agresivo, usa kiting, prioriza al jugador débil
  MAESTRO  — gestiona HP, flanquea, persigue sin rendirse, toma items
"""
from __future__ import annotations
import pygame
import math
import random
from constants import TILE_SIZE, C_RED, C_GREEN, C_YELLOW, C_WHITE

# ── AI states ─────────────────────────────────────────────────────────────────
STATE_ROAM    = "roam"
STATE_HUNT    = "hunt"
STATE_FLEE    = "flee_storm"
STATE_ATTACK  = "attack_player"
STATE_RETREAT = "retreat"    # Maestro/Experto: retrocede para curar
STATE_KITE    = "kite"       # Experto/Maestro: mantiene distancia óptima

# ── Intelligence tiers ────────────────────────────────────────────────────────
INTEL_NOVATO   = 0   # solo vaga y huye de tormenta
INTEL_APRENDIZ = 1   # caza monstruos, evita jugador
INTEL_VETERANO = 2   # caza + ataca si tiene ventaja
INTEL_EXPERTO  = 3   # agresivo, flanquea, kiting básico
INTEL_MAESTRO  = 4   # gestión de HP, persecución, flanqueo

INTEL_NAMES = {
    INTEL_NOVATO:   "Novato",
    INTEL_APRENDIZ: "Aprendiz",
    INTEL_VETERANO: "Veterano",
    INTEL_EXPERTO:  "Experto",
    INTEL_MAESTRO:  "Maestro",
}

# ── Nombres por nivel de inteligencia ─────────────────────────────────────────
BOT_NAMES_BY_INTEL = {
    INTEL_NOVATO:   ["Aldeano","Granjero","Mercader","Viajero","Peregrino",
                     "Estudiante","Aprendiz","Novicio","Recluta","Escudero"],
    INTEL_APRENDIZ: ["Cazador","Explorador","Ranger","Arquero","Rastreador",
                     "Guardabosques","Batidor","Centinela","Vigía","Patrullero"],
    INTEL_VETERANO: ["Guerrero","Soldado","Veterano","Mercenario","Luchador",
                     "Gladiador","Campeón","Combatiente","Esgrimidor","Lancero"],
    INTEL_EXPERTO:  ["Asesino","Corsario","Berserker","Valquiria","Paladín",
                     "Nigromante","Archero","Caballero","Druida","Conjurador"],
    INTEL_MAESTRO:  ["Gran Maestre","Leyenda","Inmortal","Campeón Supremo",
                     "Élite","Terror","Destructor","Apocalipsis","Dios de la Guerra","El Último"],
}

BOT_OUTFITS = [
    ((180, 60,  60), (100, 30, 30), (80,  60, 20)),
    ((60,  180, 60), (30, 100, 30), (50,  40, 10)),
    ((200, 140, 30), (120, 80, 15), (100, 80, 30)),
    ((60,  60,  180),(30,  30,110), (200,180, 60)),
    ((160, 60,  160),(80,  30, 80), (200,200, 80)),
]

# Intel badge colors shown on HUD
INTEL_COLORS = {
    INTEL_NOVATO:   (120, 120, 120),
    INTEL_APRENDIZ: (60,  180,  60),
    INTEL_VETERANO: (200, 200,  50),
    INTEL_EXPERTO:  (220, 120,  20),
    INTEL_MAESTRO:  (220,  40,  40),
}


def _assign_intel(bot_idx: int, level: int) -> int:
    """
    Assign intelligence based on bot index and level.
    Higher indices and levels get smarter bots.
    Distribution: 25% novato, 30% aprendiz, 25% veterano, 15% experto, 5% maestro
    """
    r = (bot_idx * 7 + level * 3) % 100
    if r < 25:  return INTEL_NOVATO
    if r < 55:  return INTEL_APRENDIZ
    if r < 80:  return INTEL_VETERANO
    if r < 95:  return INTEL_EXPERTO
    return INTEL_MAESTRO


class Bot:
    SIZE          = 16
    SPEED         = 118.0
    ATTACK_RANGE  = 60.0
    ATTACK_CONE   = math.radians(110)
    ATTACK_CD     = 0.55
    AGGRO_PLAYER  = 200.0
    FLEE_MARGIN   = 150.0

    _name_pools = {k: list(v) for k,v in BOT_NAMES_BY_INTEL.items()}

    def __init__(self, x: float, y: float, level: int, bot_idx: int = 0):
        self.x        = float(x)
        self.y        = float(y)
        self.level    = level
        self._bot_idx = bot_idx

        # Intelligence tier
        self.intel = _assign_intel(bot_idx, level)

        pool = Bot._name_pools.get(self.intel, [])
        if pool:
            self.name = pool.pop(random.randint(0, len(pool)-1))
        else:
            self.name = f"{INTEL_NAMES[self.intel]}{bot_idx}"

        outfit_data = BOT_OUTFITS[bot_idx % len(BOT_OUTFITS)]
        self._outfit_col, self._legs_col, self._hair_col = outfit_data

        # Stats scale with intel
        intel_hp_bonus  = {0:0, 1:10, 2:20, 3:40, 4:70}[self.intel]
        intel_atk_bonus = {0:0, 1:2,  2:5,  3:9,  4:15}[self.intel]
        self.max_hp        = 80 + level * 18 + intel_hp_bonus
        self.hp            = float(self.max_hp)
        self.attack_damage = 12 + level * 4 + intel_atk_bonus

        # Per-intel behavioral parameters
        self._aggro_range = self.AGGRO_PLAYER * {0:.0, 1:.5, 2:.8, 3:1.1, 4:1.4}[self.intel]
        self._flee_hp_pct = {0:.9, 1:.6, 2:.4, 3:.25, 4:.15}[self.intel]
        self._hunt_range  = {0:0,  1:400, 2:600, 3:800, 4:1000}[self.intel]
        self._regen_rate  = {0:3.0, 1:2.5, 2:2.0, 3:1.5, 4:1.2}[self.intel]

        self._state      = STATE_ROAM
        self._target_m   = None
        self._waypoint   = (x, y)

        # ── Learning system ───────────────────────────────────────────
        self._kills          = 0       # total kills this run
        self._dmg_dealt      = 0.0     # total damage dealt
        self._dmg_received   = 0.0     # total damage received
        self._fear_level     = 0.0     # 0=calm 1=terrified (drives flee threshold)
        self._aggression     = 0.5     # 0=passive 1=very aggressive
        self._player_uses_spells = False  # learned: player has spells
        self._last_player_attack_angle = None  # learned: player attack direction
        self._dodge_cd       = 0.0     # cooldown after successful dodge
        self._intel_upgrade_notif = None  # (old_intel, new_intel) for HUD
        self._atk_timer  = random.uniform(0, self.ATTACK_CD)
        self._path_timer = 0.0
        self._hit_flash  = 0.0
        self._inv_timer  = 0.0
        self._direction  = random.uniform(0, math.tau)
        self._wander_cd  = random.uniform(0, 3.0)
        self._pursue_timer = 0.0   # Experto/Maestro: tiempo máximo de persecución

        self.rect = pygame.Rect(int(x-self.SIZE), int(y-self.SIZE),
                                self.SIZE*2, self.SIZE*2)

    def is_dead(self) -> bool:
        return self.hp <= 0

    def take_damage(self, amount: int) -> int:
        if self._inv_timer > 0:
            return 0
        actual = max(1, amount)
        self.hp = max(0.0, self.hp - actual)
        self._hit_flash = 0.14
        self._inv_timer = 0.60
        return actual

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float, player, monsters: list, world,
               storm=None) -> int:
        if self.is_dead():
            return 0

        if self._atk_timer  > 0: self._atk_timer  -= dt
        if self._hit_flash  > 0: self._hit_flash  -= dt
        if self._inv_timer  > 0: self._inv_timer  -= dt
        if self._wander_cd  > 0: self._wander_cd  -= dt
        if self._pursue_timer > 0: self._pursue_timer -= dt
        if self._dodge_cd   > 0: self._dodge_cd   -= dt

        # ── Learning: decay fear and update aggression ────────────────
        self._fear_level = max(0.0, self._fear_level - dt * 0.05)
        # Dynamic flee threshold based on fear + base intel
        _base_flee = self._flee_hp_pct
        self._flee_hp_pct = min(0.85, _base_flee + self._fear_level * 0.3)
        # Dynamic aggro range based on aggression
        self._aggro_range = self.AGGRO_PLAYER * {
            0:.0, 1:.5, 2:.8, 3:1.1, 4:1.4}[self.intel] * (0.5 + self._aggression)
        # Intel upgrade check: promoted after enough kills
        _kill_thresholds = {0:3, 1:5, 2:8, 3:12}  # kills needed to reach next tier
        if self.intel < INTEL_MAESTRO:
            needed = _kill_thresholds.get(self.intel, 999)
            if self._kills >= needed:
                old_intel = self.intel
                self.intel = min(INTEL_MAESTRO, self.intel + 1)
                self._intel_upgrade_notif = (old_intel, self.intel)
                self._kills = 0  # reset for next tier
                # Update hunt range and regen for new tier
                self._hunt_range = {0:0,1:400,2:600,3:800,4:1000}[self.intel]
                self._regen_rate = {0:3.0,1:2.5,2:2.0,3:1.5,4:1.2}[self.intel]

        # HP regen (slower for smarter bots — they fight more)
        if self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + self._regen_rate * dt)

        self._choose_state(player, monsters, storm)

        player_dmg = 0
        if   self._state == STATE_ROAM:    self._do_roam(dt, world)
        elif self._state == STATE_HUNT:    self._do_hunt(dt, world, monsters)
        elif self._state == STATE_FLEE:    self._do_flee(dt, world, storm)
        elif self._state == STATE_ATTACK:  player_dmg = self._do_attack_player(dt, player, world)
        elif self._state == STATE_RETREAT: self._do_retreat(dt, world, storm)
        elif self._state == STATE_KITE:    player_dmg = self._do_kite(dt, player, world)

        self.rect.center = (int(self.x), int(self.y))
        return player_dmg

    # ── State decision ────────────────────────────────────────────────────────

    def _choose_state(self, player, monsters, storm):
        # Storm escape: everyone flees (even novatos)
        if storm and not storm.player_inside(self.x, self.y):
            self._state = STATE_FLEE
            return

        dist_p = math.hypot(self.x - player.x, self.y - player.y)
        hp_pct = self.hp / max(1, self.max_hp)

        # ── NOVATO: just wander ───────────────────────────────────────────
        if self.intel == INTEL_NOVATO:
            self._state = STATE_ROAM
            return

        # ── Low HP: retreat (Veterano+) ───────────────────────────────────
        if self.intel >= INTEL_VETERANO and hp_pct < self._flee_hp_pct:
            self._state = STATE_RETREAT
            return

        # ── APRENDIZ: hunt monsters, avoid player ─────────────────────────
        if self.intel == INTEL_APRENDIZ:
            living = [m for m in monsters if not m.is_dead()]
            if living:
                near = [m for m in living if math.hypot(m.x-self.x, m.y-self.y) < self._hunt_range]
                if near:
                    self._target_m = min(near, key=lambda m: math.hypot(m.x-self.x, m.y-self.y))
                    self._state = STATE_HUNT
                    return
            self._state = STATE_ROAM
            return

        # ── VETERANO+: consider attacking player ──────────────────────────
        player_hp_pct = player.hp / max(1, player.max_hp)
        attack_player = False

        if self.intel == INTEL_VETERANO:
            # Attack if close AND (stronger OR player is hurt)
            if dist_p < self._aggro_range and (
                    self.level >= player.level or player_hp_pct < 0.4):
                attack_player = True

        elif self.intel == INTEL_EXPERTO:
            # Attack aggressively — also pursue retreating player
            if dist_p < self._aggro_range:
                attack_player = True
            elif self._pursue_timer > 0:  # keep chasing
                attack_player = True

        elif self.intel == INTEL_MAESTRO:
            # Always attack if in range; kite weakened player
            if dist_p < self._aggro_range:
                attack_player = True
                self._pursue_timer = 8.0  # pursue for 8 seconds
            elif self._pursue_timer > 0:
                attack_player = True

        if attack_player:
            # Maestro/Experto: use kiting if player is full HP and bot is not
            if self.intel >= INTEL_EXPERTO and player_hp_pct > 0.8 and hp_pct < 0.7:
                self._state = STATE_KITE
                return
            self._state = STATE_ATTACK
            return

        # Hunt monsters
        living = [m for m in monsters if not m.is_dead()]
        if living and self._hunt_range > 0:
            near = [m for m in living
                    if math.hypot(m.x-self.x, m.y-self.y) < self._hunt_range]
            if near:
                # Smarter bots pick weaker monsters (easier XP)
                if self.intel >= INTEL_EXPERTO:
                    self._target_m = min(near, key=lambda m: m.level)
                else:
                    self._target_m = min(near, key=lambda m: math.hypot(m.x-self.x, m.y-self.y))
                self._state = STATE_HUNT
                return

        self._state = STATE_ROAM

    # ── State behaviours ──────────────────────────────────────────────────────

    def _do_roam(self, dt: float, world):
        if self._wander_cd <= 0:
            angle = random.uniform(0, math.tau)
            dist  = random.uniform(80, 240)
            wx = self.x + math.cos(angle) * dist
            wy = self.y + math.sin(angle) * dist
            ts  = world.tile_size
            col = int(wx // ts); row = int(wy // ts)
            if world.is_walkable(col, row):
                self._waypoint = (wx, wy)
            self._wander_cd = random.uniform(1.5, 4.0)
        self._move_toward(*self._waypoint, dt, world)

    def _do_hunt(self, dt: float, world, monsters: list):
        m = self._target_m
        if m is None or m.is_dead():
            self._target_m = None
            return
        dist = math.hypot(m.x - self.x, m.y - self.y)
        if dist > self.ATTACK_RANGE + m.SIZE:
            self._move_toward(m.x, m.y, dt, world)
        else:
            if self._atk_timer <= 0:
                self._atk_timer = self.ATTACK_CD
                dmg = max(1, self.attack_damage + random.randint(-3, 5))
                m.take_damage(dmg)
                self._dmg_dealt += dmg
                self._direction = math.atan2(m.y - self.y, m.x - self.x)
                if m.is_dead():
                    self.learn_from_kill(m.level)

    def _do_flee(self, dt: float, world, storm):
        if storm is None:
            self._do_roam(dt, world)
            return
        cx, cy = storm.center_x, storm.center_y
        self._move_toward(cx, cy, dt, world, speed_mult=1.15)

    def _do_retreat(self, dt: float, world, storm):
        """Move away from player to heal; flee storm if needed."""
        if storm and not storm.player_inside(self.x, self.y):
            self._do_flee(dt, world, storm)
            return
        # Pick a waypoint away from danger — wander randomly
        if self._wander_cd <= 0:
            angle = self._direction + math.pi + random.uniform(-0.6, 0.6)
            wx = self.x + math.cos(angle) * 200
            wy = self.y + math.sin(angle) * 200
            ts = world.tile_size
            if world.is_walkable(int(wx//ts), int(wy//ts)):
                self._waypoint = (wx, wy)
            self._wander_cd = 1.5
        self._move_toward(*self._waypoint, dt, world, speed_mult=1.1)

    def _do_attack_player(self, dt: float, player, world) -> int:
        dist = math.hypot(self.x - player.x, self.y - player.y)
        if dist > self.ATTACK_RANGE + player.SIZE:
            # Try learned dodge
            ddx, ddy = self.try_dodge(dt)
            if ddx != 0 or ddy != 0:
                self._move_toward(self.x+ddx, self.y+ddy, dt, world)
            elif self.intel >= INTEL_EXPERTO:
                flank = math.pi * 0.25 * (1 if self._bot_idx % 2 == 0 else -1)
                angle = math.atan2(player.y-self.y, player.x-self.x) + flank
                tx = player.x + math.cos(angle) * 20
                ty = player.y + math.sin(angle) * 20
                self._move_toward(tx, ty, dt, world)
            else:
                self._move_toward(player.x, player.y, dt, world)
            return 0

        if self._atk_timer <= 0:
            self._atk_timer = self.ATTACK_CD
            spread = 2 if self.intel == INTEL_MAESTRO else 4
            dmg = max(1, self.attack_damage + random.randint(-1, spread))
            self._direction = math.atan2(player.y - self.y, player.x - self.x)
            actual = player.take_damage(dmg)
            self._dmg_dealt += actual
            self._aggression = min(1.0, self._aggression + 0.02)
            return actual
        return 0

    def _do_kite(self, dt: float, player, world) -> int:
        """Keep optimal distance — attack when player closes in."""
        OPTIMAL  = self.ATTACK_RANGE * 1.3
        dist     = math.hypot(self.x - player.x, self.y - player.y)
        angle_to = math.atan2(player.y - self.y, player.x - self.x)

        if dist < OPTIMAL * 0.8:
            # Too close — back off
            tx = self.x - math.cos(angle_to) * 80
            ty = self.y - math.sin(angle_to) * 80
            self._move_toward(tx, ty, dt, world, speed_mult=1.2)
        elif dist < OPTIMAL * 1.2:
            # In sweet spot — attack
            if self._atk_timer <= 0:
                self._atk_timer = self.ATTACK_CD
                dmg = max(1, self.attack_damage + random.randint(-2, 3))
                self._direction = angle_to
                return player.take_damage(dmg)
        else:
            # Too far — close in
            self._move_toward(player.x, player.y, dt, world)

        return 0


    # ── Public learning API ───────────────────────────────────────────────────

    def learn_from_hit(self, damage: int, attacker_x: float, attacker_y: float):
        """Called when this bot takes damage. Updates fear and memory."""
        self._dmg_received += damage
        # Increase fear proportional to damage relative to max HP
        fear_gain = damage / max(1, self.max_hp)
        self._fear_level = min(1.0, self._fear_level + fear_gain * 2.5)
        # Reduce aggression when hurt
        self._aggression = max(0.1, self._aggression - 0.05)
        # Remember attacker angle for future dodge
        self._last_player_attack_angle = math.atan2(
            self.y - attacker_y, self.x - attacker_x)

    def learn_from_kill(self, target_level: int):
        """Called when this bot kills something. Increases aggression."""
        self._kills += 1
        self._dmg_dealt += target_level * 10   # proxy for target strength
        self._aggression = min(1.0, self._aggression + 0.08)
        self._fear_level = max(0.0, self._fear_level - 0.15)

    def learn_player_spell(self):
        """Called when player casts a spell near this bot."""
        if not self._player_uses_spells:
            self._player_uses_spells = True
            # Immediately increase safe distance (learned: player has ranged attack)
            if self.intel >= INTEL_VETERANO:
                self.ATTACK_RANGE = type(self).ATTACK_RANGE * 0.7  # stay further

    def try_dodge(self, dt: float) -> tuple[float, float]:
        """
        Attempt to dodge based on learned player attack angle.
        Returns (dx, dy) offset to apply if dodging, else (0,0).
        """
        if (self._last_player_attack_angle is None
                or self._dodge_cd > 0
                or self.intel < INTEL_EXPERTO):
            return 0.0, 0.0
        # 40% chance per second to dodge if learned attack pattern
        if random.random() < 0.4 * dt * (1 + self._kills * 0.1):
            self._dodge_cd = 0.8
            perp = self._last_player_attack_angle + math.pi / 2
            perp += random.choice([-1, 1]) * 0.3
            return math.cos(perp) * 60.0, math.sin(perp) * 60.0
        return 0.0, 0.0

    @property
    def combat_ratio(self) -> float:
        """dmg_dealt / max(1, dmg_received) — >1 means winning, <1 losing."""
        return self._dmg_dealt / max(1.0, self._dmg_received)

    @property
    def intel_name_full(self) -> str:
        return f"{INTEL_NAMES[self.intel]} (kills:{self._kills} ratio:{self.combat_ratio:.1f})"

    def _move_toward(self, tx: float, ty: float, dt: float, world,
                     speed_mult: float = 1.0):
        dx = tx - self.x; dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 4:
            return
        dx /= dist; dy /= dist
        self._direction = math.atan2(dy, dx)
        r  = self.SIZE
        sp = self.SPEED * speed_mult
        nx = self.x + dx * sp * dt
        ny = self.y + dy * sp * dt
        ts = world.tile_size
        if world.is_rect_walkable(nx-r, self.y-r, nx+r, self.y+r):
            self.x = nx
        if world.is_rect_walkable(self.x-r, ny-r, self.x+r, ny+r):
            self.y = ny
        ww = world.width*ts; wh = world.height*ts
        self.x = max(float(r), min(float(ww-r), self.x))
        self.y = max(float(r), min(float(wh-r), self.y))

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen, camera):
        sx = int(self.x - camera.offset_x)
        sy = int(self.y - camera.offset_y)
        if not (-80 <= sx <= camera.view_w+80 and -80 <= sy <= camera.view_h+80):
            return

        from ui.tibia_sprites import draw_bot_sprite
        draw_bot_sprite(screen, sx, sy, self._bot_idx % 4,
                        self._outfit_col, self._legs_col, self._hair_col,
                        direction=self._direction, hit_flash=self._hit_flash > 0)

        # Name + intel badge
        f    = pygame.font.SysFont("Arial", 9, bold=True)
        col  = INTEL_COLORS[self.intel]
        lbl  = f.render(f"{self.name} [{self.level}]", True, col)
        screen.blit(lbl, (sx - lbl.get_width()//2, sy - 58))

        # Intel tier badge (small colored dot)
        intel_lbl = f.render(INTEL_NAMES[self.intel][0], True, col)
        screen.blit(intel_lbl, (sx + 20, sy - 58))

        # HP bar when damaged
        if self.hp < self.max_hp:
            bw = 36; bx = sx - bw//2; by = sy - 64
            pygame.draw.rect(screen, (60, 0, 0), (bx, by, bw, 5))
            fw = int(bw * max(0, self.hp) / self.max_hp)
            pygame.draw.rect(screen, (220, 60, 60), (bx, by, fw, 5))

        # State icon
        icons = {STATE_ATTACK: "⚔", STATE_RETREAT: "💊",
                 STATE_KITE: "↺", STATE_FLEE: "💨"}
        if self._state in icons:
            f2  = pygame.font.SysFont("Arial", 11)
            ico = f2.render(icons[self._state], True, (255, 200, 80))
            screen.blit(ico, (sx - ico.get_width()//2, sy - 72))

        # Intel upgrade flash
        if self._intel_upgrade_notif is not None:
            old_i, new_i = self._intel_upgrade_notif
            fu = pygame.font.SysFont("Arial", 12, bold=True)
            up = fu.render(f"▲ {INTEL_NAMES[new_i]}!", True, (255, 255, 100))
            screen.blit(up, (sx - up.get_width()//2, sy - 86))
