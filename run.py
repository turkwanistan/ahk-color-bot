import argparse
import os
import time

import pyautogui

from engine import window
from engine.killswitch import KillSwitch
from tasks import chop_tree, wow_fish

TASKS = {
    "chop_tree": chop_tree,
    "wow_fish": wow_fish,
}


def arm_window_corner_failsafe(title_substring="RuneLite"):
    """pyautogui's default FAILSAFE_POINTS are corners of the PRIMARY monitor
    only (from pyautogui.size()). On a multi-monitor setup where RuneLite
    lives on a non-primary display at negative coordinates, none of those
    default corners are anywhere near the game window -- slamming the mouse
    to a corner of the screen you're actually watching would do nothing.
    Add the RuneLite window's own corners instead, so that gesture works."""
    left, top, right, bottom = window.find_runelite_rect(title_substring)
    corners = [(left, top), (right - 1, top), (left, bottom - 1), (right - 1, bottom - 1)]
    pyautogui.FAILSAFE_POINTS = list(pyautogui.FAILSAFE_POINTS) + corners


def window_title(task_module):
    return getattr(task_module, "WINDOW_TITLE", "RuneLite")


def coerce(spec, raw):
    return {"int": int, "float": float}.get(spec["type"], str)(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=TASKS.keys())
    parser.add_argument("--duration", type=int, default=120, help="seconds")
    parser.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                        help="override a task param, e.g. --set water_region=100,300,1800,700")
    args = parser.parse_args()

    task_module = TASKS[args.task]
    specs = {p["name"]: p for p in task_module.PARAMS}
    params = {name: p["default"] for name, p in specs.items()}
    params["duration_s"] = args.duration
    for item in args.set:
        name, raw = item.split("=", 1)
        params[name] = coerce(specs[name], raw)

    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{args.task}_{int(time.time())}.jsonl")
    print(f"logging to {log_path}", flush=True)
    print("press F12 at any time to stop immediately, F11 to pause/resume", flush=True)

    arm_window_corner_failsafe(window_title(task_module))
    kill_switch = KillSwitch()
    kill_switch.start()
    try:
        task_module.run(params, log_path, kill_switch=kill_switch)
    finally:
        kill_switch.stop()


if __name__ == "__main__":
    main()
