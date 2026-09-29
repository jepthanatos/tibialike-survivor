import json
import os
import random

SAVE_FILE = "save.json"

class Session:
    def __init__(self):
        self.persistent_level  = 0
        self.best_time         = 0.0
        self.total_runs        = 0
        self.max_storm_phase   = 0
        self.spell_memory_data = {}
        self.last_seed         = None
        self.vocation          = "sorcerer"
        self.skills_data       = {}
        self.equipment_data    = {}   # persists equipped items
        self._load()

    def _load(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE) as f:
                    d = json.load(f)
                self.persistent_level  = d.get("persistent_level", 0)
                self.best_time         = d.get("best_time", 0.0)
                self.total_runs        = d.get("total_runs", 0)
                self.max_storm_phase   = d.get("max_storm_phase", 0)
                self.spell_memory_data = d.get("spell_memory", {})
                self.last_seed         = d.get("last_seed", None)
                self.vocation          = d.get("vocation", "sorcerer")
                self.skills_data       = d.get("skills", {})
                self.equipment_data    = d.get("equipment", {})
            except Exception:
                pass

    def new_seed(self) -> int:
        """Generate and return a fresh random seed for a new run."""
        seed = random.randint(0, 2**31 - 1)
        self.last_seed = seed
        return seed

    def save(self, level, elapsed, storm_phase=0, spell_memory=None, seed=None, skills=None, inventory=None):
        self.total_runs += 1
        if level > self.persistent_level:
            self.persistent_level = level
        if elapsed > self.best_time:
            self.best_time = elapsed
        if storm_phase > self.max_storm_phase:
            self.max_storm_phase = storm_phase
        if spell_memory is not None:
            self.spell_memory_data = spell_memory.to_dict()
        if seed is not None:
            self.last_seed = seed
        if skills is not None:
            self.skills_data = skills.to_dict()
        if inventory is not None:
            # Persist equipped items (excluding consumables)
            self.equipment_data = {
                slot: item for slot, item in inventory.equipped.items()
                if item is not None and item.get("slot") != "consumable"
            }
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump({
                    "persistent_level": self.persistent_level,
                    "best_time":        round(self.best_time, 1),
                    "total_runs":       self.total_runs,
                    "max_storm_phase":  self.max_storm_phase,
                    "spell_memory":     self.spell_memory_data,
                    "last_seed":        self.last_seed,
                    "vocation":         self.vocation,
                    "skills":           self.skills_data,
                    "equipment":        self.equipment_data,
                }, f, indent=2)
        except Exception:
            pass
