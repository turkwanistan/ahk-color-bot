"""Chop tree -> drop logs -> repeat.

Regions calibrated 2026-07-30 from the live client (1062x542 RuneLite
window, classic/fixed layout). All coordinates are window-relative --
engine.window resolves the actual window rect fresh every call, so this
task doesn't care where the client sits on screen.
"""
import random

import pyautogui

from engine import capture, detect, humanize, window
from engine import input as bot_input

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

BUSY_REGION = (40, 52, 130, 80)  # "Woodcutting" status text, green while active
BUSY_COLOR = 0x00FF00
# NOTE: the "NOT woodcutting" red text is transient -- it fades after being
# idle for a while, so its absence does NOT mean busy. Detect busy (green
# present) instead and treat idle as its absence; this is unaffected by the
# red text's timeout behavior.

CHARACTER_POS = (270, 193)  # window-relative; character stays roughly here between chops

SKILLS_TAB_POS = (585, 212)  # verified live 2026-07-30: opens skills panel
INVENTORY_TAB_POS = (652, 212)  # verified live 2026-07-30: returns to inventory grid
EQUIPMENT_TAB_POS = (686, 212)  # verified live 2026-07-30: opens worn-equipment panel
COMBAT_TAB_POS = (552, 212)  # first icon in the tab row
WOODCUTTING_ICON_POS = (731, 402)  # verified live 2026-07-30: tooltip read "Woodcutting XP"

# how many idle actions (fidget or tab-peek) get spent per downtime stretch,
# not a per-tick coin flip -- a person glances at the camera/a tab once or
# twice near the start of a wait, then leaves it alone (watching something
# else) until a tree actually respawns, rather than fidgeting the whole time
IDLE_ACTIONS_PER_STRETCH = (1, 3)

INV_REGION = (571, 238, 741, 484)
INV_BOTTOM_ROW = (571, 449, 741, 484)  # last of 7 rows -- full here implies full grid
LOG_COLOR = 0xFF00FF  # same highlight color as the tree; RuneLite marks both


def is_busy(win_rect):
    img = capture.grab_region(win_rect, BUSY_REGION)
    # dominant-channel check, not exact hex -- this text sits directly over
    # the 3D viewport and blends with whatever's behind it depending on
    # camera angle, so a strict color match misses it inconsistently
    return detect.dominant_channel_present(img, high_channels=[1], low_channels=[0, 2])


def inventory_full(win_rect):
    img = capture.grab_region(win_rect, INV_BOTTOM_ROW)
    return detect.color_present(img, LOG_COLOR)


def logs_in_inventory(win_rect):
    img = capture.grab_region(win_rect, INV_REGION)
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


def check_skills_tab(win_rect):
    """A real player checking their Woodcutting XP during downtime -- opens
    skills, hovers the Woodcutting icon specifically (that's how you'd
    actually see remaining XP to level, via the tooltip), then always
    returns to the inventory tab -- inventory_full/logs_in_inventory both
    read that panel and would silently break for the rest of the session if
    left sitting on a different tab."""
    bot_input.click_point(win_rect, *SKILLS_TAB_POS, jitter_px=4)
    humanize.rest(300, 600)
    ax, ay = window.to_absolute(win_rect, *WOODCUTTING_ICON_POS)
    pyautogui.moveTo(ax, ay, duration=humanize.jitter(0.2, 0.06, 0.1, 0.4))
    humanize.rest(1200, 2800)  # reading the XP tooltip
    bot_input.click_point(win_rect, *INVENTORY_TAB_POS, jitter_px=4)
    humanize.rest(150, 300)


def check_equipment_tab(win_rect):
    """A real player glancing at worn equipment during downtime."""
    bot_input.click_point(win_rect, *EQUIPMENT_TAB_POS, jitter_px=4)
    humanize.rest(700, 1800)
    bot_input.click_point(win_rect, *INVENTORY_TAB_POS, jitter_px=4)
    humanize.rest(150, 300)


def check_combat_tab(win_rect):
    """A real player briefly checking attack style during downtime."""
    bot_input.click_point(win_rect, *COMBAT_TAB_POS, jitter_px=4)
    humanize.rest(600, 1500)
    bot_input.click_point(win_rect, *INVENTORY_TAB_POS, jitter_px=4)
    humanize.rest(150, 300)


def human_drop_order(blobs, region_bounds, rows=7):
    """Order items the way a person actually clears a grid: row by row, not
    jumping to random points all over the inventory. What varies between
    drops is WHICH coherent pattern gets used, not whether there's one --
    snake vs. straight rows, top-start vs. bottom-start, left- vs.
    right-first -- each individual drop still reads as a plausible human
    traversal, never a scatter."""
    _, y1, _, y2 = region_bounds
    row_height = (y2 - y1) / rows

    def row_of(b):
        return int(b["cy"] // row_height)

    snake = random.random() < 0.6
    start_right = random.random() < 0.3
    rows_present = sorted(set(row_of(b) for b in blobs))
    if random.random() < 0.3:
        rows_present = rows_present[::-1]  # occasionally start from the bottom row

    ordered = []
    for i, r in enumerate(rows_present):
        row_blobs = [b for b in blobs if row_of(b) == r]
        going_right = not start_right
        if snake and i % 2 == 1:
            going_right = not going_right
        row_blobs.sort(key=lambda b: b["cx"], reverse=not going_right)
        ordered.extend(row_blobs)
    return ordered


def drop_logs(win_rect, log, kill_switch=None):
    img = capture.grab_region(win_rect, INV_REGION)
    blobs = detect.find_blobs(img, LOG_COLOR, min_area=10)
    blobs = human_drop_order(blobs, INV_REGION)
    x1, y1, _, _ = INV_REGION
    log.log("drop_logs_start", count=len(blobs))
    with bot_input.ShiftClickBurst() as burst:
        for b in blobs:
            if kill_switch is not None and kill_switch.triggered.is_set():
                log.log("kill_switch_triggered_mid_drop")
                return
            burst.click(win_rect, x1 + b["cx"], y1 + b["cy"])
            humanize.rest(50, 100)
    log.log("drop_logs_done")


def run(params, log_path, kill_switch=None):
    from engine.logger import JsonlLogger
    import time

    duration_s = params["duration_s"]
    log = JsonlLogger(log_path)
    log.log("run_start", duration_s=duration_s)
    start = time.time()
    tree_clicks = 0
    was_busy = None  # None = just started, no transition to react to yet
    idle_stretch_active = False
    idle_actions_budget = 0
    idle_actions_used = 0

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
                idle_stretch_active = False  # found something -- stretch over
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

                    if not idle_stretch_active:
                        idle_stretch_active = True
                        idle_actions_budget = random.randint(*IDLE_ACTIONS_PER_STRETCH)
                        idle_actions_used = 0
                        log.log("idle_stretch_start", budget=idle_actions_budget)

                    if idle_actions_used < idle_actions_budget:
                        if random.random() < 0.4:
                            check_fn = random.choice(
                                [check_skills_tab, check_equipment_tab, check_combat_tab]
                            )
                            log.log("idle_tab_check", which=check_fn.__name__)
                            check_fn(win_rect)
                        else:
                            bot_input.idle_fidget(win_rect)
                        idle_actions_used += 1
                    # else: budget spent for this stretch -- genuinely idle
                    # now, no more outward actions until a tree appears
                humanize.rest(500, 800)
        else:
            idle_stretch_active = False  # busy again -- next downtime starts fresh
            humanize.rest(600, 900)

    log.log("run_end", tree_clicks=tree_clicks)
