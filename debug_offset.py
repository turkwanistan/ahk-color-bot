import cv2
import numpy as np

from engine import capture, window

rect = window.find_runelite_rect()
left, top, right, bottom = rect
img = capture.grab_region(rect, (0, 0, right - left, bottom - top))  # BGR, window-relative

top_area = img[0:100, 0:150]
g = top_area[:, :, 1].astype(int)
r = top_area[:, :, 2].astype(int)
b = top_area[:, :, 0].astype(int)
mask = (g > 130) & (g - r > 40) & (g - b > 40)

ys, xs = np.where(mask)
print(f"mss capture: green pixels n={len(ys)}")
if len(ys):
    print(f"window-relative x:[{xs.min()}-{xs.max()}] y:[{ys.min()}-{ys.max()}]")

cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\mss_green_crop.png", top_area)
