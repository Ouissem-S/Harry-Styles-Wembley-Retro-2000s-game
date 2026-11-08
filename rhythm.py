import json
import math
import os
import time

import pygame

import music
import pixeltext as text
from music import SONGS

DIFFS = ["easy", "normal", "hard"]
# "normal" stays the name in saved scores; players see it as Medium.
DIFF_NAMES = {"easy": "Easy", "normal": "Medium", "hard": "Hard"}
WINDOWS = {"perfect": 0.045, "great": 0.09, "good": 0.135}
POINTS = {"perfect": 1000, "great": 700, "good": 300}
HYPE = {"perfect": 0.03, "great": 0.02, "good": 0.006}
MISS_HYPE = 0.06

# Seconds an arrow takes to travel from the bottom of the track up to the receptors.
TRAVEL = 1.55
TRACK_X, LANE_W, REC_Y, TOP, BOTTOM = 484, 34, 40, 20, 348
SPEED = (BOTTOM - REC_Y) / TRAVEL
LANE_COLOURS = ["#ff5ccf", "#46e0ff", "#fcce4a", "#4fe08f"]
HYPE_COLOURS = ["#ff5ccf", "#f79454", "#fcce4a", "#4fe08f"]
JUDGE_COLOURS = {"perfect": "#fcce4a", "great": "#46e0ff", "good": "#ff8fd8", "miss": "#9a8ab8"}
GRADE_COLOURS = {"S": "#fcce4a", "A": "#4fe08f", "B": "#46e0ff", "C": "#ff8fd8", "D": "#9a8ab8"}
LABEL = "#c9b8f0"
# The dance frame Harry strikes when he hits each lane: left, down, up, right.
POSE = [1, 5, 7, 0]

ARROW = [
    "......o......", ".....oxo.....", "....oxxxo....", "...oxxxxxo...", "..oxxxxxxxo..", ".oxxxxxxxxxo.",
    "oxxxoxxxoxxxo", "oooooxxxooooo", "....oxxxo....", "....oxxxo....", "....oxxxo....", "....oxxxo....", "....ooooo...."]
# The arrow above points up; turn it to face each lane (degrees, anticlockwise).
TURN = [90, 180, 0, -90]

SAVE = os.path.join(os.path.dirname(__file__), "best_scores.json")
# get_pos() counts audio handed to the sound card, which is about one buffer ahead of what we hear.
OUTPUT_LATENCY = 512 / music.RATE


def build_chart(song, diff):
    """Arrows taken from the song's own melody and drums, so the same song and difficulty always give the same chart."""
    spb = 60 / song["bpm"]
    events = []
    for bar in range(song["bars"]):
        sec = song["sec"](bar)
        for q in range(16):
            t = (bar * 16 + q) * spb / 4
            if sec.get("lead"):
                for s, m, _ in song["lead"]["phrase"]:
                    if s == (bar % 4) * 16 + q:
                        events.append({"t": t, "k": "lead", "m": m, "pr": 3, "q": q, "bar": bar})
            if sec.get("clap") and q in song["drum"]["clap"]:
                events.append({"t": t, "k": "clap", "pr": 2, "q": q, "bar": bar})
            if sec.get("kick") and q in song["drum"]["kick"]:
                events.append({"t": t, "k": "kick", "pr": 1, "q": q, "bar": bar})
            if diff == "hard" and (sec.get("arp") or sec.get("pluck")) and q % 2 == 0:
                events.append({"t": t, "k": "arp", "pr": 0, "q": q, "bar": bar})
    events.sort(key=lambda e: (e["t"], -e["pr"]))

    gap = {"easy": max(spb * 0.98, 0.42), "normal": max(spb * 0.48, 0.24), "hard": max(spb * 0.24, 0.2)}[diff]
    notes = []
    last_t, last_pitch, last_lane = -9, None, 2
    kick_side = clap_side = arp_i = up_flip = down_flip = 0
    for e in events:
        if diff == "easy" and e["k"] != "lead" and e["q"] % (8 if song["bpm"] > 100 else 4) != 0:
            continue
        if diff == "easy" and e["k"] == "lead" and e["q"] % 4 != 0:
            continue
        if diff != "hard" and e["k"] == "kick" and notes and e["t"] - last_t < spb * 0.98:
            continue
        if e["t"] - last_t < gap - 1e-6:
            continue

        if e["k"] == "lead":
            # Rising notes go to up/right, falling notes to down/left, repeats stay put.
            if last_pitch is None or e["m"] == last_pitch:
                lane = last_lane
            elif e["m"] > last_pitch:
                up_flip ^= 1
                lane = 2 if up_flip else 3
            else:
                down_flip ^= 1
                lane = 1 if down_flip else 0
            last_pitch = e["m"]
        elif e["k"] == "kick":
            if diff == "easy":
                lane = [0, 3, 1, 2][kick_side % 4]
                kick_side += 1
            else:
                kick_side ^= 1
                lane = 0 if kick_side else 3
        elif e["k"] == "clap":
            clap_side ^= 1
            lane = 1 if clap_side else 2
        else:
            lane = arp_i % 4
            arp_i += 1

        notes.append({"t": e["t"], "lane": lane, "j": None})
        sec = song["sec"](e["bar"])
        double = (diff == "normal" and e["q"] == 0 and sec.get("lead") and e["bar"] % 4 == 0) or \
                 (diff == "hard" and e["q"] == 0 and (sec.get("lead") or sec.get("stab")))
        if double:
            notes.append({"t": e["t"], "lane": (lane + 2) % 4, "j": None})
        last_t, last_lane = e["t"], lane

    last_bar = (song["bars"] - 1) * 16 * spb / 4
    if not notes or notes[-1]["t"] < last_bar:
        notes.append({"t": last_bar, "lane": 0, "j": None})
        notes.append({"t": last_bar, "lane": 3, "j": None})
    return notes


def arrow_frames(fill, edge, light):
    base = pygame.Surface((13, 13), pygame.SRCALPHA)
    for y, row in enumerate(ARROW):
        for x, ch in enumerate(row):
            if ch == "." or (fill is None and ch == "x"):
                continue
            if ch == "o":
                colour = edge
            elif light and ((y < 5 and x <= 6) or x == 5):
                colour = light
            else:
                colour = fill
            base.set_at((x, y), pygame.Color(colour))
    return [pygame.transform.scale(pygame.transform.rotate(base, turn), (26, 26)) for turn in TURN]


def faded(surface, alpha):
    copy = surface.copy()
    copy.set_alpha(alpha)
    return copy


def lane_x(lane):
    return TRACK_X + lane * LANE_W + LANE_W / 2


def translucent(size, colour, alpha):
    surface = pygame.Surface(size)
    surface.fill(colour)
    surface.set_alpha(round(alpha * 255))
    return surface


def load_best():
    try:
        with open(SAVE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


class Rhythm:
    """The four-lane arrow track, played over one of the original songs."""

    def __init__(self, game, audio):
        self.game = game
        self.audio = audio
        self.on = False
        self.done = False
        self.loading = None
        self.song_idx = 0
        self.song = SONGS[0]
        self.spb = 60 / self.song["bpm"]
        self.diff = "normal"
        self.notes = []
        self.best = load_best()
        self.reset_score()

        self.arrows = [arrow_frames(colour, "#1a0b26", "#ffffff") for colour in LANE_COLOURS]
        self.missed_arrows = [faded(frames[lane], 89) for lane, frames in enumerate(self.arrows)]
        self.receptors = arrow_frames(None, "#b9a6e6", None)
        self.receptors_on = arrow_frames("#ffffff", "#ffffff", None)

        width = LANE_W * 4 + 12
        self.track_bg = translucent((width, BOTTOM - TOP), (10, 6, 22), 0.74)
        self.lane_tints = [translucent((LANE_W - 2, BOTTOM - TOP), pygame.Color(c), 0) for c in LANE_COLOURS]
        self.beat_line = translucent((LANE_W * 4, 2), (255, 255, 255), 0.12)
        self.progress_bg = translucent((width, 2), (255, 255, 255), 0.15)
        self.hype_bg = translucent((104, 9), (10, 6, 22), 0.8)
        self.results_bg = translucent((300, 168), (10, 6, 22), 0.88)

    def reset_score(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.counts = {"perfect": 0, "great": 0, "good": 0, "miss": 0}
        self.hype = 0.5
        self.flash = [0.0] * 4
        self.judge_name = None
        self.judge_t = 0
        self.pose = None
        self.grade = ""
        self.new_best = False

    def best_key(self, idx, diff):
        return f"together-runway-best-{SONGS[idx]['id']}-{diff}"

    def get_best(self, idx, diff):
        return int(self.best.get(self.best_key(idx, diff), 0))

    def set_diff(self, diff):
        if self.on and not self.done:
            return
        self.diff = diff

    # ---------- clock ----------

    def clock(self):
        """Seconds into the rendered file, following the audio playback position."""
        now = time.perf_counter()
        if self.audio:
            pos = pygame.mixer.music.get_pos()
            if pos >= 0 and pos != self.last_pos:
                self.last_pos = pos
                # get_pos only moves once per audio buffer, so ease towards it rather than jumping.
                target = now - (pos / 1000 - OUTPUT_LATENCY)
                if abs(target - self.anchor) > 0.05:
                    self.anchor = target
                else:
                    self.anchor += (target - self.anchor) * 0.1
        return now - self.anchor

    def song_time(self):
        return self.clock() - music.song_start(self.song)

    # ---------- starting and stopping ----------

    def start(self, idx=None):
        idx = self.song_idx if idx is None else idx
        self.song_idx = idx
        song = SONGS[idx]
        if not music.is_ready(song):
            self.loading = idx
            self.game.say(f"Tuning up {song['name']}...")
            return
        self.loading = None
        self.song = song
        self.spb = 60 / song["bpm"]

        self.game.centre()
        self.game.harry.dir = "front"
        self.reset_score()
        self.notes = build_chart(song, self.diff)
        self.on = True
        self.done = False

        self.last_pos = None
        self.anchor = time.perf_counter()
        if self.audio:
            pygame.mixer.music.load(music.path_for(song))
            pygame.mixer.music.play()
        self.game.say(f"{song['name']} - {DIFF_NAMES[self.diff]}: hit the arrows as they reach the top. Esc stops.")

    def stop(self):
        if self.audio:
            pygame.mixer.music.fadeout(100)
        self.on = False
        self.done = False
        self.game.harry.dir = "front"
        self.game.say("Free roam. Pick a song or press Enter to play.")

    def finish(self):
        self.done = True
        c = self.counts
        accuracy = (c["perfect"] + c["great"] * 0.7 + c["good"] * 0.4) / len(self.notes)
        self.grade = next((g for g, need in (("S", 0.95), ("A", 0.85), ("B", 0.7), ("C", 0.5)) if accuracy >= need), "D")
        if self.score > self.get_best(self.song_idx, self.diff):
            self.new_best = True
            self.best[self.best_key(self.song_idx, self.diff)] = self.score
            try:
                with open(SAVE, "w") as f:
                    json.dump(self.best, f, indent=1)
            except OSError:
                pass
        harry = self.game.harry
        self.game.confetti(120, harry.x, harry.y)
        self.game.say(f"{self.song['name']}: grade {self.grade} - {self.score:,} points. Enter plays again, Esc walks the runway.")

    # ---------- judging ----------

    def judge(self, name, lane):
        self.counts[name] += 1
        if name == "miss":
            self.combo = 0
            self.hype = max(0, self.hype - MISS_HYPE)
            self.pose = {"miss": True, "t": 0.3}
        else:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.score += POINTS[name] + min(self.combo, 100) * 5
            self.hype = min(1, self.hype + HYPE[name])
            self.pose = {"lane": lane, "t": 0.24}
            if self.combo % 25 == 0:
                harry = self.game.harry
                self.game.confetti(50, harry.x, harry.y)
        self.judge_name = name
        self.judge_t = 0.5

    def hit(self, lane):
        if not self.on or self.done:
            return
        self.flash[lane] = 0.14
        st = self.song_time()
        best, best_d = None, 9
        for n in self.notes:
            if n["j"] or n["lane"] != lane:
                continue
            d = abs(n["t"] - st)
            if d < best_d:
                best_d, best = d, n
            if n["t"] - st > WINDOWS["good"]:
                break
        if best is None or best_d > WINDOWS["good"]:
            return
        best["j"] = next(name for name in ("perfect", "great", "good") if best_d <= WINDOWS[name])
        self.judge(best["j"], lane)

    def update(self, dt):
        if self.loading is not None and music.is_ready(SONGS[self.loading]):
            self.start(self.loading)
        if not self.on:
            return
        st = self.song_time()
        for n in self.notes:
            if n["t"] - st > 0:
                break
            if not n["j"] and st - n["t"] > WINDOWS["good"]:
                n["j"] = "miss"
                self.judge("miss", n["lane"])
        self.flash = [max(0, f - dt) for f in self.flash]
        if self.judge_name:
            self.judge_t -= dt
            if self.judge_t <= 0:
                self.judge_name = None
        if self.pose:
            self.pose["t"] -= dt
            if self.pose["t"] <= 0:
                self.pose = None
        if not self.done and st > self.song["bars"] * 4 * self.spb + 0.6:
            self.finish()

    def dance_frame(self):
        st = self.song_time()
        return 0 if st < 0 else int(st // self.spb) % 8

    # ---------- drawing ----------

    def draw(self, screen):
        if self.loading is not None:
            text.draw(screen, "TUNING UP...", screen.get_width() / 2, 120, 18, "#ffffff")
        if not self.on:
            return
        st, spb = self.song_time(), self.spb
        x0, w = TRACK_X - 6, LANE_W * 4 + 12
        screen.blit(self.track_bg, (x0, TOP))

        pulse = max(0, 1 - (st / spb % 1) * 3) if st >= 0 else 0
        for lane, tint in enumerate(self.lane_tints):
            tint.set_alpha(min(255, round((0.07 + pulse * 0.06 + self.flash[lane] * 1.6) * 255)))
            screen.blit(tint, (TRACK_X + lane * LANE_W + 1, TOP))

        # Rainbow borders that slowly scroll through the lane colours.
        for y in range(TOP, BOTTOM):
            tt = (y - TOP) / (BOTTOM - TOP)
            colour = LANE_COLOURS[min(3, int((tt * 2 + st * 0.25) % 1 * 4))]
            screen.fill(colour, (x0, y, 2, 1))
            screen.fill(colour, (x0 + w - 2, y, 2, 1))

        first_beat = math.ceil(st / spb)
        for b in range(first_beat, first_beat + 10):
            y = REC_Y + 13 + (b * spb - st) * SPEED
            if REC_Y < y < BOTTOM:
                screen.blit(self.beat_line, (TRACK_X, round(y)), (0, 0, LANE_W * 4, 2 if b % 4 == 0 else 1))

        for lane in range(4):
            frames = self.receptors_on if self.flash[lane] > 0 else self.receptors
            screen.blit(frames[lane], (round(lane_x(lane) - 13), REC_Y))
        for n in self.notes:
            if n["j"] and n["j"] != "miss":
                continue
            y = REC_Y + (n["t"] - st) * SPEED
            if y > BOTTOM:
                break
            if y < TOP - 26:
                continue
            lane = n["lane"]
            arrow = self.missed_arrows[lane] if n["j"] == "miss" else self.arrows[lane][lane]
            screen.blit(arrow, (round(lane_x(lane) - 13), round(y)))

        cx = TRACK_X + LANE_W * 2
        if self.judge_name:
            text.draw(screen, self.judge_name.upper(), cx, 98 - (0.5 - self.judge_t) * 10, 16, JUDGE_COLOURS[self.judge_name])
        if self.combo >= 4:
            text.draw(screen, str(self.combo), cx, 126, 24, "#ffffff")
            text.draw(screen, "COMBO", cx, 154, 10, LABEL)
        text.draw(screen, f"{self.score:,}", TRACK_X + LANE_W * 4 + 4, 4, 12, "#ffffff", "right")
        text.draw(screen, f"{self.song['name'].upper()} · {DIFF_NAMES[self.diff].upper()}", TRACK_X - 10, 4, 10, LABEL, "right")

        text.draw(screen, "CROWD", 10, 4, 10, LABEL, "left")
        screen.blit(self.hype_bg, (52, 6))
        filled = round(self.hype * 100)
        for quarter in range(4):
            width = min(25, filled - quarter * 25)
            if width > 0:
                screen.fill(HYPE_COLOURS[quarter], (54 + quarter * 25, 8, width, 5))

        progress = max(0, min(1, st / (self.song["bars"] * 4 * spb)))
        screen.blit(self.progress_bg, (x0, BOTTOM + 2))
        screen.fill("#fcce4a", (x0, BOTTOM + 2, round(w * progress), 2))

        middle = screen.get_width() / 2 - 60
        if st < 0:
            beats_left = math.ceil(-st / spb)
            if beats_left > 3:
                text.draw(screen, self.song["name"].upper(), middle, 120, 18, "#ffffff")
            else:
                text.draw(screen, str(beats_left), middle, 120, 34, "#ffffff")
        elif st < spb:
            text.draw(screen, "GO!", middle, 120, 34, "#fcce4a")

        if self.done:
            self.draw_results(screen)

    def draw_results(self, screen):
        screen.blit(self.results_bg, (140, 92))
        screen.fill("#ff5ccf", (140, 92, 300, 2))
        screen.fill("#46e0ff", (140, 258, 300, 2))
        text.draw(screen, f"{self.song['name'].upper()} · {DIFF_NAMES[self.diff].upper()}", 290, 100, 14, LABEL)
        text.draw(screen, self.grade, 200, 124, 60, GRADE_COLOURS[self.grade])
        c = self.counts
        rows = [(f"PERFECT {c['perfect']}", "#fcce4a"), (f"GREAT {c['great']}", "#46e0ff"), (f"GOOD {c['good']}", "#ff8fd8"),
                (f"MISS {c['miss']}", "#9a8ab8"), (f"MAX COMBO {self.max_combo}", "#ffffff")]
        for i, (line, colour) in enumerate(rows):
            text.draw(screen, line, 264, 124 + i * 16, 12, colour, "left")
        text.draw(screen, f"{self.score:,} PTS" + ("  NEW BEST!" if self.new_best else ""), 290, 212, 14, "#ffffff")
        text.draw(screen, "ENTER: AGAIN    ESC: WALK", 290, 236, 10, LABEL)
