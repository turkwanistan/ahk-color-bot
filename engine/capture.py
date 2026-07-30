"""Screen capture of window-relative regions, always resolved against the
current window rect (never a cached absolute position)."""
import mss
import numpy as np


def grab_region(win_rect, rel_box):
    """rel_box = (x1, y1, x2, y2) relative to the window's top-left.
    Returns a BGR numpy array (OpenCV convention)."""
    left, top, _, _ = win_rect
    x1, y1, x2, y2 = rel_box
    monitor = {
        "left": left + x1,
        "top": top + y1,
        "width": x2 - x1,
        "height": y2 - y1,
    }
    with mss.mss() as sct:
        frame = np.array(sct.grab(monitor))  # BGRA
    return frame[:, :, :3]
