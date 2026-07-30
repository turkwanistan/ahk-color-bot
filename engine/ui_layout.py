"""Shared facts about the game client's UI chrome itself -- these describe
the RuneLite window layout, not any particular task, so any task running
in the same client layout can reuse them directly instead of redefining
them per-task.

Calibrated 2026-07-30 against a 1062x542 RuneLite window (classic/fixed
layout, 7 visible tabs -- no Friends List tab reachable in this compact
layout). If the client is resized or the layout mode changes, these need
re-verifying against a live screenshot -- never trust them blind.
"""

# tab bar icons -- all at the same y in this layout
COMBAT_TAB_POS = (552, 212)
SKILLS_TAB_POS = (585, 212)
QUEST_TAB_POS = (619, 212)
INVENTORY_TAB_POS = (652, 212)  # verified live: returns to inventory grid
EQUIPMENT_TAB_POS = (686, 212)  # verified live: opens worn-equipment panel
PRAYER_TAB_POS = (719, 212)
MAGIC_TAB_POS = (753, 212)

# inventory grid: 28 slots, 4 cols x 7 rows
INV_REGION = (571, 238, 741, 484)
INV_BOTTOM_ROW = (571, 449, 741, 484)  # last row -- full here implies full grid

# the "current action" status text (e.g. "Woodcutting" / "NOT woodcutting")
# sits directly over the 3D viewport at a fixed screen position regardless
# of which skill is active -- likely reusable as-is for any skilling task
# using the same overlay, but spot-verify the color for each new activity
# rather than assume: it's plausible some activities render this
# differently. Detect "busy" via the colored/active state, not the
# "NOT <skill>ing" idle text -- that text is transient and fades after
# being idle a while, so its absence does NOT reliably mean idle.
ACTIVITY_STATUS_REGION = (40, 52, 130, 80)
ACTIVITY_BUSY_COLOR = 0x00FF00

# skills panel: 3 cols x 8 rows, standard OSRS grid ordering (well-known,
# stable for years). Only Woodcutting's position has been hover-verified
# live (tooltip read "Woodcutting XP: ...") -- other entries are computed
# from the standard grid and should still be spot-checked before first
# real use on a new skill.
SKILLS_PANEL_ORIGIN = (535, 230)  # top-left of the skills panel content area
SKILLS_PANEL_COLS = 3
SKILLS_PANEL_CELL = (78.3, 31.25)

SKILL_GRID_ORDER = [
    "Attack", "Hitpoints", "Mining",
    "Strength", "Agility", "Smithing",
    "Defence", "Herblore", "Fishing",
    "Ranged", "Thieving", "Cooking",
    "Prayer", "Crafting", "Firemaking",
    "Magic", "Fletching", "Woodcutting",
    "Runecraft", "Slayer", "Farming",
    "Construction", "Hunter", "Overall",
]


def skill_icon_pos(skill_name):
    """Window-relative (x, y) center of a skill's icon in the skills panel."""
    idx = SKILL_GRID_ORDER.index(skill_name)
    row, col = divmod(idx, SKILLS_PANEL_COLS)
    ox, oy = SKILLS_PANEL_ORIGIN
    cw, ch = SKILLS_PANEL_CELL
    return (ox + (col + 0.5) * cw, oy + (row + 0.5) * ch)
