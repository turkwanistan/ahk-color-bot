import cv2
import numpy as np

from engine import capture, window
from tasks.chop_tree import IDLE_REGION, IDLE_COLOR

rect = window.find_runelite_rect()
print("window rect:", rect)
print("IDLE_REGION (window-relative):", IDLE_REGION)

img = capture.grab_region(rect, IDLE_REGION)
print("captured shape (h,w,c):", img.shape)

target_bgr = np.array([IDLE_COLOR & 0xFF, (IDLE_COLOR >> 8) & 0xFF, (IDLE_COLOR >> 16) & 0xFF], dtype=np.int16)
diff = np.abs(img.astype(np.int16) - target_bgr)
dist = diff.sum(axis=-1)
min_idx = np.unravel_index(np.argmin(dist), dist.shape)
print("closest pixel to target color, per-channel diff:", diff[min_idx], "at (y,x)=", min_idx)
print("that pixel's actual BGR:", img[min_idx])

# save a crop so we can actually look at it
cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\idle_region_debug.png", img)
print("saved crop to shots/idle_region_debug.png")
