"""
systems/spells.py
Catálogo de hechizos al estilo Tibia clásico.

Vocaciones
──────────
  knight    – cuerpo a cuerpo, poca magia
  paladin   – distancia + magia media
  sorcerer  – magia ofensiva máxima
  druid     – magia curativa y elemental

Mecánica de aprendizaje
───────────────────────
  · Los hechizos se aprenden observando a los monstruos o al subir nivel mágico.
  · El nivel mágico sube cada 8 lanzamientos.
  · Cada vocación tiene su propio catálogo de hechizos accesibles.
"""
from __future__ import annotations
import math

RARITY_ORDER = ["common", "uncommon", "rare", "epic"]

# ── Catálogo completo de hechizos ─────────────────────────────────────────────
# Campos: name, incantation (conjuro Tibia), color_rgb, mp_cost, damage,
#         speed_px_s, radius, pierce, aoe_radius, learn_thresh, min_magic_lv,
#         range_px, description, vocations (lista)

SPELL_CATALOGUE: dict[str, dict] = {

    # ── Hechizos de Sorcerer ──────────────────────────────────────────────────
    "exevo vis": {
        "name":         "Magic Missile",
        "incantation":  "exevo vis",
        "color":        (100, 180, 255),
        "mp_cost":      20,
        "damage":       30,
        "speed":        360.0,
        "radius":       6,
        "pierce":       False,
        "aoe_radius":   0,
        "learn_thresh": 3,
        "min_magic_lv": 0,
        "range_px":     460.0,
        "desc":         "Proyectil mágico básico.",
        "vocations":    ["sorcerer", "druid", "paladin", "knight"],
    },
    "exevo gran vis": {
        "name":         "Great Energy Beam",
        "incantation":  "exevo gran vis",
        "color":        (80, 160, 255),
        "mp_cost":      115,
        "damage":       120,
        "speed":        560.0,
        "radius":       5,
        "pierce":       True,
        "aoe_radius":   0,
        "learn_thresh": 5,
        "min_magic_lv": 8,
        "range_px":     700.0,
        "desc":         "Rayo de energía que atraviesa todo.",
        "vocations":    ["sorcerer"],
    },
    "exevo gran mas vis": {
        "name":         "Ultimate Energy Strike",
        "incantation":  "exevo gran mas vis",
        "color":        (60, 220, 255),
        "mp_cost":      160,
        "damage":       200,
        "speed":        480.0,
        "radius":       8,
        "pierce":       False,
        "aoe_radius":   60,
        "learn_thresh": 7,
        "min_magic_lv": 12,
        "range_px":     600.0,
        "desc":         "Golpe supremo de energía con explosión.",
        "vocations":    ["sorcerer"],
    },
    "exura mort": {
        "name":         "Death Strike",
        "incantation":  "exura mort",
        "color":        (180, 40, 200),
        "mp_cost":      40,
        "damage":       55,
        "speed":        320.0,
        "radius":       9,
        "pierce":       True,
        "aoe_radius":   30,
        "learn_thresh": 6,
        "min_magic_lv": 9,
        "range_px":     520.0,
        "desc":         "Espiral de muerte que atraviesa y explota.",
        "vocations":    ["sorcerer"],
    },
    "exevo flam": {
        "name":         "Fireball",
        "incantation":  "exevo flam",
        "color":        (255, 110, 30),
        "mp_cost":      60,
        "damage":       80,
        "speed":        280.0,
        "radius":       9,
        "pierce":       False,
        "aoe_radius":   52,
        "learn_thresh": 5,
        "min_magic_lv": 3,
        "range_px":     560.0,
        "desc":         "Bola de fuego con explosión de área.",
        "vocations":    ["sorcerer", "druid"],
    },

    # ── Hechizos de Druid ─────────────────────────────────────────────────────
    "exevo tera": {
        "name":         "Stone Shower",
        "incantation":  "exevo tera",
        "color":        (160, 120, 60),
        "mp_cost":      45,
        "damage":       50,
        "speed":        300.0,
        "radius":       8,
        "pierce":       False,
        "aoe_radius":   44,
        "learn_thresh": 4,
        "min_magic_lv": 4,
        "range_px":     480.0,
        "desc":         "Lluvia de piedras en área.",
        "vocations":    ["druid"],
    },
    "exevo gran tera": {
        "name":         "Great Stone Shower",
        "incantation":  "exevo gran tera",
        "color":        (130, 90, 40),
        "mp_cost":      110,
        "damage":       140,
        "speed":        260.0,
        "radius":       12,
        "pierce":       False,
        "aoe_radius":   64,
        "learn_thresh": 7,
        "min_magic_lv": 11,
        "range_px":     520.0,
        "desc":         "Gran lluvia de rocas devastadora.",
        "vocations":    ["druid"],
    },
    "exevo frigo": {
        "name":         "Ice Strike",
        "incantation":  "exevo frigo",
        "color":        (140, 220, 255),
        "mp_cost":      35,
        "damage":       42,
        "speed":        320.0,
        "radius":       7,
        "pierce":       False,
        "aoe_radius":   0,
        "learn_thresh": 3,
        "min_magic_lv": 2,
        "range_px":     440.0,
        "desc":         "Lanza témpano de hielo.",
        "vocations":    ["druid"],
    },
    "exevo gran mas frigo": {
        "name":         "Ultimate Ice Strike",
        "incantation":  "exevo gran mas frigo",
        "color":        (100, 200, 255),
        "mp_cost":      155,
        "damage":       190,
        "speed":        380.0,
        "radius":       10,
        "pierce":       True,
        "aoe_radius":   40,
        "learn_thresh": 8,
        "min_magic_lv": 13,
        "range_px":     600.0,
        "desc":         "Blizzard devastador que congela todo.",
        "vocations":    ["druid"],
    },

    # ── Hechizos de Paladin ───────────────────────────────────────────────────
    "exevo con": {
        "name":         "Conjure Arrow",
        "incantation":  "exevo con",
        "color":        (200, 200, 80),
        "mp_cost":      14,
        "damage":       28,
        "speed":        480.0,
        "radius":       4,
        "pierce":       False,
        "aoe_radius":   0,
        "learn_thresh": 2,
        "min_magic_lv": 0,
        "range_px":     520.0,
        "desc":         "Dispara una flecha mágica veloz.",
        "vocations":    ["paladin"],
    },
    "exevo con hur": {
        "name":         "Conjure Bolt",
        "incantation":  "exevo con hur",
        "color":        (240, 200, 50),
        "mp_cost":      22,
        "damage":       44,
        "speed":        540.0,
        "radius":       4,
        "pierce":       False,
        "aoe_radius":   0,
        "learn_thresh": 4,
        "min_magic_lv": 4,
        "range_px":     580.0,
        "desc":         "Perno sagrado de alta velocidad.",
        "vocations":    ["paladin"],
    },
    "exevo gran con": {
        "name":         "Divine Caldera",
        "incantation":  "exevo gran con",
        "color":        (255, 230, 100),
        "mp_cost":      120,
        "damage":       160,
        "speed":        400.0,
        "radius":       7,
        "pierce":       False,
        "aoe_radius":   56,
        "learn_thresh": 6,
        "min_magic_lv": 10,
        "range_px":     560.0,
        "desc":         "Lluvia de proyectiles sagrados.",
        "vocations":    ["paladin"],
    },
    "exura san": {
        "name":         "Heal Friend",
        "incantation":  "exura san",
        "color":        (80, 255, 120),
        "mp_cost":      140,
        "damage":       -60,   # negativo = curación
        "speed":        0.0,
        "radius":       0,
        "pierce":       False,
        "aoe_radius":   0,
        "learn_thresh": 4,
        "min_magic_lv": 6,
        "range_px":     0.0,
        "desc":         "Cura a ti mismo.",
        "vocations":    ["paladin", "druid"],
    },

    # ── Hechizos de Knight ────────────────────────────────────────────────────
    "exori": {
        "name":         "Berserk",
        "incantation":  "exori",
        "color":        (255, 80, 40),
        "mp_cost":      115,
        "damage":       100,
        "speed":        0.0,
        "radius":       0,
        "pierce":       False,
        "aoe_radius":   52,   # melee AOE
        "learn_thresh": 3,
        "min_magic_lv": 0,
        "range_px":     52.0,   # rango melee ampliado
        "desc":         "Ataque giratorio que daña a todos los cercanos.",
        "vocations":    ["knight"],
    },
    "exori gran": {
        "name":         "Annihilation",
        "incantation":  "exori gran",
        "color":        (255, 40, 10),
        "mp_cost":      200,
        "damage":       300,
        "speed":        0.0,
        "radius":       0,
        "pierce":       False,
        "aoe_radius":   64,
        "learn_thresh": 6,
        "min_magic_lv": 8,
        "range_px":     64.0,
        "desc":         "El golpe más devastador del Knight.",
        "vocations":    ["knight"],
    },
    "utamo vita": {
        "name":         "Magic Shield",
        "incantation":  "utamo vita",
        "color":        (100, 150, 255),
        "mp_cost":      50,
        "damage":       0,
        "speed":        0.0,
        "radius":       0,
        "pierce":       False,
        "aoe_radius":   0,
        "learn_thresh": 3,
        "min_magic_lv": 3,
        "range_px":     0.0,
        "desc":         "Escudo mágico temporal (+50% bloqueo 8s).",
        "vocations":    ["knight", "paladin"],
    },

    # ── Hechizos de monstruo (observables) ───────────────────────────────────
    "exevo mas vis": {
        "name":         "Energy Wave",
        "incantation":  "exevo mas vis",
        "color":        (80, 170, 255),
        "mp_cost":      0,
        "damage":       65,
        "speed":        420.0,
        "radius":       5,
        "pierce":       True,
        "aoe_radius":   0,
        "learn_thresh": 6,
        "min_magic_lv": 4,
        "range_px":     640.0,
        "desc":         "Onda de energía imparable (sorcerer/druid).",
        "vocations":    ["sorcerer", "druid", "paladin"],
    },
    "exura": {
        "name":         "Light Healing",
        "incantation":  "exura",
        "color":        (80, 255, 120),
        "mp_cost":      20,
        "damage":       -30,
        "speed":        0.0,
        "radius":       0,
        "pierce":       False,
        "aoe_radius":   0,
        "learn_thresh": 2,
        "min_magic_lv": 0,
        "range_px":     0.0,
        "desc":         "Curación leve.",
        "vocations":    ["druid", "paladin", "sorcerer", "knight"],
    },
    "exevo mort": {
        "name":         "Poison Wave",
        "incantation":  "exevo mort",
        "color":        (80, 220, 60),
        "mp_cost":      0,
        "damage":       38,
        "speed":        240.0,
        "radius":       8,
        "pierce":       True,
        "aoe_radius":   0,
        "learn_thresh": 4,
        "min_magic_lv": 1,
        "range_px":     500.0,
        "desc":         "Onda venenosa que atraviesa enemigos.",
        "vocations":    ["druid", "sorcerer", "paladin", "knight"],
    },
    "exevo gran mas flam": {
        "name":         "Ultimate Explosion",
        "incantation":  "exevo gran mas flam",
        "color":        (255, 80, 10),
        "mp_cost":      0,
        "damage":       180,
        "speed":        260.0,
        "radius":       11,
        "pierce":       False,
        "aoe_radius":   72,
        "learn_thresh": 9,
        "min_magic_lv": 14,
        "range_px":     560.0,
        "desc":         "La mayor explosión mágica conocida.",
        "vocations":    ["sorcerer"],
    },
}

# ── Qué hechizos puede lanzar cada tipo de monstruo ──────────────────────────
MONSTER_SPELLS: dict[str, list[str]] = {
    "rat":         [],
    "zombie":      ["exevo mort"],
    "skeleton":    ["exevo vis", "exevo mort"],
    "orc":         ["exevo vis"],
    "dark_wizard": ["exevo mas vis", "exevo gran vis", "exura mort"],
    "dragon":      ["exevo flam", "exevo gran mas flam"],
    "demon":       ["exura mort", "exevo flam", "exevo gran mas flam"],
    "dragon_lord": ["exevo gran vis", "exevo gran mas flam", "exura mort"],
    "wolf":       [],
    "troll":      [],
    "bear":       [],
    "cyclops":    ["exevo vis"],
    "fire_devil": ["exevo flam", "exevo vis"],
    "vampire":    ["exura mort", "exevo mas vis"],
}

# Rango de observación
OBSERVE_RANGE = 380.0

# ── Hechizos disponibles por vocación ────────────────────────────────────────
VOCATION_SPELLS: dict[str, list[str]] = {}
for _sid, _data in SPELL_CATALOGUE.items():
    for _voc in _data.get("vocations", []):
        VOCATION_SPELLS.setdefault(_voc, []).append(_sid)


# ── SpellMemory ───────────────────────────────────────────────────────────────
class SpellMemory:
    """Registra observaciones y hechizos aprendidos del jugador."""

    def __init__(self, known: list[str] | None = None, vocation: str = "sorcerer"):
        self.observations: dict[str, int] = {}
        self.known_spells: list[str]      = list(known or [])
        # Starting magic level per vocation (like Tibia)
        _start_ml = {"knight": 0, "paladin": 2, "druid": 4, "sorcerer": 4}
        self.magic_level: int             = _start_ml.get(vocation, 0)
        self._cast_count: int             = 0
        self.vocation: str                = vocation

    def observe(self, spell_id: str) -> bool:
        if spell_id in self.known_spells:
            return False
        if spell_id not in SPELL_CATALOGUE:
            return False
        self.observations[spell_id] = self.observations.get(spell_id, 0) + 1
        data = SPELL_CATALOGUE[spell_id]
        if (self.observations[spell_id] >= data["learn_thresh"] and
                self.magic_level >= data["min_magic_lv"]):
            self.known_spells.append(spell_id)
            return True
        return False

    def observation_progress(self, spell_id: str) -> tuple[int, int]:
        if spell_id not in SPELL_CATALOGUE:
            return 0, 1
        return self.observations.get(spell_id, 0), SPELL_CATALOGUE[spell_id]["learn_thresh"]

    def on_spell_cast(self) -> bool:
        self._cast_count += 1
        if self._cast_count >= 8:
            self._cast_count = 0
            self.magic_level += 1
            return True
        return False

    def can_learn(self, spell_id: str) -> bool:
        if spell_id not in SPELL_CATALOGUE:
            return False
        return self.magic_level >= SPELL_CATALOGUE[spell_id]["min_magic_lv"]

    def pending_spells(self) -> list[str]:
        return [sid for sid in self.observations
                if sid not in self.known_spells and sid in SPELL_CATALOGUE]

    def vocation_spells(self) -> list[str]:
        """All spell IDs accessible for this vocation."""
        return VOCATION_SPELLS.get(self.vocation, [])

    def to_dict(self) -> dict:
        return {
            "known_spells":  self.known_spells,
            "magic_level":   self.magic_level,
            "observations":  self.observations,
            "vocation":      self.vocation,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SpellMemory":
        sm = cls(known=d.get("known_spells", []),
                 vocation=d.get("vocation", "sorcerer"))
        sm.magic_level  = d.get("magic_level", 0)
        sm.observations = d.get("observations", {})
        return sm

    def __repr__(self):
        return (f"<SpellMemory voc={self.vocation} lv={self.magic_level} "
                f"known={self.known_spells}>")
