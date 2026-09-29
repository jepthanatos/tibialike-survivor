"""
ui/tibia_sprites.py
═══════════════════════════════════════════════════════════════
Funciones de dibujo de sprites.

Para cada entidad intenta primero cargar la imagen configurada
en sprites.json. Si no hay imagen (o falla la carga) dibuja el
sprite procedural equivalente.

Uso externo:
    from ui.tibia_sprites import draw_monster, draw_player_sprite
"""
from __future__ import annotations
import pygame
import math

from core.sprite_loader import sprites

SKIN   = (255, 215, 168)
SKIN_D = (220, 175, 125)


# ── Helper: draw image or fall through to callable ────────────────────────────

def _draw_image_or(screen, sx: int, sy: int,
                   section: str, key: str,
                   width: int, height: int,
                   fallback_fn, *args, **kwargs) -> bool:
    """
    Intenta dibujar la imagen (section, key) escalada a (width, height).
    La imagen se centra horizontalmente en sx y sus pies quedan en sy.
    Si no hay imagen llama fallback_fn(screen, sx, sy, *args, **kwargs).
    Devuelve True si se usó imagen, False si se usó el procedural.
    """
    img = sprites.get(section, key, width, height)
    if img is not None:
        ix = sx - img.get_width() // 2
        iy = sy - img.get_height()
        screen.blit(img, (ix, iy))
        return True
    fallback_fn(screen, sx, sy, *args, **kwargs)
    return False


# ── Public draw functions ─────────────────────────────────────────────────────

def draw_player_sprite(screen, sx: int, sy: int, outfit_idx: int,
                       outfit: tuple, legs: tuple, hair: tuple,
                       direction: float = 0.0,
                       hit_flash: bool = False,
                       bob: int = 0):
    """Draws the player sprite. Checks sprites.json[player][outfit_N] first."""
    key = f"outfit_{outfit_idx}"
    _draw_image_or(
        screen, sx, sy + bob,
        "player", key,
        32, 48,
        draw_humanoid,
        outfit, legs, hair,
        direction=direction, hit_flash=hit_flash,
    )


def draw_bot_sprite(screen, sx: int, sy: int, bot_idx: int,
                    outfit: tuple, legs: tuple, hair: tuple,
                    direction: float = 0.0,
                    hit_flash: bool = False):
    """Draws a bot sprite. Checks sprites.json[bots][bot_N] first."""
    key = f"bot_{bot_idx}"
    _draw_image_or(
        screen, sx, sy,
        "bots", key,
        32, 48,
        draw_humanoid,
        outfit, legs, hair,
        direction=direction, hit_flash=hit_flash, size_scale=0.95,
    )


def draw_monster(screen, sx: int, sy: int, mtype: str,
                 col: tuple, hit_flash: bool = False,
                 size: int = 0):
    """
    Draws a monster. Checks sprites.json[monsters][mtype] first.
    Falls back to the appropriate procedural sprite.
    """
    # Sprite dimensions per type (approximate in-game display size)
    _dims = {
        "rat":         (28, 18),
        "zombie":      (28, 44),
        "skeleton":    (26, 44),
        "orc":         (28, 48),
        "dark_wizard": (24, 52),
        "dragon":      (60, 36),
        "demon":       (60, 64),
        "dragon_lord": (72, 52),
    }
    w, h = _dims.get(mtype, (32, 44))

    # Pick fallback function
    _fallbacks = {
        "rat":         _proc_rat,
        "zombie":      _proc_zombie,
        "skeleton":    _proc_skeleton,
        "orc":         _proc_orc,
        "dark_wizard": _proc_wizard,
        "dragon":      _proc_dragon,
        "demon":       _proc_demon,
        "dragon_lord": _proc_dragon_lord,
    }
    fb = _fallbacks.get(mtype, _proc_skeleton)

    img = sprites.get("monsters", mtype, w, h)
    if img is not None:
        screen.blit(img, (sx - img.get_width()//2, sy - img.get_height()))
    else:
        if mtype == "dragon":
            fb(screen, sx, sy, col, hit_flash, size=size or 20)
        elif mtype == "dragon_lord":
            fb(screen, sx, sy, col, hit_flash)
        else:
            fb(screen, sx, sy, col, hit_flash)


# ── Procedural sprites ────────────────────────────────────────────────────────

def draw_humanoid(screen, sx: int, sy: int,
                  outfit: tuple, legs: tuple, hair: tuple,
                  direction: float = 0.0,
                  hit_flash: bool = False,
                  size_scale: float = 1.0,
                  eye_color: tuple = (50, 30, 10),
                  skin: tuple = SKIN):
    s = size_scale
    col = (255, 255, 255) if hit_flash else outfit

    # Shadow
    shadow = pygame.Surface((int(26*s)+2, int(8*s)+2), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 55), (0, 0, int(26*s), int(8*s)))
    screen.blit(shadow, (int(sx - 13*s), int(sy - 4*s)))

    # Shoes
    shoe = (55, 38, 18)
    pygame.draw.rect(screen, shoe,  (int(sx-8*s), int(sy-5*s), int(7*s), int(5*s)))
    pygame.draw.rect(screen, shoe,  (int(sx+1*s), int(sy-5*s), int(7*s), int(5*s)))

    # Legs
    lc = legs if not hit_flash else (255, 255, 255)
    pygame.draw.rect(screen, lc, (int(sx-7*s), int(sy-14*s), int(6*s), int(10*s)))
    pygame.draw.rect(screen, lc, (int(sx+1*s), int(sy-14*s), int(6*s), int(10*s)))

    # Belt
    belt = tuple(max(0, c-40) for c in col)
    pygame.draw.rect(screen, belt, (int(sx-8*s), int(sy-16*s), int(16*s), int(3*s)))

    # Torso
    pygame.draw.rect(screen, col, (int(sx-8*s), int(sy-28*s), int(16*s), int(13*s)))

    # Arms
    pygame.draw.rect(screen, col, (int(sx-12*s), int(sy-27*s), int(5*s), int(10*s)))
    pygame.draw.rect(screen, col, (int(sx+7*s),  int(sy-27*s), int(5*s), int(10*s)))

    # Hands
    pygame.draw.circle(screen, skin, (int(sx-9*s), int(sy-18*s)), max(1, int(3*s)))
    pygame.draw.circle(screen, skin, (int(sx+9*s), int(sy-18*s)), max(1, int(3*s)))

    # Neck
    pygame.draw.rect(screen, skin, (int(sx-3*s), int(sy-31*s), int(6*s), int(4*s)))

    # Head
    hr = max(1, int(9*s))
    pygame.draw.circle(screen, skin, (int(sx), int(sy-39*s)), hr)

    # Hair
    hc = hair if not hit_flash else (255, 255, 255)
    pygame.draw.arc(screen, hc,
                    (int(sx-9*s), int(sy-49*s), int(18*s), int(14*s)),
                    0.05, math.pi-0.05, max(1, int(5*s)))

    # Eyes
    eo = int(math.cos(direction) * 3 * s)
    pygame.draw.circle(screen, eye_color, (int(sx+eo-3*s), int(sy-39*s)), max(1, int(2*s)))
    pygame.draw.circle(screen, eye_color, (int(sx+eo+3*s), int(sy-39*s)), max(1, int(2*s)))


def _proc_rat(screen, sx, sy, col, hit_flash=False):
    c    = (255, 255, 255) if hit_flash else col
    dark = tuple(max(0, x-30) for x in col)
    pygame.draw.ellipse(screen, dark, (sx-13, sy-7, 26, 16))
    pygame.draw.ellipse(screen, c,    (sx-12, sy-6, 24, 14))
    pygame.draw.ellipse(screen, c,    (sx+6, sy-10, 14, 12))
    pygame.draw.ellipse(screen, dark, (sx+7, sy-11, 12, 10))
    pygame.draw.ellipse(screen, (200, 140, 140), (sx+12, sy-16, 5, 7))
    pygame.draw.ellipse(screen, (200, 140, 140), (sx+16, sy-15, 5, 7))
    pygame.draw.circle(screen, (20, 20, 20), (sx+16, sy-8), 2)
    pygame.draw.arc(screen, dark, (sx-18, sy-4, 14, 12), 0, math.pi, 2)
    for dx in (-8, -2, 4, 10):
        pygame.draw.line(screen, dark, (sx+dx, sy+7), (sx+dx-2, sy+12), 2)


def _proc_zombie(screen, sx, sy, col, hit_flash=False):
    skin_zombie = (140, 180, 120)
    direction = 0.0
    if hasattr(screen, '_zombie_dir'):
        direction = screen._zombie_dir
    draw_humanoid(screen, sx, sy,
                  (58, 132, 58), (30, 90, 30), (40, 80, 30),
                  direction=direction,
                  hit_flash=hit_flash,
                  size_scale=0.85,
                  eye_color=(20, 60, 20),
                  skin=skin_zombie)


def _proc_skeleton(screen, sx, sy, col, hit_flash=False):
    c    = (255, 255, 255) if hit_flash else col
    dark = tuple(max(0, x-40) for x in col)
    pygame.draw.rect(screen, dark, (sx-6, sy-14, 4, 12))
    pygame.draw.rect(screen, c,    (sx-5, sy-13, 3, 10))
    pygame.draw.rect(screen, dark, (sx+2, sy-14, 4, 12))
    pygame.draw.rect(screen, c,    (sx+3, sy-13, 3, 10))
    pygame.draw.rect(screen, c, (sx-7, sy-17, 14, 4))
    for x in (sx-5, sx, sx+5):
        pygame.draw.line(screen, dark, (x, sy-17), (x, sy-14), 1)
    pygame.draw.rect(screen, c, (sx-7, sy-30, 14, 14))
    for y in (sy-28, sy-24, sy-20):
        pygame.draw.line(screen, dark, (sx-6, y), (sx+6, y), 1)
    pygame.draw.line(screen, c, (sx-8, sy-29), (sx-10, sy-20), 3)
    pygame.draw.line(screen, c, (sx+8, sy-29), (sx+10, sy-20), 3)
    pygame.draw.circle(screen, c, (sx, sy-37), 9)
    pygame.draw.circle(screen, dark, (sx-3, sy-37), 2)
    pygame.draw.circle(screen, dark, (sx+3, sy-37), 2)
    pygame.draw.rect(screen, c, (sx-4, sy-30, 8, 4))
    for tx in (sx-3, sx, sx+3):
        pygame.draw.line(screen, dark, (tx, sy-30), (tx, sy-28), 1)


def _proc_orc(screen, sx, sy, col, hit_flash=False):
    c    = (255, 255, 255) if hit_flash else col
    dark = tuple(max(0, x-35) for x in col)
    skin_orc = (80, 140, 60)
    pygame.draw.rect(screen, dark, (sx-9, sy-16, 7, 13))
    pygame.draw.rect(screen, c,    (sx-8, sy-15, 6, 11))
    pygame.draw.rect(screen, dark, (sx+2, sy-16, 7, 13))
    pygame.draw.rect(screen, c,    (sx+3, sy-15, 6, 11))
    pygame.draw.rect(screen, dark, (sx-11, sy-31, 22, 16))
    pygame.draw.rect(screen, c,    (sx-10, sy-30, 20, 14))
    pygame.draw.rect(screen, c, (sx-15, sy-30, 5, 12))
    pygame.draw.rect(screen, c, (sx+10, sy-30, 5, 12))
    pygame.draw.ellipse(screen, dark, (sx-10, sy-45, 20, 18))
    pygame.draw.ellipse(screen, skin_orc if not hit_flash else c, (sx-9, sy-44, 18, 16))
    pygame.draw.line(screen, (220, 210, 180), (sx-4, sy-31), (sx-6, sy-26), 2)
    pygame.draw.line(screen, (220, 210, 180), (sx+4, sy-31), (sx+6, sy-26), 2)
    pygame.draw.circle(screen, (200, 40, 20), (sx-4, sy-39), 3)
    pygame.draw.circle(screen, (200, 40, 20), (sx+4, sy-39), 3)


def _proc_wizard(screen, sx, sy, col, hit_flash=False):
    c    = (255, 255, 255) if hit_flash else col
    dark = tuple(max(0, x-40) for x in col)
    pygame.draw.polygon(screen, dark, [(sx, sy-32), (sx-11, sy), (sx+11, sy)])
    pygame.draw.polygon(screen, c,    [(sx, sy-31), (sx-10, sy-1), (sx+10, sy-1)])
    pygame.draw.polygon(screen, dark, [(sx, sy-52), (sx-8, sy-34), (sx+8, sy-34)])
    pygame.draw.polygon(screen, c,    [(sx, sy-51), (sx-7, sy-33), (sx+7, sy-33)])
    pygame.draw.circle(screen, SKIN if not hit_flash else c, (sx, sy-38), 7)
    pygame.draw.circle(screen, (220, 100, 255), (sx-3, sy-39), 3)
    pygame.draw.circle(screen, (220, 100, 255), (sx+3, sy-39), 3)
    pygame.draw.circle(screen, (255, 200, 255), (sx-3, sy-39), 1)
    pygame.draw.circle(screen, (255, 200, 255), (sx+3, sy-39), 1)
    pygame.draw.line(screen, (100, 60, 140), (sx+9, sy-30), (sx+13, sy+2), 3)
    pygame.draw.circle(screen, (200, 100, 255), (sx+13, sy-30), 5)
    pygame.draw.circle(screen, (255, 180, 255), (sx+13, sy-30), 3)


def _proc_dragon(screen, sx, sy, col, hit_flash=False, size=20):
    c    = (255, 255, 255) if hit_flash else col
    dark = tuple(max(0, x-40) for x in col)
    s    = size / 20
    pygame.draw.ellipse(screen, dark, (int(sx-14*s), int(sy-12*s), int(28*s), int(18*s)))
    pygame.draw.ellipse(screen, c,    (int(sx-13*s), int(sy-11*s), int(26*s), int(16*s)))
    wc = tuple(max(0, x-50) for x in col)
    pygame.draw.polygon(screen, wc, [(int(sx-14*s),int(sy-8*s)),(int(sx-28*s),int(sy-24*s)),(int(sx-10*s),int(sy-2*s))])
    pygame.draw.polygon(screen, wc, [(int(sx+14*s),int(sy-8*s)),(int(sx+28*s),int(sy-24*s)),(int(sx+10*s),int(sy-2*s))])
    pygame.draw.ellipse(screen, dark, (int(sx+8*s), int(sy-18*s), int(18*s), int(14*s)))
    pygame.draw.ellipse(screen, c,    (int(sx+9*s), int(sy-17*s), int(16*s), int(12*s)))
    hc = tuple(min(255, x+40) for x in col)
    pygame.draw.line(screen, hc, (int(sx+12*s),int(sy-17*s)),(int(sx+9*s),int(sy-26*s)), max(1,int(2*s)))
    pygame.draw.line(screen, hc, (int(sx+20*s),int(sy-17*s)),(int(sx+23*s),int(sy-26*s)),max(1,int(2*s)))
    pygame.draw.circle(screen,(255,180,20),(int(sx+14*s),int(sy-13*s)),max(1,int(3*s)))
    pygame.draw.circle(screen,(255,80,10), (int(sx+14*s),int(sy-13*s)),max(1,int(2*s)))
    pygame.draw.arc(screen,dark,(int(sx-22*s),int(sy-8*s),int(16*s),int(14*s)),0,math.pi,max(1,int(3*s)))
    for dx in (-8, 4):
        pygame.draw.line(screen,dark,(int(sx+dx*s),int(sy+5*s)),(int(sx+(dx-2)*s),int(sy+12*s)),max(1,int(2*s)))


def _proc_demon(screen, sx, sy, col, hit_flash=False):
    c    = (255, 255, 255) if hit_flash else col
    dark = tuple(max(0, x-40) for x in col)
    wc   = tuple(max(0, x-60) for x in col)
    pygame.draw.polygon(screen, wc, [(sx-10,sy-20),(sx-30,sy-42),(sx-8,sy-5)])
    pygame.draw.polygon(screen, wc, [(sx+10,sy-20),(sx+30,sy-42),(sx+8,sy-5)])
    pygame.draw.rect(screen, dark, (sx-8,sy-16,6,13)); pygame.draw.rect(screen,c,(sx-7,sy-15,5,11))
    pygame.draw.rect(screen, dark, (sx+2,sy-16,6,13)); pygame.draw.rect(screen,c,(sx+3,sy-15,5,11))
    pygame.draw.rect(screen, dark, (sx-10,sy-30,20,16)); pygame.draw.rect(screen,c,(sx-9,sy-29,18,14))
    pygame.draw.rect(screen, c, (sx-14,sy-29,5,12)); pygame.draw.rect(screen,c,(sx+9,sy-29,5,12))
    pygame.draw.circle(screen,dark,(sx,sy-38),11); pygame.draw.circle(screen,c,(sx,sy-38),9)
    hc = (180,30,30)
    pygame.draw.polygon(screen,hc,[(sx-6,sy-46),(sx-12,sy-62),(sx-2,sy-46)])
    pygame.draw.polygon(screen,hc,[(sx+6,sy-46),(sx+12,sy-62),(sx+2,sy-46)])
    pygame.draw.circle(screen,(255,80,30),(sx-4,sy-40),3); pygame.draw.circle(screen,(255,200,50),(sx-4,sy-40),1)
    pygame.draw.circle(screen,(255,80,30),(sx+4,sy-40),3); pygame.draw.circle(screen,(255,200,50),(sx+4,sy-40),1)


def _proc_dragon_lord(screen, sx, sy, col, hit_flash=False):
    c = (255, 255, 255) if hit_flash else col
    aura = pygame.Surface((70, 70), pygame.SRCALPHA)
    pygame.draw.circle(aura, (*col, 30), (35, 35), 32)
    screen.blit(aura, (sx-35, sy-50))
    _proc_dragon(screen, sx, sy, col, hit_flash, size=24)
    spike_c = (200, 150, 220)
    for angle in range(-60, 70, 30):
        a  = math.radians(angle - 90)
        ex = int(sx + 28 + math.cos(a) * 14)
        ey = int(sy - 16 + math.sin(a) * 14)
        pygame.draw.line(screen, spike_c, (int(sx+28), int(sy-16)), (ex, ey), 2)
