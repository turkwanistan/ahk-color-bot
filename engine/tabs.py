"""Generic tab-peeking idle behaviors -- opening a game-UI tab, looking at
it briefly, and returning to inventory. Any task can reuse these; the only
per-task specifics are which skill's XP to check.

Must always return to the inventory tab -- inventory-reading detection
(full/empty slot checks) breaks silently for the rest of the session if
left sitting on a different tab.
"""
import pyautogui

from . import humanize, ui_layout
from . import input as bot_input
from . import window


def check_tab(win_rect, tab_pos, look_duration_range=(700, 1800)):
    """Open a tab, look at it briefly, return to inventory."""
    bot_input.click_point(win_rect, *tab_pos, jitter_px=4)
    humanize.rest(*look_duration_range)
    bot_input.click_point(win_rect, *ui_layout.INVENTORY_TAB_POS, jitter_px=4)
    humanize.rest(150, 300)


def check_skill_xp(win_rect, skill_name, look_duration_range=(1200, 2800)):
    """Open skills, hover the given skill's icon specifically -- that's how
    you'd actually see remaining XP to level via the tooltip -- then return
    to inventory."""
    bot_input.click_point(win_rect, *ui_layout.SKILLS_TAB_POS, jitter_px=4)
    humanize.rest(300, 600)
    ax, ay = window.to_absolute(win_rect, *ui_layout.skill_icon_pos(skill_name))
    pyautogui.moveTo(ax, ay, duration=humanize.jitter(0.2, 0.06, 0.1, 0.4))
    humanize.rest(*look_duration_range)
    bot_input.click_point(win_rect, *ui_layout.INVENTORY_TAB_POS, jitter_px=4)
    humanize.rest(150, 300)
