"""
systems/lifetime_stats.py
═══════════════════════════════════════════════════════════════
Historial persistente de todas las partidas y rankings.

Fichero: stats_history.json
Formato:
{
  "runs": [ <run_dict>, ... ],          ← lista cronológica (FIFO, max 100)
  "totals": { ... },                    ← acumulados de vida
  "records": { ... }                    ← récords absolutos
}

Rankings disponibles
────────────────────
  "survival"    → tiempo de supervivencia
  "level"       → nivel alcanzado
  "kills"       → muertes totales
  "damage"      → daño total infligido
  "bosses"      → jefes derrotados
  "elites"      → élites derrotados
  "spells"      → hechizos lanzados
  "xp"          → xp ganada
  "distance"    → km recorridos
"""
from __future__ import annotations
import json
import os
from typing import Any

HISTORY_FILE = "stats_history.json"
MAX_RUNS_STORED = 100
TOP_N           = 10     # entradas por ranking

RANKING_KEYS: list[tuple[str, str, str]] = [
    ("survival",  "elapsed_s",          "Supervivencia (s)"),
    ("level",     "level_reached",      "Nivel alcanzado"),
    ("kills",     "total_kills",        "Kills totales"),
    ("damage",    "total_damage_dealt", "Daño infligido"),
    ("bosses",    "boss_kills",         "Jefes derrotados"),
    ("elites",    "elite_kills",        "Élites derrotados"),
    ("spells",    "spells_cast_total",  "Hechizos lanzados"),
    ("xp",        "xp_earned",          "XP ganada"),
    ("distance",  "distance_walked_km", "Km recorridos"),
]


def _fmt_time(s: float) -> str:
    s = int(s)
    return f"{s//60:02d}:{s%60:02d}"


class LifetimeStats:
    def __init__(self):
        self.runs: list[dict]    = []
        self.totals: dict        = {}
        self.records: dict       = {}
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        if not os.path.exists(HISTORY_FILE):
            return
        try:
            with open(HISTORY_FILE) as f:
                data = json.load(f)
            self.runs    = data.get("runs", [])
            self.totals  = data.get("totals", {})
            self.records = data.get("records", {})
        except Exception:
            pass

    def save(self):
        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump({
                    "runs":    self.runs,
                    "totals":  self.totals,
                    "records": self.records,
                }, f, indent=2)
        except Exception:
            pass

    # ── Register a completed run ──────────────────────────────────────────────

    def register_run(self, run_dict: dict):
        """Call after each run with RunStats.to_dict() result."""
        # Patch: add spells_cast_total for ranking key
        sc = run_dict.get("spells_cast", {})
        run_dict["spells_cast_total"] = sum(sc.values()) if isinstance(sc, dict) else 0

        # Append and trim
        self.runs.append(run_dict)
        if len(self.runs) > MAX_RUNS_STORED:
            self.runs = self.runs[-MAX_RUNS_STORED:]

        self._update_totals(run_dict)
        self._update_records(run_dict)
        self.save()

    # ── Totals ────────────────────────────────────────────────────────────────

    def _update_totals(self, r: dict):
        additive = [
            "elapsed_s", "total_kills", "elite_kills", "boss_kills",
            "melee_hits", "melee_damage_dealt", "total_spell_damage",
            "total_damage_dealt", "damage_received", "storm_damage",
            "damage_blocked", "times_hit", "xp_earned", "mp_spent",
            "items_found", "spells_cast_total", "distance_walked_km",
        ]
        t = self.totals
        t["runs_completed"] = t.get("runs_completed", 0) + 1
        for key in additive:
            t[key] = t.get(key, 0) + r.get(key, 0)

        # Kill breakdown by monster type
        for mtype, count in r.get("kills", {}).items():
            kills_key = f"kills_{mtype}"
            t[kills_key] = t.get(kills_key, 0) + count

        # Spell damage breakdown
        for sid, dmg in r.get("spell_damage_dealt", {}).items():
            sdmg_key = f"spell_dmg_{sid}"
            t[sdmg_key] = t.get(sdmg_key, 0) + dmg

        # Spells learned (union)
        learned = set(t.get("spells_learned_ever", []))
        learned.update(r.get("spells_learned", []))
        t["spells_learned_ever"] = sorted(learned)

    # ── Records ──────────────────────────────────────────────────────────────

    def _update_records(self, r: dict):
        rec = self.records
        records_max = [
            ("longest_run_s",          "elapsed_s"),
            ("highest_level",          "level_reached"),
            ("most_kills_run",         "total_kills"),
            ("most_damage_dealt_run",  "total_damage_dealt"),
            ("most_bosses_run",        "boss_kills"),
            ("most_elites_run",        "elite_kills"),
            ("most_xp_run",            "xp_earned"),
            ("most_spells_cast_run",   "spells_cast_total"),
            ("furthest_walked_km",     "distance_walked_km"),
            ("highest_storm_phase",    "storm_phase"),
            ("most_items_found_run",   "items_found"),
        ]
        for rec_key, run_key in records_max:
            val = r.get(run_key, 0)
            if val > rec.get(rec_key, 0):
                rec[rec_key] = val

    # ── Rankings ─────────────────────────────────────────────────────────────

    def ranking(self, key: str) -> list[dict]:
        """
        Returns top-N runs sorted by `key` field (descending).
        key must be one of the rank_ids in RANKING_KEYS.
        """
        field = next((f for k, f, _ in RANKING_KEYS if k == key), key)
        sorted_runs = sorted(self.runs, key=lambda r: r.get(field, 0), reverse=True)
        return sorted_runs[:TOP_N]

    def all_rankings(self) -> dict[str, list[dict]]:
        return {k: self.ranking(k) for k, _, _ in RANKING_KEYS}

    # ── Formatted helpers ─────────────────────────────────────────────────────

    def format_record(self, key: str) -> str:
        val = self.records.get(key, 0)
        if "s" in key and "spells" not in key and "boss" not in key:
            return _fmt_time(val)
        if "km" in key:
            return f"{val:.3f} km"
        return str(int(val))

    def total_playtime_str(self) -> str:
        return _fmt_time(self.totals.get("elapsed_s", 0))

    def total_runs(self) -> int:
        return self.totals.get("runs_completed", 0)

    # ── Averages ─────────────────────────────────────────────────────────────

    def average(self, field: str) -> float:
        n = max(1, self.total_runs())
        return self.totals.get(field, 0) / n

    # ── Summary line for a run entry ─────────────────────────────────────────

    @staticmethod
    def run_summary_line(run: dict) -> str:
        t   = _fmt_time(run.get("elapsed_s", 0))
        lv  = run.get("level_reached", 0)
        k   = run.get("total_kills", 0)
        dmg = run.get("total_damage_dealt", 0)
        return f"{t}  Lv{lv}  {k}k  {dmg:,}dmg"
