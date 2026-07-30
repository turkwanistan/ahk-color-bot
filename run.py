import argparse
import os
import time

import pyautogui

from engine import window
from engine.killswitch import KillSwitch
from tasks import chop_tree

TASKS = {
    "chop_tree": chop_tree,
}


def arm_window_corner_failsafe():
    """pyautogui's default FAILSAFE_POINTS are corners of the PRIMARY monitor
    only (from pyautogui.size()). On a multi-monitor setup where RuneLite
    lives on a non-primary display at negative coordinates, none of those
    default corners are anywhere near the game window -- slamming the mouse
    to a corner of the screen you're actually watching would do nothing.
    Add the RuneLite window's own corners instead, so that gesture works."""
    left, top, right, bottom = window.find_runelite_rect()
    corners = [(left, top), (right - 1, top), (left, bottom - 1), (right - 1, bottom - 1)]
    pyautogui.FAILSAFE_POINTS = list(pyautogui.FAILSAFE_POINTS) + corners


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=TASKS.keys())
    parser.add_argument("--duration", type=int, default=120, help="seconds")
    args = parser.parse_args()

    task_module = TASKS[args.task]
    params = {"duration_s": args.duration}

    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{args.task}_{int(time.time())}.jsonl")
    print(f"logging to {log_path}", flush=True)
    print("press F12 at any time to stop immediately", flush=True)

    arm_window_corner_failsafe()
    kill_switch = KillSwitch()
    kill_switch.start()
    try:
        task_module.run(params, log_path, kill_switch=kill_switch)
    finally:
        kill_switch.stop()


if __name__ == "__main__":
    main()
