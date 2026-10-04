"""Lane D. Accuracy check. Never graded on the pixels the model was trained on."""
import numpy as np
import pandas as pd
from scipy import ndimage

from . import config as C


def score(truth, fired, where=None):
    """Hits, misses, false alarms, precision, recall. `where` limits the pixels that are graded."""
    truth = np.asarray(truth).astype(bool)
    fired = np.asarray(fired).astype(bool)
    if where is not None:
        where = np.asarray(where).astype(bool)
        truth, fired = truth[where], fired[where]
    hits = int((truth & fired).sum())
    misses = int((truth & ~fired).sum())
    false_alarms = int((~truth & fired).sum())
    precision = hits / (hits + false_alarms) if hits + false_alarms else None
    recall = hits / (hits + misses) if hits + misses else None
    return {"hits": hits, "misses": misses, "false_alarms": false_alarms,
            "precision": precision, "recall": recall}


def evaluate(truth, rule_fired, model_fired, where=None):
    """Scores for rule only, model only and combined.

    combined = either detector fired (the alerts); both = high confidence (both fired).
    """
    rule = np.asarray(rule_fired).astype(bool)
    model = np.asarray(model_fired).astype(bool)
    return {
        "rule": score(truth, rule, where),
        "model": score(truth, model, where),
        "combined": score(truth, rule | model, where),
        "both": score(truth, rule & model, where),
    }


def eye_points(profile):
    """Load data/helpers/check_points.csv (lon, lat, mining): the ~60 points checked by eye.

    Returns a DataFrame with the columns row, col, mining (bool) for the points inside the grid,
    or None if the file does not exist.
    """
    from rasterio.transform import rowcol
    from rasterio.warp import transform

    path = C.HELPERS / "check_points.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    xs, ys = transform("EPSG:4326", profile["crs"], df["lon"].tolist(), df["lat"].tolist())
    rows, cols = rowcol(profile["transform"], xs, ys)
    out = pd.DataFrame({"row": np.asarray(rows), "col": np.asarray(cols),
                        "mining": df["mining"].astype(int).astype(bool).to_numpy()})
    inside = (out.row >= 0) & (out.row < profile["height"]) & (out.col >= 0) & (out.col < profile["width"])
    return out[inside].reset_index(drop=True)


def evaluate_points(points, rule_fired, model_fired):
    """Same as evaluate, graded on the eye-checked points. A detection within 1 pixel counts."""
    def near(a):
        return ndimage.maximum_filter(np.asarray(a).astype("uint8"), size=3) > 0

    r, c = points["row"].to_numpy(), points["col"].to_numpy()
    return evaluate(points["mining"].to_numpy(), near(rule_fired)[r, c], near(model_fired)[r, c])
