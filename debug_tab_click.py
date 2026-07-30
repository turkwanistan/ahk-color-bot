import time
import cv2

from engine import capture, window
from engine import input as bot_input

rect = window.find_runelite_rect()

bot_input.click_point(rect, 585, 212, jitter_px=3)
time.sleep(0.5)
img = capture.grab_region(rect, (535, 230, 770, 480))
cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\after_skills_click.png", img)
print("clicked (585,212), saved panel content")

time.sleep(1.0)

bot_input.click_point(rect, 652, 212, jitter_px=3)
time.sleep(0.5)
img2 = capture.grab_region(rect, (535, 230, 770, 480))
cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\after_inv_click.png", img2)
print("clicked (652,212), saved panel content")
