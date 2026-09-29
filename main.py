import pygame
import sys
import random
import math
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import *
from core.world        import World
from core.camera       import Camera
from core.session      import Session
from core.level_manager import LevelManager
from entities.player     import Player
from entities.spawner    import Spawner
from entities.bot        import Bot
from entities.item_drop  import ItemDrop
from entities.projectile import Projectile, Explosion
from entities.monster    import Monster, MONSTER_DATA
from systems.loot        import try_drop_with_mult, generate_guaranteed
from systems.storm       import Storm
from systems.spells      import SpellMemory, SPELL_CATALOGUE
from systems.dungeons    import generate_dungeons, in_any_dungeon, draw_dungeons
from systems.boss        import BossManager, BOSS_TYPES
from systems.stats       import RunStats
from systems.lifetime_stats import LifetimeStats
from systems.biomes      import (BiomeMap, BIOMES, TILE_LAVA,
                                  ambient_damage, swamp_poison_tick,
                                  lava_damage, SWAMP_POISON_DMG)
from systems.elites      import roll_boss_mods, apply_modifiers
from ui.hud              import HUD
from ui.inventory_ui     import InventoryUI
from ui.storm_renderer   import StormRenderer
from ui.spell_bar        import SpellBar
from ui.stats_ui         import StatsOverlay, GameOverStats
from ui.biome_ui         import BiomeUI
from ui.dungeon_renderer import DungeonRenderer
from ui.main_menu        import MainMenu
from ui.pause_menu       import PauseMenu
from ui.vocation_select  import VocationSelect
from ui.monster_tooltip  import MonsterTooltip

NUM_BOTS = 99  # bots competidores (Battle Royale)

# ── Helpers ────────────────────────────────────────────────────────────────
class Notification:
    DURATION = 3.0
    def __init__(self, t, c=(255,255,255)): self.text=t; self.color=c; self.life=self.DURATION

def _push(pool, text, color=(220,220,220)):
    pool.append(Notification(text,color))
    if len(pool)>6: pool.pop(0)

def _upd_notes(pool,dt):
    for n in pool[:]:
        n.life-=dt
        if n.life<=0: pool.remove(n)

def _drw_notes(screen,pool,font):
    x=SCREEN_W//2; y=GAME_H-22
    for n in reversed(pool):
        a=min(255,int(255*n.life))
        s=font.render(n.text,True,n.color); s.set_alpha(a)
        screen.blit(s,(x-s.get_width()//2,y)); y-=s.get_height()+3

def _add_dn(pool,x,y,text,color):
    pool.append({'x':float(x),'y':float(y),'text':str(text),'color':color,'life':1.0,'alpha':255})

def _upd_dn(pool,dt):
    for d in pool[:]:
        d['life']-=dt; d['y']-=42*dt; d['alpha']=max(0,int(255*d['life']))
        if d['life']<=0: pool.remove(d)

def _drw_dn(screen,pool,cam,font):
    for d in pool:
        sx=int(d['x']-cam.offset_x); sy=int(d['y']-cam.offset_y)
        s=font.render(d['text'],True,d['color']); s.set_alpha(d['alpha'])
        screen.blit(s,(sx-s.get_width()//2,sy))


# ── Factory ────────────────────────────────────────────────────────────────
def _new_game(session, seed):
    from systems.skills import Skills
    from systems.spells import VOCATION_SPELLS
    world      = World(MAP_W, MAP_H, TILE_SIZE, seed=seed)
    biome_map  = BiomeMap(MAP_W, MAP_H, seed=seed)
    world.apply_biomes(biome_map)
    dungeons   = generate_dungeons(MAP_W, MAP_H, seed=seed)
    world.apply_dungeon_zones(dungeons)
    # Random spawn in periferia (zone 3) — away from center and dungeons
    from systems.zones import random_spawn_point
    _spawn_margin = 12
    _spawn_col, _spawn_row = MAP_W//2, MAP_H//2   # fallback: center
    # Try to spawn in outer 35% of map for battle-royale feel
    for _attempt in range(200):
        _col = random.randint(_spawn_margin, MAP_W-_spawn_margin)
        _row = random.randint(_spawn_margin, MAP_H-_spawn_margin)
        if not world.is_walkable(_col, _row): continue
        # Prefer periphery (distance > 35% of map radius)
        _dcx = abs(_col - MAP_W//2); _dcy = abs(_row - MAP_H//2)
        if _dcx + _dcy < (MAP_W//2)*0.35: continue
        _spawn_col, _spawn_row = _col, _row
        break
    spawn_x = _spawn_col*TILE_SIZE + TILE_SIZE//2
    spawn_y = _spawn_row*TILE_SIZE + TILE_SIZE//2
    vocation   = session.vocation
    sm         = SpellMemory.from_dict(session.spell_memory_data) \
                 if session.spell_memory_data else SpellMemory(vocation=vocation)
    # Give player their vocation starting spells
    if not sm.known_spells:
        sm.known_spells = list(VOCATION_SPELLS.get(vocation, [])[:3])
    skills     = Skills.from_dict(session.skills_data) \
                 if session.skills_data else Skills(vocation=vocation)
    outfit_idx = ["knight","paladin","druid","sorcerer"].index(vocation) \
                 if vocation in ["knight","paladin","druid","sorcerer"] else 0
    player     = Player(spawn_x, spawn_y, level=session.persistent_level,
                        spell_memory=sm, outfit_idx=outfit_idx,
                        vocation=vocation, skills=skills)
    # Restore equipment from previous run
    for slot, item in session.equipment_data.items():
        if item and slot in player.inventory.equipped:
            player.inventory.equipped[slot] = item
    camera     = Camera(SCREEN_W, SCREEN_H, MAP_W*TILE_SIZE, MAP_H*TILE_SIZE)
    camera.snap(spawn_x, spawn_y)   # instant snap to player spawn
    spawner    = Spawner(world, player.level, dungeons=dungeons, biome_map=biome_map)
    storm      = Storm(MAP_W*TILE_SIZE, MAP_H*TILE_SIZE)
    boss_mgr   = BossManager()
    run        = RunStats()
    entrances  = LevelManager.build_entrances(dungeons, biome_map, TILE_SIZE)
    lvl_mgr    = LevelManager(world, camera, entrances)

    # Spawn bots spread around the map
    bots = _spawn_bots(world, player.level, NUM_BOTS,
                       player_col=_spawn_col, player_row=_spawn_row)

    return world, player, camera, spawner, storm, dungeons, boss_mgr, run, \
           biome_map, lvl_mgr, entrances, bots


def _spawn_bots(world, player_level, count, player_col=None, player_row=None):
    """Spawn bots in random positions, well separated from player and each other."""
    bots        = []
    W, H        = world.width, world.height
    taken_spots = []
    if player_col is not None:
        taken_spots.append((player_col, player_row))

    for i in range(count):
        for _ in range(200):
            col = random.randint(8, W-8)
            row = random.randint(8, H-8)
            if not world.is_walkable(col, row): continue
            # Separation: 20 tiles from player, 6 between bots (enough for 99 bots)
            too_close = any(
                abs(col-oc)+abs(row-or_) < (20 if j == 0 else 6)
                for j,(oc,or_) in enumerate(taken_spots)
            )
            if too_close: continue
            x     = col*TILE_SIZE + TILE_SIZE//2
            y     = row*TILE_SIZE + TILE_SIZE//2
            level = max(0, player_level + random.randint(-1, 3))
            bots.append(Bot(x, y, level, bot_idx=i % 4))
            taken_spots.append((col, row))
            break
    return bots


def _spawn_dungeon_monsters(dmap, player_level, biome_name):
    from entities.monster import available_types
    ts    = dmap.tile_size
    types = available_types(player_level)
    bdata = BIOMES.get(biome_name, BIOMES["grassland"])
    wd    = bdata["spawn_weights"]
    all_w = [max(0.05, wd.get(t, 0.5)) for t in types]
    monsters = []
    for col, row in dmap.monster_spawns:
        if not dmap.is_walkable(col, row): continue
        mtype = random.choices(types, weights=all_w, k=1)[0]
        level = max(0, player_level + random.randint(0, dmap.dungeon_level+1))
        x = col*ts+ts//2; y = row*ts+ts//2
        m = Monster(x, y, mtype, level)
        from systems.elites import roll_elite, apply_modifiers as _am
        mods = roll_elite()
        if mods: _am(m, mods)
        monsters.append(m)
    return monsters


def _spawn_dungeon_boss(dmap, player_level):
    ts = dmap.tile_size
    bcol, brow = dmap.boss_spawn
    if not dmap.is_walkable(bcol, brow): bcol, brow = dmap.exit_pos
    x = bcol*ts+ts//2; y = brow*ts+ts//2
    eligible = [k for k,v in BOSS_TYPES.items() if player_level >= v["min_level"]]
    if not eligible: eligible = list(BOSS_TYPES.keys())
    btype_id = random.choice(eligible); bdata = BOSS_TYPES[btype_id]
    _MAP = {"orc":"skeleton","dark_wizard":"skeleton","dragon":"skeleton"}
    base = _MAP.get(bdata["base_type"], "skeleton")
    boss = Monster(x, y, base, player_level)
    scale         = 1.0 + player_level*0.08 + dmap.dungeon_level*0.12
    boss.max_hp   = int(bdata["hp_base"]*scale); boss.hp = float(boss.max_hp)
    boss.damage   = int(bdata["dmg_base"]*scale); boss.speed = bdata["speed"]
    boss.xp_reward= int(bdata["xp_base"]*scale); boss.aggro_r = 25
    boss.SIZE     = bdata["size"]; boss.color = bdata["color"]
    boss.outline  = tuple(max(0,c-30) for c in bdata["color"])
    apply_modifiers(boss, roll_boss_mods())
    boss.is_boss = True; boss.boss_display_name = bdata["name"]
    boss.boss_type_id = btype_id
    return boss


def _on_death(m, player, item_drops, dn, notes, dungeons, boss_mgr, run, in_dungeon=False):
    from entities.player import MONSTER_XP
    from systems.zones import get_zone, get_zone_xp_mult
    base_xp  = MONSTER_XP.get(getattr(m,"mtype","rat"), m.xp_reward)
    lv_mult  = 1.0 + (m.level * 0.04)   # +4% per monster level above base
    map_cx   = 0; map_cy = 0; map_r = 1  # zone mult not needed if we can't get map dims here
    xp       = max(1, int(base_xp * lv_mult))
    if getattr(m,"is_boss",False): xp = m.xp_reward  # bosses keep their custom XP
    run.on_kill(m); run.on_xp_gained(xp)
    leveled = player.gain_xp(xp)
    _add_dn(dn, m.x, m.y-38, f"+{xp} xp", C_GREEN)
    if leveled:
        _add_dn(dn, player.x, player.y-55, f"LEVEL {player.level}!", C_YELLOW)
    item = generate_guaranteed(m.level,"uncommon") if in_dungeon else \
           try_drop_with_mult(m, 1.65 if in_any_dungeon(dungeons,m.x,m.y) else 1.0)
    if getattr(m,"is_boss",False):
        for bi in boss_mgr.on_boss_death(m):
            item_drops.append(ItemDrop(m.x+random.randint(-20,20),
                                       m.y+random.randint(-20,20),bi))
            run.on_item_found(bi)
        notes.append(Notification(f"☠  {getattr(m,'boss_display_name','Boss')} derrotado!",(255,180,30)))
        if len(notes)>6: notes.pop(0)
    elif item:
        item_drops.append(ItemDrop(m.x+random.randint(-12,12),
                                   m.y+random.randint(-12,12),item))
        run.on_item_found(item)


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    flags  = pygame.RESIZABLE
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
    pygame.display.set_caption("Tibia Survivor")
    clock  = pygame.time.Clock()
    fullscreen = False

    font_dn   = pygame.font.SysFont("Arial", 18, bold=True)
    font_note = pygame.font.SysFont("Arial", 17, bold=True)

    session   = Session()
    lifetime  = LifetimeStats()
    menu      = MainMenu()
    pause_menu= PauseMenu()
    voc_screen= VocationSelect()

    # ── Main menu ──────────────────────────────────────────────────────────
    action = menu.run(screen, clock)
    if action == "quit": pygame.quit(); sys.exit()

    seed = (session.last_seed if action=="continue" and session.last_seed
            else session.new_seed())
    if action == "new":
        session.spell_memory_data = {}
        session.skills_data       = {}
        session.equipment_data    = {}
        pygame.event.clear()   # flush key-press that confirmed main menu
        pygame.time.wait(80)   # brief pause so display updates
        session.vocation          = voc_screen.run(screen, clock)

    (world, player, camera, spawner, storm, dungeons,
     boss_mgr, run, biome_map, lvl_mgr, entrances, bots) = _new_game(session, seed)

    hud           = HUD(SCREEN_W, SCREEN_H)
    inv_ui        = InventoryUI(SCREEN_W, SCREEN_H)
    storm_render  = StormRenderer(SCREEN_W, GAME_H)
    spell_bar     = SpellBar(SCREEN_W, SCREEN_H)
    stats_overlay = StatsOverlay()
    go_stats      = GameOverStats(SCREEN_W, SCREEN_H)
    biome_ui      = BiomeUI(SCREEN_W, GAME_H)
    dung_renderer = DungeonRenderer(TILE_SIZE)
    tooltip       = MonsterTooltip()

    damage_numbers: list=[]; item_drops: list=[]; notifications: list=[]\
    ; projectiles:  list=[]; explosions: list=[]; dung_monsters: list=[]
    dung_boss = None
    living_bots: list = list(bots)   # populated immediately from bots
    _bot_respawn_queue: list = []
    go_stats.set_bots(bots)           # ranking panel has bots from start

    elapsed=0.0; game_over=False; show_inv=False; show_stats=False; _prev_warn=False
    spectator_target = None
    _portal_timer   = 3.0
    current_biome="grassland"
    world.reveal_around(player.x, player.y)   # reveal spawn area immediately

    while True:
        dt = min(clock.tick(FPS)/1000.0, 0.05)
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                session.save(player.level,elapsed,storm.phase_reached,
                             player.spell_memory,seed,player.skills,
                             player.inventory)
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                # F11 → fullscreen toggle
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)

                elif event.key == pygame.K_ESCAPE and not game_over:
                    # Pause menu — does NOT recreate game
                    session.save(player.level,elapsed,storm.phase_reached,
                             player.spell_memory,seed,player.skills,
                             player.inventory)
                    p_action = pause_menu.run(screen, clock)
                    if p_action == "quit":
                        pygame.quit(); sys.exit()
                    elif p_action == "menu":
                        m_action = menu.run(screen, clock)
                        if m_action == "quit":
                            pygame.quit(); sys.exit()
                        elif m_action == "new":
                            seed = session.new_seed()
                            session.spell_memory_data = {}
                            session.skills_data       = {}
                            session.equipment_data    = {}
                            pygame.event.clear()
                            pygame.time.wait(80)
                            session.vocation          = voc_screen.run(screen, clock)
                            damage_numbers.clear(); item_drops.clear()
                            notifications.clear(); projectiles.clear()
                            living_bots.clear(); _bot_respawn_queue.clear()
                            explosions.clear(); dung_monsters.clear(); dung_boss=None
                            elapsed=0.0; game_over=False; show_inv=False; show_stats=False; _prev_warn=False
                            spectator_target=None; _portal_timer=3.0
                            (world,player,camera,spawner,storm,dungeons,boss_mgr,run,
                             biome_map,lvl_mgr,entrances,bots) = _new_game(session,seed)
                            living_bots[:] = list(bots)
                            go_stats.set_bots(bots)
                            storm_render=StormRenderer(SCREEN_W,GAME_H)
                            biome_ui=BiomeUI(SCREEN_W,GAME_H); current_biome="grassland"
                            camera.snap(player.x, player.y)
                            world.reveal_around(player.x, player.y)
                        # "continue" or "resume" → just continue (no recreate)
                    # "resume" → continue immediately

                elif event.key == pygame.K_TAB:
                    if game_over: go_stats.next_page()
                    else: show_stats=not show_stats; show_inv=show_inv and not show_stats

                elif event.key == pygame.K_i and not game_over and not show_stats:
                    show_inv=not show_inv

                elif event.key == pygame.K_r and game_over:
                    seed = session.new_seed()
                    session.spell_memory_data = {}
                    session.skills_data       = {}
                    session.equipment_data    = {}
                    pygame.event.clear()   # flush R key so voc screen gets clean events
                    pygame.time.wait(80)
                    session.vocation          = voc_screen.run(screen, clock)
                    # Reset ALL game state
                    damage_numbers.clear(); item_drops.clear()
                    notifications.clear(); projectiles.clear()
                    explosions.clear(); dung_monsters.clear(); dung_boss=None
                    living_bots.clear(); _bot_respawn_queue.clear()
                    elapsed=0.0; game_over=False; show_inv=False; show_stats=False; _prev_warn=False
                    spectator_target=None; _portal_timer=3.0
                    (world,player,camera,spawner,storm,dungeons,boss_mgr,run,
                     biome_map,lvl_mgr,entrances,bots) = _new_game(session,seed)
                    living_bots[:] = list(bots)
                    go_stats.set_bots(bots)
                    storm_render=StormRenderer(SCREEN_W,GAME_H)
                    biome_ui=BiomeUI(SCREEN_W,GAME_H); current_biome="grassland"
                    camera.snap(player.x, player.y)
                    world.reveal_around(player.x, player.y)

                if game_over and event.key==pygame.K_LEFT:  go_stats.cycle_ranking(-1)
                if game_over and event.key==pygame.K_RIGHT: go_stats.cycle_ranking(1)
                if game_over and event.key==pygame.K_UP:    go_stats.scroll(-1)
                if game_over and event.key==pygame.K_DOWN:  go_stats.scroll(1)

                for ki,kv in enumerate([pygame.K_1,pygame.K_2,pygame.K_3,
                                        pygame.K_4,pygame.K_5,pygame.K_6,pygame.K_7]):
                    if event.key==kv and not game_over: player.select_spell_by_index(ki); break
                if event.key==pygame.K_q and not game_over: player.cycle_spell(-1)

                if event.key==pygame.K_e and not game_over and not show_inv:
                    if lvl_mgr.in_dungeon:
                        if lvl_mgr.try_exit(player):
                            dung_monsters.clear(); dung_boss=None
                            _push(notifications,"↑  De vuelta a la superficie",(150,220,150))
                    else:
                        if lvl_mgr.try_enter(player,biome_map):
                            dlvl=lvl_mgr.current_dungeon
                            dung_monsters=_spawn_dungeon_monsters(dlvl.dmap,player.level,dlvl.dmap.biome_name)
                            dung_boss=_spawn_dungeon_boss(dlvl.dmap,player.level)
                            dung_monsters.append(dung_boss)
                            _push(notifications,f"⬇  Mazmorra nivel {dlvl.dmap.dungeon_level}",(180,100,255))

                if event.key==pygame.K_f and not game_over and not show_inv and not show_stats:
                    for drop in item_drops:
                        if not drop.is_picked_up() and drop.near_player(player):
                            if player.inventory.pick_up(drop.item):
                                drop.pickup()
                                from systems.loot import RARITY
                                _push(notifications,f"Recogido: {drop.item['name']}",
                                      RARITY[drop.item['rarity']]['color'])
                            else: _push(notifications,"Bolsa llena!",C_ORANGE)
                            break

            if event.type == pygame.MOUSEBUTTONDOWN:
                active_monsters = dung_monsters if lvl_mgr.in_dungeon else spawner.monsters
                if event.button==1:
                    if show_inv and not show_stats:
                        msg=inv_ui.handle_click(mx,my,player.inventory)
                        if msg:
                            _push(notifications,msg,C_GREEN if "Equipped" in msg else C_ORANGE)
                            run.on_item_equipped_check(player.inventory.equipped_count())
                    elif not game_over and not show_stats:
                        wx,wy=camera.screen_to_world(mx,my)
                        hits=player.attack(wx,wy,active_monsters+bots)
                        for m,dmg in hits:
                            if isinstance(m, Bot):
                                run.on_melee_hit(dmg)
                                _add_dn(damage_numbers,m.x,m.y-24,dmg,(255,200,50))
                            else:
                                run.on_melee_hit(dmg)
                                _add_dn(damage_numbers,m.x,m.y-24,dmg,C_YELLOW)
                                if m.is_dead():
                                    _on_death(m,player,item_drops,damage_numbers,
                                              notifications,dungeons,boss_mgr,run,
                                              in_dungeon=lvl_mgr.in_dungeon)
                                    if lvl_mgr.in_dungeon:
                                        dung_monsters=[x for x in dung_monsters if not x.is_dead()]
                if event.button==3 and not game_over and not show_inv and not show_stats:
                    wx,wy=camera.screen_to_world(mx,my)
                    fire=player.cast_spell(wx,wy)
                    if fire:
                        for _lb in living_bots:
                            if not _lb.is_dead() and math.hypot(_lb.x-player.x,_lb.y-player.y)<500:
                                _lb.learn_player_spell()
                    if fire:
                        data=SPELL_CATALOGUE[fire['spell_id']]
                        run.on_spell_cast(fire['spell_id'],data.get('mp_cost',0))
                        projectiles.append(Projectile(fire['x'],fire['y'],fire['dx'],fire['dy'],
                                                       fire['spell_id'],fire['damage']))
                        _push(notifications,f"✦ {data['name']}",data['color'])

        if show_inv and not show_stats:
            inv_ui.update_hover(mx,my,player.inventory)

        # ── Logic ──────────────────────────────────────────────────────────
        if not game_over and not show_inv and not show_stats:
            elapsed += dt
            in_dungeon      = lvl_mgr.in_dungeon
            active_map      = lvl_mgr.active_map
            active_monsters = dung_monsters if in_dungeon else spawner.monsters

            current_biome = (lvl_mgr.current_dungeon.dmap.biome_name if in_dungeon
                             else biome_map.get_px(player.x,player.y,TILE_SIZE))
            bd = BIOMES[current_biome]
            biome_ui.update(dt, current_biome)
            if not in_dungeon and not game_over and elapsed>1.5:
                from systems.zones import get_zone,get_zone_name,get_zone_color
                _mcx=(MAP_W//2)*TILE_SIZE;_mcy=(MAP_H//2)*TILE_SIZE
                _mr=min(MAP_W,MAP_H)//2*TILE_SIZE
                _nz=get_zone(player.x,player.y,_mcx,_mcy,_mr)
                if not hasattr(run,"_last_zone"):run._last_zone=_nz
                if _nz!=run._last_zone:
                    run._last_zone=_nz
                    _push(notifications,f"Zona: {get_zone_name(_nz)}",get_zone_color(_nz))

            player.SPEED = Player.SPEED * bd["speed_mult"]
            keys = pygame.key.get_pressed()
            player.update(keys, dt, active_map)
            player.SPEED = Player.SPEED
            run.on_player_moved(player.x, player.y)
            if not in_dungeon:
                world.reveal_around(player.x, player.y)

            # Bots (surface only)
            if not in_dungeon:
                for bot in bots:
                    if bot.is_dead(): continue
                    # Perf: only full-update bots within 65 tiles of player
                    _bdx = abs(bot.x-player.x); _bdy = abs(bot.y-player.y)
                    if _bdx + _bdy > 65*TILE_SIZE:
                        # Distant bots: just drift toward safe zone
                        if storm.distance_outside(bot.x, bot.y) > 0:
                            _cx,_cy=storm.center_x,storm.center_y
                            _dist=max(1,((bot.x-_cx)**2+(bot.y-_cy)**2)**0.5)
                            bot.x+=(_cx-bot.x)/_dist*bot.SPEED*dt*0.5
                            bot.y+=(_cy-bot.y)/_dist*bot.SPEED*dt*0.5
                            bot.hp=max(0,bot.hp-storm.current_dps*dt)
                        continue
                    pdmg = bot.update(dt, player, active_monsters, world, storm)
                    if pdmg > 0:
                        run.on_damage_received(pdmg,"monster")
                        _add_dn(damage_numbers,player.x+random.randint(-12,12),
                                player.y-22,f"-{pdmg}",(255,100,100))
                # Newly dead bots → XP
                for bot in bots:
                    if bot.is_dead() and not getattr(bot,"_death_processed",False):
                        bot._death_processed = True
                        bot_xp = max(20, 10*(bot.level+1))
                        leveled = player.gain_xp(bot_xp)
                        _add_dn(damage_numbers,bot.x,bot.y-38,f"+{bot_xp} xp",C_GREEN)
                        if leveled:
                            _add_dn(damage_numbers,player.x,player.y-55,
                                    f"LEVEL {player.level}!",C_YELLOW)
                        _push(notifications,f"¡Rival eliminado! +{bot_xp} xp",(255,200,60))
                # Bot respawn: dead bots reappear after 30s with +1 level
                for bot in bots:
                    if bot.is_dead() and not getattr(bot,'_queued_respawn',False):
                        bot._queued_respawn = True
                        _bot_respawn_queue.append((elapsed+30.0, bot._bot_idx, bot.level+1))
                # Process respawn queue
                for entry in _bot_respawn_queue[:]:
                    resp_time, bidx, blevel = entry
                    if elapsed >= resp_time:
                        _bot_respawn_queue.remove(entry)
                        for _ in range(40):
                            col=random.randint(4,MAP_W-4); row=random.randint(4,MAP_H-4)
                            if not world.is_walkable(col,row): continue
                            if abs(col-int(player.x//TILE_SIZE))+abs(row-int(player.y//TILE_SIZE))<25: continue
                            nb=Bot(col*TILE_SIZE+TILE_SIZE//2,row*TILE_SIZE+TILE_SIZE//2,blevel,bidx)
                            bots.append(nb)
                            _push(notifications,"Un rival ha reaparecido",(220,100,60))
                            break
                living_bots[:] = [b for b in bots if not b.is_dead()]
                bots = living_bots

            if in_dungeon:
                dlvl=lvl_mgr.current_dungeon; dlvl.update(dt)
                dung_monsters=[m for m in dung_monsters if not m.is_dead()]
                for m in dung_monsters:
                    dmg,spell_ev=m.update(dt,player,active_map)
                    if dmg>0:
                        run.on_damage_received(dmg,"monster")
                        _add_dn(damage_numbers,player.x+random.randint(-12,12),player.y-22,f"-{dmg}",C_RED)
                    if spell_ev:
                        _sid=spell_ev['spell_id']
                        if _sid in SPELL_CATALOGUE:
                            learned=player.observe_spell(_sid,spell_ev['x'],spell_ev['y'])
                            if learned:
                                data=SPELL_CATALOGUE.get(_sid,{})
                                _push(notifications,f"¡Aprendiste: {data.get('name','?')}!",C_PURPLE)
                                run.on_spell_learned(_sid)
                            proj=Projectile(spell_ev['x'],spell_ev['y'],spell_ev['dx'],spell_ev['dy'],
                                            _sid,
                                            int(SPELL_CATALOGUE[_sid]['damage']*0.6),
                                            owner='monster')
                            projectiles.append(proj)
            else:
                new_boss=boss_mgr.update(dt,player.level,world,player)
                if new_boss:
                    spawner.add_monster(new_boss)
                    _push(notifications,f"☠  {new_boss.boss_display_name}  ha aparecido!",(255,120,40))
                damages,spell_events=spawner.update(dt,player,world)

                # ── Skill level-up floating notifications ──
                if getattr(player, "_skill_levelup", None):
                    _sk, _lv = player._skill_levelup
                    from systems.skills import SKILL_NAMES as _SN
                    notifications.append({
                        "text":  f"▲ {_SN.get(_sk, _sk)} sube a {_lv}!",
                        "color": (80, 200, 255),
                        "life":  3.5,
                        "y":     player.y - 64,
                        "x":     player.x,
                    })
                    player._skill_levelup = None

                for dmg in damages:
                    run.on_damage_received(dmg,"monster")
                    _add_dn(damage_numbers,player.x+random.randint(-12,12),player.y-22,f"-{dmg}",C_RED)
                for ev in spell_events:
                    _sid=ev['spell_id']
                    if _sid not in SPELL_CATALOGUE: continue
                    learned=player.observe_spell(_sid,ev['x'],ev['y'])
                    if learned:
                        data=SPELL_CATALOGUE.get(_sid,{})
                        _push(notifications,f"¡Aprendiste: {data.get('name','?')}!",C_PURPLE)
                        run.on_spell_learned(_sid)
                    proj=Projectile(ev['x'],ev['y'],ev['dx'],ev['dy'],_sid,
                                    int(SPELL_CATALOGUE[_sid]['damage']*0.6),owner='monster')
                    projectiles.append(proj)
                for ent in entrances: ent.update(dt)

            # Projectiles
            for proj in projectiles[:]:
                if proj.owner=='player':
                    _targets = list(active_monsters) + [b for b in living_bots if not b.is_dead()]
                    hits=proj.update(dt,_targets)
                    for m,dmg in hits:
                        run.on_spell_hit(proj.spell_id,dmg)
                        _add_dn(damage_numbers,m.x,m.y-26,f"✦{dmg}",
                                SPELL_CATALOGUE[proj.spell_id]['color'])
                        if m.is_dead():
                            if getattr(m,"_bot_idx",None) is not None:
                                if not getattr(m,"_death_processed",False):
                                    m._death_processed = True
                                    bot_xp = max(20, 10*(m.level+1))
                                    leveled = player.gain_xp(bot_xp)
                                    _add_dn(damage_numbers,m.x,m.y-38,f"+{bot_xp} xp",C_GREEN)
                                    if leveled:
                                        _add_dn(damage_numbers,player.x,player.y-55,
                                                f"LEVEL {player.level}!",C_YELLOW)
                                    _push(notifications,f"¡Rival eliminado! +{bot_xp} xp",(255,200,60))
                            else:
                                _on_death(m,player,item_drops,damage_numbers,
                                          notifications,dungeons,boss_mgr,run,in_dungeon=in_dungeon)
                            if in_dungeon:
                                dung_monsters=[x for x in dung_monsters if not x.is_dead()]
                    if not proj.is_alive() and proj.aoe_r>0:
                        explosions.append(Explosion(proj.x,proj.y,proj.aoe_r,proj.color))
                else:
                    proj.update(dt,[])
                    if not proj.is_alive(): continue
                    if math.hypot(proj.x-player.x,proj.y-player.y)<=player.SIZE+proj.radius:
                        actual=player.take_damage(proj.damage)
                        if actual:
                            run.on_damage_received(actual,"monster")
                            _add_dn(damage_numbers,player.x+random.randint(-10,10),
                                    player.y-28,f"-{actual}",(255,100,100))
                        proj.kill()
            projectiles=[p for p in projectiles if p.is_alive()]
            for ex in explosions: ex.update(dt)
            explosions=[e for e in explosions if e.is_alive()]

            # Biome effects
            in_dung_zone=in_any_dungeon(dungeons,player.x,player.y) if not in_dungeon else False
            if not in_dungeon:
                # Lava tiles deal periodic damage (like Tibia fire fields)
                lava_dmg=lava_damage(player.x,player.y,biome_map,TILE_SIZE,dt)
                if lava_dmg>0 and not in_dung_zone:
                    actual=max(1,int(lava_dmg*0.5)-player.defense//4)  # reduced, blockable
                    player.hp=max(0.0,player.hp-actual)
                    run.on_damage_received(actual,"lava")
                    _add_dn(damage_numbers,player.x,player.y-24,f"🔥-{actual}",(255,100,20))

            if not in_dungeon:
                in_storm_zone=not storm.player_inside(player.x,player.y)
                run.on_storm_tick(dt,in_storm_zone and not in_dung_zone)
                storm_dmg=storm.update(dt,player.x,player.y)
                if storm_dmg>0 and not in_dung_zone:
                    actual=max(1,int(storm_dmg)-player.defense//2)
                    player.hp=max(0.0,player.hp-actual)
                    run.on_damage_received(actual,"storm")
                    _add_dn(damage_numbers,player.x+random.randint(-8,8),
                            player.y-30,f"☁-{actual}",C_STORM_DANGER)
                if storm.close_warning and not _prev_warn:
                    _push(notifications,f"⚠ Tormenta cierra en {int(storm.timer)}s!",C_STORM_DANGER)
                    _prev_warn=True
                if not storm.close_warning: _prev_warn=False
                if in_dung_zone:
                    zone=in_any_dungeon(dungeons,player.x,player.y)
                    if zone: run.on_dungeon_entered(zone.zone_id)

            if player._block_flash>0: run.on_damage_blocked(player.defense or 5)
            for drop in item_drops: drop.update(dt)
            item_drops=[d for d in item_drops if not d.is_picked_up()]
            run.on_item_equipped_check(player.inventory.equipped_count())
            if game_over and spectator_target and not spectator_target.is_dead():
                camera.update(spectator_target.x, spectator_target.y, dt)
            else:
                camera.update(player.x,player.y,dt)
            # Winner logic: switch spectator target or announce end
            if game_over and not getattr(run,'_winner_announced',False):
                _alive_bots = [b for b in bots if not b.is_dead()]
                if not _alive_bots:
                    run._winner_announced = True
                    _push(notifications,'¡La tormenta acaba con todos!',(180,80,255))
                elif spectator_target and spectator_target.is_dead():
                    spectator_target = max(_alive_bots, key=lambda b: b.level)
            run.level_reached=player.level; run.storm_phase=storm.phase_reached

            if player.is_dead():
                if not game_over:
                    game_over=True; run.finalise(player,storm)
                    lifetime.register_run(run.to_dict())
                    session.save(player.level,elapsed,storm.phase_reached,
                             player.spell_memory,seed,player.skills,
                             player.inventory)
                    # Spectator: follow highest-level surviving bot
                    alive_bots=[b for b in bots if not b.is_dead()]
                    if alive_bots:
                        spectator_target=max(alive_bots,key=lambda b:b.level)
                    _push(notifications,"¡Has muerto! Observando al rival más fuerte…",(220,80,80))

        _upd_dn(damage_numbers,dt); _upd_notes(notifications,dt)

        # ── Draw ───────────────────────────────────────────────────────────
        screen.fill(C_BLACK)
        in_dungeon=lvl_mgr.in_dungeon

        if in_dungeon:
            dlvl=lvl_mgr.current_dungeon
            dung_renderer.draw(screen,camera,dlvl.dmap,player.x,player.y)
            dlvl.draw_overlay(screen,camera); biome_ui.draw(screen,current_biome)
            for drop in item_drops: drop.draw(screen,camera,player)
            for m in dung_monsters: m.draw(screen,camera)
            for ex in explosions: ex.draw(screen,camera)
            for proj in projectiles: proj.draw(screen,camera)
            player.draw(screen,camera)
        if _portal_timer > 0 and not game_over:
            _portal_timer = max(0.0, _portal_timer - dt)
            _pa = int(220 * (_portal_timer/3.0))
            _ps = pygame.Surface((80,80),pygame.SRCALPHA)
            _pr = int(24+10*math.sin(elapsed*8))
            pygame.draw.circle(_ps,(180,80,255,_pa),(40,40),_pr+10)
            pygame.draw.circle(_ps,(240,180,255,_pa//3),(40,40),_pr+18,4)
            _spx,_spy=camera.world_to_screen(player.x,player.y)
            screen.blit(_ps,(int(_spx)-40,int(_spy)-40))
            dlvl.draw_portals(screen,camera,player)
            dlvl.draw_hud_banner(screen,SCREEN_W)
        else:
            world.draw(screen,camera); biome_ui.draw(screen,current_biome)
            draw_dungeons(screen,camera,dungeons,player.x,player.y)
            for ent in entrances: ent.draw(screen,camera)
            for drop in item_drops: drop.draw(screen,camera,player)
            for m in spawner.monsters: m.draw(screen,camera)
            # Draw bots
            for bot in bots: bot.draw(screen,camera)
            for ex in explosions: ex.draw(screen,camera)
            for proj in projectiles: proj.draw(screen,camera)
            player.draw(screen,camera)
            if not game_over:
                storm_render.draw(screen,camera,storm,player.x,player.y)
            boss_mgr.draw_boss_bar(screen,SCREEN_W)
            if boss_mgr.announcement_active:
                boss_mgr.draw_announcement(screen,SCREEN_W,SCREEN_H)

        _drw_dn(screen,damage_numbers,camera,font_dn)
        _drw_notes(screen,notifications,font_note)

        spell_bar.draw(screen,player)
        hud.draw(screen,player,elapsed,
                 len(dung_monsters) if in_dungeon else len(spawner.monsters),storm)
        hud.draw_skills(screen,player)
        if not in_dungeon:
            hud.draw_zone_indicator(screen,player.x,player.y,MAP_W,MAP_H)
        hud.draw_biome_badge(screen,current_biome)
        hud.draw_minimap(screen,lvl_mgr.active_map,player,
                         dung_monsters if in_dungeon else spawner.monsters,
                         None if in_dungeon else storm,
                         bots=[] if in_dungeon else living_bots)

        if show_inv and not show_stats: inv_ui.draw(screen,player.inventory,player)
        if show_stats and not game_over: stats_overlay.draw(screen,run,elapsed,player)
        if game_over: go_stats.draw(screen,run,lifetime,player,storm)

        pygame.display.flip()


if __name__=="__main__":
    main()
