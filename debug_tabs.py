import cv2
from engine import capture, window

rect = window.find_runelite_rect()
img = capture.grab_region(rect, (535, 195, 770, 230))
cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\tab_row.png", img)
print("saved, shape:", img.shape)
