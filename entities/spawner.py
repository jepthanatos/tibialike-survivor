import random
import math
from entities.monster import Monster, available_types, MONSTER_DATA
from systems.elites import roll_elite, apply_modifiers
from systems.dungeons import in_any_dungeon, MONSTER_DENSITY
from systems.biomes import BIOMES
from constants import TILE_SIZE

TARGET_POP  = 75
MIN_POP     = 60
SPAWN_MIN   = 15
SPAWN_MAX   = 42


def _biome_weighted_choice(types, biome_map, col, row, rng=random):
    """Picks a monster type weighted by the biome at (col, row)."""
    bname   = biome_map.get(col, row) if biome_map else "grassland"
    weights_dict = BIOMES.get(bname, BIOMES["grassland"])["spawn_weights"]
    weighted = []
    for t in types:
        w = weights_dict.get(t, 0.5)
        weighted.append((t, max(0.05, w)))
    all_t, all_w = zip(*weighted)
    return rng.choices(all_t, weights=all_w, k=1)[0]


class Spawner:
    def __init__(self, world, player_level, dungeons=None, biome_map=None):
        self.world      = world
        self.monsters   = []
        self._timer     = 0.0
        self._elapsed   = 0.0   # game time for difficulty scaling
        self._dungeons  = dungeons or []
        self._biome_map = biome_map
        self._fill_map(player_level)

    def _fill_map(self, player_level):
        from systems.zones import get_zone, get_zone_monster_types, get_zone_level_bonus
        W, H   = self.world.width, self.world.height
        cx, cy = W // 2, H // 2
        map_cx = cx * TILE_SIZE; map_cy = cy * TILE_SIZE
        map_r  = min(W, H) // 2 * TILE_SIZE
        types  = available_types(player_level)

        for _ in range(TARGET_POP):
            for attempt in range(60):
                col = random.randint(4, W-4); row = random.randint(4, H-4)
                if not self.world.is_walkable(col, row): continue
                mx  = col*TILE_SIZE + TILE_SIZE//2
                my  = row*TILE_SIZE + TILE_SIZE//2
                zone      = get_zone(mx, my, map_cx, map_cy, map_r)
                lv_bonus  = get_zone_level_bonus(zone)
                lv        = self._roll_level(player_level + lv_bonus//2, boost=lv_bonus//2)
                mtype     = random.choice(get_zone_monster_types(zone))
                self.monsters.append(self._make(mx, my, mtype, lv, col, row))
                break

        for zone in self._dungeons:
            for _ in range(int(20 * MONSTER_DENSITY)):
                col = int(zone.center_col + random.randint(-zone.radius+2, zone.radius-2))
                row = int(zone.center_row + random.randint(-zone.radius+2, zone.radius-2))
                if not (0<=col<W and 0<=row<H): continue
                if not self.world.is_walkable(col, row): continue
                mtype = _biome_weighted_choice(types, self._biome_map, col, row)
                level = self._roll_level(player_level, boost=3)
                x = col*TILE_SIZE+TILE_SIZE//2; y = row*TILE_SIZE+TILE_SIZE//2
                self.monsters.append(self._make(x, y, mtype, level, col, row))

    def _try_spawn_random(self, types, player_level, avoid_cx, avoid_cy,
                          min_dist, max_tries):
        W, H = self.world.width, self.world.height
        for _ in range(max_tries):
            col = random.randint(4, W-4); row = random.randint(4, H-4)
            if not self.world.is_walkable(col, row): continue
            if abs(col-avoid_cx)+abs(row-avoid_cy) < min_dist: continue
            mtype = _biome_weighted_choice(types, self._biome_map, col, row)
            level = self._roll_level(player_level)
            x = col*TILE_SIZE+TILE_SIZE//2; y = row*TILE_SIZE+TILE_SIZE//2
            return self._make(x, y, mtype, level, col, row)
        return None

    def _make(self, x, y, mtype, level, col=None, row=None):
        m    = Monster(x, y, mtype, level)
        mods = roll_elite()
        if mods: apply_modifiers(m, mods)
        return m

    def _respawn(self, player, count):
        types   = available_types(player.level)
        pc, pr  = int(player.x//TILE_SIZE), int(player.y//TILE_SIZE)
        W, H    = self.world.width, self.world.height
        spawned = 0
        for _ in range(count*20):
            if spawned >= count: break
            if self._dungeons and random.random() < 0.25:
                zone = random.choice(self._dungeons)
                col  = zone.center_col + random.randint(-zone.radius+3, zone.radius-3)
                row  = zone.center_row + random.randint(-zone.radius+3, zone.radius-3)
            else:
                angle = random.uniform(0, math.tau)
                dist  = random.randint(SPAWN_MIN, SPAWN_MAX)
                col   = int(pc + math.cos(angle)*dist)
                row   = int(pr + math.sin(angle)*dist)
            if not (0<=col<W and 0<=row<H): continue
            if not self.world.is_walkable(col, row): continue
            in_dung = any(z.contains_tile(col,row) for z in self._dungeons)
            level   = self._roll_level(player.level, boost=3 if in_dung else 0)
            from systems.zones import get_zone, get_zone_monster_types, get_zone_level_bonus
            mx   = col*TILE_SIZE+TILE_SIZE//2; my = row*TILE_SIZE+TILE_SIZE//2
            map_cx = (self.world.width//2)*TILE_SIZE
            map_cy = (self.world.height//2)*TILE_SIZE
            map_r  = min(self.world.width, self.world.height)//2*TILE_SIZE
            zone  = get_zone(mx, my, map_cx, map_cy, map_r)
            lv_bonus = get_zone_level_bonus(zone) + self.difficulty_bonus
            level = self._roll_level(player.level + lv_bonus//2, boost=lv_bonus//2)
            mtype = random.choice(get_zone_monster_types(zone))
            self.monsters.append(self._make(mx, my, mtype, level, col, row))
            spawned += 1

    def add_monster(self, monster):
        self.monsters.append(monster)

    def _roll_level(self, player_level, boost=0):
        diff = self.difficulty_bonus
        base = player_level + diff
        return random.randint(max(0, base-2), base+4+boost)

    def update(self, dt, player, world):
        damages = []; spell_events = []
        self._elapsed += dt
        self.monsters = [m for m in self.monsters if not m.is_dead()]
        for m in self.monsters:
            dmg, spell_ev = m.update(dt, player, world)
            if dmg > 0: damages.append(dmg)
            if spell_ev: spell_events.append(spell_ev)
        self._timer -= dt
        if self._timer <= 0:
            self._timer = 5.0
            if len(self.monsters) < MIN_POP:
                self._respawn(player, TARGET_POP-len(self.monsters))
        return damages, spell_events

    @property
    def difficulty_bonus(self) -> int:
        """Extra monster level based on elapsed time. +1 every 5 minutes."""
        return int(self._elapsed / 300)
