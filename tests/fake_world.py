"""
fake_world.py
Un mundo mínimo sin pygame para usar en tests de pathfinding,
monstruos y spawner.
"""

from constants import TILE_GRASS, TILE_WATER, IMPASSABLE_TILES


class FakeWorld:
    """
    Mapa de tiles configurable sin pygame.
    impassable: conjunto de (col, row) que no se pueden pisar.
    """

    def __init__(self, width=30, height=30, tile_size=32, impassable=None):
        self.width      = width
        self.height     = height
        self.tile_size  = tile_size
        self._impassable = set(impassable) if impassable else set()

        # Construir grid de tiles (todo TILE_GRASS salvo los impassable)
        self.tiles    = [[TILE_GRASS] * height for _ in range(width)]
        self.variants = [[0]          * height for _ in range(width)]
        for col, row in self._impassable:
            if 0 <= col < width and 0 <= row < height:
                self.tiles[col][row] = TILE_WATER   # impassable

    # ── API que usa el juego ──────────────────────────────────────────────────

    def is_walkable(self, col, row):
        if col < 0 or col >= self.width or row < 0 or row >= self.height:
            return False
        return self.tiles[col][row] not in IMPASSABLE_TILES

    def is_rect_walkable(self, left, top, right, bottom):
        ts = self.tile_size
        corners = [
            (left,    top),
            (right-1, top),
            (left,    bottom-1),
            (right-1, bottom-1),
        ]
        for px, py in corners:
            if not self.is_walkable(int(px // ts), int(py // ts)):
                return False
        return True

    def get_minimap(self):
        from tests.mock_pygame import FakeSurface
        return FakeSurface(), 120
