import time
import cv2
import numpy as np
import win32gui
import pyautogui
import mss

def find_rect(title):
    matches = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) == title:
            matches.append(hwnd)
    win32gui.EnumWindows(cb, None)
    return win32gui.GetWindowRect(matches[0])

rect = find_rect("AHK Color Bot Launcher")
left, top, right, bottom = rect

def shot(name):
    with mss.mss() as sct:
        img = np.array(sct.grab({"left": left, "top": top, "width": right-left, "height": bottom-top}))
    cv2.imwrite(f"shots/gui_{name}.png", img[:, :, :3])

# set duration to 8
pyautogui.click(left + 177, top + 94)
pyautogui.hotkey("ctrl", "a")
pyautogui.typewrite("8", interval=0.05)

pyautogui.click(left + 60, top + 139)  # Start
time.sleep(3)
shot("timer_running")

time.sleep(6.5)
shot("timer_finished")
