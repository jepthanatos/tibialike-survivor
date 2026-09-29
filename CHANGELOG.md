# Changelog

---

## [Actualización 24] - Crash al elegir clase corregido

### Bug CORREGIDO: Crash al elegir vocación
**Causa raíz**: `living_bots` se inicializaba como lista vacía `[]` pero **nunca se
poblaba con los bots reales** hasta el primer ciclo del bucle de juego. Si algún
sistema accedía a `living_bots` en el primer frame (minimap, proyectiles, ranking)
podía causar comportamiento inesperado o crash.

**Fix**: inmediatamente después de `_new_game()`, `living_bots` se inicializa con
`list(bots)` (los 99 bots recién creados). También:
- `go_stats.set_bots(bots)` se llama al inicio (ranking panel tiene bots desde el frame 0)
- `world.reveal_around(player.x, player.y)` se llama al inicio (spawn visible inmediatamente)
- `camera.snap()` se llama en `_new_game` — confirmado correcto

**Mismo fix en los bloques de reinicio** (tecla R y menú):
- `world.reveal_around(player.x, player.y)` añadido tras `camera.snap()`


## [Actualización 23] - HP bar Tibia, fog of war, interfaz mejorada

### Barra de vida estilo Tibia en monstruos
La barra de HP de los monstruos ahora imita el estilo clásico de Tibia:
- Solo aparece cuando el monstruo ha recibido daño (HP < max HP)
- Borde negro de 1px (efecto hundido/sunken)
- Color cambia según HP restante: **verde** (>60%), **amarillo** (30-60%), **rojo** (<30%)
- Los **bosses** tienen barra morada
- Franja de highlight en la parte superior (efecto brillante Tibia)
- Sin texto de nombre ni nivel en el hover — Tibia no lo muestra por defecto

### Sin tooltip en mouse-over
Eliminadas las llamadas a `tooltip.update()` y `tooltip.draw()` del game loop principal.
Los monstruos no muestran información al pasar el ratón — comportamiento Tibia auténtico.

### Fog of War — mapa oscuro hasta ser explorado
`World._explored[row][col]` — grid booleano que registra qué tiles ha visitado el jugador.
- Inicialmente todo es negro (`_explored = False` en todos los tiles)
- `world.reveal_around(px, py)` descubre un círculo de radio 9 tiles alrededor del jugador
- Se llama cada frame en el game loop, creando el efecto de exploración progresiva
- Las tiles no exploradas se dibujan con un overlay negro sólido (encima del tile de suelo)
- Los monstruos siguen siendo visibles aunque estén en zona no explorada (como Tibia)

### HUD estilo Tibia
- **Fondo**: marrón oscuro (`rgb(40,28,12)`) como el panel de madera de Tibia
- **Borde superior**: línea dorada (`rgb(100,70,20)`) + sombra oscura
- **Barras HP/MP**: borde negro, fondo oscuro, fill con highlight dorado en el borde
- Las barras HP/MP usan el mismo estilo hundido que el cliente oficial de Tibia


## [Actualización 22] - Bugfixes: pantalla de vocación + reinicio con R

### Bug 1 CORREGIDO: Pantalla de selección de vocación no aparecía
**Causa raíz**: el ENTER/SPACE que confirmaba el menú principal filtraba como
primer KEYDOWN en `VocationSelect.run()`, cerrándola inmediatamente.

**Fix**: `pygame.event.clear()` + `pygame.time.wait(80)` antes de cada llamada
a `voc_screen.run()`. Aplicado en los 3 flujos:
1. Primera partida (menú principal → nueva partida)
2. Reinicio con R (tras morir)
3. Nueva partida desde pausa

### Bug 2 CORREGIDO: Error al pulsar R para reiniciar tras morir
**Causa raíz**: al reiniciar, variables de estado de la partida anterior
quedaban sin resetear (`spectator_target`, `_portal_timer`, `living_bots`,
`_bot_respawn_queue`, `go_stats`), causando referencias a objetos invalidados.

**Fix**: el bloque R-restart ahora resetea explícitamente:
- `living_bots.clear()` + `_bot_respawn_queue.clear()`
- `spectator_target = None`
- `_portal_timer = 3.0`
- `go_stats.set_bots(bots)` con los nuevos bots
- `camera.snap(player.x, player.y)` para posicionar la cámara al spawn
- `session.equipment_data = {}` para nueva run limpia

El mismo fix completo se aplicó al reinicio desde el menú de pausa.


## [Actualización 21] - Sistema de aprendizaje para bots y monstruos

### Bots aprenden durante la partida

**Memoria de combate:**
- `_dmg_dealt` / `_dmg_received` — ratio que define si van ganando o perdiendo
- `_fear_level` — aumenta al recibir daño (proporcional a % HP perdido); decae con el tiempo
- `_aggression` — sube con kills (máx 1.0), baja al recibir daño

**Escalado de intel por kills:**
| Tier actual | Kills necesarios para ascender |
|---|---|
| Novato | 3 kills |
| Aprendiz | 5 kills |
| Veterano | 8 kills |
| Experto | 12 kills |

Al ascender: notificación `"¡Aldeano evoluciona a Veterano!"`. Los parámetros de combate se
actualizan al nuevo tier (más rango de caza, mejor regen, más agresividad).

**Memoria del jugador:**
- `learn_player_spell()`: al ver al jugador lanzar un hechizo, el bot sube su distancia segura
- `try_dodge()`: Expertos/Maestros con kills tienen 40%/s de esquivar basándose en el ángulo
  del último ataque del jugador

**Parámetros dinámicos:**
- Flee threshold = base_intel + fear_level × 0.3 (más miedo → huye antes)
- Aggro range = base × (0.5 + aggression) (más agresivo → detecta más lejos)

### Monstruos aprenden durante la partida

**Modo de esquive lateral (`_lateral_mode`):**
Tras recibir **3 golpes consecutivos** del jugador, el monstruo activa el movimiento lateral
(arco giratorio) durante 2.5-4 segundos en lugar de ir en línea recta al jugador. Resetea
si el monstruo consigue golpear al jugador.

**Distancia preferida aprendida (`_preferred_range`):**
Si un monstruo con hechizos recibe **2+ golpes cuerpo a cuerpo**, aprende que el jugador
lo alcanza y ajusta su `preferred_range` a `SPELL_RANGE × 0.85` — más lejos del jugador.
Los dragones y dark wizards aprenden esto rápido.

**Por tier:**
- Tier 0 (Simple): solo activación lateral — más predecibles
- Tier 1 (Normal): lateral + preferred_range para spellcasters
- Tier 2 (Táctico): lateral + preferred_range + flee al 28% HP


## [Actualización 20] - Inteligencia artificial mejorada: bots y monstruos

### Bots: 5 niveles de inteligencia
Cada bot recibe un tier asignado deterministicamente por su índice y nivel:

| Tier | Nombre | % | Comportamiento |
|---|---|---|---|
| 0 | **Novato** | 24% | Solo vaga, huye de tormenta. Nunca ataca. |
| 1 | **Aprendiz** | 30% | Caza monstruos fáciles, evita al jugador. |
| 2 | **Veterano** | 25% | Ataca jugador si tiene ventaja de nivel o jugador < 40% HP. |
| 3 | **Experto** | 15% | Agresivo, flanquea levemente, kiting básico cuando en desventaja. Persigue hasta 8s. |
| 4 | **Maestro** | 5% | Persecución extendida, gestión de HP, kiting, ataques más consistentes. |

El nombre del bot refleja su tier: Novatos son "Aldeano", "Granjero"; Maestros son "Gran Maestre", "Inmortal", etc.

### Monstruos: 3 niveles de inteligencia
| Tier | Monstruos | Comportamiento |
|---|---|---|
| 0 **Simple** | Rat, Zombie, Skeleton, Wolf, Bear, Troll | Línea recta al jugador, aggro reducido. |
| 1 **Normal** | Orc, Cyclops, Dark Wizard, Fire Devil, Vampire | Pathfinding + mantiene distancia para hechizos. |
| 2 **Táctico** | Dragon, Demon, Dragon Lord | Huye cuando HP < 28%, mantiene distancia óptima de hechizo. |

### HUD: estado del bot visible
Los bots muestran sobre su cabeza:
- Nombre (con tier) + nivel
- Barra de HP cuando están dañados
- Ícono de estado (⚔ atacando, 💊 retirándose, ↺ kiting, 💨 huyendo)


## [Actualización 19] - 99 bots enemigos (modo Battle Royale completo)

### 99 bots rivales
`NUM_BOTS = 99` — partidas de 100 participantes (99 bots + jugador) como un
Battle Royale clásico.

**Ajustes de spawn para 99 bots:**
- Separación: 20 tiles del jugador, 6 tiles entre bots
- Intentos de spawn: 2000 (de 500)
- 99/99 bots spawneados en 0.09s en mapa 150×150
- Spread: 89% ancho × 88% alto (bien distribuidos)

**Optimización de rendimiento para 99 bots:**
Los bots se dividen en dos grupos cada frame:
- **Cerca** (≤65 tiles del jugador): IA completa (pathfinding, combate, hechizos)
- **Lejos** (>65 tiles): solo drift de tormenta, sin IA. Invisible al jugador igualmente.

Resultado en tests: 60 frames con 27 bots activos + 72 en drift → **1.6ms/frame** (apto para 60 FPS).

**Panel de ranking:** funciona con 100 participantes usando fuente compacta automáticamente.


## [Actualización 18] - 20 bots enemigos + mejoras de sprites del jugador

### 20 bots competidores
`NUM_BOTS` subido de 4 a 20. Los 20 bots aparecen en posiciones aleatorias bien
distribuidas por el mapa (85% de ancho × 81% de alto en simulación).

Ajustes para acomodar 20 bots:
- Separación mínima reducida: 28 tiles del jugador, 15 tiles entre bots (mapa 150×150)
- Intentos de spawn aumentados de 200 a 500 para garantizar los 20 spawns
- `bot_idx` cicla entre 0-3 (4 colores de sprite disponibles)

### Panel de ranking para 20+ jugadores
La pantalla de game over escala automáticamente:
- ≤8 participantes: línea de 22px de alto
- >8 participantes: línea de 14px de alto (fuente pequeña `_f_xs`)
- Panel se ancla al mínimo y=8 para no salirse de pantalla

### Sprites del jugador mejorados
4 sprites pixel art Tibia-style generados proceduralmente (48×48px):
- **Knight** — armadura azul, espada y escudo
- **Paladin** — túnica roja, arco y escudo
- **Druid** — capa verde, bastón de naturaleza
- **Sorcerer** — robe morado, staff mágico con orbe
Los 4 bots tienen colores diferenciados (dorado, naranja, cian, verde-amarillo).


## [Actualización 16] - Bugfixes críticos + cobertura de tests

### Bug 1 CORREGIDO: Crash cuando un monstruo lanza un hechizo
**Causa raíz**: `entities/monster.py` tenía IDs del catálogo antiguo hardcodeados:
- `dark_wizard: ['poison_bolt', 'decay_wave']` → corregido a `['exevo mas vis', 'exura mort']`
- `dragon: ['fireball', 'energy_beam']` → corregido a `['exevo flam', 'exevo gran mas flam']`

**Fix adicional en `main.py`**: guard defensivo en ambos bloques de spell events:
```python
if _sid not in SPELL_CATALOGUE: continue  # skip unknown
```
Esto evita que cualquier ID inválido futuro cause un crash.

### Bug 2 CORREGIDO: Pantalla de selección de vocación no aparecía al inicio
**Causa raíz**: `voc_screen = VocationSelect()` no estaba instanciado antes del menú
principal, y la primera rama `action == "new"` no llamaba a `voc_screen.run()`.
**Fix**: `VocationSelect()` se crea antes del menú, y se llama en los 3 flujos de nueva partida.

### Completitud del sistema
Además de los bugs, se añadieron los elementos que faltaban para que el sistema esté completo:
- **Loot para los 6 nuevos monstruos**: wolf, troll, bear, cyclops, fire_devil, vampire
- **Spells para nuevos monstruos**: cyclops→exevo vis, fire_devil→exevo flam+exevo vis, vampire→exura mort+exevo mas vis
- **Zonas actualizadas** con los nuevos monstruos: vampire en centro, bear/wolf/troll en periferia

### Tests: 969 tests (+22 nuevos en `test_bugfixes.py`)
6 clases de tests que cubren los casos extremos que faltaban:
- `TestMonsterSpellIDs` — todos los IDs en MONSTER_SPELLS existen en SPELL_CATALOGUE
- `TestVocationSelectInMain` — VocationSelect instanciado y llamado ≥3 veces
- `TestAllMonstersHaveLoot` — los 14 monstruos tienen tabla de loot con ítems válidos
- `TestAllMonstersHaveXP` — los 14 monstruos en MONSTER_XP con escalado correcto
- `TestZoneMonsterValidity` — zonas referencian tipos válidos
- `TestSpellIDGlobalConsistency` — todos los spell IDs son incantaciones Tibia válidas


## [Actualización 15] - Polish/UX: portal, bots en minimapa, notificaciones de zona

### Efecto de portal al spawn
Durante los primeros 3 segundos de cada partida, el jugador aparece rodeado de un
destello de círculos morados pulsantes (efecto de portal mágico) que se desvanece
progresivamente. Evoca el portal de teletransporte de Tibia clásico.

### Bots visibles en el minimapa
`hud.draw_minimap(..., bots=living_bots)` — los 4 bots rivales aparecen como
cuadrados de colores distintos en el minimapa:
- Bot 0: amarillo (255,200,0)
- Bot 1: naranja (255,140,0)
- Bot 2: rojo-naranja (255,80,0)
- Bot 3: verde-amarillo (200,255,0)
El jugador sigue siendo el punto blanco central.

### Notificaciones de cambio de zona
Al cruzar entre zonas de dificultad aparece un mensaje flotante coloreado:
"Zona: Centro", "Zona: Medio", etc. con el color de la zona correspondiente.
Se activa solo después del primer segundo para evitar notificaciones falsas al spawn.

### Lógica de ganador al final
Cuando el espectador (bot seguido) muere, la cámara pasa automáticamente al
siguiente bot vivo con más nivel. Cuando el último bot muere, aparece la notificación
"¡La tormenta acaba con todos!" morada.


## [Actualización 14] - Bloques 5+6: Items persistentes + 6 monstruos nuevos

### Bloque 5: Items persistentes entre runs
Los items equipados al final de una partida (o al morir) se guardan en `save.json`
y se restauran automáticamente al iniciar la siguiente run.

- `Session.equipment_data` almacena los 6 slots: weapon, armor, helmet, boots, ring, amulet
- Al crear el `Player` en `_new_game()`, los items se reequipan antes de empezar
- `session.save(..., inventory=player.inventory)` se llama al morir

### Bloque 6: 6 nuevos monstruos Tibia
Añadidos al `MONSTER_DATA` con stats, XP y dibujo procedural:

| Monstruo | Min. nivel | HP base | XP | Descripción |
|---|---|---|---|---|
| **Wolf** | 2 | 25 | 18 | Rápido (90 px/s), pack hunter |
| **Troll** | 4 | 50 | 55 | Lento pero resistente |
| **Bear** | 5 | 70 | 100 | Fuerza media, common en bosques |
| **Cyclops** | 13 | 140 | 900 | Grande, fuerte, nivel medio |
| **Fire Devil** | 17 | 110 | 200 | Rápido, daño de fuego |
| **Vampire** | 18 | 160 | 1200 | Tier alto antes del dragon |

Total: **14 tipos de monstruos** (rat, zombie, skeleton, orc, dark_wizard, dragon,
demon, dragon_lord + wolf, troll, bear, cyclops, fire_devil, vampire).

### Distribución de monstruos por zona (confirmado en simulación):
- Centro: avg nivel **14.8** (demon, dragon_lord)
- Interior: avg nivel **10.3** (dragon, fire_devil, vampire)
- Medio: avg nivel **7.7** (cyclops, dark_wizard, orc)
- Periferia: avg nivel **7.2** (rat, wolf, troll, zombie, skeleton)

### Bloque 3 (también en este update): modo espectador y ranking
- Al morir, cámara sigue al bot con más nivel
- Pantalla game over con ranking 1°-4° con nivel y estado vivo/muerto


## [Actualización 13] - XP Tibia, modo espectador y ranking final

### Bloque 3: Modo espectador al morir
Cuando el jugador muere, la partida continúa:
- La cámara sigue automáticamente al **bot con más nivel** que siga vivo
- Notificación: "¡Has muerto! Observando al rival más fuerte…"
- Los bots siguen actualizándose y combatiendo entre sí
- `GameOverStats` muestra el **panel de ranking** con todos los participantes

### Panel de ranking final
Visible en pantalla de game over (esquina inferior izquierda):
- Lista ordenada por nivel: 🥇 primero, 🥈 segundo, 🥉 tercero
- Muestra nivel, vocación/bot, y ☠ si está muerto
- `go_stats.set_bots(bots)` proporciona la lista de rivales

### Bloque 4: Fórmula XP de Tibia oficial
`entities/player.py` — función `tibia_xp_for_next_level(lv)`:
```
xp(lv) = 50 × (lv³ - 5·lv² + 8·lv - 4) / 3
```
Ejemplos:
| Nivel | XP necesaria |
|---|---|
| 1→2 | 100 XP (mínimo) |
| 5→6 | 733 XP |
| 10→11 | 3,900 XP |
| 20→21 | 17,733 XP |
| 50→51 | 119,233 XP |

### Tabla de XP por monstruo (valores Tibia clásico)
`MONSTER_XP = {rat:20, zombie:50, skeleton:35, orc:115, dark_wizard:385, dragon:4000, demon:6000, dragon_lord:7200}`
La XP escala +4% por nivel del monstruo encima del base.

### Ganancias de stats por nivel (por vocación)
Como Tibia: al subir de nivel cada vocación gana diferente cantidad de HP/MP/ATK:
| Vocación | HP/nivel | MP/nivel | ATK/nivel |
|---|---|---|---|
| Knight | +15 | +5 | +4 |
| Paladin | +10 | +15 | +3 |
| Druid | +8 | +30 | +2 |
| Sorcerer | +8 | +30 | +2 |


## [Actualización 12] - Spawn aleatorio + Zonas de dificultad radiales

### Bloque 1: Spawn aleatorio en mapa grande
Al iniciar una partida, el jugador aparece en una posición aleatoria de la periferia
del mapa (>35% de distancia al centro), y los 4 bots aparecen en posiciones aleatorias
separadas al menos 30 tiles del jugador y 25 tiles entre sí.

Esto recrea la mecánica de portal mágico del Battle Royale: nadie sabe dónde están
los demás al principio. La cámara hace snap instantáneo al punto de spawn.

### Bloque 2: Zonas de dificultad radiales (nuevo: `systems/zones.py`)
El mapa se divide en 4 anillos concéntricos como en los servidores de Tibia clásico:

| Zona | Distancia al centro | Monstruos | Nivel extra | Indicador |
|---|---|---|---|---|
| **Centro** | <25% | Demon, Dragon Lord, Dragon | +15 | 🔴 Rojo |
| **Interior** | 25-45% | Dragon, Dark Wizard | +8 | 🟠 Naranja |
| **Medio** | 45-65% | Orc, Dark Wizard, Skeleton | +3 | 🟡 Amarillo |
| **Periferia** | >65% | Rat, Zombie, Skeleton, Orc | +0 | 🟢 Verde |

El spawner respeta las zonas: un demonio solo aparece cerca del centro,
las ratas solo en la periferia. A medida que avanza la partida (+5 min = +1 nivel),
los monstruos de todas las zonas escalan.

### HUD: zona actual + minimapa con anillos
- El HUD muestra "Zona: Centro" / "Zona: Periferia" etc. en el centro inferior
  con el color de la zona correspondiente
- El minimapa muestra los anillos de las 4 zonas con colores semitransparentes

### Tests
34 tests nuevos en `tests/test_zones.py`: get_zone, nombres, colores, tipos de monstruos,
bonus de nivel, multiplicador de XP, random_spawn_point con separación garantizada.


## [Actualización 11] - Suelo sin daño + tiles estilo Tibia

### El suelo ya no quita vida
En Tibia el suelo de hierba, arena, piedra y pantano no hace daño al jugador.
Solo los monstruos, la tormenta y las tiles de lava (zona volcánica) son peligrosas.

Cambios en `systems/biomes.py`:
- **Desierto**: `damage_ps` 0.8 → 0.0 (la arena no quema)
- **Pantano**: `poison_chance` 0.55 → 0.0 (el barro solo ralentiza)
- El daño de lava sigue activo pero es opcional y reducido (tiles individuales)
- La tormenta sigue siendo la amenaza principal que cierra el mapa

### Tiles renovados (estilo Tibia clásico)
Nuevas extracciones del OpenTibia Sprite Pack con coordenadas optimizadas:
- **Grass** (r2c6): verde profundo con textura densa
- **Dirt** (r7c6): tierra marrón cálida
- **Sand** (r7c3): arena beige
- **Stone** (r13c4): adoquín oscuro de mazmorra Tibia
- **Lava** (r8c1): naranja con grietas negras pronunciadas
- **Water** (r15c11): azul Tibia brillante
- **Snow** (r18c0): blanco suave
- **Swamp** (r11c7): verde oliva pantanoso


## [Actualización 10] - Escalado de dificultad, bots respawn, HUD mejorado

### Bots respawn al morir
30 segundos tras morir, cada bot reaparece en posición aleatoria con nivel +1.
Notificación: "Un rival ha reaparecido".

### XP al eliminar bots
Melee o hechizo: `max(20, 10*(nivel+1))` XP con número flotante. ¡Rival eliminado!

### Hechizos afectan a bots
Proyectiles apuntan a `active_monsters + living_bots`.

### Escalado de dificultad con el tiempo
`difficulty_bonus`: +1 nivel de monstruo por cada 5 minutos. A 50 min = +10 niveles.

### Duración de partida: 57 min
6 fases de tormenta: 13+10+8+6+4+2 min de espera + cierres.

### HUD mejorado
Vocación visible bajo el nivel. Panel TAB incluye sección SKILLS con barra de XP.


## [Actualización 9] - Duración de partida, XP por bots, hechizos vs bots, observación de hechizos

### Bug: El círculo cerraba demasiado pronto (4.8 min → 57 min)
`systems/storm.py` — `PHASE_DATA` reescrito con 6 fases, duraciones como Tibia:

| Fase | Espera | Cierre | DPS |
|---|---|---|---|
| Fase I   | 13 min | 4 min | 2 |
| Fase II  | 10 min | 3 min | 5 |
| Fase III | 8 min  | 2.5 min | 10 |
| Fase IV  | 6 min  | 2 min | 22 |
| Fase V   | 4 min  | 1.5 min | 42 |
| Fase VI  | 2 min  | 1 min | 80 |

Total: **~57 minutos** de partida + supervivencia en zona final.

### Bug: Matar bots de IA no daba XP
`main.py` — cuando un bot muere (por melee, hechizo o tormenta), el jugador recibe
`max(20, 10 × (nivel+1))` XP con número flotante y notificación: `¡Rival eliminado! +20 xp`.
El flag `_death_processed` evita doble conteo.

### Bug: Los hechizos no afectaban a los bots
`main.py` — los proyectiles del jugador ahora tienen como objetivo
`active_monsters + living_bots`. Si un hechizo mata a un bot,
se procesa el XP igual que con muerte por melee.

### Bug: Vocaciones no empezaban con su nivel mágico correcto
`systems/spells.py` — `SpellMemory` ahora inicializa `magic_level` según vocación:
knight=0, paladin=2, druid=4, sorcerer=4.
Esto hace que Sorcerer y Druid puedan aprender hechizos de mayor nivel desde el principio.

### Observación de hechizos
La observación de hechizos de monstruos en superficie ya era funcional — `spawner.update()`
devuelve `spell_events` y el bucle principal los pasa a `player.observe_spell()`. 
Se verificó que el flujo estaba correcto en ambas rutas (superficie y mazmorra).


## [Actualización 9] - Corrección de bugs de gameplay

### Círculo cierra demasiado pronto → Partidas de ~57 minutos
`systems/storm.py` — PHASE_DATA reescrito con 6 fases y duraciones muy superiores:

| Fase | Espera | Cierre | Total |
|---|---|---|---|
| Fase I | 13 min | 4 min | 17 min |
| Fase II | 10 min | 3 min | 13 min |
| Fase III | 8 min | 2.5 min | 10.5 min |
| Fase IV | 6 min | 2 min | 8 min |
| Fase V | 4 min | 1.5 min | 5.5 min |
| Fase VI | 2 min | 1 min | 3 min |
| **Total** | | | **~57 min** |

### Matar bots da experiencia
Los bots (contrincantes IA) ahora dan XP al morir: `max(20, 10×(nivel+1))`.
Funciona tanto para muerte por melee como por hechizo.
Aparece notificación flotante: "¡Rival eliminado! +20 xp".

### Las magias ya afectan a los bots
Los proyectiles del jugador ahora incluyen a los bots como objetivo: `proj.update(dt, active_monsters + living_bots)`.
Los bots también reciben daño de explosiones AOE.

### Sistema de observación de hechizos mejorado
- **Nivel de magia inicial por vocación** (como Tibia): Knight=0, Paladin=2, Druid/Sorcerer=4
- **exevo vis** ahora es observable por todas las vocaciones (antes solo sorcerer)
- **exevo mort** observable por todas las vocaciones con min_magic_lv=1
- **exevo mas vis** y **exevo flam** con umbrales reducidos y acceso ampliado
- Los dragones/demonios siguen lanzando hechizos que el jugador puede aprender por observación


## [Actualización 8] - HUD de Skills + Notificaciones de subida de nivel

### Skills siempre visibles en pantalla
`hud.draw_skills(screen, player)` muestra en la esquina inferior derecha del HUD:
- **Skill primario** (según vocación) con nombre, nivel y barra de XP animada
- **Skills secundarios** en fila compacta (3 letras + nivel)

### Notificaciones flotantes de skill up
Cada vez que un skill sube de nivel aparece un mensaje azul flotante sobre el personaje:
`▲ Espada sube a 16!` — con la misma mecánica de las notificaciones de hechizo aprendido.

### Panel TAB: sección de Skills
El overlay de estadísticas (tecla TAB) ahora incluye una sección **SKILLS** con:
- Todos los skills y su nivel actual
- Barra de progreso de XP hacia el siguiente nivel

### Eventos de skill level-up
`player._skill_levelup` se activa cuando sube cualquier skill (melee, magic, shielding).
El juego consume el evento en el mismo frame y genera la notificación correspondiente.


## [Actualización 7] - Sprites reales del OpenTibia Sprite Pack (CC BY 4.0)

Integración de sprites del [OpenTibia Sprite Pack](https://github.com/peonso/opentibia_sprite_pack)
(licencia Creative Commons Attribution 4.0 Internacional — peonso et al.).

### Sprites integrados

**Monstruos** (en `assets/monsters/`):
- `rat.png` — Rata beige animada (c01 r4c3)
- `zombie.png` — Humanoide oscuro con pelo rojo (c01 r1c0)
- `skeleton.png` — Caballero con armadura plateada y espada (c01 r2c0)
- `orc.png` — Criatura verde grande 48×48 (c02 r6c0)
- `dark_wizard.png` — Mago azul con estrella 48×32 (c02 r3c0)
- `dragon.png` — Dragón verde grande 64×64 (c02 r7c2)
- `demon.png` — Criatura roja armada con cola 64×64 (c04 r0c0)
- `dragon_lord.png` — Variante mayor del demon 64×64 (c04 r2c0)

**Jugador y bots** (en `assets/player/`):
- `outfit_0..3.png` — Knight humanoid isométrico (c03 rows 1,3,5,7 col 1)
- `bot_0..3.png` — Misma base, frames alternativos (c03 rows 9,11,13,15 col 1)

**Tiles de suelo** (en `assets/tiles/`):
- `grass.png` — Verde brillante (tiles r5c4)
- `dirt.png` — Tierra marrón (tiles r7c8)
- `lava.png` — Naranja con grietas (tiles r8c0)
- `water.png` — Azul profundo (tiles r47c0)
- `snow.png` — Blanco/gris claro (tiles r18c0)
- `sand.png` — Arena cálida (tiles r7c14)
- `swamp.png` — Verde oliva pantanoso (tiles r11c4)
- `stone.png` — Adoquín oscuro (tiles r13c4)

### Cambios técnicos
- `sprites.json` — actualizado con todas las rutas reales
- `core/world.py` — `_build_tile_surfaces()` consulta `SpriteLoader` antes de dibujar proceduralmente
- `tests/test_sprite_loader.py` — actualizado para aceptar valores no-null en sprites.json

El sistema de fallback procedural sigue activo: si un archivo falta, el juego usa el sprite generado por código sin errores.


## [Actualización 6] - Movimiento de cámara suave (sin flickering)

### Problema
El jugador se movía tile a tile (32px por paso) y la cámara saltaba
exactamente esos 32px de golpe cada vez. Con el mapa de tiles detrás,
eso creaba un flickering muy molesto a la vista.

### Solución: interpolación lerp exponencial (`core/camera.py`)
La cámara ahora se **desliza suavemente** hacia el jugador en lugar de
teletransportarse. Implementado con lerp exponencial:

```
factor = 1 - e^(-LERP_SPEED × dt)
```

Con `LERP_SPEED = 12` a 60fps, cada frame cierra el **18%** del gap restante
(≈ 5.8px por paso de 32px). La cámara converge completamente en ~0.4 segundos.

| Antes | Después |
|---|---|
| Salto de 32px instantáneo | Máximo 6.5px por frame |
| Flickering visible | Deslizamiento suave |

- **`Camera.snap(cx, cy)`**: teleport instantáneo para transiciones de mazmorra
  (entrar/salir) donde el deslizamiento no tiene sentido.
- **`round()` en lugar de `int()`** para los offsets de tile en `world.py` y
  `dungeon_renderer.py`, eliminando shimming de ±1 pixel en los tiles.
- `LERP_SPEED` es una constante en `camera.py` fácil de ajustar (mayor = más rápido).

### Tests
11 tests nuevos en `TestCameraLerp` (en `test_camera.py`):
primer frame instantáneo, lerp parcial en frames siguientes, convergencia,
snap, dt=0, factor a 60fps, clamp en bordes del mundo.


## [Actualización 5] - Vocaciones, hechizos Tibia, skills y loot fiel al original

### Vocaciones
Pantalla de selección de vocación (`ui/vocation_select.py`) al iniciar nueva partida:

| Vocación | Hechizos iniciales | Fuerte en |
|---|---|---|
| Knight | exori, exori gran, utamo vita | HP, defensa, Shielding |
| Paladin | exevo con, exevo gran con, exura san | Distancia, equilibrio |
| Druid | exevo frigo, exevo tera, exevo gran mas frigo | Magia curativa/elemental |
| Sorcerer | exevo vis, exevo gran vis, exevo flam | Magia ofensiva máxima |

La vocación persiste en `save.json` y determina el outfit del personaje.

### Hechizos estilo Tibia (`systems/spells.py`)
20 hechizos con conjuros latinos: `exori`, `exevo gran vis`, `exevo gran mas flam`, `utamo vita`, etc.
La spell bar muestra el conjuro. Monstruos usan sus propias tablas: dragones → `exevo flam`,
demonios → `exura mort`, Dragon Lord → `exevo gran vis`.

### Skills con el uso (`systems/skills.py`)
Sword, axe, club, distance, shielding, magic, fist — todos empiezan en nivel 10.
Fórmula XP: `50 × n^1.6` (igual que Tibia). Cada acción sube el skill correspondiente.
Los skills dan bonus de daño/bloqueo. Se guardan en `save.json`.

### Loot fiel a Tibia (`systems/loot.py`)
Items con nombres reales: Fire Sword, Dragon Scale Mail, Boots of Haste, Platinum Amulet,
Demon Armor, Soft Boots, Dragon Slayer, Ring of Stars, etc.
Cada criatura tiene su tabla propia: Rat → Cheese; Dragon → Dragon Scale Mail, Fire Sword;
Demon → Demon Armor, Demon Shield; Dragon Lord → Dragon Slayer, Soft Boots.

### Tests
- 47 tests nuevos en `test_skills.py`
- 35 tests nuevos en `test_vocations.py`


## [Actualización 4] - Configuración de sprites via JSON

### Añadido
- **`sprites.json`**: fichero de configuración en la raíz del juego. Cada entrada puede apuntar a un fichero `.png`/`.jpg` o ser `null` (usa el sprite procedural). Incluye comentarios explicativos (`_readme`) con tamaños de referencia.
- **`core/sprite_loader.py`** (`SpriteLoader`): carga, valida y cachea las imágenes de `sprites.json`. La primera llamada a `get()` dispara la carga del JSON. Las imágenes se escalan automáticamente al tamaño del sprite. Si el fichero no existe o la ruta es incorrecta, cae silenciosamente al sprite procedural sin errores.
- Método `reload()` para recarga en caliente sin reiniciar el juego.
- Método `summary()` que imprime el estado de cada sprite (cargado / no encontrado / pendiente).
- `has(section, key)` para verificar si hay una ruta configurada.

### Cómo usar sprites.json
```json
{
  "monsters": {
    "rat": "mis_sprites/rata.png",
    "dragon": null
  },
  "player": {
    "outfit_0": "mis_sprites/jugador.png"
  }
}
```
Las rutas son relativas al directorio del juego. Si el fichero no existe, se dibuja el sprite procedural sin avisos.

### Cambiado
- `entities/monster.py`: todos los `_draw_*` delegan en `draw_monster()`.
- `entities/player.py`: `draw()` llama a `draw_player_sprite()`.
- `entities/bot.py`: `draw()` llama a `draw_bot_sprite()`.
- `ui/tibia_sprites.py`: reorganizado con `draw_monster()`, `draw_player_sprite()`, `draw_bot_sprite()` que comprueban el loader primero.

### Tests
- 27 tests nuevos en `test_sprite_loader.py` cubriendo: carga de JSON, entradas null, rutas inexistentes, caché, reload, `has()`, `summary()`, y que `sprites.json` existe y es válido con todas las secciones requeridas en null por defecto.


## [Actualización 3] - Movimiento tile a tile estilo Tibia clásico

### Cambiado
- **Movimiento tile a tile**: el jugador ya no se mueve de forma continua en píxeles. Al pulsar una dirección el personaje avanza exactamente 32px (1 tile), igual que en Tibia original. La posición siempre queda centrada en un tile.
- **Solo 4 direcciones**: arriba, abajo, izquierda, derecha. Sin diagonal libre. Cuando se pulsan dos teclas a la vez, la prioridad es vertical (arriba/abajo) sobre horizontal.
- **`WALK_DELAY = 0.18s`**: tiempo mínimo entre pasos (equivalente a la velocidad de caminar de Tibia). Se reduce con objetos de velocidad.
- **Animación de bob**: pequeño movimiento vertical al caminar, como los sprites de Tibia.
- **`Player.walk_delay`**: propiedad calculada que reduce el delay con bonificadores de velocidad del equipo.

### Corregido
- Tests de movimiento actualizados para verificar el sistema de tiles (posición siempre múltiplo de 32+16, bloqueo por tile impassable, rate-limiting de pasos).

### Tests de integración verificados
- Snap al tile más cercano al crear el jugador.
- Un paso = exactamente 1 tile (32px).
- Sin movimiento diagonal.
- Walk delay impide moverse más de 1 tile por `WALK_DELAY` segundos.
- Bloqueo correcto por tiles impassable.
- La posición es siempre el centro de un tile (`n*32 + 16`).
- Lanzar hechizos funciona desde posiciones tile.
- La dirección y `_facing` se actualizan correctamente.


## [Actualización 2] - Sprites Tibia, bots, pantalla completa, mejoras de rendimiento

### Añadido
- **Sprites humanoides estilo Tibia** (`ui/tibia_sprites.py`): módulo compartido con funciones de dibujo para personajes humanoides con cabeza, pelo, ojos, cuello, cuerpo, brazos, cinturón, piernas y zapatos. Cada tipo de monstruo tiene su propio sprite temático:
  - Rata: cuerpo ovalado, orejas, cola curvada, patas
  - Zombie: humanoide verdoso con skin verde-grisácea
  - Esqueleto: estructura ósea visible, cráneo con cuencas, costillas, mandíbula
  - Orco: humanoide rechoncho verde, colmillos salientes, ojos rojos
  - Dark Wizard: túnica triangular, sombrero cónico, báculo con orbe púrpura
  - Dragón: cuerpo escamoso, alas, cuernos, ojos de fuego, cola
  - Demon: humanoide musculoso rojo, cuernos grandes, alas oscuras
  - Dragon Lord: dragón enorme con corona de picos y aura
- **Bots competidores** (`entities/bot.py`): 4 rivales con IA que intentan sobrevivir junto al jugador. Con nombres únicos (Asesino, Cazador, Guerrero...) y outfits de colores distintos. Máquina de estados: ROAM / HUNT_MONSTERS / FLEE_STORM / ATTACK_PLAYER. Atacan al jugador si están cerca y son más fuertes, cazan monstruos para ganar XP, huyen de la tormenta. Muestran su nombre, nivel y barra de HP encima.
- **Menú de pausa** (`ui/pause_menu.py`): overlay semitransparente al pulsar ESC con opciones Continuar / Menú Principal / Salir. No destruye ni reinicia la partida actual.
- **Fullscreen con F11**: alterna entre modo ventana y pantalla completa sin reiniciar el juego.
- Ventana redimensionable (flag `pygame.RESIZABLE`).

### Corregido
- **ESC ya no reinicia el mapa**: pulsar ESC abre el menú de pausa. Volver al menú principal y elegir "Continuar" reanuda la misma partida. Sólo "Nueva Partida" genera un mundo nuevo.
- El jugador humanoid ahora muestra el sprite correcto (ya no es un círculo).

### Cambiado
- **Tooltip ultraligero**: ahora solo muestra nombre + nivel + barra HP compacta. Se actualiza cada 80ms en lugar de cada frame. No se activa dentro de mazmorras (donde hay menos monstruos y el rendimiento no es problema). Elimina el lag al acumular muchos enemigos.
- `Player.draw()` usa el nuevo sistema de sprites humanoides.
- `Monster.draw()` delega en `tibia_sprites.py` para todos los tipos.

### Tests
- 18 tests nuevos para `Bot` (init, daño, estados, dibujo, regeneración).
- 8 tests nuevos para `PauseMenu` (activación, hover, click, dibujo).
- Tests de tooltip actualizados para el API simplificado.
Todos los cambios relevantes del proyecto, del más reciente al más antiguo.

---

## [Actualización 1] - Menú, nuevos monstruos, tooltip, semilla aleatoria

### Añadido
- **Menú principal** (`ui/main_menu.py`): pantalla de inicio con Nueva Partida, Continuar, Borrar Progreso y Salir. Muestra resumen del save. Confirmación antes de borrar. Navegable con teclado y ratón.
- **Demon** (nivel mínimo 25): humanoide rojo con alas y cuernos. Usa Death Coil y Fireball.
- **Dragon Lord** (nivel mínimo 30): el más poderoso. Corona de picos, ojos púrpura. Usa Energy Beam, Death Coil y Fireball. Mayor tamaño y XP de todos los tipos.
- **Tooltip de monstruos** (`ui/monster_tooltip.py`): al hacer hover aparece nombre, nivel, HP, daño, velocidad, modificadores de élite y hechizos conocidos. Fade suave.
- **Semilla aleatoria por partida**: cada partida genera una semilla única para el mapa, biomas, mazmorras y spawns. Persiste en `save.json`.
- `Session.new_seed()`: genera y registra una semilla nueva.
- Desde ESC se puede volver al menú principal sin cerrar el juego.
- README.md y CHANGELOG.md.

### Cambiado
- `Session.save()` acepta el parámetro opcional `seed`.
- `World`, `BiomeMap` y `generate_dungeons` reciben la semilla dinámica.
- Mock de pygame ampliado con más constantes de teclas y `FakeRect` completo.

### Tests
- 43 tests nuevos en `test_extras.py`.

---

## [Fase 8] - Mazmorras con niveles reales

### Añadido
- **`core/dungeon_generator.py`**: generador BSP. Salas sin solapamiento conectadas por corredores en L (árbol de expansión mínima). Tiles: DWALL, DFLOOR, DCORR, DENTRY, DEXIT, DLAVA. El tamaño escala con la profundidad.
- **`core/level_manager.py`**: pila superficie ↔ mazmorra. Teleport del jugador y reajuste de cámara. Portales animados de entrada (⬇ púrpura) y salida (⬆ verde).
- **`ui/dungeon_renderer.py`**: paredes con patrón ladrillo, suelo con rejilla, antorchas con glow pulsante, viñeta oscura.
- Jefe garantizado en la sala del fondo con 2–3 mods de élite.
- Drops mínimo `uncommon` en todos los kills dentro de mazmorra.
- Sin daño de tormenta en mazmorras. Oscuridad ambiental y banner de profundidad.

### Tests
- 54 tests nuevos en `test_dungeons_levels.py`.

---

## [Fase 7] - Biomas con efectos reales

### Añadido
- **`systems/biomes.py`**: 5 biomas con efectos. `BiomeMap` por Voronoi. Centro siempre Praderas.
- Tiles nuevos: TILE_LAVA (impassable), TILE_SNOW, TILE_SAND, TILE_SWAMP con sprites propios.
- Efectos: Tundra (−18% vel), Desierto (−0.8 HP/s), Pantano (−22% vel + veneno), Volcánico (lava −15 HP/s).
- **`ui/biome_ui.py`**: tinte ambiental, partículas temáticas (nieve, arena, ceniza, burbujas), banner al entrar.
- Badge de bioma en HUD. Spawner ponderado por bioma.

### Tests
- 61 tests nuevos en `test_biomes.py`.

---

## [Fase 6] - Estadísticas y rankings

### Añadido
- **`systems/stats.py`** (`RunStats`): 18 métricas en tiempo real (kills, daño, hechizos, ítems, movimiento, tormenta, mazmorras...).
- **`systems/lifetime_stats.py`** (`LifetimeStats`): hasta 100 partidas en `stats_history.json`, 11 récords absolutos, 9 rankings Top-10.
- **`ui/stats_ui.py`**: overlay in-game (TAB) + Game Over con 4 páginas: Resumen, Rankings (←→), Totales de vida, Historial (↑↓).

### Tests
- 65 tests nuevos en `test_stats.py`.

---

## [Fase 5] - Élites, jefes y zonas de mazmorra planas

### Añadido
- **`systems/elites.py`**: 18% spawn élite con 1–2 mods. 6 modificadores: Berserker, Armored, Swift, Regenerating, Venomous, Giant.
- **`systems/boss.py`**: jefes a los 90/180/280/400/540 s. 3 tipos (Orc Warchief, Lich, Ancient Dragon). Barra HP superior. Drops mínimo `rare`.
- **`systems/dungeons.py`**: 4 zonas circulares en el mapa. Doble densidad spawn, loot ×1.65, sin tormenta.
- Monstruos nuevos: Orc (lv10), Dark Wizard (lv15), Dragon (lv20).

### Tests
- 89 tests nuevos en `test_elites.py` y `test_dungeons_boss.py`.

---

## [Fase 4] - Hechizos aprendibles por observación

### Añadido
- **`systems/spells.py`**: 7 hechizos. `SpellMemory` con observaciones, umbral, nivel mágico, serialización.
- **`entities/projectile.py`**: proyectiles con trail, glow, pierce, AOE, preview de radio.
- Windup visible en monstruos (orbe de carga animado).
- **`ui/spell_bar.py`**: barra lateral con hotkeys 1–7, progreso de observaciones.
- Persistencia de SpellMemory en `save.json`.

### Controles nuevos
- Click derecho: lanzar hechizo | `1`–`7`: seleccionar | `Q`/`E`: ciclar.

### Tests
- 91 tests nuevos en `test_spells.py` y `test_projectile.py`.

---

## [Fase 3] - Tormenta estilo Fortnite

### Añadido
- **`systems/storm.py`**: 5 fases WAITING→CLOSING. Daño creciente fuera del anillo.
- **`ui/storm_renderer.py`**: niebla, anillo con glow, preview siguiente anillo, flecha dirección, viñeta roja.
- Panel de tormenta en HUD y anillo en minimapa.

---

## [Fase 2] - Equipamiento e inventario

### Añadido
- **`systems/inventory.py`**: 6 ranuras + bolsa 20 ítems.
- **`systems/loot.py`**: 32 plantillas, 4 rarezas, drop chance variable.
- **`entities/item_drop.py`**: objetos en suelo con animación bob y tooltip.
- **`ui/inventory_ui.py`**: panel con ranuras, bolsa, tooltips, equipar/desequipar.

---

## [Fase 1] - Base jugable

### Añadido
- Mapa 150×150 tiles procedural (suciedad, piedra, agua, árboles). Cámara centrada con clamp.
- 3 monstruos: Rat, Zombie, Skeleton. A* con límite de nodos. Wander cuando no agredidos.
- Ataque melee en arco. XP y niveles. HUD completo. Minimapa. Persistencia `save.json`.
- Runner de tests sin pantalla (`mock_pygame.py`, `fake_world.py`).
