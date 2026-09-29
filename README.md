# Tibia Survivor

Un juego de supervivencia roguelite inspirado en Tibia con zona de tormenta al estilo Fortnite. Sobrevive el mayor tiempo posible eliminando monstruos, aprendiendo hechizos, explorando mazmorras y escapando de la tormenta que se cierra.

---

## Requisitos

- Python 3.10 o superior
- pygame 2.1.0 o superior

```bash
pip install pygame
```

## Cómo jugar

```bash
cd tibia_survivor
python main.py
```

---

## Controles

### Movimiento y combate
| Tecla | Acción |
|---|---|
| `W A S D` | Mover al jugador |
| Click izquierdo | Ataque melee en arco hacia el cursor |
| Click derecho | Lanzar hechizo seleccionado |
| `F` | Recoger ítem del suelo |
| `E` | Entrar / salir de mazmorra (cerca del portal) |

### Hechizos
| Tecla | Acción |
|---|---|
| `1` – `7` | Seleccionar hechizo por número |
| `Q` | Ciclar al hechizo anterior |
| `E` | Ciclar al siguiente (fuera de portal) |

### Interfaz
| Tecla | Acción |
|---|---|
| `I` | Abrir / cerrar inventario |
| `TAB` | Stats en partida / ciclar páginas en Game Over |
| `←` `→` | Cambiar ranking (Game Over) |
| `↑` `↓` | Scroll historial (Game Over) |
| `R` | Reiniciar tras morir |
| `ESC` | Cerrar panel / volver al menú |

---

## Mecánicas

### Hechizos por observación

Los hechizos no se desbloquean subiendo de nivel: hay que **observar a los monstruos lanzarlos**. Cuando un monstruo hace windup (orbe de carga visible), si estás dentro del rango de observación (~380 px) se acumula un contador. Al alcanzar el umbral *y* tener el nivel mágico necesario, aprendes el hechizo. El nivel mágico sube cada 8 hechizos lanzados.

| Hechizo | Aprende de | Obs. | Nv. mágico | Nota |
|---|---|---|---|---|
| Spark | Rat | 3 | 0 | Básico rápido |
| Poison Bolt | Zombie | 4 | 2 | Daño extra |
| Decay Wave | Zombie | 5 | 3 | Pierce |
| Bone Shard | Skeleton | 4 | 4 | Muy veloz |
| Fireball | Skeleton | 6 | 6 | Explosión AOE |
| Energy Beam | Skeleton | 7 | 8 | Pierce + rápido |
| Death Coil | Skeleton alto nivel | 8 | 10 | Pierce + AOE |

### La Tormenta

Se cierra en 5 fases progresivas. El minimapa muestra el anillo actual y el siguiente. Una flecha señala la dirección al interior seguro. Las mazmorras son refugios: dentro no hay daño de tormenta.

### Biomas

El mapa se divide en regiones Voronoi con efectos distintos sobre el jugador:

| Bioma | Efecto | Monstruos favoritos |
|---|---|---|
| 🌿 Praderas | Sin penalización | Todos |
| ❄ Tundra | −18% velocidad | Skeleton, Orc |
| 🏜 Desierto | −0.8 HP/s calor | Orc, Dark Wizard |
| 🌿 Pantano | −22% vel + veneno | Zombie, Dark Wizard |
| 🌋 Volcánico | Lava −15 HP/s | Dragon, Dragon Lord |

### Mazmorras con niveles

Las mazmorras se generan proceduralmente al entrar (generador BSP). Contienen monstruos de mayor nivel, un jefe garantizado con modificadores de élite, drops mínimo `uncommon` y ningún daño de tormenta. Se accede a través de los portales ⬇ púrpura visibles en el mapa.

### Monstruos

| Nombre | Nivel mín. | Especial |
|---|---|---|
| Rat | 0 | Aprende Spark |
| Zombie | 3 | Aprende Poison Bolt, Decay Wave |
| Skeleton | 7 | Aprende hasta Death Coil |
| Orc | 10 | Tanque resistente |
| Dark Wizard | 15 | Usa veneno y ondas |
| Dragon | 20 | Fireball y Energy Beam |
| Demon | 25 | Death Coil y Fireball, muy resistente |
| Dragon Lord | 30 | El más poderoso, tres hechizos |

### Élites y Jefes

El 18% de los monstruos son élites con 1–2 modificadores (Berserker, Armored, Swift, Regenerating, Venomous, Giant). Los jefes de superficie aparecen cada 90–540 segundos; los jefes de mazmorra son siempre garantizados. Los jefes sueltan mínimo 2 ítems de rareza `rare`.

### Inventario

6 ranuras de equipo + bolsa de 20 ítems. Cuatro rarezas: `common`, `uncommon`, `rare`, `epic`. Stats que mejoran: daño, defensa, HP/MP, regen HP, velocidad de ataque, rango, XP bonus, bloqueo.

---

## Estadísticas

Pulsa `TAB` durante la partida para ver stats en tiempo real. Al morir, 4 páginas de resultados:

1. **Resumen** — partida completa + nuevos récords
2. **Rankings** — Top 10 en 9 categorías
3. **Totales de vida** — acumulados + récords absolutos + medias
4. **Historial** — todas las partidas ordenadas por fecha

---

## Persistencia

- `save.json` — nivel persistente, hechizos aprendidos, mejor tiempo, semilla
- `stats_history.json` — historial de hasta 100 partidas con métricas completas

Cada partida usa una semilla aleatoria única que garantiza mundos siempre distintos.

---

## Arquitectura

```
tibia_survivor/
├── main.py                    # Bucle principal + menú
├── constants.py               # Tiles, colores, dimensiones
├── core/
│   ├── camera.py              # Cámara
│   ├── dungeon_generator.py   # Generador BSP de mazmorras
│   ├── level_manager.py       # Pila de niveles superficie ↔ mazmorra
│   ├── session.py             # Persistencia JSON
│   └── world.py               # Mapa tile-based con biomas
├── entities/
│   ├── item_drop.py           # Objetos en el suelo
│   ├── monster.py             # 8 tipos + A* + hechizos + sprites
│   ├── player.py              # Jugador con hechizos, inventario, stats
│   ├── projectile.py          # Proyectiles con trail, pierce, AOE
│   └── spawner.py             # Spawn ponderado por bioma + élites
├── systems/
│   ├── biomes.py              # 5 biomas con efectos reales
│   ├── boss.py                # Jefes periódicos con barra HP
│   ├── dungeons.py            # Zonas de mazmorra en el mapa
│   ├── elites.py              # 6 modificadores de élite
│   ├── inventory.py           # 6 slots + bolsa 20 ítems
│   ├── lifetime_stats.py      # Historial persistente + 9 rankings
│   ├── loot.py                # 32 plantillas, 4 rarezas
│   ├── pathfinding.py         # A* con límite de nodos
│   ├── spells.py              # Catálogo + SpellMemory
│   ├── stats.py               # RunStats (18 métricas en tiempo real)
│   └── storm.py               # Tormenta 5 fases estilo Fortnite
└── ui/
    ├── biome_ui.py            # Tinte ambiental, partículas, banner
    ├── dungeon_renderer.py    # Renderizador de mazmorras con antorchas
    ├── hud.py                 # Barras HP/MP/XP, HUD completo
    ├── inventory_ui.py        # Panel de inventario con tooltips
    ├── main_menu.py           # Menú principal
    ├── monster_tooltip.py     # Tooltip al hacer hover sobre monstruos
    ├── spell_bar.py           # Barra lateral de hechizos
    ├── stats_ui.py            # StatsOverlay + GameOverStats 4 páginas
    └── storm_renderer.py      # Niebla, glow, flecha de dirección
```

## Tests

```bash
python run_tests.py
```

776 tests unitarios sin necesidad de pantalla ni pygame real (mock completo).
