"""
systems/inventory.py
Gestión de inventario: bolsa y ranuras de equipamiento.
"""
SLOTS = ['weapon','armor','helmet','boots','ring','amulet']

MAX_BAG_SIZE = 20


class Inventory:
    def __init__(self):
        self.equipped: dict[str, dict | None] = {slot: None for slot in SLOTS}
        self.bag: list[dict] = []

    # ── Operaciones ───────────────────────────────────────────────────────────

    def pick_up(self, item: dict) -> bool:
        """Añade el item a la bolsa. Devuelve True si cabe."""
        if len(self.bag) >= MAX_BAG_SIZE:
            return False
        self.bag.append(item)
        return True

    def equip(self, item: dict) -> tuple[bool, dict | None]:
        """
        Equipa un item que ya está en la bolsa.
        - Si la ranura estaba ocupada, el item anterior va a la bolsa.
        - Si la bolsa está llena y habría que devolver el anterior, falla.
        Devuelve (éxito, item_desequipado_o_None).
        """
        slot = item['slot']
        old  = self.equipped[slot]

        if old is not None and len(self.bag) >= MAX_BAG_SIZE:
            return False, None  # bolsa llena, no cabe el desplazado

        self.equipped[slot] = item
        if item in self.bag:
            self.bag.remove(item)

        if old is not None:
            self.bag.append(old)

        return True, old

    def unequip(self, slot: str) -> bool:
        """Desequipa la ranura y manda el item a la bolsa. Falla si bolsa llena."""
        item = self.equipped.get(slot)
        if item is None:
            return False
        if len(self.bag) >= MAX_BAG_SIZE:
            return False
        self.equipped[slot] = None
        self.bag.append(item)
        return True

    def drop_from_bag(self, index: int) -> dict | None:
        """Elimina y devuelve el item de la bolsa en la posición dada."""
        if 0 <= index < len(self.bag):
            return self.bag.pop(index)
        return None

    # ── Consultas de stats ────────────────────────────────────────────────────

    def stat(self, name: str) -> float:
        """Suma de un stat específico de todos los equipos activos."""
        total = 0.0
        for item in self.equipped.values():
            if item:
                total += item['stats'].get(name, 0)
        return total

    @property
    def all_stats(self) -> dict:
        """Dict acumulado de todos los stats de los equipos activos."""
        result: dict = {}
        for item in self.equipped.values():
            if item:
                for k, v in item['stats'].items():
                    result[k] = result.get(k, 0) + v
        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def bag_full(self) -> bool:
        return len(self.bag) >= MAX_BAG_SIZE

    def equipped_count(self) -> int:
        return sum(1 for v in self.equipped.values() if v is not None)

    def __repr__(self):
        eq = {s: (v['name'] if v else '—') for s, v in self.equipped.items()}
        return f"<Inventory equipped={eq} bag={len(self.bag)}/{MAX_BAG_SIZE}>"
