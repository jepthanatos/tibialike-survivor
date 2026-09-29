"""
systems/loot.py
Ítems y drops al estilo Tibia clásico.

Cada criatura tiene su tabla de loot fiel al juego original.
Los ítems tienen nombres reales de Tibia (Fire Sword, Dragon Scale Mail, etc.)
"""
from __future__ import annotations
import random
from typing import Optional

# ── Rarezas ───────────────────────────────────────────────────────────────────
RARITY = {
    "common":   {"color": (180, 180, 180), "weight": 60},
    "uncommon": {"color": ( 55, 210,  80), "weight": 25},
    "rare":     {"color": ( 80, 135, 245), "weight": 12},
    "epic":     {"color": (210,  65, 245), "weight":  3},
}

RARITY_ORDER = ["common", "uncommon", "rare", "epic"]


def _rarity_by_level(level: int) -> str:
    weights = [60, 25, 12, 3]
    # Higher level → slightly better rarity
    bonus = min(level // 5, 4)
    w = [max(1, weights[0]-bonus*3), weights[1]+bonus, weights[2]+bonus, weights[3]+bonus//2]
    return random.choices(RARITY_ORDER, weights=w, k=1)[0]


# ── Catálogo de ítems Tibia ───────────────────────────────────────────────────
# slot: weapon | armor | helmet | boots | ring | amulet
# weapon_type: sword | axe | club | distance  (para skill gain)

ITEM_TEMPLATES = [
    # ── Weapons ──────────────────────────────────────────────────────────────
    # Swords
    {"name":"Sword",            "slot":"weapon","rarity":"common",  "weapon_type":"sword","stats":{"atk_damage":12}},
    {"name":"Sabre",            "slot":"weapon","rarity":"common",  "weapon_type":"sword","stats":{"atk_damage":14}},
    {"name":"Broadsword",       "slot":"weapon","rarity":"uncommon","weapon_type":"sword","stats":{"atk_damage":22}},
    {"name":"Long Sword",       "slot":"weapon","rarity":"uncommon","weapon_type":"sword","stats":{"atk_damage":26}},
    {"name":"Fire Sword",       "slot":"weapon","rarity":"rare",    "weapon_type":"sword","stats":{"atk_damage":35}},
    {"name":"Dragon Slayer",    "slot":"weapon","rarity":"epic",    "weapon_type":"sword","stats":{"atk_damage":55}},
    # Axes
    {"name":"Hand Axe",         "slot":"weapon","rarity":"common",  "weapon_type":"axe",  "stats":{"atk_damage":11}},
    {"name":"Battle Axe",       "slot":"weapon","rarity":"uncommon","weapon_type":"axe",  "stats":{"atk_damage":24}},
    {"name":"Heroic Axe",       "slot":"weapon","rarity":"rare",    "weapon_type":"axe",  "stats":{"atk_damage":38}},
    # Clubs
    {"name":"Club",             "slot":"weapon","rarity":"common",  "weapon_type":"club", "stats":{"atk_damage":10}},
    {"name":"Mace",             "slot":"weapon","rarity":"common",  "weapon_type":"club", "stats":{"atk_damage":14}},
    {"name":"War Hammer",       "slot":"weapon","rarity":"uncommon","weapon_type":"club", "stats":{"atk_damage":28}},
    # Distance
    {"name":"Bow",              "slot":"weapon","rarity":"common",  "weapon_type":"distance","stats":{"atk_damage":15, "atk_range":32}},
    {"name":"Crossbow",         "slot":"weapon","rarity":"uncommon","weapon_type":"distance","stats":{"atk_damage":22, "atk_range":48}},
    {"name":"Arbalest",         "slot":"weapon","rarity":"rare",    "weapon_type":"distance","stats":{"atk_damage":36, "atk_range":64}},
    # Staves (magic)
    {"name":"Wand of Decay",    "slot":"weapon","rarity":"common",  "weapon_type":"sword","stats":{"atk_damage": 8, "mp_bonus":10}},
    {"name":"Wand of Cosmic Energy","slot":"weapon","rarity":"uncommon","weapon_type":"sword","stats":{"atk_damage":14,"mp_bonus":20}},
    {"name":"Druid Staff",      "slot":"weapon","rarity":"rare",    "weapon_type":"sword","stats":{"atk_damage":18,"mp_bonus":40}},
    {"name":"Spellbook of Dark Mysteries","slot":"weapon","rarity":"epic","weapon_type":"sword","stats":{"atk_damage":25,"mp_bonus":80}},

    # ── Armors ────────────────────────────────────────────────────────────────
    {"name":"Leather Armor",    "slot":"armor", "rarity":"common",  "stats":{"defense": 5}},
    {"name":"Chain Armor",      "slot":"armor", "rarity":"common",  "stats":{"defense": 8}},
    {"name":"Plate Armor",      "slot":"armor", "rarity":"uncommon","stats":{"defense":14}},
    {"name":"Knight Armor",     "slot":"armor", "rarity":"rare",    "stats":{"defense":20, "max_hp":30}},
    {"name":"Dragon Scale Mail","slot":"armor", "rarity":"epic",    "stats":{"defense":28, "max_hp":60}},
    {"name":"Demon Armor",      "slot":"armor", "rarity":"epic",    "stats":{"defense":32, "max_hp":80}},

    # ── Helmets ───────────────────────────────────────────────────────────────
    {"name":"Leather Helmet",   "slot":"helmet","rarity":"common",  "stats":{"defense": 3}},
    {"name":"Chain Helmet",     "slot":"helmet","rarity":"common",  "stats":{"defense": 5}},
    {"name":"Iron Helmet",      "slot":"helmet","rarity":"uncommon","stats":{"defense": 9}},
    {"name":"Crown Helmet",     "slot":"helmet","rarity":"rare",    "stats":{"defense":14, "max_hp":20}},
    {"name":"Dragon Helmet",    "slot":"helmet","rarity":"epic",    "stats":{"defense":18, "max_hp":40}},

    # ── Boots ─────────────────────────────────────────────────────────────────
    {"name":"Leather Boots",    "slot":"boots", "rarity":"common",  "stats":{"defense": 2}},
    {"name":"Chain Boots",      "slot":"boots", "rarity":"common",  "stats":{"defense": 4}},
    {"name":"Plate Boots",      "slot":"boots", "rarity":"uncommon","stats":{"defense": 7}},
    {"name":"Boots of Haste",   "slot":"boots", "rarity":"rare",    "stats":{"atk_speed":0.20}},
    {"name":"Soft Boots",       "slot":"boots", "rarity":"epic",    "stats":{"atk_speed":0.30,"hp_regen":2.5}},

    # ── Rings ─────────────────────────────────────────────────────────────────
    {"name":"Dwarven Ring",     "slot":"ring",  "rarity":"common",  "stats":{"defense": 3}},
    {"name":"Ring of Healing",  "slot":"ring",  "rarity":"uncommon","stats":{"hp_regen":1.5}},
    {"name":"Might Ring",       "slot":"ring",  "rarity":"rare",    "stats":{"atk_damage":12}},
    {"name":"Ring of Stars",    "slot":"ring",  "rarity":"epic",    "stats":{"max_hp":50, "defense":8}},

    # ── Amulets ───────────────────────────────────────────────────────────────
    {"name":"Bronze Amulet",    "slot":"amulet","rarity":"common",  "stats":{"defense": 3}},
    {"name":"Silver Amulet",    "slot":"amulet","rarity":"uncommon","stats":{"defense": 5, "hp_regen":0.8}},
    {"name":"Platinum Amulet",  "slot":"amulet","rarity":"rare",    "stats":{"max_hp":40, "defense": 8}},
    {"name":"Demon Shield",     "slot":"amulet","rarity":"epic",    "stats":{"block_chance":0.15,"defense":12}},
]

# Index by slot for fast lookup
_BY_SLOT: dict[str, list[dict]] = {}
for _t in ITEM_TEMPLATES:
    _BY_SLOT.setdefault(_t["slot"], []).append(_t)

_ALL_SLOTS = ["weapon", "armor", "helmet", "boots", "ring", "amulet"]


# ── Loot tables per creature (Tibia faithful) ─────────────────────────────────

CREATURE_LOOT: dict[str, list[tuple[float, str]]] = {
    # (drop_chance 0-1, item_name)
    "rat": [
        (0.50, "Cheese"),
        (0.20, "Leather Boots"),
        (0.05, "Club"),
    ],
    "zombie": [
        (0.40, "Leather Helmet"),
        (0.30, "Leather Armor"),
        (0.15, "Chain Helmet"),
        (0.05, "Mace"),
        (0.02, "War Hammer"),
    ],
    "skeleton": [
        (0.40, "Chain Helmet"),
        (0.25, "Sword"),
        (0.20, "Mace"),
        (0.10, "Chain Armor"),
        (0.05, "Battle Axe"),
        (0.02, "Broadsword"),
    ],
    "orc": [
        (0.50, "Chain Armor"),
        (0.30, "Iron Helmet"),
        (0.20, "Battle Axe"),
        (0.10, "Plate Boots"),
        (0.05, "War Hammer"),
        (0.02, "Plate Armor"),
    ],
    "dark_wizard": [
        (0.40, "Wand of Decay"),
        (0.25, "Wand of Cosmic Energy"),
        (0.15, "Ring of Healing"),
        (0.10, "Silver Amulet"),
        (0.05, "Druid Staff"),
        (0.01, "Spellbook of Dark Mysteries"),
    ],
    "dragon": [
        (0.50, "Dragon Helmet"),
        (0.30, "Dragon Scale Mail"),
        (0.20, "Fire Sword"),
        (0.15, "Crown Helmet"),
        (0.10, "Ring of Stars"),
        (0.02, "Dragon Slayer"),
    ],
    "demon": [
        (0.40, "Demon Armor"),
        (0.30, "Demon Shield"),
        (0.20, "Dragon Slayer"),
        (0.10, "Ring of Stars"),
        (0.05, "Soft Boots"),
    ],
    "dragon_lord": [
        (0.60, "Dragon Scale Mail"),
        (0.40, "Dragon Slayer"),
        (0.30, "Demon Armor"),
        (0.20, "Soft Boots"),
        (0.10, "Ring of Stars"),
        (0.05, "Spellbook of Dark Mysteries"),
    ],
    "wolf":       [(0.40,"Leather Boots"),(0.20,"Club"),(0.05,"Chain Helmet")],
    "troll":      [(0.40,"Club"),(0.25,"Leather Armor"),(0.10,"Hand Axe"),(0.04,"Chain Armor")],
    "bear":       [(0.45,"Leather Armor"),(0.25,"Chain Helmet"),(0.10,"Mace"),(0.04,"Plate Boots")],
    "cyclops":    [(0.50,"War Hammer"),(0.30,"Plate Armor"),(0.15,"Iron Helmet"),(0.05,"Crown Helmet"),(0.02,"Heroic Axe")],
    "fire_devil": [(0.40,"Wand of Decay"),(0.25,"Silver Amulet"),(0.10,"Ring of Healing"),(0.05,"Wand of Cosmic Energy")],
    "vampire":    [(0.50,"Plate Armor"),(0.30,"Crown Helmet"),(0.15,"Ring of Healing"),(0.08,"Platinum Amulet"),(0.03,"Knight Armor")],
}

# Items that are consumables (no slot)
CONSUMABLES = {"Cheese"}


def _item_from_name(name: str, level: int) -> Optional[dict]:
    """Build an item dict from a Tibia item name."""
    if name in CONSUMABLES:
        return {"name": name, "slot": "consumable", "rarity": "common",
                "item_level": level, "stats": {"hp_bonus": 10}}
    # Search templates
    for t in ITEM_TEMPLATES:
        if t["name"] == name:
            item = dict(t)
            item["item_level"] = level
            # Scale stats slightly with level
            scaled = {}
            for stat, val in t["stats"].items():
                if isinstance(val, (int, float)) and val > 0:
                    scaled[stat] = round(val * (1 + level * 0.04), 2)
                else:
                    scaled[stat] = val
            item["stats"] = scaled
            return item
    return None


def try_drop(monster) -> Optional[dict]:
    """Standard drop for a monster (uses creature loot table)."""
    mtype = getattr(monster, "mtype", "rat")
    level = getattr(monster, "level", 0)
    table = CREATURE_LOOT.get(mtype, [])
    drops = []
    for chance, item_name in table:
        if random.random() < chance:
            item = _item_from_name(item_name, level)
            if item:
                drops.append(item)
    return drops[0] if drops else None


def try_drop_with_mult(monster, multiplier: float = 1.0) -> Optional[dict]:
    """Like try_drop but scales chances by multiplier."""
    if getattr(monster, "is_boss", False):
        return generate_item(getattr(monster, "level", 0))
    mtype = getattr(monster, "mtype", "rat")
    level = getattr(monster, "level", 0)
    table = CREATURE_LOOT.get(mtype, [])
    drops = []
    for chance, item_name in table:
        if random.random() < min(0.95, chance * multiplier):
            item = _item_from_name(item_name, level)
            if item:
                drops.append(item)
    if not drops and random.random() < 0.12 * multiplier:
        return generate_item(level)
    return drops[0] if drops else None


def generate_item(level: int, rarity: str = None, slot: str = None) -> dict:
    """Generate a random item of given level and optional rarity."""
    if rarity is None:
        rarity = _rarity_by_level(level)
    if slot is None:
        slot = random.choice(_ALL_SLOTS)
    candidates = [t for t in _BY_SLOT.get(slot, []) if t["rarity"] == rarity]
    if not candidates:
        candidates = _BY_SLOT.get(slot, ITEM_TEMPLATES)
    template = random.choice(candidates)
    item = dict(template)
    item["item_level"] = level
    scaled = {}
    for stat, val in template["stats"].items():
        if isinstance(val, (int, float)) and val > 0:
            scaled[stat] = round(val * (1 + level * 0.04), 2)
        else:
            scaled[stat] = val
    item["stats"] = scaled
    return item


def generate_guaranteed(item_level: int, min_rarity: str = "uncommon") -> dict:
    """Generate an item with at least min_rarity quality."""
    min_idx = RARITY_ORDER.index(min_rarity) if min_rarity in RARITY_ORDER else 0
    for _ in range(20):
        item = generate_item(item_level)
        if RARITY_ORDER.index(item["rarity"]) >= min_idx:
            return item
    return generate_item(item_level, rarity=min_rarity)

RARITY_ORDER = ["common", "uncommon", "rare", "epic"]
