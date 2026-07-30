"""Color detection over a captured region. Replaces AHK's single-pixel
PixelSearch with a vectorized mask + connected-components, so we get every
matching blob and its centroid in one pass instead of hand-listing slot
coordinates."""
import cv2
import numpy as np


def _hex_to_bgr(color_hex):
    r = (color_hex >> 16) & 0xFF
    g = (color_hex >> 8) & 0xFF
    b = color_hex & 0xFF
    return np.array([b, g, r], dtype=np.uint8)


def color_present(img_bgr, color_hex, tolerance=15):
    target = _hex_to_bgr(color_hex)
    diff = np.abs(img_bgr.astype(np.int16) - target.astype(np.int16))
    mask = np.all(diff <= tolerance, axis=-1)
    return bool(np.any(mask))


def dominant_channel_present(img_bgr, high_channels, low_channels, min_value=130, min_diff=40):
    """More robust to alpha-blended overlays than exact-hex matching.

    HUD text drawn directly over the 3D viewport (no solid backing panel)
    blends with whatever's rendered behind it, so its on-screen color drifts
    with camera angle/terrain instead of staying a fixed hex value. Checking
    that specific channels dominate by a margin -- rather than requiring a
    near-pure hex match -- tolerates that blending. Channels are BGR indices
    (0=B, 1=G, 2=R).
    """
    img = img_bgr.astype(np.int16)
    mask = np.ones(img.shape[:2], dtype=bool)
    for hc in high_channels:
        mask &= img[:, :, hc] > min_value
        for lc in low_channels:
            mask &= (img[:, :, hc] - img[:, :, lc]) > min_diff
    return bool(np.any(mask))


def find_blobs(img_bgr, color_hex, tolerance=15, min_area=4):
    """Returns list of dicts: {cx, cy, area} in region-local pixel coords,
    one per connected blob of matching color, largest first."""
    target = _hex_to_bgr(color_hex)
    diff = np.abs(img_bgr.astype(np.int16) - target.astype(np.int16))
    mask = np.all(diff <= tolerance, axis=-1).astype(np.uint8)

    n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)

    blobs = []
    for label in range(1, n_labels):  # skip label 0 = background
        area = stats[label, cv2.CC_STAT_AREA]
        if area < min_area:
            continue
        cx, cy = centroids[label]
        blobs.append({"cx": float(cx), "cy": float(cy), "area": int(area)})

    blobs.sort(key=lambda b: b["area"], reverse=True)
    return blobs
