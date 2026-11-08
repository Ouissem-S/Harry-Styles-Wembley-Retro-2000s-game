import os

import pygame

FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "PixelifySans-Bold.ttf")
OUTLINE = (26, 11, 38)

_fonts = {}
_cache = {}


def font(size):
    if size not in _fonts:
        try:
            _fonts[size] = pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError):
            _fonts[size] = pygame.font.Font(None, round(size * 1.3))
    return _fonts[size]


def render(text, size, colour, outline=True):
    """Text with no anti-aliasing, so every pixel is fully on or off, with a 1-pixel dark outline."""
    key = (text, size, colour, outline)
    if key not in _cache:
        f = font(size)
        glyphs = f.render(text, False, pygame.Color(colour)).convert_alpha()
        if not outline:
            _cache[key] = glyphs
        else:
            shade = f.render(text, False, OUTLINE).convert_alpha()
            out = pygame.Surface((glyphs.get_width() + 2, glyphs.get_height() + 2), pygame.SRCALPHA)
            for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2), (2, 2)):
                out.blit(shade, (dx, dy))
            out.blit(glyphs, (1, 1))
            _cache[key] = out
    return _cache[key]


def draw(screen, text, x, y, size, colour, align="center", outline=True):
    surf = render(text, size, colour, outline)
    if align == "center":
        x -= surf.get_width() / 2
    elif align == "right":
        x -= surf.get_width()
    screen.blit(surf, (round(x), round(y)))
    return surf.get_rect(topleft=(round(x), round(y)))
