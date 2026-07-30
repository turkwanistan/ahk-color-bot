import cv2
from engine import capture, window

rect = window.find_runelite_rect()
left, top, right, bottom = rect
print("window rect:", rect, "logical size:", right - left, "x", bottom - top)

img = capture.grab_region(rect, (0, 0, right - left, bottom - top))
print("mss captured size (h,w,c):", img.shape)

cv2.imwrite(r"C:\Users\Wanstation\Downloads\ahk-color-bot\shots\mss_fullwindow.png", img)
print("saved")
