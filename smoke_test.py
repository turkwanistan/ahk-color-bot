"""Read-only sanity check: no clicks, just verifies window lookup + detection."""
from engine import window
from tasks import chop_tree

rect = window.find_runelite_rect()
print("window rect:", rect)

print("is_busy:", chop_tree.is_busy(rect))
print("inventory_full:", chop_tree.inventory_full(rect))
print("find_tree:", chop_tree.find_tree(rect))
