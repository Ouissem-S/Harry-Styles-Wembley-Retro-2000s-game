# Build "Together Runway": a pixel-art concert stage game with a rhythm mode

You are working in my game project. Build the game described below inside this codebase.

A complete, working reference implementation is in `reference/together_runway.html`. It is a single self-contained HTML page with all assets embedded. When anything in this brief is unclear, open that file, read its `<script>`, and match its behaviour exactly. Do not copy its embedded base64 images; use the PNG files in `assets/` instead.

## 0. Engine and setup

- Use the engine or framework this project already uses. Follow its existing folder layout, naming and code style.
- If the project is empty, use **Phaser 3 + TypeScript + Vite**.
- Copy everything in `assets/` into the project's asset folder unchanged. Never edit, resize or re-export the PNGs.
- Before writing code, tell me which engine you detected and list the files you plan to create.

## 1. Rendering rules (pixel-perfect)

- Native resolution: **640 × 360**. All coordinates in this brief are in these native pixels.
- Scale the whole game by the largest **whole number** that fits the window (×3 = 1920 × 1080, ×2 = 1280 × 720). Never use fractional scaling unless the window is smaller than 640 × 360.
- Nearest-neighbour filtering everywhere, no smoothing or anti-aliasing, and round every draw position to whole pixels.
- Text drawn inside the game uses the "Pixelify Sans" font (Google Fonts) with a 1-pixel dark outline `#1a0b26`. Snap text alpha to fully on or fully off so it stays crisp.

## 2. Assets (`assets/`)

| File | What it is |
|---|---|
| `concert_pixel_640x360.png` | The stage background: main stage and screens on the left, rectangular runway with a cross through the middle, centre square, arches over the two right-hand pits, crowd and stands. |
| `walk_mask_640x360.png` | Walkable area. White (R > 127) = Harry can stand here. Black = not walkable. Same size as the background. |
| `layout_points.json` | Key points in native pixels: `intersection` (331, 203) is the start point; runway ends and arch tops are included too. |
| `sprites2026/harry_suit_*.png` | Harry in the red suit jacket, shirt and tie. |
| `sprites2026/harry_shirtsleeves_*.png` | Harry with the jacket off, rolled sleeves, loosened tie (finale look). |
| `sprites2026/dancers_dance.png` | Two backing dancers. |
| `sprites2026/sprites2026.json` | Machine-readable description of every sheet below. |

**Every sprite frame is 24 × 36 px. The anchor is the feet at (12, 35)**: to draw a character standing at (x, y), draw the frame's top-left at (x − 12, y − 35).

Per outfit (`suit`, `shirtsleeves`), there are six sheets:

| Sheet | Rows | Columns | Speed |
|---|---|---|---|
| `main` | back, front, left, right | 0 idle, 1 special (back: wave with mic up; front: sing into mic; sides: breathe), 2–5 walk | walk 8 fps |
| `run` | back, front, left, right | 6 frames, pumping-arm run | 12 fps |
| `sprint` | back, front, left, right | 6 frames, open-armed sprint | 12 fps |
| `hop` | back, front, left, right | 4 frames: crouch, lift, tuck, land | see 4.3 |
| `dance` | 1 row | 8 frames, "Dance No More" sashay, facing the crowd | 6 fps (free roam) or one frame per beat (rhythm) |
| `emotes` | row 0 bow (3), row 1 blow kiss (3), row 2 peace sign (2) | | see 4.3 |

`dancers_dance.png` has 2 rows (dancer A, dancer B) × 8 frames, matching Harry's dance frame for frame.

"back" means facing away from the camera, toward the stage screens. "front" faces the crowd and camera.

## 3. World and movement

- Draw the background at (0, 0). Harry starts at the intersection (331, 203) facing **back**, in the **suit** outfit.
- Walk speed is 44 px/s. Run speed is 82 px/s in the suit and 92 px/s in shirtsleeves. Vertical movement is multiplied by 0.75 for the perspective.
- **Walkable check:** a position is valid if the mask pixel at (round(x), round(y)) is white.
- **Sliding along angled walkways (important):** the walkways are diagonal on screen, so a straight step often leaves the mask. For each step (mx, my), try rotating the step by these angles in radians, in this order, and take the first valid one: `0, 0.35, −0.35, 0.7, −0.7, 1.05, −1.05, 1.4, −1.4, 1.57, −1.57`. If none is valid, don't move.
- **Facing:** if |dx| > |dy|, face left or right; otherwise face back (moving up) or front (moving down).
- Draw a small shadow under every character: a dark rectangle 14 px wide and 2 px tall at the feet, plus a 10 × 1 px rectangle under it, colour rgba(20, 8, 40, 0.55).
- Draw a soft pink radial spotlight (additive blend, about 34 px radius, alpha 0.35) centred 10 px above Harry's feet.
- Draw characters back to front, sorted by their feet y.

## 4. Free-roam mode

### 4.1 Controls

| Input | Action |
|---|---|
| Arrows / WASD | Walk |
| Hold Shift | Run. In suit: `run` sheet. In shirtsleeves: `sprint` sheet. |
| F | Toggle the Dance No More dance with the dancers |
| H | Hop |
| B / K / P | Bow / Blow a kiss / Peace sign |
| Q | Water spray |
| Space | Wave (back row, main column 1) with a confetti burst |
| J | Jacket off / on (switch outfit) |
| R | Back to the centre, facing back |
| 1 / 2 / 3, Enter | Start a rhythm song (section 5) |

Also add on-screen buttons for touch: a 4-way D-pad and buttons for Run (toggle), Dance, Hop, Bow, Kiss, Peace, Water, Wave, Jacket, Centre. Show the setlist (section 5.6) under the game view.

### 4.2 Idle and walk animation

- Idle: main column 0. Every 2.4 s, show column 1 for 0.6 s.
- Walk: main columns 2 to 5 at 8 fps.

### 4.3 One-shot actions

Walking cancels any action except hop.

| Action | Duration | Frames |
|---|---|---|
| Hop | 0.5 s | `hop` frame 0 for progress p < 0.18, 1 for p < 0.45, 2 for p < 0.8, then 3. Move forward in the facing direction at 28 px/s (with the slide rule). Lift the sprite by `sin(clamp((p − 0.15) / 0.7, 0, 1) × π) × 7` px; the shadow stays on the floor. |
| Bow | 1.3 s | emotes row 0, sequence 0, 1, 2, 2, 2, 1, 0 spread evenly over the duration. Faces front. |
| Kiss | 1.0 s | emotes row 1, sequence 0, 0, 1, 2, 2. At 0.55 s, spawn a pixel heart that floats up and to the right for 1.6 s. |
| Peace | 1.2 s | emotes row 2, sequence 0, 1, 0, 1 |
| Water | 1.1 s | front main row, sequence 1, 1, 0, 0. Spawn 26 light-blue droplets from about 26 px above the feet, shooting upward with gravity. |
| Wave | 0.9 s | back main column 1, plus 40 confetti pieces |

### 4.4 Dance No More (free roam)

Pressing F plays the 8-frame `dance` sheet at 6 fps, facing front. Two dancers stand about 19 px to Harry's left (dancer A, row 0, 2 px higher) and right (dancer B, row 1, 2 px lower). Snap each dancer to the nearest walkable pixel within 14 px. They play the same frame as Harry. Walking stops the dance.

## 5. Rhythm mode (four-lane arrow track)

### 5.1 Starting and stopping

Start from a setlist card, 1/2/3 or Enter. On start:

1. Put Harry at the intersection facing front, with both dancers.
2. Build the chart (5.3) and play a 1-bar count-in (4 beats) with the song name, then "3, 2, 1, GO!".
3. Esc stops the song. On the results screen, Enter plays the same song again.

During the song, arrows and WASD hit lanes instead of moving Harry, and other actions are disabled.

### 5.2 Music: three original tracks

The three songs are **original compositions** written for this game. **Do not use, imitate or reference any real artist's recordings, melodies or lyrics.** Synthesise them live with the Web Audio API. If the engine cannot synthesise audio, write a small Node or browser script that renders each track with `OfflineAudioContext` to `.ogg`, and play that file instead. In both cases, the timing source for gameplay must be the audio clock.

Song data (copy as-is):

```js
const SONGS = [
  { id: "neon", name: "Neon Laps", style: "Synth-pop", bpm: 128, bars: 36,
    prog: [[52, [0, 3, 7]], [48, [0, 4, 7]], [55, [0, 4, 7]], [50, [0, 4, 7]]],          // Em  C  G  D
    drum: { kick: [0, 4, 8, 12], clap: [4, 12], hat: [1, 3, 5, 7, 9, 11, 13, 15], open: [2, 6, 10, 14] },
    bass: { type: "sawtooth", cut: 900, vol: 0.17, pat: [[0, 0, 2], [2, 0, 2], [4, 0, 2], [6, 0, 2], [8, 0, 2], [10, 0, 2], [12, 0, 2], [14, 12, 2]] },
    lead: { type: "square", cut: 3200, vol: 0.075, phrase: [
      [0, 71, 2], [2, 71, 2], [4, 69, 2], [6, 67, 4], [10, 64, 2], [12, 67, 4],
      [16, 76, 4], [20, 74, 2], [22, 72, 2], [24, 71, 6],
      [32, 67, 2], [34, 69, 2], [36, 71, 4], [40, 74, 2], [42, 71, 2], [44, 69, 4],
      [48, 66, 2], [50, 67, 2], [52, 69, 4], [56, 74, 6]] },
    arp: { type: "square", cut: 2600, vol: 0.035, pat: [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 4, 3, 2, 1, 2, 3] },
    pad: { vol: 0.03 },
    sec: (b) => ({ kick: b >= 2 && !(b >= 20 && b < 22), clap: b >= 4 && b < 20 || b >= 22, hat: true,
                   bass: b >= 4 && !(b >= 20 && b < 24), lead: (b >= 12 && b < 20) || b >= 24,
                   arp: b < 4 || b >= 12, pad: b >= 4 && b < 12 || (b >= 20 && b < 24), filter: b >= 20 && b < 24 }) },

  { id: "velvet", name: "Velvet Floor", style: "Disco-funk", bpm: 112, bars: 32,
    prog: [[50, [0, 3, 7, 10, 14]], [43, [0, 4, 7, 10]], [48, [0, 4, 7, 11]], [45, [0, 3, 7, 10]]],   // Dm9 G7 Cmaj7 Am7
    drum: { kick: [0, 4, 8, 12], clap: [4, 12], hat: [1, 3, 5, 7, 9, 11, 13, 15], open: [2, 6, 10, 14] },
    bass: { type: "square", cut: 650, vol: 0.2, pat: [[0, 0, 2], [3, 12, 1], [6, 0, 2], [8, 12, 1], [10, 7, 2], [12, 0, 1], [14, 12, 2]] },
    lead: { type: "sawtooth", cut: 2400, vol: 0.06, phrase: [
      [2, 69, 2], [4, 72, 2], [7, 74, 3], [10, 72, 2], [12, 69, 3],
      [18, 67, 2], [20, 71, 2], [22, 74, 4], [27, 77, 2], [29, 76, 3],
      [32, 76, 2], [34, 74, 2], [36, 72, 4], [41, 67, 2], [43, 69, 3],
      [48, 72, 2], [50, 69, 2], [52, 67, 2], [54, 64, 6]] },
    pluck: { type: "square", cut: 1800, vol: 0.03, steps: [0, 3, 6, 9, 10, 13] },
    stab: { type: "sawtooth", cut: 2200, vol: 0.035, steps: [6, 14] },
    sec: (b) => ({ kick: b >= 2 && !(b >= 12 && b < 16), clap: b >= 4, hat: b >= 0, bass: true,
                   lead: (b >= 4 && b < 12) || (b >= 16 && b < 28), pluck: b >= 4, stab: b >= 8 && b < 12 || b >= 16,
                   filter: b >= 12 && b < 16 }) },

  { id: "glow", name: "Slow Glow", style: "Half-time", bpm: 90, bars: 24,
    prog: [[41, [0, 4, 7]], [45, [0, 3, 7]], [46, [0, 4, 7]], [48, [0, 4, 7]]],           // F  Am  Bb  C
    drum: { kick: [0, 10], clap: [8], hat: [2, 6, 10, 14], open: [] },
    bass: { type: "triangle", cut: 900, vol: 0.26, pat: [[0, 0, 6], [10, 0, 2], [12, 7, 4]] },
    lead: { type: "triangle", cut: 4000, vol: 0.1, phrase: [
      [0, 69, 6], [6, 72, 2], [8, 69, 4], [12, 67, 4],
      [16, 64, 6], [22, 67, 2], [24, 69, 8],
      [32, 74, 6], [38, 72, 2], [40, 70, 4], [44, 69, 4],
      [48, 67, 4], [52, 69, 2], [54, 72, 2], [56, 67, 8]] },
    pad: { vol: 0.045 },
    sec: (b) => ({ kick: b >= 4, clap: b >= 4, hat: b >= 2, bass: b >= 2, lead: b >= 4 && b < 22, pad: true, filter: false }) },
];
```

How to read it:

- Time runs on a 16th-note grid. `bar = floor(step / 16)`, `q = step % 16`, step length = (60 / bpm) / 4 seconds. Song length = `bars × 16` steps.
- `prog[bar % 4]` = [root MIDI note, chord intervals]. `sec(bar)` says which parts play in that bar.
- **kick:** sine wave, pitch 150 → 42 Hz over 0.12 s, peak 0.9, decay 0.2 s, on `drum.kick` steps.
- **clap:** white noise through a bandpass at 1700 Hz (peak 0.34, 0.13 s), plus a second hit 12 ms later at 1500 Hz (0.2, 0.1 s), on `drum.clap`.
- **hats:** open hat on `drum.open` (highpass 7500 Hz, peak 0.14, 0.12 s); closed hat on the other `drum.hat` steps (highpass 9000 Hz, 0.05, 0.03 s).
- **bass:** for each `[step, semitoneOffset, lengthInSteps]` in `bass.pat`, play `root + offset` with `bass.type` through a lowpass at `bass.cut`, volume `bass.vol`, for length × 0.9.
- **lead:** the `lead.phrase` repeats every 4 bars as `[stepIn64, midi, lengthInSteps]`. Play two `lead.type` oscillators detuned −7 and +7 cents, attack 10 ms, length × 0.92.
- **arp:** `arp.pat[q]` indexes the chord tones from `root + 24`, wrapping up an octave past the last tone. 0.09 s notes.
- **pluck:** on `pluck.steps`, play chord tone `ch[(q >> 1) % ch.length]` from `root + 24`, 0.06 s.
- **stab:** on `stab.steps`, play the first four chord tones from `root + 24`, 0.16 s.
- **pad:** on q = 0, play the first three chord tones from `root + 12` as triangle waves, 350 ms attack, held for one bar.
- When `sec.filter` is true, send that bar's drums and instruments (not the kick) through a 700 Hz lowpass for a muffled breakdown.
- Envelope for every voice: start at 0.0001, rise linearly to the peak over the attack (3 ms unless stated), then fall exponentially to 0.0008 by the end of the note.
- Master gain 0.55 into a dynamics compressor.
- Count-in: four short square-wave beeps (MIDI 88, then 81, 81, 81), 0.06 s each.
- Schedule audio about 150 ms ahead on a 25 ms timer.

### 5.3 Charts (generated from the music, deterministic)

1. Collect events for every step of the song, all on the same time grid:
   - **lead** (priority 3): every lead-note onset in bars where `sec.lead` is on, with its MIDI pitch.
   - **clap** (priority 2): `drum.clap` steps where `sec.clap` is on.
   - **kick** (priority 1): `drum.kick` steps where `sec.kick` is on.
   - **arp** (priority 0, Hard only): even steps in bars with `sec.arp` or `sec.pluck`.
2. Sort the events by time, highest priority first when times are equal.
3. Minimum gap between kept arrows (spb = seconds per beat):
   - Easy: max(spb × 0.98, 0.42 s)
   - Normal: max(spb × 0.48, 0.24 s)
   - Hard: max(spb × 0.24, 0.2 s)
4. Filters:
   - Easy keeps non-lead events only on q % 8 == 0 (if bpm > 100) or q % 4 == 0 (otherwise), and lead events only on q % 4 == 0.
   - Easy and Normal drop a kick if it falls less than spb × 0.98 after the last kept arrow.
5. Lanes are 0 = left, 1 = down, 2 = up, 3 = right.
   - **lead:** if the pitch rises, alternate between lanes 2 and 3; if it falls, alternate between 1 and 0; if it repeats, reuse the last lane.
   - **kick:** Easy cycles 0, 3, 1, 2; Normal and Hard alternate 0 and 3.
   - **clap:** alternate 1 and 2.
   - **arp:** cycle 0 to 3.
6. Double arrows (a second arrow at the same time in lane (lane + 2) % 4):
   - Normal: on q == 0 in lead bars where bar % 4 == 0.
   - Hard: on q == 0 in bars with lead or stab.
7. If the last kept arrow is before the final bar, add a double arrow in lanes 0 and 3 at the start of the final bar.

### 5.4 Judging and scoring

- Timing windows: Perfect ≤ 45 ms, Great ≤ 90 ms, Good ≤ 135 ms.
- A key press judges the closest unjudged arrow in that lane within 135 ms. Presses with no arrow in range do nothing (no penalty).
- An arrow left unjudged 135 ms after its time is a Miss.
- Points: Perfect 1000, Great 700, Good 300, plus min(combo, 100) × 5.
- Combo resets on a Miss. Every 25 combo, burst 50 confetti pieces.
- Crowd hype runs from 0 to 1 and starts at 0.5. Perfect +0.03, Great +0.02, Good +0.006, Miss −0.06. There is no fail state.
- Grade from accuracy = (perfect + great × 0.7 + good × 0.4) / total arrows: S ≥ 0.95, A ≥ 0.85, B ≥ 0.7, C ≥ 0.5, otherwise D.
- Save the best score per song and difficulty (localStorage on web, or the engine's save system) under `together-runway-best-<songId>-<difficulty>`.

### 5.5 Track and HUD layout (native pixels)

- **Track:** 4 lanes, each 34 px wide, starting at x = 484, from y = 20 to y = 348.
  - Background rgba(10, 6, 22, 0.74).
  - Each lane gets a faint tint in its colour (left `#ff5ccf`, down `#46e0ff`, up `#fcce4a`, right `#4fe08f`). The tint pulses on each beat and flashes for 0.14 s when that lane is pressed.
  - 2 px rainbow borders cycling through the lane colours and scrolling slowly.
  - Faint horizontal beat lines (2 px on the first beat of each bar) rising with the arrows.
- **Arrows:** the 13 × 13 arrow shape from the reference, drawn at exactly 2× (26 × 26), filled with the lane colour, a white highlight and a dark outline.
  - Receptors are outline-only arrows at y = 40, and turn white while pressed.
  - Arrows travel from the bottom of the track to the receptors in 1.55 s: `y = 40 + (noteTime − songTime) × speed`, where speed = (348 − 40) / 1.55.
  - A missed arrow stays visible at 35% opacity until it scrolls off.
- **Text:**
  - Judgement text (PERFECT / GREAT / GOOD / MISS) at the track centre around y = 98, rising slightly as it fades over 0.5 s.
  - Combo number (24 px) at y = 126 with "COMBO" under it, shown when combo ≥ 4.
  - Score at the top right. Song name and difficulty at the top, to the left of the track.
- **Hype meter:** a "CROWD" label at (10, 4) and a 100 px bar at (54, 8), coloured pink → orange → yellow → green in quarters.
- **Progress:** a 2 px song-progress bar under the track.
- **Results panel:** at (140, 92), 300 × 168. It shows the song and difficulty, a large grade letter, the Perfect / Great / Good / Miss counts, max combo, points (plus "NEW BEST!" when it is one), and "ENTER: AGAIN  ESC: WALK".

### 5.6 Harry and dancers during a song

- Before beat 0: Harry stands on front main column 0.
- On the beat: Harry and both dancers show `dance` frame `floor(songTime / secondsPerBeat) % 8`.
- On a hit: for 0.24 s, Harry strikes a pose by lane. Left uses dance frame 1, down 5, up 7, right 0.
- On a miss: for 0.3 s, Harry shows front main column 0 and jitters 1 px left and right (a stumble).
- Setlist UI (outside or below the game view): three cards showing number, name, style, BPM and best score for the selected difficulty; an Easy / Normal / Hard toggle (default Normal); and a Stop button while a song is playing.

## 6. Ambient polish

- **Twinkles:** at load, pick about 35% of bright background pixels (r + g + b > 520) below y = 150 that are not on the walk mask. Each one flickers on a sine wave with its own speed and phase in the show palette: `#ee627e #f79454 #fcce4a #7a90da #42b88a #ffffff #ff5ccf #46e0ff`. Skip this if the player prefers reduced motion.
- **Confetti:** 1–2 px pieces in the same palette with gravity, lasting about 2 s.

## 7. Done when

- [ ] The game renders at 640 × 360, scales by whole numbers, and every pixel stays sharp.
- [ ] Harry starts on the intersection facing the screens and can walk the full runway, cross, centre square and both arches, sliding smoothly along the diagonal walkways.
- [ ] Every free-roam action in 4.1 works, and jacket on/off swaps every animation.
- [ ] All three songs play in time. Arrow timing is driven by the audio clock, and charts match section 5.3 for all three difficulties.
- [ ] Judging, scoring, hype, grades and saved best scores match section 5.4.
- [ ] It works with keyboard and touch.
- [ ] Nothing uses real artists' audio or lyrics.

When finished, give me a short summary of the files you created and how to run the game.
