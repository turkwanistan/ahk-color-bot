"""Offline check of the WoW fishing detection math (no screen, no input).
Run: python -m tests.test_wow_fish  (Windows python, repo root)."""
import json
import threading
from unittest import mock

import numpy as np

from tasks import wow_fish


def demo():
    still = np.full((120, 200, 3), 80, np.uint8)
    moved = still.copy()
    moved[40:80, 120:160] = 200  # "bobber landed" in cell row 1, col 3 (step 40)

    d = wow_fish.cell_diffs(still, moved, 40)
    assert d.shape == (3, 5) and d[1, 3] == 120 and d.sum() == 120

    pts = wow_fish.scan_points((10, 20, 210, 140), 40, still, moved, moved)
    assert pts[0] == (10 + 3 * 40 + 20, 20 + 1 * 40 + 20) and len(pts) == 15
    json.dumps(pts[0])  # logged as-is: numpy ints would crash the JSONL logger

    assert wow_fish.parse_region("1, 2,30,40") == (1, 2, 30, 40)

    # sunrise case: waves churn hard between every frame, the bobber lands
    # and holds still -- novelty ranks it first though waves change more
    rng = np.random.default_rng(1)
    def waves():
        return rng.integers(0, 70, (320, 680, 3)).astype(np.uint8)
    before, after, after2 = waves(), waves(), waves()
    for f in (after, after2):
        f[150:180, 500:530] = 200  # 30x30 bobber
    assert wow_fish.cell_diffs(before, after, 40).max() < 70
    pts = wow_fish.scan_points((0, 0, 680, 320), 40, before, after, after2)
    assert abs(pts[0][0] - 515) <= 20 and abs(pts[0][1] - 165) <= 20, pts[:3]
    assert len(set(pts)) == len(pts)
    json.dumps(pts)

    # bobbing (small diffs) stays under the threshold, the splash crosses it
    rng = np.random.default_rng(0)
    bob = [np.clip(still[:60, :60] + rng.integers(0, 4, (60, 60, 3)), 0, 255).astype(np.uint8)
           for _ in range(6)]
    splash = np.full((60, 60, 3), 230, np.uint8)
    splash2 = np.full((60, 60, 3), 140, np.uint8)  # churning particles: every frame differs
    ks = mock.Mock(triggered=threading.Event())
    # a one-frame twitch over threshold is not a bite...
    frames = iter(bob + [splash] + bob)
    with mock.patch.object(wow_fish.capture, "grab_region", lambda r, b: next(frames)), \
            mock.patch.object(wow_fish.time, "time", side_effect=[0] + [1] * 11 + [99] * 50):
        bit, peak, _, _, _, _ = wow_fish.wait_for_bite(None, (0, 0, 60, 60), 60, 20.0, 10, ks)
    assert not bit and peak > 100
    # ...a splash that lasts is
    frames = iter(bob + [splash, splash2, splash, splash2] + bob)
    with mock.patch.object(wow_fish.capture, "grab_region", lambda r, b: next(frames)):
        bit, peak, _, _, _, _ = wow_fish.wait_for_bite(None, (0, 0, 60, 60), 60, 20.0, float("inf"), ks)
    assert bit and peak > 100

    frames = iter(bob * 3)
    with mock.patch.object(wow_fish.capture, "grab_region", lambda r, b: next(frames)), \
            mock.patch.object(wow_fish.time, "time", side_effect=[0] + [1] * 5 + [99] * 50):
        bit, peak, _, _, _, _ = wow_fish.wait_for_bite(None, (0, 0, 60, 60), 60, 20.0, 10, ks)
    assert not bit and peak < 5

    # a splash whose animation repeats a frame between polls still counts
    # (3 of 5 over threshold, not 3 in a row)
    frames = iter(bob + [splash, splash2, splash2, splash] + bob)
    with mock.patch.object(wow_fish.capture, "grab_region", lambda r, b: next(frames)):
        bit, _, _, _, _, _ = wow_fish.wait_for_bite(None, (0, 0, 60, 60), 60, 20.0, float("inf"), ks)
    assert bit

    # landing history: the usual spot is hovered first, the grid spirals out from it
    flat = np.zeros((320, 680, 3), np.uint8)
    pts = wow_fish.scan_points((0, 0, 680, 320), 40, flat, flat, flat, history=[(300, 100), (320, 120), (310, 90)])
    assert pts[0] == (310, 100) and abs(pts[1][0] - 310) <= 40 and abs(pts[1][1] - 100) <= 40, pts[:3]
    # wide horizontal spread: the walk covers the landing band sideways first
    band = [(200, 100), (420, 104), (300, 98), (360, 102), (250, 96)]
    pts = wow_fish.scan_points((0, 0, 680, 320), 40, flat, flat, flat, history=band)
    assert all(abs(y - 100) <= 40 for _, y in pts[1:9]), pts[:9]

    # daylight: bobbing ~2.5, a splash holding ~5 (2x the median) never makes
    # 3-of-5 over the spike threshold but the sustained rule catches it --
    # and plain bobbing with a few spikes does not trip it
    lvl = lambda v: np.full((60, 60, 3), 80 + v, np.uint8)
    day = [lvl(0) if i % 2 else lvl(3 if i % 3 else 2) for i in range(40)]   # diffs 2-3
    spiky = day[:30] + [lvl(10)] + day[1:25]  # one big twitch: 2 high diffs in a 6-poll window
    frames = iter(spiky)
    with mock.patch.object(wow_fish.capture, "grab_region", lambda r, b: next(frames)), \
            mock.patch.object(wow_fish.time, "time", side_effect=[0] + [1] * 53 + [99] * 50):
        bit, _, _, _, _, _ = wow_fish.wait_for_bite(None, (0, 0, 60, 60), 60, 3.5, 10, ks, ratio=3.0)
    assert not bit
    held = day[:30] + [lvl(5 * (i % 2)) for i in range(12)]   # diffs 5 every poll
    frames = iter(held + day)
    with mock.patch.object(wow_fish.capture, "grab_region", lambda r, b: next(frames)):
        bit, _, _, diffs, thr, _ = wow_fish.wait_for_bite(
            None, (0, 0, 60, 60), 60, 3.5, float("inf"), ks, ratio=3.0)
    assert bit and thr > 5, thr  # spike rule alone (3x p95) could not fire on 5s

    # a bobber sliding out from under the cursor is re-found, not "gone"
    frames = iter(bob * 3)
    handles = iter([7, 3, 9, 9, 9, 9, 9])
    with mock.patch.object(wow_fish.capture, "grab_region", lambda r, b: next(frames)), \
            mock.patch.object(wow_fish, "cursor_handle", lambda: next(handles)), \
            mock.patch.object(wow_fish.time, "time", side_effect=[0, 1, 1, 1, 99, 99]):
        bit, _, _, _, _, gone = wow_fish.wait_for_bite(
            None, (0, 0, 60, 60), 60, 20.0, 10, ks, bobber_cursor=7, relocate=lambda: True)
    assert not bit and not gone

    # brighter light: bobbing churns at ~12, a fixed 4.5 would fire on it --
    # the ratio lifts this cast's threshold above the bobbing and still
    # catches the splash
    gl = [np.full((60, 60, 3), 80 + (12 if i % 2 else 0), np.uint8) for i in range(40)]
    frames = iter(gl + [splash, splash2, splash, splash2] + gl)
    with mock.patch.object(wow_fish.capture, "grab_region", lambda r, b: next(frames)):
        bit, peak, _, diffs, thr, _ = wow_fish.wait_for_bite(
            None, (0, 0, 60, 60), 60, 4.5, float("inf"), ks, ratio=2.0)
    assert bit and thr == 24 and max(diffs[:39]) == 12, (bit, thr, max(diffs[:39]))
    frames = iter(gl * 2)
    with mock.patch.object(wow_fish.capture, "grab_region", lambda r, b: next(frames)), \
            mock.patch.object(wow_fish.time, "time", side_effect=[0] + [1] * 78 + [99] * 50):
        bit, _, _, _, _, _ = wow_fish.wait_for_bite(None, (0, 0, 60, 60), 60, 4.5, 10, ks, ratio=2.0)
    assert not bit  # same glinting with the fixed 4.5 alone would have clicked

    # the bobber despawning (its cursor reverting under the parked mouse)
    # ends the cast early, before the timeout
    frames = iter(bob * 3)
    handles = iter([7, 7, 7, 3])
    with mock.patch.object(wow_fish.capture, "grab_region", lambda r, b: next(frames)), \
            mock.patch.object(wow_fish, "cursor_handle", lambda: next(handles)):
        bit, _, _, diffs, _, gone = wow_fish.wait_for_bite(
            None, (0, 0, 60, 60), 60, 20.0, float("inf"), ks, bobber_cursor=7)
    assert not bit and gone and len(diffs) == 3

    # a cursor handle freed mid-read is "no match", not a crash
    assert wow_fish.cursor_signature(0x7FFF0000) is None

    # audio: steady ambience doesn't trip it, a sudden splash over it does
    class FakeMeter:
        def __init__(self, levels): self.levels = levels
        def since(self, ts): return [(t, v) for t, v in self.levels if t > ts]
    now = wow_fish.time.time()
    calm = [(now - 3 + i * 0.02, 0.05) for i in range(140)]
    assert not wow_fish.heard_splash(FakeMeter(calm + [(now - 0.05, 0.06)]), 2.5, 0.02)[0]
    heard, loud, ref = wow_fish.heard_splash(FakeMeter(calm + [(now - 0.05, 0.2)]), 2.5, 0.02)
    assert heard and loud == 0.2 and ref == 0.05
    assert not wow_fish.heard_splash(FakeMeter([(now - 0.05, 0.01)]), 2.5, 0.02)[0]  # silence before: floor rules
    noisy = [(now - 3 + i * 0.02, 0.035) for i in range(140)]
    assert wow_fish.heard_splash(FakeMeter(noisy + [(now - 0.05, 0.09)]), 3.0, 0.03)[0]  # loud over noise
    assert not wow_fish.heard_splash(FakeMeter(noisy + [(now - 0.05, 0.07)]), 3.0, 0.03)[0]

    ks.triggered.set()  # F12 ends the wait without a bite
    frames = iter(bob * 3)
    with mock.patch.object(wow_fish.capture, "grab_region", lambda r, b: next(frames)):
        bit, _, _, _, _, _ = wow_fish.wait_for_bite(None, (0, 0, 60, 60), 60, 20.0, float("inf"), ks)
    assert not bit
    print("wow_fish detection checks passed")


if __name__ == "__main__":
    demo()
