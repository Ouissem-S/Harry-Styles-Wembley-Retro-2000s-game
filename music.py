import math
import os
import threading
import wave

import numpy as np

# All three tracks are original compositions written for this game.
# Time runs on a 16th-note grid; see rhythm.py for how the charts are built from the same data.
SONGS = [
    {"id": "neon", "name": "Neon Laps", "style": "Synth-pop", "bpm": 128, "bars": 36,
     "prog": [(52, [0, 3, 7]), (48, [0, 4, 7]), (55, [0, 4, 7]), (50, [0, 4, 7])],  # Em  C  G  D
     "drum": {"kick": [0, 4, 8, 12], "clap": [4, 12], "hat": [1, 3, 5, 7, 9, 11, 13, 15], "open": [2, 6, 10, 14]},
     "bass": {"type": "sawtooth", "cut": 900, "vol": 0.17,
              "pat": [(0, 0, 2), (2, 0, 2), (4, 0, 2), (6, 0, 2), (8, 0, 2), (10, 0, 2), (12, 0, 2), (14, 12, 2)]},
     "lead": {"type": "square", "cut": 3200, "vol": 0.075, "phrase": [
         (0, 71, 2), (2, 71, 2), (4, 69, 2), (6, 67, 4), (10, 64, 2), (12, 67, 4),
         (16, 76, 4), (20, 74, 2), (22, 72, 2), (24, 71, 6),
         (32, 67, 2), (34, 69, 2), (36, 71, 4), (40, 74, 2), (42, 71, 2), (44, 69, 4),
         (48, 66, 2), (50, 67, 2), (52, 69, 4), (56, 74, 6)]},
     "arp": {"type": "square", "cut": 2600, "vol": 0.035, "pat": [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 4, 3, 2, 1, 2, 3]},
     "pad": {"vol": 0.03},
     "sec": lambda b: {"kick": b >= 2 and not (20 <= b < 22), "clap": 4 <= b < 20 or b >= 22, "hat": True,
                       "bass": b >= 4 and not (20 <= b < 24), "lead": 12 <= b < 20 or b >= 24,
                       "arp": b < 4 or b >= 12, "pad": 4 <= b < 12 or 20 <= b < 24, "filter": 20 <= b < 24}},

    {"id": "velvet", "name": "Velvet Floor", "style": "Disco-funk", "bpm": 112, "bars": 32,
     "prog": [(50, [0, 3, 7, 10, 14]), (43, [0, 4, 7, 10]), (48, [0, 4, 7, 11]), (45, [0, 3, 7, 10])],  # Dm9 G7 Cmaj7 Am7
     "drum": {"kick": [0, 4, 8, 12], "clap": [4, 12], "hat": [1, 3, 5, 7, 9, 11, 13, 15], "open": [2, 6, 10, 14]},
     "bass": {"type": "square", "cut": 650, "vol": 0.2,
              "pat": [(0, 0, 2), (3, 12, 1), (6, 0, 2), (8, 12, 1), (10, 7, 2), (12, 0, 1), (14, 12, 2)]},
     "lead": {"type": "sawtooth", "cut": 2400, "vol": 0.06, "phrase": [
         (2, 69, 2), (4, 72, 2), (7, 74, 3), (10, 72, 2), (12, 69, 3),
         (18, 67, 2), (20, 71, 2), (22, 74, 4), (27, 77, 2), (29, 76, 3),
         (32, 76, 2), (34, 74, 2), (36, 72, 4), (41, 67, 2), (43, 69, 3),
         (48, 72, 2), (50, 69, 2), (52, 67, 2), (54, 64, 6)]},
     "pluck": {"type": "square", "cut": 1800, "vol": 0.03, "steps": [0, 3, 6, 9, 10, 13]},
     "stab": {"type": "sawtooth", "cut": 2200, "vol": 0.035, "steps": [6, 14]},
     "sec": lambda b: {"kick": b >= 2 and not (12 <= b < 16), "clap": b >= 4, "hat": b >= 0, "bass": True,
                       "lead": 4 <= b < 12 or 16 <= b < 28, "pluck": b >= 4, "stab": 8 <= b < 12 or b >= 16,
                       "filter": 12 <= b < 16}},

    {"id": "glow", "name": "Slow Glow", "style": "Half-time", "bpm": 90, "bars": 24,
     "prog": [(41, [0, 4, 7]), (45, [0, 3, 7]), (46, [0, 4, 7]), (48, [0, 4, 7])],  # F  Am  Bb  C
     "drum": {"kick": [0, 10], "clap": [8], "hat": [2, 6, 10, 14], "open": []},
     "bass": {"type": "triangle", "cut": 900, "vol": 0.26, "pat": [(0, 0, 6), (10, 0, 2), (12, 7, 4)]},
     "lead": {"type": "triangle", "cut": 4000, "vol": 0.1, "phrase": [
         (0, 69, 6), (6, 72, 2), (8, 69, 4), (12, 67, 4),
         (16, 64, 6), (22, 67, 2), (24, 69, 8),
         (32, 74, 6), (38, 72, 2), (40, 70, 4), (44, 69, 4),
         (48, 67, 4), (52, 69, 2), (54, 72, 2), (56, 67, 8)]},
     "pad": {"vol": 0.045},
     "sec": lambda b: {"kick": b >= 4, "clap": b >= 4, "hat": b >= 2, "bass": b >= 2, "lead": 4 <= b < 22,
                       "pad": True, "filter": False}},
]

RATE = 44100
# Silence before the count-in, so the first beep isn't clipped while the device wakes up.
LEAD_IN = 0.35
# Ringing notes keep going after the last step.
TAIL = 3.0
MASTER = 0.55
# Bump this when the synth changes, so old renders in the cache are thrown away.
VERSION = 1

CACHE = os.path.join(os.path.dirname(__file__), ".cache", "music")

# One second of noise shared by every clap and hat, like a single noise buffer.
NOISE = np.random.default_rng(7).uniform(-1, 1, RATE)


def mtof(m):
    return 440 * 2 ** ((m - 69) / 12)


def song_start(song):
    """Seconds into the rendered file where song time 0 (the first downbeat) lands."""
    return LEAD_IN + 4 * 60 / song["bpm"]


def path_for(song):
    return os.path.join(CACHE, f"{song['id']}-v{VERSION}.wav")


def is_ready(song):
    return os.path.exists(path_for(song))


# ---------- voices ----------

def envelope(peak, dur, attack=0.003):
    """Rise from silence to the peak, then fall exponentially to almost nothing by the end of the note."""
    end = max(dur, attack + 0.02)
    t = np.arange(int(end * RATE)) / RATE
    rise = 0.0001 + (peak - 0.0001) * t / attack
    fall = peak * (0.0008 / peak) ** ((t - attack) / (end - attack))
    return np.where(t < attack, rise, fall)


def poly_blep(t, dt):
    """Smooths the jumps in square and saw waves so high notes don't alias."""
    out = np.zeros_like(t)
    lo = t < dt
    x = t[lo] / dt
    out[lo] = x + x - x * x - 1
    hi = t > 1 - dt
    x = (t[hi] - 1) / dt
    out[hi] = x * x + x + x + 1
    return out


def oscillator(kind, freq, n):
    dt = freq / RATE
    t = (np.arange(n) * dt) % 1.0
    if kind == "sine":
        return np.sin(t * math.tau)
    if kind == "triangle":
        return 1 - 4 * np.abs(t - 0.5)
    if kind == "sawtooth":
        return 2 * t - 1 - poly_blep(t, dt)
    return np.where(t < 0.5, 1.0, -1.0) + poly_blep(t, dt) - poly_blep((t + 0.5) % 1.0, dt)


def biquad(kind, freq, n):
    """Frequency response of a Web Audio style biquad (default Q) on an rfft of length n."""
    w0 = math.tau * freq / RATE
    cos, sin = math.cos(w0), math.sin(w0)
    if kind == "bandpass":
        alpha = sin / 2
        b = (alpha, 0, -alpha)
    else:
        # Lowpass and highpass read Q in dB, and the default is 1 dB.
        alpha = sin / (2 * 10 ** (1 / 20))
        b = ((1 - cos) / 2, 1 - cos, (1 - cos) / 2) if kind == "lowpass" else ((1 + cos) / 2, -(1 + cos), (1 + cos) / 2)
    a = (1 + alpha, -2 * cos, 1 - alpha)
    z = np.exp(-1j * np.linspace(0, math.pi, n // 2 + 1))
    return (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)


def apply_filter(x, kind, freq):
    # Filtering in the frequency domain, with enough padding that the filter's ringing doesn't wrap around.
    n = 1 << (len(x) + 4096 - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, n) * biquad(kind, freq, n), n)[:len(x)]


def tone(kind, midi, peak, dur, cut, attack=0.003, detune=0):
    env = envelope(peak, dur, attack)
    wave_ = oscillator(kind, mtof(midi) * 2 ** (detune / 1200), len(env))
    return apply_filter(wave_, "lowpass", cut) * env


def noise_hit(kind, freq, peak, dec):
    env = envelope(peak, dec, 0.001)
    return apply_filter(NOISE[:len(env)], kind, freq) * env


def kick():
    env = envelope(0.9, 0.2)
    t = np.arange(len(env)) / RATE
    freq = np.where(t < 0.12, 150 * (42 / 150) ** (t / 0.12), 42)
    return np.sin(np.cumsum(freq) * math.tau / RATE) * env


# ---------- arranging ----------

class Mix:
    def __init__(self, seconds):
        self.dry = np.zeros(int(seconds * RATE) + 1)
        # Everything in a breakdown bar goes through one muffling lowpass at the end.
        self.muffled = np.zeros_like(self.dry)
        self.voices = {}

    def add(self, t, key, make, muffled=False):
        # The same note comes round again and again, so render each one once.
        if key not in self.voices:
            self.voices[key] = make()
        voice = self.voices[key]
        bus = self.muffled if muffled else self.dry
        start = int(round(t * RATE))
        end = min(len(bus), start + len(voice))
        bus[start:end] += voice[:end - start]


def play_step(mix, song, st, t):
    spb = 60 / song["bpm"]
    if st < 0:
        if st % 4 == 0:
            m = 88 if st == -16 else 81
            mix.add(t, ("beep", m), lambda: tone("square", m, 0.12, 0.06, 4000))
        return

    bar, q = st // 16, st % 16
    sec = song["sec"](bar)
    root, chord = song["prog"][bar % len(song["prog"])]
    f = bool(sec.get("filter"))
    drum = song["drum"]

    if sec.get("kick") and q in drum["kick"]:
        mix.add(t, ("kick",), kick)
    if sec.get("clap") and q in drum["clap"]:
        mix.add(t, ("clap",), lambda: noise_hit("bandpass", 1700, 0.34, 0.13), f)
        mix.add(t + 0.012, ("clap2",), lambda: noise_hit("bandpass", 1500, 0.2, 0.1), f)
    if sec.get("hat"):
        if q in drum["open"]:
            mix.add(t, ("open",), lambda: noise_hit("highpass", 7500, 0.14, 0.12), f)
        elif q in drum["hat"]:
            mix.add(t, ("hat",), lambda: noise_hit("highpass", 9000, 0.05, 0.03), f)

    bass = song["bass"]
    if sec.get("bass"):
        for s, off, d in bass["pat"]:
            if s == q:
                dur = d * spb / 4 * 0.9
                mix.add(t, ("bass", root + off, d), lambda: tone(bass["type"], root + off, bass["vol"], dur, bass["cut"], 0.004), f)

    lead = song["lead"]
    if sec.get("lead"):
        ps = (bar % 4) * 16 + q
        for s, m, d in lead["phrase"]:
            if s == ps:
                dur = d * spb / 4 * 0.92
                mix.add(t, ("lead-", m, d), lambda: tone(lead["type"], m, lead["vol"], dur, lead["cut"], 0.01, -7), f)
                mix.add(t, ("lead+", m, d), lambda: tone(lead["type"], m, lead["vol"] * 0.8, dur, lead["cut"], 0.01, 7), f)

    arp = song.get("arp")
    if sec.get("arp") and arp:
        idx = arp["pat"][q]
        m = root + 24 + chord[idx % len(chord)] + 12 * (idx // len(chord))
        mix.add(t, ("arp", m), lambda: tone(arp["type"], m, arp["vol"], 0.09, arp["cut"], 0.002), f)

    pluck = song.get("pluck")
    if sec.get("pluck") and pluck and q in pluck["steps"]:
        m = root + 24 + chord[(q >> 1) % len(chord)]
        mix.add(t, ("pluck", m), lambda: tone(pluck["type"], m, pluck["vol"], 0.06, pluck["cut"], 0.002), f)

    stab = song.get("stab")
    if sec.get("stab") and stab and q in stab["steps"]:
        for iv in chord[:4]:
            m = root + 24 + iv
            mix.add(t, ("stab", m), lambda: tone(stab["type"], m, stab["vol"], 0.16, stab["cut"], 0.004), f)

    pad = song.get("pad")
    if sec.get("pad") and pad and q == 0:
        for iv in chord[:3]:
            m = root + 12 + iv
            mix.add(t, ("pad", m), lambda: tone("triangle", m, pad["vol"], 4 * spb * 0.95, 1600, 0.35), f)


def compress(x, threshold=-24.0, knee=30.0, ratio=12.0, attack=0.003, release=0.25):
    """A plain feed-forward compressor with the same default settings as a browser's DynamicsCompressor."""
    def curve(db):
        over = db - threshold
        soft = np.where(over < -knee / 2, db, db + (1 / ratio - 1) * (over + knee / 2) ** 2 / (2 * knee))
        return np.where(over > knee / 2, threshold + over / ratio, soft)

    block = 32
    n = len(x) // block * block
    peaks = np.abs(x[:n]).reshape(-1, block).max(axis=1)
    level = 20 * np.log10(np.maximum(peaks, 1e-6))
    target = curve(level) - level

    up = math.exp(-block / (attack * RATE))
    down = math.exp(-block / (release * RATE))
    gain_db = np.empty_like(target)
    g = 0.0
    for i, want in enumerate(target.tolist()):
        k = up if want < g else down
        g = want + (g - want) * k
        gain_db[i] = g

    # Make up some of the level the curve takes away from a full-scale signal.
    makeup = -float(curve(np.array(0.0)) * 0.6)
    gains = np.repeat(10 ** ((gain_db + makeup) / 20), block)
    gains = np.concatenate([gains, np.full(len(x) - n, gains[-1] if len(gains) else 1.0)])
    return x * gains


def render(song):
    spb = 60 / song["bpm"]
    step_len = spb / 4
    first = song_start(song)
    mix = Mix(first + song["bars"] * 16 * step_len + TAIL)
    for st in range(-16, song["bars"] * 16):
        play_step(mix, song, st, first + st * step_len)
    out = mix.dry + apply_filter(mix.muffled, "lowpass", 700)
    return np.clip(compress(out * MASTER), -1, 1)


def write_wav(path, samples):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pcm = (samples * 32767).astype("<i2")
    stereo = np.repeat(pcm, 2)
    # Write to a temporary name first so a half-written file is never played.
    tmp = path + ".part"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(stereo.tobytes())
    os.replace(tmp, path)


def ensure(song):
    if not is_ready(song):
        write_wav(path_for(song), render(song))
    return path_for(song)


def prepare_all():
    """Render any songs that aren't cached yet, in the background so the stage loads straight away."""
    def work():
        for song in SONGS:
            ensure(song)
    threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    import time
    for song in SONGS:
        began = time.perf_counter()
        write_wav(path_for(song), render(song))
        print(f"{song['name']}: {time.perf_counter() - began:.1f}s -> {path_for(song)}")
