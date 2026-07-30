import cv2
import numpy as np

from engine import detect
from tasks.chop_tree import BUSY_REGION

img = cv2.imread(r"C:\Users\Wanstation\.runelite\screenshots\Were Family\2026-07-30_08-20-18.png")
print("screenshot shape (h,w,c):", img.shape)

# this screenshot is RuneLite's own canvas capture, offset -8px in x vs
# window-relative coords (measured earlier), 0 in y
x1, y1, x2, y2 = BUSY_REGION
canvas_region = (x1 - 8, y1, x2 - 8, y2)
cx1, cy1, cx2, cy2 = canvas_region
crop = img[cy1:cy2, cx1:cx2]
print("BUSY_REGION crop shape:", crop.shape)

result = detect.dominant_channel_present(crop, high_channels=[1], low_channels=[0, 2])
print("is_busy would report:", result)

# show exactly which pixels triggered it, if any
g = crop[:, :, 1].astype(int)
r = crop[:, :, 2].astype(int)
b = crop[:, :, 0].astype(int)
mask = (g > 130) & (g - r > 40) & (g - b > 40)
ys, xs = np.where(mask)
print(f"matching pixel count: {len(ys)}")
if len(ys):
    for y, x in list(zip(ys, xs))[:10]:
        print(f"  at ({x},{y}) BGR={tuple(crop[y,x])}")

cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\stuck_busy_region.png", crop)
