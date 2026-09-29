"""
systems/elites.py
Sistema de modificadores de élite para monstruos.

Un 18 % de los monstruos spawneados puede ser élite con uno o dos modificadores.
Los jefes siempre tienen modificadores múltiples.
"""
from __future__ import annotations
import random

# ── Definición de modificadores ───────────────────────────────────────────────
# (id, nombre, color_badge, hp_mult, dmg_mult, speed_mult, xp_mult, regen_ps, description)

MODIFIERS: dict[str, dict] = {
    "berserker": {
        "name":      "Berserker",
        "color":     (220, 60, 40),
        "hp_mult":   1.25,
        "dmg_mult":  1.60,
        "spd_mult":  1.30,
        "xp_mult":   1.80,
        "regen_ps":  0.0,
        "desc":      "Ataque y velocidad elevados.",
    },
    "armored": {
        "name":      "Armored",
        "color":     (140, 160, 200),
        "hp_mult":   2.20,
        "dmg_mult":  1.10,
        "spd_mult":  0.80,
        "xp_mult":   2.00,
        "regen_ps":  0.0,
        "desc":      "HP muy alto, algo más lento.",
    },
    "swift": {
        "name":      "Swift",
        "color":     (80, 220, 180),
        "hp_mult":   0.90,
        "dmg_mult":  1.20,
        "spd_mult":  1.80,
        "xp_mult":   1.60,
        "regen_ps":  0.0,
        "desc":      "Extremadamente rápido.",
    },
    "regenerating": {
        "name":      "Regenerating",
        "color":     (80, 200, 80),
        "hp_mult":   1.50,
        "dmg_mult":  1.10,
        "spd_mult":  1.00,
        "xp_mult":   1.70,
        "regen_ps":  12.0,   # HP por segundo
        "desc":      "Se regenera constantemente.",
    },
    "venomous": {
        "name":      "Venomous",
        "color":     (130, 210, 50),
        "hp_mult":   1.10,
        "dmg_mult":  1.40,
        "spd_mult":  1.10,
        "xp_mult":   1.65,
        "regen_ps":  0.0,
        "desc":      "Daño aumentado con veneno.",
    },
    "giant": {
        "name":      "Giant",
        "color":     (200, 150, 80),
        "hp_mult":   3.00,
        "dmg_mult":  1.50,
        "spd_mult":  0.70,
        "xp_mult":   2.50,
        "regen_ps":  5.0,
        "desc":      "Enorme, muy resistente.",
    },
}

MODIFIER_KEYS = list(MODIFIERS.keys())

# Probabilidad de spawn élite (por monstruo normal)
ELITE_CHANCE = 0.18
# Máximo de modificadores en un élite normal
MAX_ELITE_MODS = 2


def roll_elite() -> list[str]:
    """
    Tira los dados para élite.
    Devuelve lista de modifier_ids (vacía si no es élite).
    """
    if random.random() > ELITE_CHANCE:
        return []
    count = 1 if random.random() < 0.75 else 2
    return random.sample(MODIFIER_KEYS, min(count, len(MODIFIER_KEYS)))


def roll_boss_mods() -> list[str]:
    """Los jefes siempre tienen 2-3 modificadores."""
    count = random.randint(2, min(3, len(MODIFIER_KEYS)))
    return random.sample(MODIFIER_KEYS, count)


def apply_modifiers(monster, mod_ids: list[str]):
    """
    Aplica modificadores a un monstruo in-place.
    Guarda la lista en monster.elite_mods y ajusta sus stats.
    """
    monster.elite_mods = list(mod_ids)
    if not mod_ids:
        monster.is_elite = False
        return

    monster.is_elite = True

    hp_m = dmg_m = spd_m = xp_m = 1.0
    regen_total = 0.0

    for mid in mod_ids:
        d = MODIFIERS[mid]
        hp_m   *= d["hp_mult"]
        dmg_m  *= d["dmg_mult"]
        spd_m  *= d["spd_mult"]
        xp_m   *= d["xp_mult"]
        regen_total += d["regen_ps"]

    monster.max_hp     = max(1, int(monster.max_hp  * hp_m))
    monster.hp         = float(monster.max_hp)
    monster.damage     = max(1, int(monster.damage  * dmg_m))
    monster.speed      = monster.speed * spd_m
    monster.xp_reward  = max(1, int(monster.xp_reward * xp_m))
    monster.elite_regen = regen_total

    # Visually larger SIZE for giant/armored elites
    if "giant" in mod_ids:
        monster.SIZE = int(monster.SIZE * 1.55)
    elif "armored" in mod_ids:
        monster.SIZE = int(monster.SIZE * 1.20)


def elite_badge_color(mod_ids: list[str]) -> tuple:
    """Returns the most prominent badge colour from the modifiers."""
    if not mod_ids:
        return (180, 180, 180)
    return MODIFIERS[mod_ids[0]]["color"]
