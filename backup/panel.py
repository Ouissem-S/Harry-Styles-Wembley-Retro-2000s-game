import pygame

import pixeltext as text
from music import SONGS
from rhythm import DIFF_NAMES, DIFFS

# Drawn in window pixels underneath the game view, so it stays readable whatever the game's scale.
HEIGHT = 122
PAD = 5

NIGHT = "#0c0818"
PLUM = "#1c1233"
LINE = "#3a2a5e"
TEXT = "#efe6ff"
MUTED = "#a996cf"
NEON = "#ff5ccf"
CYAN = "#46e0ff"
SUIT = "#d02e3e"

DPAD = {"up": (1, 0), "left": (0, 1), "right": (2, 1), "down": (1, 2)}
DPAD_CELL = 16
ACTIONS = ["run", "dance", "hop", "bow", "kiss", "peace", "water", "wave", "jacket", "centre"]
LABELS = {"run": "Run", "dance": "Dance", "hop": "Hop", "bow": "Bow", "kiss": "Kiss", "peace": "Peace",
          "water": "Water", "wave": "Wave", "centre": "Centre"}


class Panel:
    """Setlist, difficulty and on-screen buttons, for playing with a mouse or a touch screen."""

    def __init__(self, game, on_stop):
        self.game = game
        self.on_stop = on_stop
        self.rect = pygame.Rect(0, 0, 640, HEIGHT)
        self.buttons = {}
        # The D-pad button currently held down, if any.
        self.pressed = None

    def layout(self, rect):
        self.rect = rect
        b = {}
        x, y = rect.x + PAD, rect.y + PAD
        inner = rect.w - PAD * 2

        diff_w, stop_w = 50, 48
        cards_w = inner - (diff_w * 3 + stop_w + PAD * 4)
        card_w = (cards_w - PAD * 2) // 3
        for i in range(3):
            b[f"song{i}"] = pygame.Rect(x + i * (card_w + PAD), y, card_w, 40)
        dx = x + cards_w + PAD
        for i, diff in enumerate(DIFFS):
            b[f"diff-{diff}"] = pygame.Rect(dx + i * (diff_w + PAD), y + 9, diff_w, 22)
        b["stop"] = pygame.Rect(dx + 3 * (diff_w + PAD), y + 9, stop_w, 22)

        y += 40 + PAD
        for name, (cx, cy) in DPAD.items():
            b[f"dpad-{name}"] = pygame.Rect(x + cx * DPAD_CELL, y + cy * DPAD_CELL, DPAD_CELL - 1, DPAD_CELL - 1)
        ax = x + DPAD_CELL * 3 + PAD * 2
        act_w = (rect.right - PAD - ax - PAD * 4) // 5
        for i, name in enumerate(ACTIONS):
            col, row = i % 5, i // 5
            b[name] = pygame.Rect(ax + col * (act_w + PAD), y + row * 24, act_w, 22)
        self.status_y = y + 48 + PAD
        self.buttons = b

    # ---------- input ----------

    def mouse_down(self, pos):
        game, rhythm = self.game, self.game.rhythm
        for name, rect in self.buttons.items():
            if not rect.collidepoint(pos):
                continue
            if name == "stop" and not rhythm.on:
                continue
            if name.startswith("dpad-"):
                direction = name[5:]
                self.pressed = direction
                if rhythm.on:
                    rhythm.hit({"left": 0, "down": 1, "up": 2, "right": 3}[direction])
                else:
                    game.held.add(direction)
            elif name.startswith("song"):
                rhythm.start(int(name[4:]))
            elif name.startswith("diff-"):
                rhythm.set_diff(name[5:])
            elif name == "stop":
                self.on_stop()
            elif name == "run":
                game.run_toggle = not game.run_toggle
            elif name == "dance":
                game.toggle_dance()
            elif name == "jacket":
                game.toggle_jacket()
            elif name == "centre":
                game.centre()
            else:
                game.start_action(name)
            return True
        return False

    def mouse_up(self):
        if self.pressed:
            self.game.held.discard(self.pressed)
            self.pressed = None

    # ---------- drawing ----------

    def button(self, window, rect, label, on=False, hot=False, colour=None):
        fill = colour or (NEON if on else PLUM)
        window.fill(fill, rect)
        pygame.draw.rect(window, CYAN if hot else LINE, rect, 1)
        text.draw(window, label, rect.centerx, rect.centery - 8, 12, NIGHT if on else TEXT, outline=False)

    def draw(self, window):
        game, rhythm = self.game, self.game.rhythm
        window.fill(NIGHT, self.rect)
        b = self.buttons

        for i, song in enumerate(SONGS):
            rect = b[f"song{i}"]
            selected = i == rhythm.song_idx
            window.fill(PLUM, rect)
            pygame.draw.rect(window, NEON if selected else LINE, rect, 1)
            text.draw(window, f"{i + 1}  {song['name']}", rect.x + 6, rect.y + 1, 12, TEXT, "left", outline=False)
            text.draw(window, f"{song['style']} · {song['bpm']} BPM", rect.x + 6, rect.y + 14, 10, MUTED, "left", outline=False)
            best = rhythm.get_best(i, rhythm.diff)
            text.draw(window, f"Best {best:,}" if best else "No score yet", rect.x + 6, rect.y + 26, 10, CYAN, "left", outline=False)

        for diff in DIFFS:
            self.button(window, b[f"diff-{diff}"], DIFF_NAMES[diff], on=diff == rhythm.diff)
        if rhythm.on:
            self.button(window, b["stop"], "Stop", colour=SUIT)

        for name, rect in b.items():
            if name.startswith("dpad-"):
                direction = name[5:]
                window.fill(NEON if self.pressed == direction else PLUM, rect)
                pygame.draw.rect(window, LINE, rect, 1)
                draw_triangle(window, rect, direction, NIGHT if self.pressed == direction else TEXT)

        for name in ACTIONS:
            if name == "jacket":
                off = game.harry.outfit != "suit"
                self.button(window, b[name], "Jacket on" if off else "Jacket off", colour=SUIT if off else None)
            else:
                self.button(window, b[name], LABELS[name], on=name == "run" and game.run_toggle, hot=name == "dance")

        text.draw(window, game.status, self.rect.x + PAD, self.status_y, 10, MUTED, "left", outline=False)


def draw_triangle(window, rect, direction, colour):
    cx, cy, r = rect.centerx, rect.centery, 4
    points = {
        "up": [(cx, cy - r), (cx - r, cy + r - 1), (cx + r, cy + r - 1)],
        "down": [(cx, cy + r), (cx - r, cy - r + 1), (cx + r, cy - r + 1)],
        "left": [(cx - r, cy), (cx + r - 1, cy - r), (cx + r - 1, cy + r)],
        "right": [(cx + r, cy), (cx - r + 1, cy - r), (cx - r + 1, cy + r)],
    }[direction]
    pygame.draw.polygon(window, colour, points)
