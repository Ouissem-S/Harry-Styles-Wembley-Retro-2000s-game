import json
import math
import os
import random
import sys

import numpy as np
import pygame

import music
import pixeltext as text
from rhythm import POSE, Rhythm
from screens import Screens

ASSETS = os.path.join(os.path.dirname(__file__), "assets")

WIDTH, HEIGHT = 640, 360
FPS = 60
FRAME_W, FRAME_H = 24, 36
# Sprites are drawn so this pixel of the frame lands on the character's feet.
ANCHOR_X, ANCHOR_Y = 12, 35

ROWS = {"back": 0, "front": 1, "left": 2, "right": 3}
DIRECTIONS = {"back": (0, -1), "front": (0, 1), "left": (-1, 0), "right": (1, 0)}
NIGHT = "#0c0818"
PALETTE = ["#ee627e", "#f79454", "#fcce4a", "#7a90da", "#42b88a", "#ffffff", "#ff5ccf", "#46e0ff"]

WALK_SPEED = 44
RUN_SPEED = {"suit": 82, "shirtsleeves": 92}
HOP_SPEED = 28
# The floor is seen at an angle, so moving up or down the screen covers less ground.
PERSPECTIVE = 0.75
# The walkways are diagonal on screen, so if a step would leave them, try turning it a little at a time.
SLIDE_ANGLES = [0, 0.35, -0.35, 0.7, -0.7, 1.05, -1.05, 1.4, -1.4, 1.57, -1.57]
# How far the dancers stand either side of Harry.
DANCER_GAP = 19

# One-shot actions: how long they last and which frames they step through.
ACTIONS = {
    "hop": {"dur": 0.5, "sheet": "hop"},
    "bow": {"dur": 1.3, "sheet": "emotes", "row": 0, "seq": [0, 1, 2, 2, 2, 1, 0]},
    "kiss": {"dur": 1.0, "sheet": "emotes", "row": 1, "seq": [0, 0, 1, 2, 2]},
    "peace": {"dur": 1.2, "sheet": "emotes", "row": 2, "seq": [0, 1, 0, 1]},
    "water": {"dur": 1.1, "sheet": "main", "row": 1, "seq": [1, 1, 0, 0]},
    "wave": {"dur": 0.9},
}
ACTION_NAMES = {"hop": "Hop", "bow": "Bow", "kiss": "Blow a kiss", "peace": "Peace sign", "water": "Water spray", "wave": "Wave"}

SHADOW = (20, 8, 40, 140)
# How long a message such as "Jacket off" stays up at the top of the stage.
MESSAGE_TIME = 3.0
KEY_HINTS = "ARROWS WALK  SHIFT RUN  F DANCE  H HOP  B BOW  K KISS  P PEACE  Q WATER  SPACE WAVE  J JACKET  R CENTRE  ESC MENU"
HEART = [(1, 0), (3, 0), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (1, 2), (2, 2), (3, 2), (2, 3)]

MOVE_KEYS = {
    "left": (pygame.K_LEFT, pygame.K_a), "right": (pygame.K_RIGHT, pygame.K_d),
    "up": (pygame.K_UP, pygame.K_w), "down": (pygame.K_DOWN, pygame.K_s),
}
LANE_KEYS = {pygame.K_LEFT: 0, pygame.K_a: 0, pygame.K_DOWN: 1, pygame.K_s: 1,
             pygame.K_UP: 2, pygame.K_w: 2, pygame.K_RIGHT: 3, pygame.K_d: 3}
ACTION_KEYS = {pygame.K_h: "hop", pygame.K_b: "bow", pygame.K_k: "kiss", pygame.K_p: "peace",
               pygame.K_q: "water", pygame.K_SPACE: "wave"}
SONG_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_KP1: 0, pygame.K_KP2: 1, pygame.K_KP3: 2}


def load_json(name):
    with open(os.path.join(ASSETS, name)) as f:
        return json.load(f)


def load_sheet(name):
    """Cut a sheet into rows of 24x36 frames."""
    sheet = pygame.image.load(os.path.join(ASSETS, name)).convert_alpha()
    return [[sheet.subsurface((x, y, FRAME_W, FRAME_H)) for x in range(0, sheet.get_width(), FRAME_W)]
            for y in range(0, sheet.get_height(), FRAME_H)]


def make_glow(radius, colour):
    """A soft round spotlight, added on top of the stage."""
    size = 104
    xs, ys = np.meshgrid(np.arange(size) + 0.5 - size / 2, np.arange(size) + 0.5 - size / 2, indexing="ij")
    fade = 1 - np.clip((np.hypot(xs, ys) - 1) / (radius - 1), 0, 1)
    pixels = np.stack([fade * c * 0.35 for c in colour], axis=-1)
    return pygame.surfarray.make_surface(pixels.round().astype(np.uint8))


def make_shadow(half):
    shadow = pygame.Surface((half * 2, 3), pygame.SRCALPHA)
    shadow.fill(SHADOW, (0, 0, half * 2, 2))
    shadow.fill(SHADOW, (2, 2, half * 2 - 4, 1))
    return shadow


def js_round(v):
    # Round halves up, like the reference, rather than to the nearest even number.
    return math.floor(v + 0.5)


class Harry:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.dir = "back"
        self.t = 0.0
        self.moving = False
        self.running = False
        self.outfit = "suit"
        self.act = None
        self.act_t = 0.0
        self.dancing = False
        self.dance_start = 0.0


class Game:
    def __init__(self, reduced_motion):
        layout = load_json("layout_points.json")
        sprites = load_json("sprites2026.json")
        self.start = tuple(js_round(v) for v in layout["intersection"])
        self.background = pygame.image.load(os.path.join(ASSETS, layout["image"])).convert()
        mask = pygame.image.load(os.path.join(ASSETS, "walk_mask_640x360.png")).convert()
        # Indexed [x, y]: True where Harry can stand.
        self.walk = pygame.surfarray.array3d(mask)[:, :, 0] > 127

        self.sheets = {}
        for outfit, info in sprites["outfits"].items():
            self.sheets[outfit] = {name: load_sheet(sheet["file"]) for name, sheet in info.items()}
        self.dancers = load_sheet(sprites["dancers"]["file"])

        self.glow = make_glow(34, (255, 150, 230))
        self.dance_glow = make_glow(48, (255, 170, 90))
        self.shadows = {half: make_shadow(half) for half in (5, 6, 7)}

        self.twinkles = [] if reduced_motion else self.pick_twinkles()
        self.particles = []
        self.harry = Harry(*self.start)
        self.status = ""
        self.status_t = 0.0
        self.rhythm = None
        self.hint_bar = pygame.Surface((WIDTH, 14))
        self.hint_bar.fill(NIGHT)
        self.hint_bar.set_alpha(190)

    def pick_twinkles(self):
        colours = pygame.surfarray.array3d(self.background).astype(int)
        bright = colours.sum(axis=2) > 520
        bright[:, :150] = False
        bright &= ~self.walk
        xs, ys = np.nonzero(bright & (np.random.random(bright.shape) < 0.35))
        n = len(xs)
        return {
            "x": xs, "y": ys,
            "speed": 1.5 + np.random.random(n) * 4,
            "phase": np.random.random(n) * 6.3,
            "colour": [pygame.Color(PALETTE[i]) for i in np.random.randint(len(PALETTE), size=n)],
        }

    def say(self, message):
        self.status = message
        self.status_t = MESSAGE_TIME if message else 0.0

    # ---------- walking ----------

    def can_stand(self, x, y):
        xi, yi = js_round(x), js_round(y)
        return 0 <= xi < WIDTH and 0 <= yi < HEIGHT and self.walk[xi, yi]

    def nearest_stand(self, x, y):
        if self.can_stand(x, y):
            return x, y
        for r in range(1, 14):
            for a in range(16):
                nx = x + math.cos(a / 16 * 6.283) * r
                ny = y + math.sin(a / 16 * 6.283) * r * 0.6
                if self.can_stand(nx, ny):
                    return nx, ny
        return x, y

    def step(self, mx, my):
        h = self.harry
        for a in SLIDE_ANGLES:
            rx = mx * math.cos(a) - my * math.sin(a)
            ry = mx * math.sin(a) + my * math.cos(a)
            if self.can_stand(h.x + rx, h.y + ry):
                h.x += rx
                h.y += ry
                return True
        return False

    # ---------- particles ----------

    def confetti(self, n, x, y):
        for _ in range(n):
            self.particles.append({
                "kind": "confetti", "x": x + (random.random() - 0.5) * 30, "y": y - 30 - random.random() * 20,
                "vx": (random.random() - 0.5) * 70, "vy": -30 - random.random() * 60, "g": 70,
                "colour": random.choice(PALETTE), "life": 1.6 + random.random() * 0.8,
                "w": 2 if random.random() < 0.5 else 1, "h": 1 if random.random() < 0.5 else 2})

    def heart(self):
        h = self.harry
        self.particles.append({"kind": "heart", "x": h.x + 9, "y": h.y - 30, "vx": 10 + random.random() * 8, "vy": -16,
                               "g": 0, "life": 1.6, "colour": "#ff6fb0"})

    def water(self):
        h = self.harry
        for _ in range(26):
            self.particles.append({
                "kind": "drop", "x": h.x, "y": h.y - 26, "vx": (random.random() - 0.5) * 26, "vy": -70 - random.random() * 40,
                "g": 140, "life": 1.2, "colour": "#bfe9ff" if random.random() < 0.5 else "#7fd2ff", "w": 1, "h": 2})

    # ---------- actions ----------

    def start_action(self, name):
        h = self.harry
        if self.rhythm.on or h.act == name:
            return
        h.dancing = False
        h.act, h.act_t = name, 0.0
        if name not in ("hop", "wave"):
            h.dir = "front"
        if name == "wave":
            h.dir = "back"
            self.confetti(40, h.x, h.y)
        if name == "water":
            self.water()
        self.say(ACTION_NAMES[name])

    def toggle_dance(self):
        h = self.harry
        if self.rhythm.on:
            return
        h.act = None
        h.dancing = not h.dancing
        if h.dancing:
            h.dance_start = h.t
            h.dir = "front"
            self.confetti(60, h.x, h.y)
            self.say("Dance No More with the dancers. Walk to stop.")
        else:
            self.say("")

    def toggle_jacket(self):
        h = self.harry
        h.outfit = "shirtsleeves" if h.outfit == "suit" else "suit"
        self.say("Red jacket back on" if h.outfit == "suit" else "Jacket off, tie loosened. Run for the finale sprint.")

    def centre(self):
        h = self.harry
        h.x, h.y = self.start
        h.dir = "back"
        h.act = None
        h.dancing = False
        self.say("")

    # ---------- update ----------

    def update_particles(self, dt):
        for p in self.particles:
            p["vy"] += p["g"] * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        self.particles = [p for p in self.particles if p["life"] > 0 and p["y"] < HEIGHT]

    def update(self, dt, pressed):
        h = self.harry
        self.status_t = max(0.0, self.status_t - dt)
        if self.rhythm.on:
            self.rhythm.update(dt)
            h.t += dt
            self.update_particles(dt)
            return
        self.rhythm.update(dt)

        def on(direction):
            return any(pressed[k] for k in MOVE_KEYS[direction])

        dx = on("right") - on("left")
        dy = on("down") - on("up")
        h.moving = dx != 0 or dy != 0
        shift = pressed[pygame.K_LSHIFT] or pressed[pygame.K_RSHIFT]
        h.running = h.moving and shift
        if h.moving:
            if h.dancing:
                h.dancing = False
                self.say("")
            if h.act and h.act != "hop":
                h.act = None
            length = math.hypot(dx, dy)
            speed = (RUN_SPEED[h.outfit] if h.running else WALK_SPEED) * dt
            self.step(dx / length * speed, dy / length * speed * PERSPECTIVE)
            if abs(dx) > abs(dy):
                h.dir = "left" if dx < 0 else "right"
            else:
                h.dir = "back" if dy < 0 else "front"

        if h.act:
            action = ACTIONS[h.act]
            before = h.act_t
            h.act_t += dt
            if h.act == "hop":
                vx, vy = DIRECTIONS[h.dir]
                self.step(vx * HOP_SPEED * dt, vy * HOP_SPEED * dt * PERSPECTIVE)
            if h.act == "kiss" and before < 0.55 <= h.act_t:
                self.heart()
            if h.act_t >= action["dur"]:
                h.act = None
                self.say("")
        h.t += dt
        self.update_particles(dt)

    # ---------- drawing ----------

    def harry_sprite(self):
        """The frame to draw for Harry, plus how far to lift (negative y) or jitter (x) it."""
        h, r = self.harry, self.rhythm
        sheets = self.sheets[h.outfit]
        row = ROWS[h.dir]
        if r.on:
            if r.pose and r.pose.get("miss"):
                # A stumble: stand still and jitter a pixel either way.
                return sheets["main"][ROWS["front"]][0], 0, 1 if int(r.pose["t"] * 30) % 2 else -1
            if r.pose:
                return sheets["dance"][0][POSE[r.pose["lane"]]], 0, 0
            if r.song_time() < 0:
                return sheets["main"][ROWS["front"]][0], 0, 0
            return sheets["dance"][0][r.dance_frame()], 0, 0
        if h.dancing:
            return sheets["dance"][0][int((h.t - h.dance_start) * 6) % 8], 0, 0
        if h.act:
            action = ACTIONS[h.act]
            p = min(0.999, h.act_t / action["dur"])
            if h.act == "hop":
                f = 0 if p < 0.18 else 1 if p < 0.45 else 2 if p < 0.8 else 3
                lift = math.sin(min(1, max(0, (p - 0.15) / 0.7)) * math.pi) * 7
                return sheets["hop"][row][f], -js_round(lift), 0
            if h.act == "wave":
                return sheets["main"][ROWS["back"]][1], 0, 0
            return sheets[action["sheet"]][action["row"]][action["seq"][int(p * len(action["seq"]))]], 0, 0
        if h.running:
            sheet = sheets["run"] if h.outfit == "suit" else sheets["sprint"]
            return sheet[row][int(h.t * 12) % 6], 0, 0
        if h.moving:
            return sheets["main"][row][2 + int(h.t * 8) % 4], 0, 0
        # Idle, with a sing, wave or breath every 2.4 seconds.
        return sheets["main"][row][1 if h.t % 2.4 > 1.8 else 0], 0, 0

    def draw_stage(self, screen, t):
        """The stadium on its own, with the crowd's lights twinkling. The menus use it as their backdrop too."""
        screen.blit(self.background, (0, 0))
        tw = self.twinkles
        if tw:
            lit = np.nonzero(np.sin(t * tw["speed"] + tw["phase"]) > 0.55)[0]
            for i in lit:
                screen.set_at((tw["x"][i], tw["y"][i]), tw["colour"][i])

    def draw(self, screen):
        h, r = self.harry, self.rhythm
        self.draw_stage(screen, h.t)

        glow = self.dance_glow if h.dancing else self.glow
        screen.blit(glow, (js_round(h.x) - 52, js_round(h.y) - 62), special_flags=pygame.BLEND_RGB_ADD)

        # Everyone on stage, drawn back to front by where their feet are.
        people = []
        if h.dancing or r.on:
            frame = r.dance_frame() if r.on else int((h.t - h.dance_start) * 6) % 8
            ax, ay = self.nearest_stand(h.x - DANCER_GAP, h.y - 2)
            bx, by = self.nearest_stand(h.x + DANCER_GAP, h.y + 2)
            people.append((ay, self.dancers[0][frame], ax, ay, 0, 6))
            people.append((by, self.dancers[1][frame], bx, by, 0, 6))
        frame, lift, jitter = self.harry_sprite()
        people.append((h.y, frame, h.x + jitter, h.y, lift, 5 if lift else 7))
        people.sort(key=lambda person: person[0])
        for _, frame, x, y, lift, shadow in people:
            screen.blit(self.shadows[shadow], (js_round(x) - shadow, js_round(y) - 1))
            screen.blit(frame, (js_round(x) - ANCHOR_X, js_round(y + lift) - ANCHOR_Y))

        for p in self.particles:
            x, y = js_round(p["x"]), js_round(p["y"])
            if p["kind"] == "heart":
                for px, py in HEART:
                    screen.fill(p["colour"], (x + px, y + py, 1, 1))
            else:
                screen.fill(p["colour"], (x, y, p["w"], p["h"]))

        r.draw(screen)
        if not r.on:
            self.draw_hints(screen)

    def draw_hints(self, screen):
        """The latest message along the top, and every key along the bottom, while walking the runway."""
        if self.status_t > 0:
            text.draw(screen, self.status.upper(), WIDTH / 2, 6, 10, "#ffffff")
        screen.blit(self.hint_bar, (0, HEIGHT - 14))
        text.draw(screen, KEY_HINTS, WIDTH / 2, HEIGHT - 15, 10, "#c9b8f0")


def fit(window_size, fill=False):
    """Where the game view goes: the largest whole-number scale that fits,
    or with fill on, as big as the window allows even if some pixels end up a little wider than others."""
    w, h = window_size
    scale = min(w // WIDTH, h // HEIGHT)
    if scale >= 1 and not fill:
        view_w, view_h = WIDTH * scale, HEIGHT * scale
    else:
        # Fill mode, or a window smaller than the game itself.
        factor = min(w / WIDTH, h / HEIGHT)
        view_w, view_h = max(1, int(WIDTH * factor)), max(1, int(HEIGHT * factor))
    return pygame.Rect((w - view_w) // 2, (h - view_h) // 2, view_w, view_h)


def starting_size():
    try:
        desk_w, desk_h = pygame.display.get_desktop_sizes()[0]
    except (AttributeError, IndexError, pygame.error):
        desk_w, desk_h = 1280, 900
    # Leave room for the menu bar, dock and window title.
    room_w, room_h = desk_w - 40, desk_h - 90
    scale = max(1, min(room_w // WIDTH, room_h // HEIGHT))
    return WIDTH * scale, HEIGHT * scale


def main():
    reduced_motion = "--reduced-motion" in sys.argv or os.environ.get("REDUCED_MOTION") == "1"
    pygame.mixer.pre_init(music.RATE, -16, 2, 512)
    pygame.init()
    audio = pygame.mixer.get_init() is not None
    music.prepare_all()

    pygame.display.set_caption("Together Runway")
    window = pygame.display.set_mode(starting_size(), pygame.RESIZABLE)
    screen = pygame.Surface((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    game = Game(reduced_motion)
    game.rhythm = Rhythm(game, audio)
    menus = Screens(game, audio)
    fill = False

    running = True
    while running:
        dt = min(0.05, clock.tick(FPS) / 1000)
        rhythm = game.rhythm
        playing = menus.state == "play"
        view = fit(window.get_size(), fill)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION) and not playing:
                # Menus are drawn in game pixels, so map the mouse back into them.
                x = (event.pos[0] - view.x) * WIDTH / view.w
                y = (event.pos[1] - view.y) * HEIGHT / view.h
                if event.type == pygame.MOUSEMOTION:
                    menus.mouse_move((x, y))
                elif event.button == 1:
                    menus.mouse_down((x, y))
            elif event.type == pygame.KEYDOWN:
                key = event.key
                if key == pygame.K_z:
                    fill = not fill
                elif not playing:
                    menus.key_down(key)
                elif menus.fade:
                    pass
                elif rhythm.on:
                    # During a song the arrows hit lanes and everything else waits.
                    if key in LANE_KEYS:
                        rhythm.hit(LANE_KEYS[key])
                    elif key == pygame.K_ESCAPE:
                        menus.leave_song()
                    elif key in (pygame.K_RETURN, pygame.K_KP_ENTER) and rhythm.done:
                        rhythm.start(rhythm.song_idx)
                elif key == pygame.K_ESCAPE:
                    menus.leave_free()
                elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    rhythm.start(rhythm.song_idx)
                elif key in SONG_KEYS:
                    rhythm.start(SONG_KEYS[key])
                elif key in ACTION_KEYS:
                    game.start_action(ACTION_KEYS[key])
                elif key == pygame.K_f:
                    game.toggle_dance()
                elif key == pygame.K_j:
                    game.toggle_jacket()
                elif key == pygame.K_r:
                    game.centre()

        if menus.quit:
            running = False
        menus.update(dt)
        if menus.state == "play":
            game.update(dt, pygame.key.get_pressed())
            game.draw(screen)
        else:
            menus.draw(screen)
        menus.draw_fade(screen)

        window.fill(NIGHT)
        if view.size == screen.get_size():
            window.blit(screen, view)
        else:
            window.blit(pygame.transform.scale(screen, view.size), view)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
