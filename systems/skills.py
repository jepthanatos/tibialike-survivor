"""
systems/skills.py
════════════════════════════════════════════════════════════════
Skills al estilo Tibia que suben con el uso.

Skills disponibles
──────────────────
  sword      – cada golpe de espada da XP
  axe        – cada golpe de hacha da XP
  club       – cada golpe de maza da XP
  distance   – cada proyectil (paladin) da XP
  shielding  – cada bloqueo da XP
  magic      – cada hechizo da XP (= magic_level en SpellMemory)
  fist       – cada golpe desarmado da XP

Fórmula de XP requerida para el siguiente nivel (como Tibia):
  XP(n) = 50 * (n ** 1.6)
  →  nivel 1  :  50 xp
  →  nivel 10 :  1580 xp
  →  nivel 50 :  35350 xp
"""
from __future__ import annotations
import math

SKILL_NAMES = {
    "sword":    "Espada",
    "axe":      "Hacha",
    "club":     "Maza",
    "distance": "Distancia",
    "shielding":"Escudo",
    "magic":    "Magia",
    "fist":     "Puño",
}

ALL_SKILLS = list(SKILL_NAMES.keys())

# XP requerida para pasar del nivel n al n+1
def xp_for_level(n: int) -> int:
    return max(1, int(50 * (n ** 1.6)))


class Skills:
    """Registra y actualiza los skills del jugador."""

    def __init__(self, vocation: str = "sorcerer"):
        self.vocation = vocation
        # nivel de cada skill (todos empiezan en 10 como Tibia)
        self.levels: dict[str, int] = {s: 10 for s in ALL_SKILLS}
        # XP acumulada en el nivel actual
        self.xp: dict[str, float]   = {s: 0.0 for s in ALL_SKILLS}

        # Ajuste inicial por vocación
        self._apply_vocation_bonus()

    def _apply_vocation_bonus(self):
        bonuses = {
            "knight":   {"sword": 5, "axe": 5, "club": 5, "shielding": 5},
            "paladin":  {"distance": 6, "shielding": 3},
            "sorcerer": {"magic": 4},
            "druid":    {"magic": 4},
        }
        for skill, bonus in bonuses.get(self.vocation, {}).items():
            self.levels[skill] += bonus

    # ── Ganar XP ──────────────────────────────────────────────────────────────

    def gain(self, skill: str, amount: float = 1.0) -> bool:
        """
        Añade `amount` de XP al skill.
        Devuelve True si subió de nivel.
        """
        if skill not in self.levels:
            return False
        self.xp[skill] += amount
        needed = xp_for_level(self.levels[skill])
        if self.xp[skill] >= needed:
            self.xp[skill] -= needed
            self.levels[skill] += 1
            return True
        return False

    def gain_melee(self, weapon_type: str = "sword") -> bool:
        """Llamar cada golpe de melee exitoso."""
        return self.gain(weapon_type, 1.0)

    def gain_shielding(self) -> bool:
        """Llamar cada bloqueo."""
        return self.gain("shielding", 2.0)

    def gain_distance(self) -> bool:
        """Llamar cada proyectil de paladin."""
        return self.gain("distance", 1.0)

    def gain_magic(self) -> bool:
        """Llamar cada hechizo lanzado."""
        return self.gain("magic", 1.5)

    # ── Bonificadores al daño / velocidad ────────────────────────────────────

    def melee_bonus(self, weapon_type: str = "sword") -> int:
        """Bonus de daño basado en nivel de skill (cada 10 niveles +5% daño)."""
        lv = self.levels.get(weapon_type, 10)
        return max(0, int((lv - 10) * 0.5))

    def distance_bonus(self) -> int:
        lv = self.levels.get("distance", 10)
        return max(0, int((lv - 10) * 0.6))

    def magic_bonus(self) -> int:
        lv = self.levels.get("magic", 10)
        return max(0, int((lv - 10) * 0.8))

    def shielding_bonus(self) -> float:
        """Extra block chance based on shielding level."""
        lv = self.levels.get("shielding", 10)
        return min(0.30, (lv - 10) * 0.006)

    # ── Active skill for vocation ─────────────────────────────────────────────

    def primary_skill(self) -> str:
        return {
            "knight":  "sword",
            "paladin": "distance",
            "sorcerer":"magic",
            "druid":   "magic",
        }.get(self.vocation, "sword")

    def progress(self, skill: str) -> float:
        """0.0 – 1.0 progress toward next level."""
        if skill not in self.levels:
            return 0.0
        needed = xp_for_level(self.levels[skill])
        return min(1.0, self.xp[skill] / needed)

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "vocation": self.vocation,
            "levels":   dict(self.levels),
            "xp":       {k: round(v, 2) for k, v in self.xp.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Skills":
        sk = cls(vocation=d.get("vocation", "sorcerer"))
        sk.levels.update(d.get("levels", {}))
        sk.xp.update({k: float(v) for k, v in d.get("xp", {}).items()})
        return sk

    def __repr__(self):
        primary = self.primary_skill()
        return (f"<Skills voc={self.vocation} "
                f"{primary}={self.levels[primary]} "
                f"shield={self.levels['shielding']}>")
