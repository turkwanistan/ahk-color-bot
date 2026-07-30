"""Generic inventory-grid helpers -- usable by any task that clicks a set
of detected blobs sitting in an inventory-shaped grid (dropping logs, ore,
whatever), not specific to any one activity."""
import random


def human_drop_order(blobs, region_bounds, rows=7):
    """Order items the way a person actually clears a grid: row by row, not
    jumping to random points all over the inventory. What varies between
    drops is WHICH coherent pattern gets used, not whether there's one --
    snake vs. straight rows, top-start vs. bottom-start, left- vs.
    right-first -- each individual drop still reads as a plausible human
    traversal, never a scatter."""
    _, y1, _, y2 = region_bounds
    row_height = (y2 - y1) / rows

    def row_of(b):
        return int(b["cy"] // row_height)

    snake = random.random() < 0.6
    start_right = random.random() < 0.3
    rows_present = sorted(set(row_of(b) for b in blobs))
    if random.random() < 0.3:
        rows_present = rows_present[::-1]  # occasionally start from the bottom row

    ordered = []
    for i, r in enumerate(rows_present):
        row_blobs = [b for b in blobs if row_of(b) == r]
        going_right = not start_right
        if snake and i % 2 == 1:
            going_right = not going_right
        row_blobs.sort(key=lambda b: b["cx"], reverse=not going_right)
        ordered.extend(row_blobs)
    return ordered
