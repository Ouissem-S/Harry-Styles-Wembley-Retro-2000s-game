import json
import math
import os
import random

import pygame

from ribbon import Ribbon

ASSETS = os.path.join(os.path.dirname(__file__), "assets")

WIDTH, HEIGHT = 640, 360
SCALE = 2
FPS = 60

# Characters are drawn after the scene is scaled up, so this is window pixels per sprite pixel.
# 2 matches the scene's own pixel size, so Harry is 24x36 in scene pixels.
SPRITE_SCALE = 2
OUTFIT = "suit"
BPM = 120
# How far either side of Harry the dancers stand, along his runway.
DANCER_GAP = 30

# Anything above this line is roof, truss and screens, so the crowd effects leave it alone.
CROWD_TOP = 60
# The stage and its big screens on the left.
STAGE_RECT = pygame.Rect(0, 0, 235, 215)
# The people right in front of the camera, below the railing.
FRONT_ROW = [(0, 232), (330, 330), (330, 360), (0, 360)]

# Each move is a key sequence on the ribbon and the animation Harry plays when it's done.
# "frames" points into the outfit's sheets: (sheet, row, first column, number of frames).
# "repeat" plays the frames more than once, "hold" keeps the last frame up for a moment.
MOVES = {
    "Sashay": {"keys": ["A", "D", "A", "D", "SPACE"], "frames": ("dance", 0, 0, 8), "fps": 6},
    "Hop": {"keys": ["W", "W", "SPACE"], "frames": ("hop", "front", 0, 4), "fps": 8, "repeat": 2, "jump": 6},
    "Take a Bow": {"keys": ["S", "S", "SPACE"], "frames": ("emotes", 0, 0, 3), "fps": 4, "hold": 0.6},
    "Blow a Kiss": {"keys": ["W", "D", "SPACE"], "frames": ("emotes", 1, 0, 3), "fps": 4, "hold": 0.6},
    "Peace Sign": {"keys": ["A", "D", "SPACE"], "frames": ("emotes", 2, 0, 2), "fps": 4, "hold": 0.8},
    "Sing It": {"keys": ["S", "W", "SPACE"], "frames": ("main", "front", 0, 2), "fps": 4, "repeat": 3},
    "Open Arms": {"keys": ["A", "S", "D", "W", "SPACE"], "frames": ("sprint", "front", 0, 6), "fps": 12, "repeat": 2},
}

# How long the crowd jumps higher after Harry lands a move.
CHEER_TIME = 1.5


def load_json(name):
    with open(os.path.join(ASSETS, name)) as f:
        return json.load(f)


def cut_frames(sheet, frame_w, frame_h, scale):
    """Cut a sheet into rows of frames, scaled up."""
    rows = []
    for y in range(0, sheet.get_height(), frame_h):
        row = []
        for x in range(0, sheet.get_width(), frame_w):
            frame = sheet.subsurface((x, y, frame_w, frame_h))
            row.append(pygame.transform.scale(frame, (frame_w * scale, frame_h * scale)))
        rows.append(row)
    return rows


def load_sheet(name, sprites):
    sheet = pygame.image.load(os.path.join(ASSETS, name)).convert_alpha()
    return cut_frames(sheet, sprites["frame_w"], sprites["frame_h"], SPRITE_SCALE)


def runway_centre(walk_mask, x, near_y):
    """The middle of the runway at column x, picking the strip closest to near_y."""
    best = None
    y = 0
    while y < HEIGHT:
        if walk_mask.get_at((x, y))[0] > 128:
            top = y
            while y < HEIGHT and walk_mask.get_at((x, y))[0] > 128:
                y += 1
            centre = (top + y - 1) / 2
            if best is None or abs(centre - near_y) < abs(best - near_y):
                best = centre
        y += 1
    return round(best)


def runway_cover(walk_mask, grow):
    # White wherever the runway is, grown a few pixels so the crowd never wobbles over its edges.
    walk_mask = walk_mask.copy()
    walk_mask.set_colorkey((0, 0, 0))
    cover = pygame.Surface(walk_mask.get_size())
    for dx in range(-grow, grow + 1):
        for dy in range(-grow, grow + 1):
            cover.blit(walk_mask, (dx, dy))
    return cover


def crowd_layers(background, cover):
    """Split the crowd into the front row and the floor, each as a surface with everything else keyed out."""
    blocked = pygame.Surface((WIDTH, HEIGHT))
    blocked.fill((0, 0, 0))
    blocked.blit(cover, (0, 0))
    blocked.fill((255, 255, 255), STAGE_RECT)
    blocked.fill((255, 255, 255), (0, 0, WIDTH, 180))

    front_shape = pygame.Surface((WIDTH, HEIGHT))
    front_shape.fill((255, 255, 255))
    pygame.draw.polygon(front_shape, (0, 0, 0), FRONT_ROW)

    front = background.copy()
    front_cut = front_shape.copy()
    front_cut.set_colorkey((0, 0, 0))
    front.blit(front_cut, (0, 0))
    front.set_colorkey((255, 255, 255))

    floor = background.copy()
    blocked.set_colorkey((0, 0, 0))
    floor.blit(blocked, (0, 0))
    inverse_front = pygame.Surface((WIDTH, HEIGHT))
    inverse_front.fill((0, 0, 0))
    pygame.draw.polygon(inverse_front, (255, 255, 255), FRONT_ROW)
    inverse_front.set_colorkey((0, 0, 0))
    floor.blit(inverse_front, (0, 0))
    floor.set_colorkey((255, 255, 255))

    return front, floor


def make_strips(layer, width, top):
    strips = []
    for x in range(0, WIDTH, width):
        strip = layer.subsurface((x, top, min(width, WIDTH - x), HEIGHT - top))
        strips.append((x, top, strip, random.uniform(0, math.tau)))
    return strips


def draw_bouncing(screen, strips, beat, height):
    for x, y, strip, phase in strips:
        # Everyone jumps on the beat, but not all at exactly the same moment.
        hop = abs(math.sin(beat * math.pi + phase * 0.25))
        screen.blit(strip, (x, y - round(hop * height)))


def pick_phone_lights(cover, count):
    lights = []
    while len(lights) < count:
        x = random.randrange(WIDTH)
        y = random.randrange(CROWD_TOP, HEIGHT)
        if STAGE_RECT.collidepoint(x, y) or cover.get_at((x, y))[0] > 0:
            continue
        colour = random.choice([(255, 255, 255), (255, 200, 255), (200, 220, 255), (255, 120, 220)])
        lights.append((x, y, colour, random.uniform(0, math.tau), random.uniform(1.5, 4.0)))
    return lights


def draw_phone_lights(screen, lights, t):
    for x, y, colour, phase, speed in lights:
        glow = math.sin(t * speed + phase)
        if glow < 0.3:
            continue
        sway = round(math.sin(t * 2 + phase) * 1.5)
        screen.set_at((x + sway, y), colour)
        if glow > 0.85:
            screen.set_at((x + sway, y - 1), colour)


BEAMS = [
    # (origin, colour, sweep centre, sweep width, speed)
    ((60, 70), (60, 20, 90), 0.9, 0.5, 0.7),
    ((140, 72), (80, 30, 110), 0.6, 0.6, 0.9),
    ((200, 90), (40, 40, 120), 0.4, 0.5, 1.1),
    ((330, 20), (70, 30, 100), 1.6, 0.6, 0.6),
    ((480, 25), (40, 50, 120), 2.0, 0.5, 0.8),
]


def draw_beams(screen, beams_surface, t):
    beams_surface.fill((0, 0, 0))
    for (ox, oy), colour, centre, width, speed in BEAMS:
        angle = centre + math.sin(t * speed) * width
        spread = 0.06
        # Longest and faintest first, so each beam is brightest near the light and fades out.
        for step in range(8, 0, -1):
            length = 50 * step
            fade = (9 - step) / 8
            shade = tuple(int(c * fade) for c in colour)
            left = (ox + math.cos(angle - spread) * length, oy + math.sin(angle - spread) * length)
            right = (ox + math.cos(angle + spread) * length, oy + math.sin(angle + spread) * length)
            pygame.draw.polygon(beams_surface, shade, [(ox, oy), left, right])
    screen.blit(beams_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


def make_spotlight(radius_x, radius_y):
    pool = pygame.Surface((radius_x * 2, radius_y * 2))
    pool.fill((0, 0, 0))
    for i in range(6, 0, -1):
        k = i / 6
        shade = int(70 * (1 - k) + 10)
        pygame.draw.ellipse(pool, (shade, shade - 5, shade), (radius_x * (1 - k), radius_y * (1 - k), radius_x * 2 * k, radius_y * 2 * k))
    return pool


def load_move_frames(outfit, sprites):
    sheets = {}
    moves = {}
    for name, move in MOVES.items():
        sheet_name, row, first, count = move["frames"]
        info = outfit[sheet_name]
        if sheet_name not in sheets:
            sheets[sheet_name] = load_sheet(info["file"], sprites)
        if isinstance(row, str):
            row = info["rows"].index(row)
        moves[name] = sheets[sheet_name][row][first:first + count]
    return moves


def move_pose(move, frames, elapsed):
    """The frame and jump height for a move `elapsed` seconds in, or None once it's over."""
    played = int(elapsed * move["fps"])
    total = len(frames) * move.get("repeat", 1)
    if played < total:
        index = played % len(frames)
        # The hop sheet only crouches and tucks, the lift itself happens here.
        jump = move.get("jump", 0) if index in (1, 2) else 0
        return frames[index], jump
    if elapsed < total / move["fps"] + move.get("hold", 0):
        return frames[-1], 0
    return None


def draw_character(window, frame, x, y, anchor_x, anchor_y):
    window.blit(frame, (x * SCALE - anchor_x * SPRITE_SCALE, y * SCALE - anchor_y * SPRITE_SCALE))


def main():
    pygame.init()
    pygame.display.set_caption("Harry Styles: Dance All the Time")
    window = pygame.display.set_mode((WIDTH * SCALE, HEIGHT * SCALE))
    screen = pygame.Surface((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    layout = load_json("layout_points.json")
    sprites = load_json("sprites2026.json")

    background = pygame.image.load(os.path.join(ASSETS, layout["image"])).convert()
    walk_mask = pygame.image.load(os.path.join(ASSETS, "walk_mask_640x360.png")).convert()
    outfit = sprites["outfits"][OUTFIT]
    harry_main = load_sheet(outfit["main"]["file"], sprites)
    harry_idle = harry_main[outfit["main"]["rows"].index("front")][0]
    dancers = load_sheet(sprites["dancers"]["file"], sprites)
    dancer_fps = sprites["dancers"]["fps"]
    move_frames = load_move_frames(outfit, sprites)

    ribbon = Ribbon(MOVES, WIDTH, HEIGHT)
    current_move = None
    move_started = 0
    cheer_until = 0

    cover = runway_cover(walk_mask, 3)
    front, floor = crowd_layers(background, cover)
    front_strips = make_strips(front, 40, 225)
    floor_strips = make_strips(floor, 6, 180)
    phone_lights = pick_phone_lights(cover, 350)

    beams_surface = pygame.Surface((WIDTH, HEIGHT))
    spotlight = make_spotlight(20, 6)
    shadow = pygame.Surface((16, 4), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 120), shadow.get_rect())

    # Harry starts facing the crowd, standing where the runways cross,
    # with dancer A on the left of the screen and dancer B on the right.
    harry_x, harry_y = layout["intersection"]
    harry_x, harry_y = round(harry_x), round(harry_y)
    dancer_spots = []
    for x in (harry_x - DANCER_GAP, harry_x + DANCER_GAP):
        dancer_spots.append((x, runway_centre(walk_mask, x, harry_y)))
    anchor_x, anchor_y = sprites["anchor"]

    running = True
    while running:
        t = pygame.time.get_ticks() / 1000
        beat = t * BPM / 60
        dance_frame = int(t * dancer_fps) % len(dancers[0])

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.KEYDOWN:
                done = ribbon.press(event.key, t)
                if done:
                    current_move = done
                    move_started = t
                    cheer_until = t + CHEER_TIME

        harry_frame, harry_jump = harry_idle, 0
        if current_move:
            pose = move_pose(MOVES[current_move], move_frames[current_move], t - move_started)
            if pose:
                harry_frame, harry_jump = pose
            else:
                current_move = None

        cheering = t < cheer_until

        screen.blit(background, (0, 0))
        draw_bouncing(screen, floor_strips, beat, 3 if cheering else 1)
        draw_phone_lights(screen, phone_lights, t)
        draw_beams(screen, beams_surface, t)

        draw_bouncing(screen, front_strips, beat, 6 if cheering else 3)

        for x, y in [(harry_x, harry_y)] + dancer_spots:
            screen.blit(spotlight, (x - spotlight.get_width() // 2, y - spotlight.get_height() // 2), special_flags=pygame.BLEND_RGB_ADD)
            screen.blit(shadow, (x - shadow.get_width() // 2, y - shadow.get_height() // 2))

        ribbon.draw(screen, t)

        pygame.transform.scale(screen, window.get_size(), window)

        # Characters go straight onto the window so their pixels stay whole at SPRITE_SCALE.
        for row, (x, y) in zip(dancers, dancer_spots):
            draw_character(window, row[dance_frame], x, y, anchor_x, anchor_y)
        draw_character(window, harry_frame, harry_x, harry_y - harry_jump, anchor_x, anchor_y)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
