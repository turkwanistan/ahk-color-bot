"""Chop tree -> drop logs -> repeat.

Tree-specific only. Shared client-layout facts, drop ordering, tab-check
behaviors, and idle pacing all live in engine/ -- see ui_layout.py,
inventory.py, tabs.py, idle_behavior.py. A new task (mining, etc.) reuses
all of that directly instead of copy-pasting it.
"""
import functools
import random

from engine import capture, detect, humanize, tabs, ui_layout, window
from engine import input as bot_input
from engine.idle_behavior import IdleBehaviorManager
from engine.inventory import human_drop_order

DISPLAY_NAME = "Chop Tree"
PARAMS = [
    {"name": "duration_s", "label": "Duration (seconds)", "type": "int", "default": 120},
]

TREE_REGION = (0, 20, 530, 358)  # whole game viewport, not a sub-box --
# the tree's on-screen position drifts as the character/camera moves
# between chops, and a tight box eventually misses it once it drifts past
# an edge (confirmed 2026-07-30: tree found at canvas x=184, 14px outside
# the previous box's left edge at 198, while the bot sat idle thinking
# nothing was there)
TREE_COLOR = 0xFF00FF

CHARACTER_POS = (270, 193)  # window-relative; character stays roughly here between chops

LOG_COLOR = 0xFF00FF  # same highlight color as the tree; RuneLite marks both


def is_busy(win_rect):
    img = capture.grab_region(win_rect, ui_layout.ACTIVITY_STATUS_REGION)
    # dominant-channel check, not exact hex -- this text sits directly over
    # the 3D viewport and blends with whatever's behind it depending on
    # camera angle, so a strict color match misses it inconsistently
    return detect.dominant_channel_present(
        img, high_channels=[1], low_channels=[0, 2]
    )


def inventory_full(win_rect):
    img = capture.grab_region(win_rect, ui_layout.INV_BOTTOM_ROW)
    return detect.color_present(img, LOG_COLOR)


def logs_in_inventory(win_rect):
    img = capture.grab_region(win_rect, ui_layout.INV_REGION)
    return len(detect.find_blobs(img, LOG_COLOR, min_area=10))


def find_tree(win_rect):
    img = capture.grab_region(win_rect, TREE_REGION)
    blobs = detect.find_blobs(img, TREE_COLOR, min_area=20)
    if not blobs:
        return None
    x1, y1, _, _ = TREE_REGION

    # weighted toward the closest tree, not strictly always the closest --
    # a human doesn't compute exact Euclidean distance and win-take-all on
    # it every single time; always picking the true nearest is itself a
    # detectable pattern given enough samples
    points = [(x1 + b["cx"], y1 + b["cy"]) for b in blobs]
    weights = [
        1.0 / (((ax - CHARACTER_POS[0]) ** 2 + (ay - CHARACTER_POS[1]) ** 2) ** 0.5 + 20)
        for ax, ay in points
    ]
    return random.choices(points, weights=weights, k=1)[0]


def drop_logs(win_rect, log, kill_switch=None):
    img = capture.grab_region(win_rect, ui_layout.INV_REGION)
    blobs = detect.find_blobs(img, LOG_COLOR, min_area=10)
    blobs = human_drop_order(blobs, ui_layout.INV_REGION)
    x1, y1, _, _ = ui_layout.INV_REGION
    log.log("drop_logs_start", count=len(blobs))
    with bot_input.ShiftClickBurst() as burst:
        for b in blobs:
            if kill_switch is not None and kill_switch.triggered.is_set():
                log.log("kill_switch_triggered_mid_drop")
                return
            burst.click(win_rect, x1 + b["cx"], y1 + b["cy"])
            humanize.rest(50, 100)
    log.log("drop_logs_done")


def _build_idle_manager():
    check_woodcutting_xp = functools.partial(tabs.check_skill_xp, skill_name="Woodcutting")
    check_woodcutting_xp.__name__ = "check_skill_xp[Woodcutting]"
    check_equipment = functools.partial(tabs.check_tab, tab_pos=ui_layout.EQUIPMENT_TAB_POS)
    check_equipment.__name__ = "check_tab[Equipment]"
    check_combat = functools.partial(tabs.check_tab, tab_pos=ui_layout.COMBAT_TAB_POS)
    check_combat.__name__ = "check_tab[Combat]"

    return IdleBehaviorManager(
        actions=[bot_input.idle_fidget, check_woodcutting_xp, check_equipment, check_combat],
        weights=[9, 2, 2, 2],  # fidget most common; tab checks the rest, evenly
    )


def run(params, log_path, kill_switch=None):
    from engine.logger import JsonlLogger
    import time

    duration_s = params["duration_s"]
    log = JsonlLogger(log_path)
    log.log("run_start", duration_s=duration_s)
    start = time.time()
    tree_clicks = 0
    was_busy = None  # None = just started, no transition to react to yet
    idle_mgr = _build_idle_manager()

    while time.time() - start < duration_s:
        if kill_switch is not None and kill_switch.triggered.is_set():
            log.log("kill_switch_triggered")
            break

        win_rect = window.find_runelite_rect()

        if inventory_full(win_rect):
            drop_logs(win_rect, log, kill_switch=kill_switch)
            humanize.rest(400, 700)
            was_busy = False
            continue

        busy_now = is_busy(win_rect)

        if busy_now is False and was_busy is True:
            # character just went idle -- a human doesn't notice and react
            # instantly, and not with the same delay every time either
            log.log("noticing_idle")
            humanize.reaction_delay()
            win_rect = window.find_runelite_rect()  # state may have moved on during the pause

        was_busy = busy_now

        if not busy_now:
            tree = find_tree(win_rect)
            if tree:
                idle_mgr.reset()  # found something -- stretch over
                bot_input.click_point(win_rect, *tree)
                tree_clicks += 1
                log.log("click_tree", x=tree[0], y=tree[1])

                # walking to the tree takes a variable amount of time, and
                # the busy indicator stays false the whole walk -- poll for
                # it instead of guessing a fixed delay, so we don't re-click
                # (and interrupt the walk) while still en route
                wait_start = time.time()
                became_busy = False
                while time.time() - wait_start < 6:
                    if kill_switch is not None and kill_switch.triggered.is_set():
                        break
                    humanize.rest(300, 450)
                    if is_busy(window.find_runelite_rect()):
                        became_busy = True
                        break
                if not became_busy:
                    log.log("click_tree_no_busy_confirmation")
            else:
                # downtime (waiting on respawn) -- put it to use instead of
                # sitting frozen: clear out any logs already held now, so
                # there's more room once a tree does appear
                pending = logs_in_inventory(win_rect)
                if pending > 0:
                    log.log("no_tree_found_early_drop", count=pending)
                    drop_logs(win_rect, log, kill_switch=kill_switch)
                else:
                    log.log("no_tree_found")
                    idle_mgr.maybe_act(win_rect, log=log)
                humanize.rest(500, 800)
        else:
            idle_mgr.reset()  # busy again -- next downtime starts fresh
            humanize.rest(600, 900)

    log.log("run_end", tree_clicks=tree_clicks)
