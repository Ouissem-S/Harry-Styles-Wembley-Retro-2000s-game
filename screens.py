import math
import random

import numpy as np
import pygame

import music
import pixeltext as text
from music import SONGS
from rhythm import DIFF_NAMES, DIFFS

WIDTH, HEIGHT = 640, 360

PLUM = "#1c1233"
LINE = "#3a2a5e"
TEXT = "#efe6ff"
MUTED = "#a996cf"
NEON = "#ff5ccf"
CYAN = "#46e0ff"
GOLD = "#fcce4a"
DARK = "#1a0b26"

FADE_OUT, FADE_IN = 0.35, 0.45
# The banner writes itself out like the arches on the stage screens: (words, size, colour, shadow, y, arch, seconds per letter).
BANNER = [
    ("TOGETHER", 20, CYAN, DARK, 52, -7, 0.13),
    ("HARRY STYLES", 44, GOLD, NEON, 80, 0, 0.16),
    ("TOGETHER", 20, CYAN, DARK, 146, 7, 0.13),
]
BANNER_START = 0.7
# How long a new letter takes to drop into place, and how long it flashes white.
DROP_TIME, FLASH_TIME = 0.15, 0.1

COVER_W, COVER_H = 168, 96

MOVE_LEFT = (pygame.K_LEFT, pygame.K_a)
MOVE_RIGHT = (pygame.K_RIGHT, pygame.K_d)
MOVE_UP = (pygame.K_UP, pygame.K_w)
MOVE_DOWN = (pygame.K_DOWN, pygame.K_s)
CONFIRM = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


# ---------- song covers ----------

def bands(surface, colours, top, bottom):
    """A stepped gradient, one flat band per colour, like a small palette would give."""
    n = len(colours)
    for i, colour in enumerate(colours):
        y0 = top + (bottom - top) * i // n
        y1 = top + (bottom - top) * (i + 1) // n
        surface.fill(colour, (0, y0, COVER_W, y1 - y0))


def stars(surface, rng, count, bottom):
    for _ in range(count):
        surface.set_at((rng.randrange(COVER_W), rng.randrange(bottom)), pygame.Color("#ffffff" if rng.random() < 0.5 else "#c9b8f0"))


def cover_neon():
    """Synth-pop: a striped sunset over a neon grid."""
    s = pygame.Surface((COVER_W, COVER_H))
    rng = random.Random(1)
    horizon = 58
    bands(s, ["#1a0b3a", "#2a1050", "#46166a", "#6a1f7a", "#a32a80", "#ff5ccf"], 0, horizon)
    stars(s, rng, 18, 30)
    cx, cy, r = 84, 50, 28
    for y in range(cy - r, horizon):
        half = math.sqrt(max(0, r * r - (y - cy) ** 2))
        k = (y - (cy - r)) / (horizon - (cy - r))
        colour = GOLD if k < 0.4 else "#f79454" if k < 0.7 else NEON
        # Gaps across the bottom of the sun get thicker towards the horizon.
        below = y - (cy - 8)
        if below >= 0 and below % 6 >= 6 - (1 + below // 6):
            continue
        s.fill(colour, (round(cx - half), y, round(half * 2), 1))
    s.fill("#120822", (0, horizon, COVER_W, COVER_H - horizon))
    for i in range(-7, 8):
        pygame.draw.line(s, "#2a6f96", (cx + i * 6, horizon), (cx + i * 34, COVER_H))
    for k in range(1, 8):
        y = horizon + round((COVER_H - horizon) * (k / 7) ** 1.8)
        s.fill(CYAN, (0, y, COVER_W, 1))
    s.fill(NEON, (0, horizon, COVER_W, 1))
    return s


def cover_velvet():
    """Disco-funk: a mirror ball over a lit-up floor."""
    s = pygame.Surface((COVER_W, COVER_H))
    rng = random.Random(2)
    floor = 64
    bands(s, ["#1a0612", "#2a0a1e", "#3e0f2a", "#521433"], 0, floor)
    cx, cy, r = 84, 30, 18
    for a in range(10):
        angle = a / 10 * math.tau + 0.2
        tip = (cx + math.cos(angle) * 140, cy + math.sin(angle) * 140)
        side = (cx + math.cos(angle + 0.12) * 140, cy + math.sin(angle + 0.12) * 140)
        pygame.draw.polygon(s, "#6b1d3f", [(cx, cy), tip, side])
    pygame.draw.line(s, "#c9b8f0", (cx, 0), (cx, cy - r))
    tiles = ["#7a90da", "#c9b8f0", "#46e0ff", "#b9a6e6"]
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy > r * r:
                continue
            if x % 4 == 0 or y % 4 == 0:
                colour = "#2a1a4a"
            elif dx + dy < -15:
                colour = "#ffffff"
            elif dx + dy > 13:
                colour = LINE
            else:
                colour = tiles[(x // 4 * 7 + y // 4 * 3) % 4]
            s.set_at((x, y), pygame.Color(colour))
    for _ in range(6):
        x, y = rng.randrange(20, COVER_W - 20), rng.randrange(6, floor - 6)
        for px, py in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            s.set_at((x + px, y + py), pygame.Color("#ffffff"))

    s.fill("#0c0818", (0, floor, COVER_W, COVER_H - floor))
    lit = ["#a8327a", "#2f8aa8", "#a88a32", "#2f9a62"]
    y = floor + 1
    for row, h in enumerate([5, 7, 9, 10]):
        w = 14 + row * 6
        offset = (COVER_W // 2) % w - w // 2
        for i, x in enumerate(range(offset - w, COVER_W, w)):
            s.fill(lit[(i + row) % 4], (x + 1, y, w - 1, h - 1))
        y += h
    return s


def cover_glow():
    """Half-time: a low moon over a crowd holding up lights."""
    s = pygame.Surface((COVER_W, COVER_H))
    rng = random.Random(3)
    bands(s, ["#0c0818", "#1f1236", "#3a1f5e", "#6e2c6e", "#b04a6e", "#f79454"], 0, 72)
    stars(s, rng, 14, 28)
    for radius, colour in ((15, "#8a4a7a"), (11, "#e8a98a"), (9, "#ffd9b0"), (7, "#fff1d6")):
        pygame.draw.circle(s, colour, (124, 26), radius)
    crowd = "#0c0818"
    s.fill(crowd, (0, 80, COVER_W, COVER_H - 80))
    for x in range(-2, COVER_W, 9):
        top = 74 + rng.randrange(4)
        pygame.draw.circle(s, crowd, (x + 4, top), 4)
        s.fill(crowd, (x, top + 3, 9, COVER_H - top))
        if rng.random() < 0.45:
            hand = (x + 7, top - 10 - rng.randrange(5))
            pygame.draw.line(s, crowd, (x + 7, top + 3), hand, 2)
            s.fill("#f79454", (hand[0] - 1, hand[1] - 2, 3, 3))
            s.fill(GOLD, (hand[0], hand[1] - 2, 1, 2))
    return s


COVERS = [cover_neon, cover_velvet, cover_glow]


# ---------- sounds ----------

def make_sound(samples):
    pcm = (np.clip(samples * music.MASTER, -1, 1) * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack([pcm, pcm])))


def make_sounds():
    return {
        "letter": make_sound(music.tone("square", 84, 0.07, 0.045, 3500)),
        "move": make_sound(music.tone("triangle", 76, 0.3, 0.07, 4000)),
        "select": make_sound(np.concatenate([music.tone("square", 79, 0.12, 0.07, 4000),
                                             music.tone("square", 86, 0.12, 0.12, 4000)])),
        "back": make_sound(music.tone("square", 72, 0.1, 0.09, 3000)),
    }


# ---------- menus ----------

class Screens:
    """The title, mode and song menus in front of the stage, and the fades between them."""

    def __init__(self, game, audio):
        self.game = game
        self.rhythm = game.rhythm
        self.sounds = make_sounds() if audio else {}
        self.covers = [make() for make in COVERS]
        self.quit = False
        self.clock = 0.0
        self.mode = None
        self.diff = self.rhythm.diff
        self.fade = None
        self.dim = pygame.Surface((WIDTH, HEIGHT))
        self.dim.fill("#0c0818")
        self.black = pygame.Surface((WIDTH, HEIGHT))

        walk = game.sheets["suit"]["main"][1][2:6]
        self.walkers = [pygame.transform.scale(frame, (72, 108)) for frame in walk]
        self.letters = self.lay_out_banner()
        self.written_at = self.letters[-1]["at"] + 0.4

        self.set_state("title")
        # Open on black and fade the title in.
        self.fade = {"t": FADE_OUT, "action": None, "done": True}

    def lay_out_banner(self):
        letters = []
        at = BANNER_START
        for words, size, colour, shadow, y, arch, gap in BANNER:
            f = text.font(size)
            spacing = 3 if size < 30 else 1
            width = f.size(words)[0] + spacing * (len(words) - 1)
            left = (WIDTH - width) / 2
            for i, ch in enumerate(words):
                x = left + f.size(words[:i])[0] + i * spacing
                # Bend the line like the arches on the screens: the middle letters sit higher or lower.
                u = (x + f.size(ch)[0] / 2 - WIDTH / 2) / (width / 2)
                if ch != " ":
                    letters.append({"ch": ch, "x": x, "y": y + arch * (1 - u * u), "size": size,
                                    "colour": colour, "shadow": shadow, "at": at})
                at += gap if ch != " " else gap * 2
            at += 0.25
        return letters

    def set_state(self, state):
        self.state = state
        self.t = 0.0
        if state == "title":
            self.focus = "start"
        elif state == "mode":
            self.focus = self.diff
        elif state == "songs":
            self.focus = f"song{self.rhythm.song_idx}"

    def play(self, name):
        if name in self.sounds:
            self.sounds[name].play()

    def go(self, action):
        """Fade to black, do the action while the screen is dark, then fade back in."""
        if self.fade is None:
            self.fade = {"t": 0.0, "action": action, "done": False}

    # ---------- what each screen holds ----------

    def items(self):
        """Every clickable thing on the current screen, in the order the arrow keys step through them."""
        if self.state == "title":
            if self.t < self.written_at:
                return {}
            return {"start": pygame.Rect(260, 214, 120, 26), "quit": pygame.Rect(260, 248, 120, 26)}
        if self.state == "mode":
            items = {"free": pygame.Rect(130, 254, 120, 26)}
            for i, diff in enumerate(DIFFS):
                items[diff] = pygame.Rect(346 + i * 72, 254, 66, 26)
            items["back"] = pygame.Rect(12, 334, 64, 18)
            return items
        if self.state == "songs":
            items = {f"song{i}": self.card_rect(i) for i in range(len(SONGS))}
            items["back"] = pygame.Rect(12, 334, 64, 18)
            return items
        return {}

    def card_rect(self, i):
        return pygame.Rect(28 + i * 200, 60, 184, 262)

    def activate(self, item):
        if item == "start":
            self.play("select")
            self.go(lambda: self.set_state("mode"))
        elif item == "quit":
            self.quit = True
        elif item == "free":
            self.play("select")
            self.go(self.enter_free)
        elif item in DIFFS:
            self.play("select")
            self.diff = item
            self.rhythm.set_diff(item)
            self.go(lambda: self.set_state("songs"))
        elif item.startswith("song"):
            self.play("select")
            idx = int(item[4:])
            self.go(lambda: self.enter_song(idx))
        elif item == "back":
            self.back()

    def back(self):
        self.play("back")
        if self.state == "mode":
            self.go(lambda: self.set_state("title"))
        elif self.state == "songs":
            self.go(lambda: self.set_state("mode"))

    def enter_free(self):
        self.state = "play"
        self.mode = "free"
        self.game.centre()
        self.game.say("Free mode: walk the runway. Enter or 1/2/3 plays a song, Esc goes back to the menu.")

    def enter_song(self, idx):
        self.state = "play"
        self.mode = "game"
        self.rhythm.set_diff(self.diff)
        self.rhythm.start(idx)

    def leave_song(self):
        """Esc or Stop during a song: in game mode that means back to the song list."""
        self.rhythm.stop()
        if self.mode == "game":
            self.go(lambda: self.set_state("songs"))

    def leave_free(self):
        self.play("back")
        self.go(lambda: self.set_state("mode"))

    # ---------- input ----------

    def key_down(self, key):
        if self.fade:
            return
        if self.state == "title" and self.t < self.written_at:
            # Any key skips the banner writing itself out.
            self.t = self.written_at
            return
        if key == pygame.K_ESCAPE:
            self.back()
            return
        order = [name for name in self.items() if name != "back"]
        if not order:
            return
        if key in CONFIRM:
            self.activate(self.focus)
            return
        step = 0
        if self.state == "title":
            step = -1 if key in MOVE_UP else 1 if key in MOVE_DOWN else 0
        else:
            step = -1 if key in MOVE_LEFT else 1 if key in MOVE_RIGHT else 0
        if step:
            i = order.index(self.focus) if self.focus in order else 0
            self.focus = order[(i + step) % len(order)]
            self.play("move")

    def mouse_down(self, pos):
        if self.fade:
            return
        if self.state == "title" and self.t < self.written_at:
            self.t = self.written_at
            return
        for name, rect in self.items().items():
            if rect.collidepoint(pos):
                self.focus = name
                self.activate(name)
                return
        # The free mode card is a big target too, not just its button.
        if self.state == "mode" and pygame.Rect(70, 62, 240, 232).collidepoint(pos):
            self.focus = "free"
            self.activate("free")

    def mouse_move(self, pos):
        if self.fade:
            return
        for name, rect in self.items().items():
            if rect.collidepoint(pos) and name != self.focus and name != "back":
                self.focus = name
                self.play("move")

    # ---------- update ----------

    def update(self, dt):
        self.clock += dt
        if self.state == "title":
            before = self.t
            self.t += dt
            # A soft tick for each letter as it lands.
            if any(before < letter["at"] <= self.t for letter in self.letters):
                self.play("letter")
        else:
            self.t += dt
        if self.fade:
            self.fade["t"] += dt
            if self.fade["t"] >= FADE_OUT and not self.fade["done"]:
                self.fade["done"] = True
                if self.fade["action"]:
                    self.fade["action"]()
            if self.fade["t"] >= FADE_OUT + FADE_IN:
                self.fade = None

    # ---------- drawing ----------

    def draw(self, screen):
        self.game.draw_stage(screen, self.clock)
        self.dim.set_alpha(110 if self.state == "title" else 175)
        screen.blit(self.dim, (0, 0))
        if self.state == "title":
            self.draw_title(screen)
        elif self.state == "mode":
            self.draw_mode(screen)
        elif self.state == "songs":
            self.draw_songs(screen)

    def draw_fade(self, screen):
        if not self.fade:
            return
        t = self.fade["t"]
        k = t / FADE_OUT if t < FADE_OUT else 1 - (t - FADE_OUT) / FADE_IN
        self.black.set_alpha(round(max(0, min(1, k)) * 255))
        screen.blit(self.black, (0, 0))

    def button(self, screen, rect, label, focused, size=14, lift=0):
        rect = rect.move(0, -lift)
        screen.fill(NEON if focused else PLUM, rect)
        pygame.draw.rect(screen, "#ffffff" if focused else LINE, rect, 1)
        text.draw(screen, label, rect.centerx, rect.centery - size * 0.62, size, DARK if focused else TEXT, outline=not focused)

    def hint(self, screen, words):
        text.draw(screen, words, WIDTH / 2 + 30, 338, 10, MUTED)

    def draw_title(self, screen):
        for letter in self.letters:
            age = self.t - letter["at"]
            if age < 0:
                continue
            drop = round(6 * (1 - min(1, age / DROP_TIME)))
            x, y = letter["x"], letter["y"] - drop
            colour = "#ffffff" if age < FLASH_TIME else letter["colour"]
            text.draw(screen, letter["ch"], x + 2, y + 2, letter["size"], letter["shadow"], "left")
            text.draw(screen, letter["ch"], x, y, letter["size"], colour, "left")

        items = self.items()
        if items:
            # The buttons slide up a few pixels as they appear.
            rise = round(4 * (1 - min(1, (self.t - self.written_at) / 0.25)))
            for name, label in (("start", "START"), ("quit", "QUIT")):
                self.button(screen, items[name].move(0, rise), label, self.focus == name)
            if int(self.clock * 2) % 2 == 0:
                text.draw(screen, "ARROWS + ENTER, OR CLICK", WIDTH / 2, 296, 10, MUTED)

    def card(self, screen, rect, focused):
        rect = rect.move(0, -3 if focused else 0)
        screen.fill(PLUM, rect)
        pygame.draw.rect(screen, NEON if focused else LINE, rect, 2 if focused else 1)
        return rect

    def draw_mode(self, screen):
        text.draw(screen, "PICK A MODE", WIDTH / 2, 16, 22, GOLD)
        items = self.items()
        game_focused = self.focus in DIFFS

        free = self.card(screen, pygame.Rect(70, 62, 240, 232), self.focus == "free")
        walker = self.walkers[int(self.clock * 8) % 4]
        screen.blit(walker, (free.centerx - 36, free.y + 12))
        text.draw(screen, "FREE MODE", free.centerx, free.y + 124, 18, TEXT)
        text.draw(screen, "Walk the runway, dance, wave", free.centerx, free.y + 152, 10, MUTED)
        text.draw(screen, "and hop at your own pace", free.centerx, free.y + 164, 10, MUTED)
        self.button(screen, items["free"], "WALK", self.focus == "free", lift=3 if self.focus == "free" else 0)

        play = self.card(screen, pygame.Rect(330, 62, 240, 232), game_focused)
        clip = pygame.Rect(play.x + 20, play.y + 12, play.w - 40, 104)
        screen.set_clip(clip)
        arrows = self.rhythm.arrows
        receptors = self.rhythm.receptors
        for lane in range(4):
            x = clip.x + 14 + lane * 44
            # One arrow per lane keeps rising to its receptor, which lights up as it lands, like on the real track.
            y = clip.bottom - (self.clock * 60 + lane * 26) % 104
            landed = y <= clip.y + 4
            screen.blit((self.rhythm.receptors_on if landed or y < clip.y + 10 else receptors)[lane], (x, clip.y + 4))
            if not landed:
                screen.blit(arrows[lane][lane], (x, round(y)))
        screen.set_clip(None)
        text.draw(screen, "GAME MODE", play.centerx, play.y + 124, 18, TEXT)
        text.draw(screen, "Hit the arrows on the beat", play.centerx, play.y + 152, 10, MUTED)
        text.draw(screen, "Pick how hard:", play.centerx, play.y + 164, 10, MUTED)
        for diff in DIFFS:
            self.button(screen, items[diff], DIFF_NAMES[diff].upper(), self.focus == diff, 12, lift=3 if game_focused else 0)

        self.button(screen, items["back"], "< BACK", False, 10)
        self.hint(screen, "ARROWS MOVE   ENTER CHOOSES   ESC GOES BACK")

    def draw_songs(self, screen):
        text.draw(screen, "PICK A SONG", WIDTH / 2, 10, 22, GOLD)
        text.draw(screen, f"GAME MODE · {DIFF_NAMES[self.diff].upper()}", WIDTH / 2, 38, 10, CYAN)
        for i, song in enumerate(SONGS):
            focused = self.focus == f"song{i}"
            rect = self.card(screen, self.card_rect(i), focused)
            cover = pygame.Rect(rect.x + 8, rect.y + 8, COVER_W, COVER_H)
            screen.blit(self.covers[i], cover)
            if focused:
                # A light catches the cover now and then.
                sweep = (self.clock * 120) % (COVER_W * 3) - COVER_W
                screen.set_clip(cover)
                for w in range(6):
                    x = round(cover.x + sweep + w)
                    pygame.draw.line(screen, "#ffffff" if w in (2, 3) else "#c9b8f0", (x, cover.bottom), (x + 40, cover.y))
                screen.set_clip(None)
            pygame.draw.rect(screen, LINE, cover, 1)

            text.draw(screen, song["name"].upper(), rect.centerx, rect.y + 112, 16, TEXT)
            text.draw(screen, f"{song['style']} · {song['bpm']} BPM", rect.centerx, rect.y + 138, 10, MUTED)
            text.draw(screen, f"{song['bars']} BARS · TRACK {i + 1}", rect.centerx, rect.y + 152, 10, MUTED)
            best = self.rhythm.get_best(i, self.diff)
            text.draw(screen, f"BEST {best:,}" if best else "NO SCORE YET", rect.centerx, rect.y + 176, 12, CYAN if best else MUTED)
            choose = pygame.Rect(rect.centerx - 50, rect.bottom - 40, 100, 26)
            self.button(screen, choose, "CHOOSE", focused)

        self.button(screen, self.items()["back"], "< BACK", False, 10)
        self.hint(screen, "ARROWS MOVE   ENTER PLAYS   ESC GOES BACK")
