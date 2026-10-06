"""WoW: Forever fishing -- cast, find the bobber, wait for the splash, loot.

Screen-reading only: mss frames, the OS cursor handle and OS-level
mouse/keyboard input. Nothing reads, hooks or modifies the game client.

In-game setup before every run:
- Auto Loot on (Options > Controls).
- Fishing on an action-bar key matching the "Fishing key" param.
- First-person view (scroll fully in), facing open water, camera still.
- UI hidden with Alt+Z, so no nameplates or tooltips sit over the water.
- At least "Max casts" free bag slots -- full bags are not detected.
- Optional fast path: `/console SoftTargetInteract 3` and bind
  "Interact With Target"; put that key in "Interact key" to skip the
  bobber scan.

Calibration (never guessed): capture the window with debug_wow_shot.py,
pick the water region from that screenshot, then run once with
splash threshold 0 (observe-only: logs per-cast diff peaks, never clicks)
and set the threshold between the bobbing baseline and the splash peaks.

Verified 2026-10-06, Stormwind canal at night, 2560x1440 windowed-fullscreen,
UI visible: water_region=860,540,1540,790 (top edge below the far quay --
patrolling guards there light the cursor too), bite_box=120,
splash_threshold=3.5 as the floor under splash_ratio=2.0 (a 4.5 floor missed a
faint 4.36 splash on a calm cast; no-bite peaks stay under 2x their p95).
Bobbing p95 1-3.2, splash peaks 5.5-14.8. Last live
run: 10 casts, bobber found in 1-3 hovers, 7 bites -> 7 fish (bag diff). 25-cast sunrise run (ratio 2.0, floor
4.5, 3 consecutive): 16 bites -> 16 fish, 2-3 splashes missed -> this tuning.
"""
import os
import time
import zlib

import cv2
import numpy as np
import pyautogui
import win32gui
import win32ui

from engine import capture, humanize, window
from engine import input as bot_input

DISPLAY_NAME = "WoW Fish"
WINDOW_TITLE = "World of Warcraft"
PARAMS = [
    {"name": "duration_s", "label": "Duration (seconds)", "type": "int", "default": 300},
    {"name": "max_casts", "label": "Max casts (<= free bag slots)", "type": "int", "default": 10},
    {"name": "fish_key", "label": "Fishing key", "type": "str", "default": "1"},
    {"name": "interact_key", "label": "Interact key (blank = scan)", "type": "str", "default": ""},
    {"name": "water_region", "label": "Water region x1,y1,x2,y2", "type": "str", "default": ""},
    {"name": "grid_step", "label": "Scan grid step (px)", "type": "int", "default": 40},
    {"name": "bite_box", "label": "Bite box size (px)", "type": "int", "default": 60},
    {"name": "splash_threshold", "label": "Splash threshold (0 = observe)", "type": "float", "default": 0.0},
    # 2.0 missed a sustained 5.4-6.7 splash over a 3.1 bobbing p95 (needed 6.3);
    # no-bite casts have peaked at <= 1.4x their p95
    {"name": "splash_ratio", "label": "Splash x bobbing (0 = fixed only)", "type": "float", "default": 1.6},
    # measured 2026-10-06: a cast lasts ~30 s (a late bite's bobber vanished
    # at 31.9 s after the key press), not 21 -- the wait also ends early as
    # soon as the bobber's cursor goes away, so this is only a ceiling
    {"name": "cast_timeout_s", "label": "Max wait per cast (seconds)", "type": "float", "default": 33.0},
    {"name": "bobber_cursor_sig", "label": "Bobber cursor sig (blank = any)", "type": "str", "default": ""},
    {"name": "save_shots", "label": "Save debug shots (0/1)", "type": "int", "default": 1},
]

SHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shots")
CAST_SETTLE_MS = (1800, 2600)  # bobber flies and lands before the scan starts
HOVER_SETTLE_S = 0.06  # the client swaps the cursor a frame or two after a move
FLOOR_FRAMES = 30  # ~1.5 s of plain bobbing measured per cast (earliest bite seen: 6 s)
# second bite rule: a splash that holds a moderate level. In daylight a
# sustained 4.6-6.8 splash can stay under the spike threshold the whole way
# (9 of 46 casts missed, 2026-10-06 midday); averaged over 6 polls those
# splashes' 6-poll median sat at 1.7-2.1x the cast's bobbing median (a mean
# would let one big twitch through)
SUSTAIN_FRAMES, SUSTAIN_RATIO = 6, 1.6
CONFIRM_FRAMES, CONFIRM_WINDOW = 3, 5  # 3 of the last 5 polls over threshold: a one-frame
# twitch spikes only 2 diffs (in, out); a splash keeps churning, though its
# animation can repeat a frame between polls (25-cast run: a 7.0 splash missed
# when 3 *consecutive* polls were required)
CAREFUL_HOVERS = 4  # first candidates get a person-paced move; a fallback sweep goes fast

# pacing borrowed from the OSRS tasks: gaussian everything, a usual reaction
# plus an occasional slow one, and the odd pause where nothing happens. No
# camera/zoom fidgets -- those would move the calibrated water region.
SLOW_REACTION_P, SLOW_REACTION_MS = 0.08, (650, 1200)  # still inside the bite window
SHORT_BREAK_P, SHORT_BREAK_MS = 0.07, (3000, 8000)
LONG_BREAK_P, LONG_BREAK_MS = 0.015, (15000, 45000)


def parse_region(text):
    x1, y1, x2, y2 = (int(v) for v in text.split(","))
    assert x1 < x2 and y1 < y2, f"bad region {text}"
    return x1, y1, x2, y2


def cell_diffs(prev, cur, cell):
    """Mean abs diff per cell x cell block: (rows, cols) array. Used both to
    order the bobber scan and, in interact mode, to spot a splash anywhere."""
    d = np.abs(cur.astype(np.int16) - prev.astype(np.int16)).mean(axis=2)
    rows, cols = d.shape[0] // cell, d.shape[1] // cell
    return d[: rows * cell, : cols * cell].reshape(rows, cell, cols, cell).mean(axis=(1, 3))


def cursor_handle():
    return win32gui.GetCursorInfo()[1]


def cursor_signature(hcursor):
    """CRC of the cursor's bitmaps. WoW hands out a new cursor handle every
    cast, but a given cursor *shape* keeps its pixels -- so the bobber's
    interact cursor can be told apart from an NPC's (a quay guard locked the
    scan once on 2026-10-06)."""
    info = win32gui.GetIconInfo(hcursor)
    try:
        crc = 0
        for hbm in info[3:5]:
            if hbm:
                crc = zlib.crc32(win32ui.CreateBitmapFromHandle(int(hbm)).GetBitmapBits(True), crc)
        return crc
    finally:
        for hbm in info[3:5]:
            if hbm:
                win32gui.DeleteObject(hbm)


def hover(win_rect, x, y, fast=False):
    ax, ay = window.to_absolute(win_rect, x, y)
    duration = (humanize.jitter(0.05, 0.015, 0.02, 0.09) if fast
                else humanize.jitter(0.16, 0.05, 0.08, 0.3))
    pyautogui.moveTo(ax, ay, duration=duration, tween=pyautogui.easeOutQuad)
    time.sleep(HOVER_SETTLE_S)


def press(key):
    pyautogui.keyDown(key)
    time.sleep(humanize.jitter(0.07, 0.02, 0.04, 0.13))
    pyautogui.keyUp(key)


def _gray_diff(a, b):
    return np.abs(a.astype(np.int16) - b.astype(np.int16)).mean(axis=2).astype(np.float32)


def novelty(before, after, after2):
    """Per-pixel "new and holding still": changed since the cast in BOTH later
    frames, but barely changed between them. The landed bobber scores high;
    waves score ~0 because they also churn between after and after2. (At
    sunrise, plain before/after change ranked rolling wave bands above the
    bobber: 15 and 40 hovers on 2026-10-06.)"""
    d1, d2, d12 = _gray_diff(after, before), _gray_diff(after2, before), _gray_diff(after2, after)
    return np.minimum(d1, d2) - d12


def bobber_candidates(before, after, after2, step, k=6):
    """Region-local peaks of novelty, each a bobber-sized blob apart."""
    score = cv2.blur(novelty(before, after, after2), (step, step))
    pts = []
    for _ in range(k):
        y, x = np.unravel_index(int(np.argmax(score)), score.shape)
        if score[y, x] <= 0:
            break
        pts.append((int(x), int(y)))
        cv2.circle(score, (int(x), int(y)), step, -1e9, -1)  # next peak elsewhere
    return pts


def scan_points(region, step, before, after, after2, history=()):
    """Where recent bobbers landed (casts land within ~150 px of each other),
    then novelty peaks, then the whole grid -- spiralling out from the usual
    landing spot once there is history, by cell novelty before that. A dark,
    far bobber can have less novelty than sunlit waves (13 and 18 hovers on
    2026-10-06); the landing history doesn't care about light."""
    x1, y1, _, _ = region
    peaks = [(x1 + x, y1 + y) for x, y in bobber_candidates(before, after, after2, step, k=3)]
    if history:
        hist = np.array(history, dtype=float)
        mx, my = (int(v) for v in np.median(hist, axis=0))
        # landings spread along the cast line more than across it (x +-150,
        # y +-50 here): walk the grid in the spread's own shape, not a circle
        # (a circle spent 30-51 hovers reaching a bobber 120 px off-median)
        sx, sy = np.maximum(hist.std(axis=0), 20.0) if len(hist) > 2 else (60.0, 60.0)
        peaks = [(mx, my)] + peaks
    nov = novelty(before, after, after2)
    rows, cols = nov.shape[0] // step, nov.shape[1] // step
    cells = nov[: rows * step, : cols * step].reshape(rows, step, cols, step).mean(axis=(1, 3))
    order = np.dstack(np.unravel_index(np.argsort(-cells, axis=None), cells.shape))[0]
    grid = [(int(x1 + c * step + step // 2), int(y1 + r * step + step // 2)) for r, c in order]
    if history:
        grid.sort(key=lambda g: ((g[0] - mx) / sx) ** 2 + ((g[1] - my) / sy) ** 2)
    grid = [g for g in grid
            if all(abs(g[0] - p[0]) > step // 2 or abs(g[1] - p[1]) > step // 2 for p in peaks)]
    return peaks + grid


def find_bobber(win_rect, points, baseline, kill_switch, want_sig=None):
    """First point whose cursor differs from plain water -- and, given
    want_sig, has the bobber cursor's exact shape (NPCs light it too).
    Returns (point or None, hovers, signatures of non-matching hits)."""
    misses = []
    for i, (x, y) in enumerate(points):
        if kill_switch is not None and kill_switch.triggered.is_set():
            return None, i, misses
        hover(win_rect, x, y, fast=i >= CAREFUL_HOVERS)
        h = cursor_handle()
        if want_sig is not None:
            # by shape, not by "differs from baseline": the baseline hover can
            # itself land on a lingering bobber (cast 9, 2026-10-06)
            sig = cursor_signature(h)
            if sig == want_sig:
                return (x, y), i + 1, misses
            if h != baseline:
                misses.append(sig)
        elif h != baseline:
            return (x, y), i + 1, misses
    return None, len(points), misses


def click_bobber(win_rect, bobber, on_bobber):
    """Right-click somewhere on the bobber, not the exact pixel that first lit
    the cursor -- but only on a spot the cursor confirms is still bobber."""
    for _ in range(3):
        x = bobber[0] + humanize.jitter(0, 6, -12, 12)
        y = bobber[1] + humanize.jitter(0, 5, -10, 10)
        hover(win_rect, x, y, fast=True)
        if on_bobber():
            break
    else:
        x, y = bobber
        hover(win_rect, x, y, fast=True)
    bot_input.click_point(win_rect, x, y, jitter_px=0, button="right")


def drift_mouse(win_rect):
    """Idle mouse wander during a break -- no clicks, keys or camera moves."""
    left, top, right, bottom = win_rect
    x = np.random.uniform(0.15, 0.85) * (right - left)
    y = np.random.uniform(0.2, 0.8) * (bottom - top)
    ax, ay = window.to_absolute(win_rect, x, y)
    pyautogui.moveTo(ax, ay, duration=humanize.jitter(0.5, 0.2, 0.2, 1.1),
                     tween=pyautogui.easeInOutQuad)


def maybe_break(win_rect, log, kill_switch):
    """The odd pause between casts; returns True if F12 fired during it."""
    roll = np.random.random()
    if roll < LONG_BREAK_P:
        span = LONG_BREAK_MS
    elif roll < LONG_BREAK_P + SHORT_BREAK_P:
        span = SHORT_BREAK_MS
    else:
        return False
    log.log("pause", span_ms=span)
    drift_mouse(win_rect)
    return humanize.rest(*span, kill_switch=kill_switch)


def bite_box(win_rect, center, size):
    left, top, right, bottom = win_rect
    x, y = center
    h = size // 2
    return (max(0, x - h), max(0, y - h), min(right - left, x + h), min(bottom - top, y + h))


def save_shot(enabled, name, img):
    if enabled:
        os.makedirs(SHOTS_DIR, exist_ok=True)
        cv2.imwrite(os.path.join(SHOTS_DIR, name), img)


def wait_for_bite(win_rect, box, cell, threshold, deadline, kill_switch, ratio=0.0,
                  bobber_cursor=None, relocate=None):
    """Poll the box; return (bit, peak_diff, frame_at_peak, diffs). A bite is
    CONFIRM_FRAMES consecutive frames over threshold: the splash lasts, a
    single bobbing twitch doesn't (live run: 10 clicks, 8 catches when one
    frame was enough). threshold <= 0 never bites; diffs is calibration data.

    Lighting moves the bobbing level (sun glints at day, flat water at
    night), so with ratio > 0 the threshold for this cast is
    max(threshold, ratio x p95 of the first FLOOR_FRAMES diffs) -- the fixed
    threshold becomes a floor. Live data 2026-10-06: real bites were >= 2.6x
    their cast's bobbing p95, no-bite casts peaked ~1.4x.

    With bobber_cursor (the handle seen while hovering the bobber; the mouse
    stays parked on it), the wait also ends when that cursor goes away --
    the bobber despawned, so the cast is over. Returns gone=True then."""
    prev = capture.grab_region(win_rect, box)
    peak, peak_frame, diffs, recent = 0.0, prev, [], []
    sustain_thr = None
    while time.time() < deadline:
        if kill_switch is not None and kill_switch.triggered.is_set():
            break
        time.sleep(0.05)
        if bobber_cursor is not None and cursor_handle() != bobber_cursor:
            # the bobber bobs and drifts: from an edge hover it can slide out
            # from under the cursor while still alive (a 6.5 s "despawn",
            # 2026-10-06) -- look around it before calling the cast over
            if relocate is None or not relocate():
                return False, peak, peak_frame, diffs, threshold, True
            bobber_cursor = cursor_handle()
        cur = capture.grab_region(win_rect, box)
        d = float(cell_diffs(prev, cur, cell).max())
        diffs.append(d)
        if ratio > 0 and len(diffs) == FLOOR_FRAMES and threshold > 0:
            sustain_thr = max(threshold, SUSTAIN_RATIO * float(np.median(diffs)))
            threshold = max(threshold, ratio * float(np.percentile(diffs, 95)))
        if d > peak:
            peak, peak_frame = d, cur
        measuring = ratio > 0 and len(diffs) <= FLOOR_FRAMES  # no bites until the floor is known
        recent = (recent + [0 < threshold <= d and not measuring])[-CONFIRM_WINDOW:]
        sustained = (sustain_thr is not None and len(diffs) > FLOOR_FRAMES + SUSTAIN_FRAMES
                     and float(np.median(diffs[-SUSTAIN_FRAMES:])) >= sustain_thr)  # median: one twitch can't carry it
        if sum(recent) >= CONFIRM_FRAMES or sustained:
            return True, peak, peak_frame, diffs, threshold, False
        prev = cur
    return False, peak, peak_frame, diffs, threshold, False


def run(params, log_path, kill_switch=None):
    from engine.logger import JsonlLogger

    log = JsonlLogger(log_path)
    series_log = JsonlLogger(log_path.replace(".jsonl", "_series.jsonl"))  # per-cast diffs, for tuning
    if not params["water_region"]:
        log.log("run_aborted", reason="water_region not calibrated")
        return
    region = parse_region(params["water_region"])
    threshold = params["splash_threshold"]
    interact_key = params["interact_key"].strip()
    want_sig = int(params["bobber_cursor_sig"]) if str(params["bobber_cursor_sig"]).strip() else None
    shots = bool(params["save_shots"])
    run_id = int(time.time())
    log.log("run_start", **params, observe_only=threshold <= 0)

    def killed():
        return kill_switch is not None and kill_switch.triggered.is_set()

    # launching from the GUI or a terminal leaves that window focused --
    # give the user a few seconds to click into WoW before the first key
    focus_deadline = time.time() + 30
    while not window.is_foreground(WINDOW_TITLE) and time.time() < focus_deadline:
        if humanize.rest(250, 250, kill_switch=kill_switch):
            break
    log.log("waited_for_focus", focused=window.is_foreground(WINDOW_TITLE))

    stats = dict(casts=0, no_bobber=0, bites=0, timeouts=0, loot_clicks=0)
    history = []  # recent bobber landing spots, newest last
    start = time.time()
    while stats["casts"] < params["max_casts"] and time.time() - start < params["duration_s"]:
        if killed():
            break
        win_rect = window.find_runelite_rect(WINDOW_TITLE)
        if not window.is_foreground(WINDOW_TITLE):
            log.log("stopped_not_foreground")  # never type into another app
            break

        # OSRS-style pacing between casts: a varied beat to "notice" the
        # last cast is done, and now and then a longer pause
        if humanize.reaction_delay(kill_switch):
            break
        if maybe_break(win_rect, log, kill_switch):
            break
        if not window.is_foreground(WINDOW_TITLE):  # user may have tabbed out during the pause
            log.log("stopped_not_foreground")
            break
        win_rect = window.find_runelite_rect(WINDOW_TITLE)

        # baseline cursor over plain water, before the bobber exists
        x1, y1, x2, y2 = region
        hover(win_rect, np.random.uniform(x1, x2), np.random.uniform(y1, y2))
        baseline = cursor_handle()
        baseline_sig = cursor_signature(baseline)  # read now: WoW may free old cursor handles
        before = capture.grab_region(win_rect, region)

        press(params["fish_key"])
        cast_ts = time.time()
        stats["casts"] += 1
        n = stats["casts"]
        log.log("cast", n=n, baseline_cursor=baseline)
        if humanize.rest(*CAST_SETTLE_MS, kill_switch=kill_switch):
            break
        # watch only within the cast: past it, the despawning bobber reads as
        # a splash (live run 2026-10-06: a 21.45 s "bite" looted nothing).
        # Recast variance comes from the pacing before the next cast instead.
        deadline = cast_ts + params["cast_timeout_s"]

        if interact_key:
            box, cell, bobber = region, params["bite_box"], None
        else:
            after = capture.grab_region(win_rect, region)
            time.sleep(humanize.jitter(0.3, 0.05, 0.2, 0.4))  # waves move on, the bobber stays
            after2 = capture.grab_region(win_rect, region)
            points = scan_points(region, params["grid_step"], before, after, after2, history)
            scan_start = time.time()
            bobber, hovers, misses = find_bobber(win_rect, points, baseline, kill_switch, want_sig)
            if bobber is not None:
                bobber = list(bobber)  # relocate() may nudge it
                history = (history + [tuple(bobber)])[-8:]
            log.log("bobber_scan", n=n, found=bobber is not None, x=bobber and bobber[0],
                    y=bobber and bobber[1], hovers=hovers, of=len(points),
                    scan_s=round(time.time() - scan_start, 2),
                    hit_sig=bobber and cursor_signature(cursor_handle()),
                    baseline_sig=baseline_sig, other_cursor_sigs=misses)
            if killed():
                break
            if bobber is None or hovers > 2:  # keep the frames that fooled the ranking
                save_shot(shots, f"wow_fish_{run_id}_{n:02d}_scan_before.png", before)
                save_shot(shots, f"wow_fish_{run_id}_{n:02d}_scan_after.png", after)
                save_shot(shots, f"wow_fish_{run_id}_{n:02d}_scan_after2.png", after2)
            if bobber is None:
                stats["no_bobber"] += 1
                continue
            box = bite_box(win_rect, bobber, params["bite_box"])
            cell = min(box[2] - box[0], box[3] - box[1])

        def on_bobber():
            h = cursor_handle()
            return cursor_signature(h) == want_sig if want_sig is not None else h != baseline

        def relocate():
            """Hover a small ring around the bobber; re-park on it if found."""
            for dx, dy in ((0, 0), (0, -14), (14, 0), (0, 14), (-14, 0), (0, -28), (0, 28)):
                hover(win_rect, bobber[0] + dx, bobber[1] + dy, fast=True)
                if on_bobber():
                    bobber[:] = [bobber[0] + dx, bobber[1] + dy]
                    log.log("bobber_relocated", n=n, x=bobber[0], y=bobber[1])
                    return True
            return False

        bit, peak, frame, diffs, used_thr, gone = wait_for_bite(
            win_rect, box, cell, threshold, deadline, kill_switch, params["splash_ratio"],
            bobber_cursor=None if interact_key else cursor_handle(),
            relocate=None if interact_key else relocate)
        if killed():
            break
        waited = round(time.time() - cast_ts, 2)
        series_log.log("series", n=n, bit=bit, gone=gone, waited_s=waited,
                       threshold=round(used_thr, 2), diffs=[round(v, 2) for v in diffs])
        floor = dict(p50=round(float(np.percentile(diffs, 50)), 2),
                     p95=round(float(np.percentile(diffs, 95)), 2),
                     second=round(sorted(diffs)[-2], 2),
                     threshold=round(used_thr, 2)) if len(diffs) > 1 else {}
        if not bit:
            stats["timeouts"] += 1
            i = int(np.argmax(diffs)) if diffs else 0
            log.log("timeout", n=n, waited_s=waited, bobber_gone=gone, peak_diff=round(peak, 2), **floor,
                    around_peak=[round(v, 1) for v in diffs[max(0, i - 6):i + 7]])
            save_shot(shots, f"wow_fish_{run_id}_{n:02d}_timeout_peak.png", frame)
            humanize.rest(400, 900, kill_switch=kill_switch)
            continue

        stats["bites"] += 1
        log.log("bite", n=n, waited_s=waited, diff=round(peak, 2), **floor)
        save_shot(shots, f"wow_fish_{run_id}_{n:02d}_bite.png", frame)
        slow = np.random.random() < SLOW_REACTION_P
        if humanize.rest(*(SLOW_REACTION_MS if slow else (180, 550)), kill_switch=kill_switch):
            break
        if interact_key:
            press(interact_key)
        else:
            click_bobber(window.find_runelite_rect(WINDOW_TITLE), bobber, on_bobber)
        stats["loot_clicks"] += 1
        log.log("loot_click", n=n, via="interact_key" if interact_key else "right_click",
                slow_reaction=slow)
        humanize.rest(1200, 2200, kill_switch=kill_switch)  # auto loot + GCD before recasting

    if killed():
        log.log("kill_switch_triggered")
    log.log("run_end", **stats)
