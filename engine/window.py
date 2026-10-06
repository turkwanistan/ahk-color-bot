"""Locates the RuneLite window fresh every call.

Position and monitor can change session to session (or mid-session, if the
user drags it) -- nothing here is allowed to cache a rect across calls.
"""
import win32gui


class WindowNotFoundError(RuntimeError):
    pass


def find_runelite_rect(title_substring="RuneLite"):
    """Returns (left, top, right, bottom) in absolute virtual-screen coords."""
    matches = []

    def _enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if title_substring.lower() in title.lower():
            matches.append(hwnd)

    win32gui.EnumWindows(_enum_handler, None)

    # an exact title wins over substring hits -- "World of Warcraft" would
    # otherwise also match a browser window showing a WoW site
    exact = [h for h in matches if win32gui.GetWindowText(h).lower() == title_substring.lower()]
    if exact:
        matches = exact

    if not matches:
        raise WindowNotFoundError(f"No visible window with '{title_substring}' in its title")
    if len(matches) > 1:
        raise WindowNotFoundError(
            f"Found {len(matches)} windows matching '{title_substring}' -- ambiguous"
        )

    return win32gui.GetWindowRect(matches[0])


def is_foreground(title_substring):
    """True if the focused window's title contains title_substring -- check
    before sending keys so they never land in some other app."""
    title = win32gui.GetWindowText(win32gui.GetForegroundWindow())
    return title_substring.lower() in title.lower()


def to_absolute(rect, rel_x, rel_y):
    """Window-relative (rel_x, rel_y) -> absolute virtual-screen coords."""
    left, top, _, _ = rect
    return left + rel_x, top + rel_y
