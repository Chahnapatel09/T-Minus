"""Lane B. Rule-based detector."""
from . import config as C

NONE, CLEARED, WATER = 0, 1, 2


def detect(before, after, confirm=None, forest=None):
    """Forest pixels that drop >= C.DROP_DB or fall below C.WATER_DB, and stay that way on `confirm`.

    All inputs are dB arrays on the same grid. Returns uint8: 0 none, 1 cleared, 2 water.
    """
    raise NotImplementedError
