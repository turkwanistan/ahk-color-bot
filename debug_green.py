import cv2
import numpy as np

img = cv2.imread(r"C:\Users\Wanstation\.runelite\screenshots\Were Family\2026-07-30_08-07-22.png")
print("shape (h,w,c):", img.shape)

top_area = img[0:100, 0:150]
r = top_area[:, :, 2].astype(int)
g = top_area[:, :, 1].astype(int)
b = top_area[:, :, 0].astype(int)
mask = (g > 130) & (g - r > 40) & (g - b > 40)

ys, xs = np.where(mask)
print(f"green-ish pixels n={len(ys)}")
if len(ys):
    print(f"x:[{xs.min()}-{xs.max()}] y:[{ys.min()}-{ys.max()}]")
    # mode color among matches
    colors = top_area[ys, xs]
    uniq, counts = np.unique(colors.reshape(-1, 3), axis=0, return_counts=True)
    top5 = uniq[np.argsort(counts)[::-1][:5]]
    top5_counts = counts[np.argsort(counts)[::-1][:5]]
    for c, cnt in zip(top5, top5_counts):
        b_, g_, r_ = c
        print(f"  BGR={tuple(c)} hex=0x{r_:02X}{g_:02X}{b_:02X} count={cnt}")

cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\green_crop.png", top_area)
