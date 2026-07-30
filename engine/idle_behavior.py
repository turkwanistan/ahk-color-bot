"""Generic downtime pacing -- a few actions early in a wait (for a resource
respawn, a trade, whatever), then genuine stillness until something
changes. A human glances at the camera or a tab once or twice near the
start of a wait, then leaves it alone (watching something else) rather
than fidgeting the entire time. Any task with idle downtime can reuse this
instead of reimplementing the budget/reset bookkeeping.
"""
import random


def _action_name(action):
    if hasattr(action, "__name__"):
        return action.__name__
    func = getattr(action, "func", None)  # functools.partial
    if func is not None:
        return getattr(func, "__name__", repr(action))
    return repr(action)


class IdleBehaviorManager:
    def __init__(self, actions, weights=None, actions_per_stretch=(1, 3)):
        """actions: list of callables taking (win_rect,) -- e.g. a mouse
        drift/camera fidget plus one or more tab-check behaviors.
        weights: optional relative weights for random.choices, same length
        as actions (default: uniform)."""
        self.actions = actions
        self.weights = weights
        self.actions_per_stretch = actions_per_stretch
        self._active = False
        self._budget = 0
        self._used = 0

    def reset(self):
        """Call when the downtime stretch ends (target found / busy again)
        so the next stretch starts fresh with a new random budget."""
        self._active = False

    def maybe_act(self, win_rect, log=None):
        """Call once per idle tick. Spends from the stretch's budget if any
        remains, otherwise does nothing (genuinely idle)."""
        if not self._active:
            self._active = True
            self._budget = random.randint(*self.actions_per_stretch)
            self._used = 0
            if log:
                log.log("idle_stretch_start", budget=self._budget)

        if self._used < self._budget:
            action = random.choices(self.actions, weights=self.weights, k=1)[0]
            if log:
                log.log("idle_action", which=_action_name(action))
            action(win_rect)
            self._used += 1
        # else: budget spent for this stretch -- stay still
