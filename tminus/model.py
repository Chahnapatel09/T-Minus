"""Lane D. Random forest: probability that a pixel is mining."""
import numpy as np
from scipy import ndimage
from sklearn.ensemble import RandomForestClassifier

from . import config as C

FEATURES = ["before", "after", "diff", "min_later", "texture_5x5", "slope", "worldcover"]


def _texture(arr, size=5):
    """Local standard deviation in a size x size window."""
    fill = np.nanmean(arr) if np.isfinite(arr).any() else 0.0
    a = np.where(np.isnan(arr), fill, arr).astype("float64")
    mean = ndimage.uniform_filter(a, size)
    sq = ndimage.uniform_filter(a * a, size)
    return np.sqrt(np.clip(sq - mean * mean, 0, None)).astype("float32")


def features(before, after, min_later, slope, worldcover, extra=None):
    """Per-pixel features in FEATURES order, then any `extra` layers ({name: (H, W)}, e.g. the
    foundation-model features from embed.change_layers). Returns an (H, W, n) float32 array."""
    layers = [before, after, before - after, min_later, _texture(after), slope, worldcover]
    layers += list((extra or {}).values())
    return np.stack([np.asarray(x, dtype="float32") for x in layers], axis=-1)


def train(feats, mining, stable_forest, other_clearing):
    """Fit the classifier.

    Label 1: inside a 2019 mining polygon.
    Label 0: stable forest more than C.NEG_FOREST_MIN_DIST_M from any mining polygon, or other
    clearings more than C.NEG_MIN_DIST_M from one.
    Balanced classes, train/test split by C.BLOCK_M blocks.
    Returns (classifier, held-out test pixels). The test pixels are a dict:
    "mask" (bool H x W, labelled pixels in held-out blocks) and "truth" (bool H x W, mining).
    """
    h, w, nf = feats.shape
    mining = np.asarray(mining).astype(bool)
    if not mining.any():
        raise ValueError("no mining pixels: is data/helpers/mining2019.tif on the grid?")
    dist = ndimage.distance_transform_edt(~mining) * C.RES
    # Stable forest is "not mining" right up to a mine's edge: this also teaches the model that being
    # next to a mine is not enough. Other clearings only count when well away from any mine.
    negative = ((np.asarray(stable_forest).astype(bool) & (dist > C.NEG_FOREST_MIN_DIST_M))
                | (np.asarray(other_clearing).astype(bool) & (dist > C.NEG_MIN_DIST_M)))
    del dist
    labelled = mining | negative

    side = max(1, int(C.BLOCK_M // C.RES))
    n_bc = -(-w // side)
    block = ((np.arange(h) // side)[:, None] * n_bc + (np.arange(w) // side)[None, :]).astype("int32")
    rng = np.random.default_rng(C.SEED)
    usable = np.unique(block[labelled])
    if len(usable) < 2:
        raise ValueError("need labelled pixels in at least two blocks to split train and test")
    n_test = min(len(usable) - 1, max(1, round(C.TEST_FRACTION * len(usable))))
    held_out = np.isin(block, rng.choice(usable, size=n_test, replace=False))

    pos = np.flatnonzero((mining & ~held_out).ravel())
    neg = np.flatnonzero((negative & ~held_out).ravel())
    n = min(len(pos), len(neg), C.MAX_SAMPLES_PER_CLASS)
    if n == 0:
        raise ValueError("a class has no training pixels after the block split")
    idx = np.concatenate([rng.choice(pos, n, replace=False), rng.choice(neg, n, replace=False)])
    flat = feats.reshape(-1, nf)
    y = np.r_[np.ones(n, dtype=int), np.zeros(n, dtype=int)]
    clf = RandomForestClassifier(n_estimators=200, min_samples_leaf=5, class_weight="balanced",
                                 n_jobs=-1, random_state=C.SEED)
    clf.fit(flat[idx], y)
    return clf, {"mask": labelled & held_out, "truth": mining}


def predict(clf, feats):
    """Probability-of-mining raster, float32 (H, W)."""
    h, w, nf = feats.shape
    out = np.zeros((h, w), dtype="float32")
    step = max(1, 2_000_000 // w)
    for r in range(0, h, step):
        chunk = feats[r:r + step].reshape(-1, nf)
        out[r:r + step] = clf.predict_proba(chunk)[:, 1].reshape(-1, w)
    return out
