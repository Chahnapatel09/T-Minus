"""Lane D. Random forest: probability that a pixel is mining."""
from . import config as C

FEATURES = ["before", "after", "diff", "min_later", "texture_5x5", "slope", "worldcover"]


def features(before, after, min_later, slope, worldcover):
    """Per-pixel features in FEATURES order."""
    raise NotImplementedError


def train(feats, mining, stable_forest, other_clearing):
    """Fit the classifier.

    Label 1: inside a 2019 mining polygon.
    Label 0: stable forest or clearings more than C.NEG_MIN_DIST_M from any mining polygon.
    Balanced classes, train/test split by C.BLOCK_M blocks.
    Returns (classifier, held-out test pixels).
    """
    raise NotImplementedError


def predict(clf, feats):
    """Probability-of-mining raster."""
    raise NotImplementedError
