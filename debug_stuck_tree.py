import cv2

from engine import detect
from tasks.chop_tree import TREE_REGION, TREE_COLOR

img = cv2.imread(r"C:\Users\Wanstation\.runelite\screenshots\Were Family\2026-07-30_08-20-18.png")

x1, y1, x2, y2 = TREE_REGION
canvas_region = (x1 - 8, y1, x2 - 8, y2)
cx1, cy1, cx2, cy2 = canvas_region
crop = img[cy1:cy2, cx1:cx2]
print("TREE_REGION crop shape:", crop.shape)

blobs = detect.find_blobs(crop, TREE_COLOR, min_area=20)
print(f"blobs found: {len(blobs)}")
for b in blobs:
    print(f"  cx={b['cx']:.1f} cy={b['cy']:.1f} area={b['area']}  -> absolute click target: ({cx1+b['cx']:.1f}, {cy1+b['cy']:.1f})")

cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\stuck_tree_region.png", crop)
