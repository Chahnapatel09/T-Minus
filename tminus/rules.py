"""Lane B. Rule-based detector."""
import numpy as np

from . import config as C

NONE, CLEARED, WATER = 0, 1, 2


def _state(before, after):
    """(changed, water) for one later scene against the baseline."""
    water = after < C.WATER_DB
    return ((before - after) >= C.DROP_DB) | water, water


def detect(before, after, confirm=None, forest=None):
    """Forest pixels that drop >= C.DROP_DB or fall below C.WATER_DB, and stay that way on `confirm`.

    All inputs are dB arrays on the same grid. A pixel is forest if `before` is brighter than
    C.FOREST_MIN_DB (and inside `forest`, a boolean mask, when one is given).
    Returns uint8: 0 none, 1 cleared, 2 water.
    """
    is_forest = before > C.FOREST_MIN_DB
    if forest is not None:
        is_forest &= forest.astype(bool)
    changed, water = _state(before, after)
    if confirm is not None:
        still_changed, still_water = _state(before, confirm)
        changed &= still_changed
        water &= still_water
    changed &= is_forest
    out = np.where(changed, np.where(water, WATER, CLEARED), NONE)
    return out.astype("uint8")
