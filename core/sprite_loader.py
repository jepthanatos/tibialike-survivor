"""
core/sprite_loader.py
═══════════════════════════════════════════════════════════════
Carga y cachea los sprites definidos en sprites.json.

Uso
───
    from core.sprite_loader import sprites

    img = sprites.get("monsters", "rat")   # Surface o None
    if img:
        screen.blit(img, (sx - img.get_width()//2, sy - img.get_height()//2))
    else:
        # dibujar sprite procedural

El módulo es un singleton: la primera importación carga el JSON
y pre-valida todos los paths. Las imágenes individuales se cargan
en la primera llamada a get() y se mantienen en caché.
"""
from __future__ import annotations
import json
import os
import pygame

# Ruta del JSON relativa a este fichero
_CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'sprites.json')
_SPRITES_DIR = os.path.dirname(_CONFIG_FILE)   # directorio raíz del juego


class SpriteLoader:
    """Singleton que gestiona la carga de sprites desde sprites.json."""

    def __init__(self, config_path: str = _CONFIG_FILE):
        self._config:  dict[str, dict[str, str | None]] = {}
        self._cache:   dict[tuple, pygame.Surface]      = {}
        self._missing: set                              = set()
        self._loaded   = False
        self._config_path = config_path

    # ── Carga ─────────────────────────────────────────────────────────────────

    def load(self):
        """Lee sprites.json. Llamado automáticamente en el primer get()."""
        if self._loaded:
            return
        self._loaded = True
        try:
            with open(self._config_path, encoding='utf-8') as f:
                raw = json.load(f)
            # Eliminar la clave de documentación
            for key, value in raw.items():
                if key.startswith('_'):
                    continue
                if isinstance(value, dict):
                    self._config[key] = value
        except FileNotFoundError:
            pass   # sin fichero → todo procedral
        except (json.JSONDecodeError, Exception) as e:
            print(f"[SpriteLoader] Warning: could not parse sprites.json: {e}")

    def reload(self):
        """Recarga el JSON y limpia la caché (útil para edición en caliente)."""
        self._config.clear()
        self._cache.clear()
        self._missing.clear()
        self._loaded = False
        self.load()

    # ── Consulta ──────────────────────────────────────────────────────────────

    def get(self, section: str, key: str,
            width: int = 0, height: int = 0) -> pygame.Surface | None:
        """
        Devuelve la Surface para (section, key), escalada a (width, height)
        si se especifica. Devuelve None si no hay imagen configurada o
        si el fichero no existe.

        section  — categoría: "monsters", "player", "bots", "tiles", "ui"
        key      — nombre dentro de la categoría: "rat", "outfit_0", etc.
        width    — ancho deseado en px (0 = tamaño original)
        height   — alto deseado en px (0 = tamaño original)
        """
        if not self._loaded:
            self.load()

        cache_key = (section, key, width, height)
        if cache_key in self._cache:
            return self._cache[cache_key]
        if cache_key in self._missing:
            return None

        # Buscar path en config
        path = self._config.get(section, {}).get(key)
        if path is None:
            self._missing.add(cache_key)
            return None

        # Resolver path relativo al directorio del juego
        if not os.path.isabs(path):
            path = os.path.join(_SPRITES_DIR, path)

        if not os.path.exists(path):
            self._missing.add(cache_key)
            return None

        try:
            surf = pygame.image.load(path).convert_alpha()
            if width > 0 and height > 0:
                surf = pygame.transform.scale(surf, (width, height))
            self._cache[cache_key] = surf
            return surf
        except Exception as e:
            print(f"[SpriteLoader] Warning: could not load '{path}': {e}")
            self._missing.add(cache_key)
            return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def has(self, section: str, key: str) -> bool:
        """True si hay una ruta no-null configurada para (section, key)."""
        if not self._loaded:
            self.load()
        return bool(self._config.get(section, {}).get(key))

    def configured_sections(self) -> list[str]:
        if not self._loaded:
            self.load()
        return list(self._config.keys())

    def summary(self) -> str:
        """Resumen legible del estado del loader."""
        if not self._loaded:
            self.load()
        lines = ["SpriteLoader status:"]
        for section, keys in self._config.items():
            active = [(k, v) for k, v in keys.items() if v is not None]
            if active:
                lines.append(f"  {section}:")
                for k, v in active:
                    loaded = any(ck[0]==section and ck[1]==k for ck in self._cache)
                    missing = any(mk[0]==section and mk[1]==k for mk in self._missing)
                    status = "✓ cargado" if loaded else ("✗ no encontrado" if missing else "pendiente")
                    lines.append(f"    {k}: {v}  [{status}]")
        if len(lines) == 1:
            lines.append("  (sin sprites configurados — usando todos procedurales)")
        return "\n".join(lines)


# ── Singleton global ──────────────────────────────────────────────────────────
sprites = SpriteLoader()
