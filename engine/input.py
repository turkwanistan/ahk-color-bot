"""Humanized mouse input. Coordinates are always window-relative in;
translated to absolute virtual-screen coords right before the actual
pyautogui call."""
import random
import time

import pyautogui

from . import humanize
from .window import to_absolute

pyautogui.FAILSAFE = True  # slam mouse into a screen corner to abort
pyautogui.PAUSE = 0.05  # RuneLite (Java client) can miss an instantaneous
# synthetic mouse-down+up -- give each low-level event a moment to land
# instead of firing them back to back.

# pyautogui.moveTo(duration=...) is LINEAR (constant velocity) unless a tween
# is given -- a flat velocity profile is a well-known bot signature, real
# mouse movement accelerates/decelerates. Vary the easing curve itself too,
# not just timing, so every move doesn't share one identical shape.
_TREE_TWEENS = [pyautogui.easeOutQuad, pyautogui.easeInOutQuad, pyautogui.easeOutSine]


def click_point(win_rect, rel_x, rel_y, jitter_px=12, button="left"):
    """Single deliberate click -- used for tree targeting, where we want
    margin around each event so the game reliably registers it.

    jitter_px defaults wide (not +-4) -- a tree canopy is a large clickable
    sprite and a real player clicks anywhere across it, not clustered on the
    exact detected centroid every time.
    """
    ax, ay = to_absolute(win_rect, rel_x, rel_y)
    ax += humanize.jitter(0, jitter_px / 2, -jitter_px, jitter_px)
    ay += humanize.jitter(0, jitter_px / 2, -jitter_px, jitter_px)

    pyautogui.moveTo(
        ax, ay,
        duration=humanize.jitter(0.18, 0.06, 0.08, 0.4),
        tween=random.choice(_TREE_TWEENS),
    )
    time.sleep(0.05)
    pyautogui.mouseDown(button=button)
    time.sleep(humanize.jitter(0.06, 0.02, 0.03, 0.12))  # real click hold duration
    pyautogui.mouseUp(button=button)


def idle_fidget(win_rect, viewport_box=(20, 30, 500, 340)):
    """Small human-like idle actions for downtime (waiting on a respawn)
    instead of sitting frozen polling every 500ms -- occasional mouse drift,
    a brief camera-rotation tap, or a zoom nudge, picked at random."""
    x1, y1, x2, y2 = viewport_box
    roll = random.random()

    if roll < 0.4:
        rx = random.uniform(x1, x2)
        ry = random.uniform(y1, y2)
        ax, ay = to_absolute(win_rect, rx, ry)
        pyautogui.moveTo(
            ax, ay,
            duration=humanize.jitter(0.3, 0.1, 0.15, 0.6),
            tween=random.choice(_TREE_TWEENS),
        )
    elif roll < 0.6:
        key = random.choice(["left", "right"])
        pyautogui.keyDown(key)
        time.sleep(humanize.jitter(0.15, 0.05, 0.05, 0.3))
        pyautogui.keyUp(key)
    elif roll < 0.75:
        # zoom nudge -- move over the viewport first, real scroll-zooming
        # happens with the cursor over the game view, not wherever it was
        cx = (x1 + x2) / 2 + random.uniform(-60, 60)
        cy = (y1 + y2) / 2 + random.uniform(-40, 40)
        ax, ay = to_absolute(win_rect, cx, cy)
        pyautogui.moveTo(ax, ay, duration=humanize.jitter(0.15, 0.05, 0.08, 0.3))
        pyautogui.scroll(random.choice([-3, -2, 2, 3]))
    # else: do nothing this tick -- not every idle moment should trigger a fidget


class ShiftClickBurst:
    """Hold shift once, fire a fast sequence of clicks -- how a real player
    actually clears an inventory (rapid shift-clicks, not a slow deliberate
    move+click per item with shift re-toggled every time)."""

    def __enter__(self):
        pyautogui.keyDown("shift")
        self._prev_pause = pyautogui.PAUSE
        pyautogui.PAUSE = 0.01
        time.sleep(0.08)  # let the game register shift-down before clicks start
        return self

    def __exit__(self, *exc):
        time.sleep(0.03)
        pyautogui.keyUp("shift")
        pyautogui.PAUSE = self._prev_pause

    def click(self, win_rect, rel_x, rel_y, jitter_px=3):
        ax, ay = to_absolute(win_rect, rel_x, rel_y)
        ax += humanize.jitter(0, jitter_px / 2, -jitter_px, jitter_px)
        ay += humanize.jitter(0, jitter_px / 2, -jitter_px, jitter_px)

        pyautogui.moveTo(
            ax, ay,
            duration=humanize.jitter(0.03, 0.012, 0.015, 0.07),
            tween=random.choice(_TREE_TWEENS),
        )
        pyautogui.mouseDown()
        time.sleep(humanize.jitter(0.025, 0.008, 0.015, 0.045))
        pyautogui.mouseUp()
