import time
import cv2

from engine import capture, window
from engine import input as bot_input

rect = window.find_runelite_rect()

bot_input.click_point(rect, 686, 212, jitter_px=3)
time.sleep(0.6)
img = capture.grab_region(rect, (535, 230, 770, 480))
cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\after_equip_click.png", img)
print("clicked (686,212), saved")

bot_input.click_point(rect, 652, 212, jitter_px=3)
