import time
import cv2

from engine import capture, window
from engine import input as bot_input
import pyautogui

rect = window.find_runelite_rect()

# open skills tab
bot_input.click_point(rect, 585, 212, jitter_px=3)
time.sleep(0.6)

# hover estimated Woodcutting icon position (row 6 of 8, col 3 of 3)
wx, wy = 731, 402
ax, ay = window.to_absolute(rect, wx, wy)
pyautogui.moveTo(ax, ay, duration=0.2)
time.sleep(0.8)

img = capture.grab_region(rect, (535, 230, 900, 480))
cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\wc_hover_check.png", img)
print("hovered at", wx, wy, "-- saved for visual check")

# revert to inventory
bot_input.click_point(rect, 652, 212, jitter_px=3)
