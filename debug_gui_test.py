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
print("gui rect:", rect)

def shot(name):
    with mss.mss() as sct:
        img = np.array(sct.grab({"left": left, "top": top, "width": right-left, "height": bottom-top}))
    cv2.imwrite(f"shots/gui_{name}.png", img[:, :, :3])

# set duration to 4
pyautogui.click(left + 177, top + 94)
pyautogui.hotkey("ctrl", "a")
pyautogui.typewrite("4", interval=0.05)

# click Start
pyautogui.click(left + 60, top + 139)
time.sleep(1.5)
shot("running")

time.sleep(3)
shot("after_finish")
