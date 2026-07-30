import cv2
import numpy as np

from engine import capture, window

rect = window.find_runelite_rect()
left, top, right, bottom = rect
img = capture.grab_region(rect, (0, 0, right - left, bottom - top))  # full window, BGR

# red-ish: R high, G low, B low (only look at the top part of the viewport, avoid chatbox)
top_area = img[0:130, 0:250]
r = top_area[:, :, 2].astype(int)
g = top_area[:, :, 1].astype(int)
b = top_area[:, :, 0].astype(int)
mask = (r > 180) & (g < 90) & (b < 90)

ys, xs = np.where(mask)
if len(ys) == 0:
    print("no red pixels found in top-left 250x130 area")
else:
    print(f"n={len(ys)} x:[{xs.min()}-{xs.max()}] y:[{ys.min()}-{ys.max()}]")
    # histogram by row
    for y_band in range(0, 130, 5):
        count = int(((ys >= y_band) & (ys < y_band + 5)).sum())
        if count:
            print(f"  y {y_band}-{y_band+5}: {count}")

cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\top_area_debug.png", top_area)
print("saved crop of top-left 250x130 area for visual check")
