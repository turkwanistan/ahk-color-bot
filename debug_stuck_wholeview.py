import cv2

from engine import detect
from tasks.chop_tree import TREE_COLOR

img = cv2.imread(r"C:\Users\Wanstation\.runelite\screenshots\Were Family\2026-07-30_08-20-18.png")

viewport = img[0:360, 0:530]  # whole game viewport in canvas coords
blobs = detect.find_blobs(viewport, TREE_COLOR, min_area=20)
print(f"blobs found in FULL viewport: {len(blobs)}")
for b in blobs:
    print(f"  canvas coords: cx={b['cx']:.1f} cy={b['cy']:.1f} area={b['area']}")

print()
print("TREE_REGION in canvas coords was: (198, 134, 384, 355)")
