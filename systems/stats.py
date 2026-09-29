"""
systems/stats.py
══════════════════════════════════════════════════════════════
Tracking de estadísticas en tiempo real y acumuladas.

RunStats     → estadísticas de UNA partida (se resetea al reiniciar)
LifetimeStats→ histórico de TODAS las partidas + rankings

Métricas rastreadas por partida
────────────────────────────────
Supervivencia
  elapsed_s           tiempo total de la partida
  level_reached       nivel final
  storm_phase         fase de tormenta alcanzada
  time_in_storm_s     segundos dentro de la tormenta
  dungeon_zones_entered  zonas de mazmorra visitadas

Combate
  kills               dict  mtype → int
  elite_kills         int
  boss_kills          int
  melee_hits          int   impactos cuerpo a cuerpo exitosos
  melee_damage_dealt  int
  spell_damage_dealt  dict  spell_id → int
  spells_cast         dict  spell_id → int
  spells_learned      list  spell_ids aprendidos en esta run

Daño recibido
  damage_received     int   total
  storm_damage        int
  damage_blocked      int   daño bloqueado por escudo
  times_hit           int

Recursos
  xp_earned           int
  mp_spent            int
  items_found         int
  items_equipped_peak int   máximo equipado simultáneamente
  best_gear_rarity    str   rareza más alta obtenida

Movimiento
  distance_walked_px  float  píxeles totales recorridos
"""
from __future__ import annotations
import time
import datetime
from typing import Any


# Rarezas en orden ascendente (para comparar)
RARITY_ORDER = ["common", "uncommon", "rare", "epic"]


class RunStats:
    """Estadísticas de una sola partida."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.start_ts: float         = time.time()
        self.elapsed_s: float        = 0.0
        self.level_reached: int      = 0
        self.storm_phase: int        = 0
        self.time_in_storm_s: float  = 0.0
        self.dungeon_zones_entered: set = set()

        self.kills: dict[str, int]         = {}
        self.elite_kills: int              = 0
        self.boss_kills: int               = 0
        self.melee_hits: int               = 0
        self.melee_damage_dealt: int       = 0
        self.spell_damage_dealt: dict[str,int] = {}
        self.spells_cast: dict[str, int]   = {}
        self.spells_learned: list[str]     = []

        self.damage_received: int  = 0
        self.storm_damage: int     = 0
        self.damage_blocked: int   = 0
        self.times_hit: int        = 0

        self.xp_earned: int        = 0
        self.mp_spent: int         = 0
        self.items_found: int      = 0
        self.items_equipped_peak: int = 0
        self.best_gear_rarity: str = "common"

        self.distance_walked_px: float = 0.0
        self._last_px: tuple | None   = None

    # ── Helpers para registrar eventos ────────────────────────────────────────

    def on_kill(self, monster):
        mtype = monster.mtype
        self.kills[mtype] = self.kills.get(mtype, 0) + 1
        if getattr(monster, "is_boss", False):
            self.boss_kills += 1
        elif getattr(monster, "is_elite", False):
            self.elite_kills += 1

    def on_melee_hit(self, damage: int):
        self.melee_hits += 1
        self.melee_damage_dealt += damage

    def on_spell_hit(self, spell_id: str, damage: int):
        self.spell_damage_dealt[spell_id] = (
            self.spell_damage_dealt.get(spell_id, 0) + damage)

    def on_spell_cast(self, spell_id: str, mp_cost: int):
        self.spells_cast[spell_id] = self.spells_cast.get(spell_id, 0) + 1
        self.mp_spent += mp_cost

    def on_spell_learned(self, spell_id: str):
        if spell_id not in self.spells_learned:
            self.spells_learned.append(spell_id)

    def on_damage_received(self, amount: int, source: str = "monster"):
        if amount <= 0:
            return
        self.damage_received += amount
        self.times_hit += 1
        if source == "storm":
            self.storm_damage += amount

    def on_damage_blocked(self, amount: int):
        self.damage_blocked += amount

    def on_item_found(self, item: dict):
        self.items_found += 1
        rarity = item.get("rarity", "common")
        if RARITY_ORDER.index(rarity) > RARITY_ORDER.index(self.best_gear_rarity):
            self.best_gear_rarity = rarity

    def on_item_equipped_check(self, equipped_count: int):
        if equipped_count > self.items_equipped_peak:
            self.items_equipped_peak = equipped_count

    def on_player_moved(self, px: float, py: float):
        if self._last_px is not None:
            self.distance_walked_px += (
                abs(px - self._last_px[0]) + abs(py - self._last_px[1]))
        self._last_px = (px, py)

    def on_dungeon_entered(self, zone_id: int):
        self.dungeon_zones_entered.add(zone_id)

    def on_storm_tick(self, dt: float, in_storm: bool):
        if in_storm:
            self.time_in_storm_s += dt

    def on_xp_gained(self, amount: int):
        self.xp_earned += amount

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def total_kills(self) -> int:
        return sum(self.kills.values())

    @property
    def total_spell_damage(self) -> int:
        return sum(self.spell_damage_dealt.values())

    @property
    def total_damage_dealt(self) -> int:
        return self.melee_damage_dealt + self.total_spell_damage

    @property
    def total_spells_cast(self) -> int:
        return sum(self.spells_cast.values())

    @property
    def favourite_spell(self) -> str | None:
        if not self.spells_cast:
            return None
        return max(self.spells_cast, key=self.spells_cast.get)

    @property
    def most_killed_type(self) -> str | None:
        if not self.kills:
            return None
        return max(self.kills, key=self.kills.get)

    @property
    def km_walked(self) -> float:
        return self.distance_walked_px / 32_000  # 32 px/tile ×1000 tiles/km

    @property
    def dungeon_count(self) -> int:
        return len(self.dungeon_zones_entered)

    def finalise(self, player, storm):
        """Call this when the run ends to snapshot final values."""
        self.elapsed_s    = (time.time() - self.start_ts)
        self.level_reached = player.level
        self.storm_phase   = storm.phase_reached

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "date":                  datetime.datetime.now().isoformat(timespec="seconds"),
            "elapsed_s":             round(self.elapsed_s, 1),
            "level_reached":         self.level_reached,
            "storm_phase":           self.storm_phase,
            "time_in_storm_s":       round(self.time_in_storm_s, 1),
            "dungeon_count":         self.dungeon_count,
            "kills":                 dict(self.kills),
            "total_kills":           self.total_kills,
            "elite_kills":           self.elite_kills,
            "boss_kills":            self.boss_kills,
            "melee_hits":            self.melee_hits,
            "melee_damage_dealt":    self.melee_damage_dealt,
            "spell_damage_dealt":    dict(self.spell_damage_dealt),
            "total_spell_damage":    self.total_spell_damage,
            "total_damage_dealt":    self.total_damage_dealt,
            "spells_cast":           dict(self.spells_cast),
            "spells_learned":        list(self.spells_learned),
            "damage_received":       self.damage_received,
            "storm_damage":          self.storm_damage,
            "damage_blocked":        self.damage_blocked,
            "times_hit":             self.times_hit,
            "xp_earned":             self.xp_earned,
            "mp_spent":              self.mp_spent,
            "items_found":           self.items_found,
            "items_equipped_peak":   self.items_equipped_peak,
            "best_gear_rarity":      self.best_gear_rarity,
            "distance_walked_km":    round(self.km_walked, 3),
        }
