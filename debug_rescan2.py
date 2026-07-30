import cv2
import numpy as np

from engine import capture, window

rect = window.find_runelite_rect()
left, top, right, bottom = rect
img = capture.grab_region(rect, (0, 0, right - left, bottom - top))  # full window, BGR

viewport = img[0:360, 0:530]  # whole game viewport, excludes chatbox/sidebar
r = viewport[:, :, 2].astype(int)
g = viewport[:, :, 1].astype(int)
b = viewport[:, :, 0].astype(int)
mask = (r > 130) & (r - g > 60) & (r - b > 60)  # reddish relative to its own g/b, looser

ys, xs = np.where(mask)
print(f"n={len(ys)}")
if len(ys):
    print(f"x:[{xs.min()}-{xs.max()}] y:[{ys.min()}-{ys.max()}]")
    for y_band in range(0, 360, 10):
        count = int(((ys >= y_band) & (ys < y_band + 10)).sum())
        if count:
            print(f"  y {y_band}-{y_band+10}: {count}")

cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\viewport_debug.png", viewport)
print("saved full viewport crop")
