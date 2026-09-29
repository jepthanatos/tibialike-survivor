"""
core/camera.py
Cámara con interpolación suave (lerp exponencial).

El jugador se mueve tile a tile (saltos de 32px),
pero la cámara se desliza suavemente hacia él cada frame.
Esto elimina el flickering visual sin cambiar la mecánica de movimiento.

LERP_SPEED  controla la rapidez del seguimiento:
  · 20+  → casi instantáneo
  · 12   → suave y responsivo (default)
  · <8   → cinematográfico, más lento
"""
import math

LERP_SPEED = 12.0


class Camera:
    def __init__(self, view_w, view_h, world_w, world_h):
        self.view_w  = view_w
        self.view_h  = view_h
        self.world_w = world_w
        self.world_h = world_h
        self.offset_x = 0.0
        self.offset_y = 0.0
        self._target_x = 0.0
        self._target_y = 0.0
        self._initialised = False

    def update(self, cx, cy, dt: float = 0.016):
        """Mueve la cámara suavemente hacia (cx, cy)."""
        tx = cx - self.view_w / 2
        ty = cy - self.view_h / 2
        tx = max(0.0, min(tx, float(self.world_w - self.view_w)))
        ty = max(0.0, min(ty, float(self.world_h - self.view_h)))
        self._target_x = tx
        self._target_y = ty

        if not self._initialised:
            self.offset_x = tx
            self.offset_y = ty
            self._initialised = True
            return

        # Lerp exponencial: suave, sin overshooting
        factor = 1.0 - math.exp(-LERP_SPEED * dt) if dt > 0 else 0.0
        factor = min(1.0, max(0.0, factor))
        self.offset_x += (self._target_x - self.offset_x) * factor
        self.offset_y += (self._target_y - self.offset_y) * factor
        self.offset_x = max(0.0, min(self.offset_x, float(self.world_w - self.view_w)))
        self.offset_y = max(0.0, min(self.offset_y, float(self.world_h - self.view_h)))

    def snap(self, cx, cy):
        """Teleporta la cámara instantáneamente. Para transiciones de mazmorra."""
        tx = cx - self.view_w / 2
        ty = cy - self.view_h / 2
        self.offset_x = max(0.0, min(tx, float(self.world_w - self.view_w)))
        self.offset_y = max(0.0, min(ty, float(self.world_h - self.view_h)))
        self._target_x = self.offset_x
        self._target_y = self.offset_y
        self._initialised = True

    def world_to_screen(self, wx, wy):
        return wx - self.offset_x, wy - self.offset_y

    def screen_to_world(self, sx, sy):
        return sx + self.offset_x, sy + self.offset_y

    def is_visible(self, wx, wy, margin=64):
        sx, sy = self.world_to_screen(wx, wy)
        return (-margin <= sx <= self.view_w + margin and
                -margin <= sy <= self.view_h + margin)
