"""
systems/storm.py
Zona segura que encoge en fases al estilo Battle Royale.

Ciclo de cada fase:
  WAITING  → cuenta atrás visible, el círculo se queda fijo
  CLOSING  → el radio interpola linealmente hasta el objetivo
  (repetir con la siguiente fase)
  DONE     → radio mínimo alcanzado, daño máximo permanente
"""
import math
import random

# ── Datos de fase ─────────────────────────────────────────────────────────────
# (nombre, espera_s, cierre_s, fracción_objetivo, dps_fuera)
PHASE_DATA = [
    #  name          wait_s  close_s  radius_frac  dps
    ("Fase I",       780,    240,    0.80,          2),
    ("Fase II",      600,    180,    0.62,          5),
    ("Fase III",     480,    150,    0.44,         10),
    ("Fase IV",      360,    120,    0.28,         22),
    ("Fase V",       240,     90,    0.14,         42),
    ("Fase VI",      120,     60,    0.05,         80),
]

STATE_WAITING = "WAITING"
STATE_CLOSING = "CLOSING"
STATE_DONE    = "DONE"

# Cuánto avisa antes de que empiece a cerrarse (segundos)
CLOSE_WARNING_AT = 15.0

# La tormenta acumula daño fraccional para no depender de iframes del jugador
_DMG_TICK = 0.5   # aplica daño cada 0.5 s (con DPS calculado)


class Storm:
    def __init__(self, map_w_px: float, map_h_px: float):
        self.map_w = map_w_px
        self.map_h = map_h_px

        # Centro inicial: centro exacto del mapa
        self.center_x = map_w_px / 2.0
        self.center_y = map_h_px / 2.0

        # Radio inicial: 88 % del radio del mapa (deja algo de tormenta desde el principio)
        self._base_radius = min(map_w_px, map_h_px) / 2.0
        self.radius       = self._base_radius * 0.88

        self._phase_idx   = 0
        self._state       = STATE_WAITING
        self._timer       = float(PHASE_DATA[0][1])   # wait_s

        # Para CLOSING: lerp entre estos dos valores
        self._radius_start  = self.radius
        self._radius_target = self.radius
        self._close_total   = 1.0   # duración total del cierre

        # Para daño continuo (independiente de iframes)
        self._dmg_accum = 0.0

        # Señal de advertencia enviada este ciclo
        self._warned_close = False

        self.phase_reached = 0   # máxima fase alcanzada (para estadísticas)

    # ── Propiedades públicas ──────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state

    @property
    def phase_name(self) -> str:
        if self._state == STATE_DONE:
            return "COLAPSO"
        return PHASE_DATA[min(self._phase_idx, len(PHASE_DATA) - 1)][0]

    @property
    def phase_number(self) -> int:
        return self._phase_idx + 1

    @property
    def current_dps(self) -> float:
        if self._state == STATE_DONE:
            return 100.0
        return float(PHASE_DATA[self._phase_idx][4])

    @property
    def timer(self) -> float:
        """Segundos restantes en el estado actual."""
        return max(0.0, self._timer)

    @property
    def closing_progress(self) -> float:
        """0..1 avance del cierre actual (solo durante CLOSING)."""
        if self._state != STATE_CLOSING or self._close_total <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - self._timer / self._close_total))

    @property
    def next_radius(self) -> float:
        """Radio objetivo de la siguiente fase (para mostrar el anillo de aviso)."""
        if self._state == STATE_DONE:
            return self.radius
        if self._state == STATE_CLOSING:
            return self._radius_target
        # WAITING → calcula cuál será el target cuando cierre
        if self._phase_idx < len(PHASE_DATA):
            frac = PHASE_DATA[self._phase_idx][3]
            return self._base_radius * frac
        return self.radius

    @property
    def close_warning(self) -> bool:
        """True cuando está esperando y quedan ≤ CLOSE_WARNING_AT segundos."""
        return (self._state == STATE_WAITING and
                not self._warned_close and
                self._timer <= CLOSE_WARNING_AT)

    # ── Lógica principal ──────────────────────────────────────────────────────

    def update(self, dt: float, player_x: float, player_y: float) -> float:
        """
        Actualiza la tormenta y aplica daño continuo si el jugador está fuera.
        Devuelve el daño que debe aplicarse al jugador este frame (float).
        No usa iframes: el daño es continuo y acumulado.
        """
        if self._state == STATE_DONE:
            return self._storm_damage(dt, player_x, player_y)

        self._timer -= dt

        if self._state == STATE_WAITING:
            if self._timer <= 0:
                self._start_closing()
            elif self.close_warning:
                self._warned_close = True   # la señal se emite una vez por fase

        elif self._state == STATE_CLOSING:
            # Interpolar radius → target
            t = 1.0 - max(0.0, self._timer) / self._close_total
            self.radius = self._radius_start + (self._radius_target - self._radius_start) * t

            if self._timer <= 0:
                self.radius = self._radius_target
                self._advance_phase()

        return self._storm_damage(dt, player_x, player_y)

    def player_inside(self, px: float, py: float) -> bool:
        dx = px - self.center_x
        dy = py - self.center_y
        return math.hypot(dx, dy) <= self.radius

    def distance_outside(self, px: float, py: float) -> float:
        """Distancia en píxeles fuera del radio seguro (0 si está dentro)."""
        return max(0.0, math.hypot(px - self.center_x, py - self.center_y) - self.radius)

    # ── Helpers internos ──────────────────────────────────────────────────────

    def _storm_damage(self, dt: float, px: float, py: float) -> float:
        if self.player_inside(px, py):
            self._dmg_accum = 0.0
            return 0.0
        self._dmg_accum += self.current_dps * dt
        if self._dmg_accum >= _DMG_TICK * self.current_dps:
            dmg            = self._dmg_accum
            self._dmg_accum = 0.0
            return dmg
        return 0.0

    def _start_closing(self):
        pd = PHASE_DATA[self._phase_idx]
        self._radius_start  = self.radius
        self._radius_target = self._base_radius * pd[3]
        self._close_total   = float(pd[2])
        self._timer         = self._close_total
        self._state         = STATE_CLOSING
        self.phase_reached  = max(self.phase_reached, self._phase_idx + 1)

        # El centro puede desplazarse ligeramente cada dos fases
        if self._phase_idx % 2 == 1:
            drift = self._radius_target * 0.18
            self.center_x = max(self._radius_target,
                                min(self.map_w - self._radius_target,
                                    self.center_x + random.uniform(-drift, drift)))
            self.center_y = max(self._radius_target,
                                min(self.map_h - self._radius_target,
                                    self.center_y + random.uniform(-drift, drift)))

    def _advance_phase(self):
        self._phase_idx += 1
        if self._phase_idx >= len(PHASE_DATA):
            self._state = STATE_DONE
            self.radius = self._radius_target
        else:
            pd             = PHASE_DATA[self._phase_idx]
            self._timer    = float(pd[1])
            self._state    = STATE_WAITING
            self._warned_close = False

    # ── Representación ────────────────────────────────────────────────────────

    def __repr__(self):
        return (f"<Storm state={self._state} phase={self._phase_idx} "
                f"r={self.radius:.0f} timer={self._timer:.1f}>")
