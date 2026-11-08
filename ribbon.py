import math
import random

import pygame

# Arrow keys work the same as WASD.
KEY_NAMES = {
    pygame.K_w: "W", pygame.K_UP: "W",
    pygame.K_a: "A", pygame.K_LEFT: "A",
    pygame.K_s: "S", pygame.K_DOWN: "S",
    pygame.K_d: "D", pygame.K_RIGHT: "D",
    pygame.K_SPACE: "SPACE",
}

HEIGHT = 34
CAP = 18
SPACE_CAP = 42
GAP = 5
MISS_FLASH = 0.35
POINTS = 100

BAND = (14, 6, 30)
PINK = (255, 80, 200)
CYAN = (80, 230, 255)
WHITE = (255, 255, 255)
DIM = (110, 90, 150)
RED = (255, 60, 80)


class Ribbon:
    """The strip at the bottom of the screen that shows which keys to press next."""

    def __init__(self, moves, width, height):
        self.moves = moves
        self.rect = pygame.Rect(0, height - HEIGHT, width, HEIGHT)
        self.font = pygame.font.Font(None, 16)
        self.big_font = pygame.font.Font(None, 22)
        self.score = 0
        self.streak = 0
        self.missed_at = -10
        self.move = None
        self.new_sequence()

    def new_sequence(self):
        choices = [name for name in self.moves if name != self.move]
        self.move = random.choice(choices)
        self.keys = self.moves[self.move]["keys"]
        self.progress = 0

    def press(self, key, t):
        """Feed in a key press. Returns the name of the move when its sequence is finished."""
        name = KEY_NAMES.get(key)
        if name is None:
            return None

        if name != self.keys[self.progress]:
            self.progress = 0
            self.streak = 0
            self.missed_at = t
            return None

        self.progress += 1
        if self.progress < len(self.keys):
            return None

        done = self.move
        self.streak += 1
        self.score += POINTS * self.streak
        self.new_sequence()
        return done

    def draw(self, screen, t):
        band = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        band.fill((*BAND, 220))
        screen.blit(band, self.rect)
        pygame.draw.line(screen, PINK, self.rect.topleft, self.rect.topright)
        pygame.draw.line(screen, CYAN, (0, self.rect.top + 1), (self.rect.right, self.rect.top + 1))

        middle = self.rect.centery + 1
        missed = t - self.missed_at < MISS_FLASH

        label = self.font.render("NEXT MOVE", False, DIM)
        screen.blit(label, (10, middle - 11))
        name = self.big_font.render(self.move.upper(), False, RED if missed else WHITE)
        screen.blit(name, (10, middle - 1))

        widths = [SPACE_CAP if k == "SPACE" else CAP for k in self.keys]
        x = self.rect.centerx - (sum(widths) + GAP * (len(widths) - 1)) // 2
        for i, (key, w) in enumerate(zip(self.keys, widths)):
            self.draw_cap(screen, key, x, middle, w, i, t, missed)
            x += w + GAP

        score = self.big_font.render(f"{self.score:06d}", False, WHITE)
        screen.blit(score, (self.rect.right - score.get_width() - 10, middle - 12))
        if self.streak > 1:
            streak = self.font.render(f"STREAK x{self.streak}", False, PINK)
            screen.blit(streak, (self.rect.right - streak.get_width() - 10, middle + 3))

    def draw_cap(self, screen, key, x, middle, w, i, t, missed):
        if missed:
            fill, edge, text = (60, 10, 20), RED, RED
            lift = 0
        elif i < self.progress:
            fill, edge, text = CYAN, CYAN, BAND
            lift = 0
        elif i == self.progress:
            pulse = (math.sin(t * 10) + 1) / 2
            edge = tuple(int(p + (c - p) * pulse) for p, c in zip(PINK, WHITE))
            fill, text = (60, 20, 80), WHITE
            lift = 2
        else:
            fill, edge, text = BAND, DIM, DIM
            lift = 0

        cap = pygame.Rect(x, middle - CAP // 2 - lift, w, CAP)
        pygame.draw.rect(screen, fill, cap, border_radius=3)
        pygame.draw.rect(screen, edge, cap, 1, border_radius=3)
        letter = self.font.render(key, False, text)
        screen.blit(letter, letter.get_rect(center=(cap.centerx, cap.centery + 1)))
