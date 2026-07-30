"""Randomized timing/positioning. Python's random.gauss() already does what
the AHK Box-Muller code had to hand-roll (randposition/rest) -- this whole
file is a fraction of the size of the AHK equivalent."""
import random
import time


def jitter(mu, sigma, lo, hi):
    return max(lo, min(hi, random.gauss(mu, sigma)))


def rest(t1_ms, t2_ms):
    mean = (t1_ms + t2_ms) / 2
    sd = (t2_ms - t1_ms) / 3
    delay_ms = max(t1_ms * 0.5, min(t2_ms * 1.5, random.gauss(mean, sd)))
    time.sleep(delay_ms / 1000)


def reaction_delay():
    """How long a human takes to notice their character went idle and react
    -- not instant, not constant. Usually a quick beat; occasionally (still
    watching a video, alt-tabbed, distracted) noticeably slower. Call this
    once on the busy->idle transition, not on every poll thereafter -- a
    human doesn't re-hesitate every tick once they've already reacted."""
    if random.random() < 0.15:
        rest(1500, 3500)  # distracted / slow to notice
    else:
        rest(150, 900)  # normal noticing variance
