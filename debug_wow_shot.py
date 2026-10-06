"""Read-only calibration capture: saves the whole WoW window to
shots/wow_window.png (gitignored) and prints its rect. Crop/inspect it to
pick the water region -- coordinates in that PNG are window-relative."""
import os

import cv2
import win32gui

from engine import capture, window
from tasks.wow_fish import WINDOW_TITLE, cursor_signature

rect = window.find_runelite_rect(WINDOW_TITLE)
left, top, right, bottom = rect
img = capture.grab_region(rect, (0, 0, right - left, bottom - top))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots", "wow_window.png")
cv2.imwrite(out, img)
print("window rect:", rect, "size:", right - left, "x", bottom - top)
h = win32gui.GetCursorInfo()[1]
print("cursor handle now:", h, "signature:", cursor_signature(h),
      "(hover the bobber for its bobber_cursor_sig)")
print("saved", out)
