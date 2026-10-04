"""Lane C. Gathers what the pipeline wrote in outputs/ into the one object the web page reads.

  python app/dashboard.py        # prints a summary of what the page would show

The shape is described at the top of app/web/data.js, which holds the sample
shown when there are no results yet.
"""
import base64
import io
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tminus import config as C  # noqa: E402
from tminus import crackdown as crackdown_mod  # noqa: E402
from tminus import rio  # noqa: E402

ASSETS = Path(__file__).resolve().parent / "assets"
PROMINENT_MIN_PX = 400    # smallest patch kept in the simplified overlay, in overlay-image pixels
TYPES = {"pond": "pond", "bare sand / tailings": "bare", "fresh clearing": "clearing"}
SCORE_NAMES = {"rule": "Rule only", "model": "Model only", "combined": "Either detector (all alerts)",
               "both": "Both agree (high confidence)"}


def _prominent(path):
    """The confidence overlay cut down to the changes that stand out: high confidence only,
    where the detections are dense, in patches of PROMINENT_MIN_PX pixels or more. PNG data URI."""
    from scipy import ndimage
    from tminus import webout

    rgba = np.asarray(Image.open(path).convert("RGBA"))
    high = (rgba[..., 3] > 0) & (rgba[..., :3] == webout.HIGH_RGBA[:3]).all(axis=-1)
    core = ndimage.uniform_filter(high.astype("float32"), 9) > 0.55
    core = ndimage.binary_closing(core, np.ones((5, 5), dtype=bool))
    labels, n = ndimage.label(core)
    sizes = ndimage.sum(core, labels, range(1, n + 1))
    keep = np.isin(labels, 1 + np.flatnonzero(sizes >= PROMINENT_MIN_PX))
    out = np.zeros(rgba.shape, dtype="uint8")
    out[keep] = (220, 20, 20, 190)
    buf = io.BytesIO()
    Image.fromarray(out, "RGBA").save(buf, "PNG", optimize=True)
    return _uri(buf.getvalue(), "image/png")


def out_dir():
    """outputs/, or another results folder named in TMINUS_OUT (handy for a teammate's copy)."""
    return Path(os.environ.get("TMINUS_OUT") or C.OUT)


def stamp(out=None):
    """Changes whenever the pipeline rewrites its results, so callers can cache build()."""
    out = Path(out or out_dir())
    files = [out / n for n in ("alerts.csv", "crackdown.csv", "crackdown_amw.csv", "accuracy.json")]
    files += sorted((out / "web").glob("*")) + sorted(ASSETS.glob("*")) + sorted(Path(C.HELPERS).glob("*.tif"))
    return tuple((str(p), p.stat().st_mtime) for p in files if p.exists())


def _iso(date):
    return f"{date[:4]}-{date[4:6]}-{date[6:]}"


def _clean(v):
    """JSON-safe: NaN to None, numpy scalars to Python."""
    if hasattr(v, "item"):
        v = v.item()
    return None if isinstance(v, float) and math.isnan(v) else v


def _uri(data, mime):
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def _scene(path):
    """A scene PNG as (dB array with NaN where there is no data, WebP data URI that keeps the gaps clear)."""
    rgba = np.asarray(Image.open(path).convert("RGBA"))
    grey, alpha = rgba[..., 0], rgba[..., 3]
    lo, hi = C.DB_STRETCH
    db = np.where(alpha > 0, lo + grey.astype("float32") / 255 * (hi - lo), np.nan)
    buf = io.BytesIO()
    Image.fromarray(np.dstack([grey, grey, grey, alpha]), "RGBA").save(buf, "WEBP", quality=85)
    return db, _uri(buf.getvalue(), "image/webp")


def _sample(db, rows, cols):
    """Mean brightness in the 3 x 3 pixels around each point (None where there is no data)."""
    h, w = db.shape
    out = []
    for r, c in zip(rows, cols):
        win = db[max(r - 1, 0):min(r + 2, h), max(c - 1, 0):min(c + 2, w)]
        out.append(round(float(np.nanmean(win)), 1) if np.isfinite(win).any() else None)
    return out


def _scores(block, best="both"):
    rows = []
    for key, sc in block.items():
        rows.append({"name": SCORE_NAMES.get(key, key), "hits": sc["hits"], "misses": sc["misses"],
                     "false_alarms": sc["false_alarms"], "precision": sc["precision"], "recall": sc["recall"],
                     "best": key == best})
    return rows


def _accuracy(acc):
    if not acc:
        return {"tables": [], "comparison": None}
    tables = []
    if "held_out" in acc:
        tables.append({
            "title": "Held-out map blocks", "unit": "pixels", "rows": _scores(acc["held_out"]),
            "note": f"Graded on {acc['held_out_pixels']:,} pixels in 2 km blocks the model never saw in training, "
                    f"against {acc.get('label_source', 'the mining labels')} (scene {_iso(acc['label_date'])})."})
    if "new_mining" in acc:
        tables.append({
            "title": f"New mining only, {acc['new_mining_years']}", "unit": "pixels",
            "rows": _scores(acc["new_mining"]),
            "note": "The same held-out blocks, graded only on mining that Amazon Mining Watch first confirmed "
                    "in these years. This is the test of change detection."})
    if len(acc.get("variants", {})) > 1:
        tables.append({
            "title": "Does the foundation model help?", "unit": "pixels",
            "rows": _scores(acc["variants"], best=acc.get("model_used")),
            "note": "The same random forest, trained with and without features from a pretrained radar network "
                    f"(ResNet50, SSL4EO-S12 Sentinel-1). The better one makes the map: {acc['model_used']}."})
    if "eye_points" in acc:
        tables.append({
            "title": "Points checked by eye", "unit": "points", "rows": _scores(acc["eye_points"]),
            "note": f"{acc['eye_points_n']} points checked by eye on the imagery. A detection within one pixel counts."})
    comparison = None
    if acc.get("comparison"):
        comparison = {
            "rows": [{k: _clean(v) for k, v in row.items()} for row in acc["comparison"]],
            "note": "Every model on the same held-out blocks, against Amazon Mining Watch. All mining: does it find "
                    f"mining land, old or new, by {acc['label_date'][:4]}? New mining: does it find mining that "
                    f"appeared in {acc.get('new_mining_years', 'the period')}? Inside AMW mines: the share of "
                    "everything it flags that falls inside Amazon Mining Watch's mines."}
    return {"tables": tables, "comparison": comparison}


def _amw():
    """Amazon Mining Watch on the grid (python -m tminus.labels), or None. Returns (array, profile)."""
    path = Path(C.HELPERS) / "amw_year.tif"
    if not path.exists():
        return None
    arr, profile = rio.read(path)
    return np.nan_to_num(arr).astype("int32"), profile


def _amw_at(amw, profile, lons, lats):
    """The AMW year at each point (0 = not mapped as mining, or outside the grid)."""
    from rasterio.transform import rowcol
    from rasterio.warp import transform

    xs, ys = transform("EPSG:4326", profile["crs"], list(lons), list(lats))
    rows, cols = rowcol(profile["transform"], xs, ys)
    rows, cols = np.asarray(rows), np.asarray(cols)
    inside = (rows >= 0) & (rows < amw.shape[0]) & (cols >= 0) & (cols < amw.shape[1])
    out = np.zeros(len(rows), dtype="int32")
    out[inside] = amw[rows[inside], cols[inside]]
    return out


def _agreement(alerts, years, last_year, first_year):
    """How many alerts land on mining that Amazon Mining Watch had mapped by the last scene."""
    hit = (years > 0) & (years <= last_year)
    old = hit & (years <= first_year)
    area = alerts["area_ha"].to_numpy()

    def part(label, mask):
        return {"label": label, "alerts": int(mask.sum()), "ha": round(float(area[mask].sum()), 1)}

    return {
        "last_year": last_year,
        "alerts": int(len(alerts)), "alerts_in": int(hit.sum()),
        "ha": round(float(area.sum()), 1), "ha_in": round(float(area[hit].sum()), 1),
        "parts": [part(f"In a mine mapped by {first_year} (that year or earlier)", old),
                  part(f"In a mine first confirmed {first_year + 1} to {last_year}", hit & ~old),
                  part(f"Not in a mine mapped by {last_year}", ~hit)],
    }


def _crackdown(out, amw=None):
    path = out / "crackdown.csv"
    if not path.exists():
        return None
    tbl = pd.read_csv(path)
    summ = crackdown_mod.summary(tbl)
    summary = {phase: {"inside": _clean(summ.loc[phase, "inside_ha_per_month"]),
                       "outside": _clean(summ.loc[phase, "outside_ha_per_month"])} for phase in ("before", "after")}
    # The pipeline writes this table when it has the labels; otherwise make it here from the same function.
    a = None
    if (out / "crackdown_amw.csv").exists():
        a = pd.read_csv(out / "crackdown_amw.csv")
    elif amw is not None:
        a = crackdown_mod.amw_table(amw[0], amw[1])
    amw = [{"label": str(int(r.year)), "inside": float(r.inside_ha), "outside": float(r.outside_ha)}
           for r in a.itertuples()] if a is not None and len(a) else None
    return {
        "event": "Operation Mercury", "date": _iso(C.CRACKDOWN), "unit": "ha per month",
        "rows": [{"start": r.start, "end": r.end, "phase": r.phase,
                  "inside": float(r.inside_ha_per_month), "outside": float(r.outside_ha_per_month)}
                 for r in tbl.itertuples()],
        "summary": summary, "amw": amw,
    }


def build(out=None):
    """The page's data, or None when the pipeline has not written results yet."""
    out = Path(out or out_dir())
    web = out / "web"
    if not (web / "meta.json").exists() or not (out / "alerts.csv").exists():
        return None
    meta = json.loads((web / "meta.json").read_text(encoding="utf8"))
    dates = [d for d in meta["dates"] if (web / f"scene_{d}.png").exists()]
    if len(dates) < 2:
        return None
    (south, west), (north, east) = meta["bounds"]

    alerts = pd.read_csv(out / "alerts.csv")
    amw = _amw()
    amw_years = _amw_at(amw[0], amw[1], alerts["lon"], alerts["lat"]) if amw is not None and len(alerts) else None
    scenes, series, size = [], [], None
    for d in dates:
        db, uri = _scene(web / f"scene_{d}.png")
        size = size or db.shape
        if db.shape != size:
            raise SystemExit(f"scene_{d}.png is not the same size as scene_{dates[0]}.png: rerun the pipeline.")
        h, w = db.shape
        cols = np.clip(((alerts["lon"] - west) / (east - west) * w).astype(int), 0, w - 1)
        rows = np.clip(((north - alerts["lat"]) / (north - south) * h).astype(int), 0, h - 1)
        scenes.append({"date": _iso(d), "img": uri})
        series.append(_sample(db, rows.tolist(), cols.tolist()))
    h, w = size

    recs = []
    for i, rec in enumerate(alerts.to_dict("records")):
        rec = {k: _clean(v) for k, v in rec.items()}
        recs.append({
            "id": rec["id"], "type": TYPES.get(rec["type"], "clearing"), "area_ha": rec["area_ha"],
            "confidence": rec["confidence"], "in_buffer": bool(rec["in_buffer"]),
            "in_indigenous": bool(rec["in_indigenous"]), "dist_road_m": rec["dist_road_m"],
            "dist_river_m": rec["dist_river_m"], "priority": rec["priority"], "first_seen": rec["first_seen"],
            "lon": rec["lon"], "lat": rec["lat"], "series": [s[i] for s in series],
        })
        if amw_years is not None:
            recs[-1]["amw_year"] = int(amw_years[i])

    overlay = web / "confidence.png"
    optical = next((p for pat in ("sentinel2*.png", "sentinel2*.jpg", "optical*.png", "optical*.jpg")
                    for p in sorted(ASSETS.glob(pat))), None)
    acc_path = out / "accuracy.json"
    years = sorted({d[:4] for d in dates})
    accuracy = _accuracy(json.loads(acc_path.read_text(encoding="utf8")) if acc_path.exists() else None)
    if amw_years is not None and (amw[0] > 0).any():
        accuracy["agreement"] = _agreement(alerts, amw_years, int(dates[-1][:4]), int(amw[0][amw[0] > 0].min()))
    # Which context maps the run had. A flag that is False everywhere means the map was missing.
    helper = lambda name: (Path(C.HELPERS) / f"{name}.tif").exists()  # noqa: E731
    mapped = {
        "buffer": bool(alerts["in_buffer"].any()) or helper("buffer"),
        "indigenous": bool(alerts["in_indigenous"].any()) or helper("indigenous"),
        "road": bool(alerts["dist_road_m"].notna().any()),
        "river": bool(alerts["dist_river_m"].notna().any()),
        "amw": amw_years is not None,
    }
    return {
        "sample": False,
        "sensor": "RADARSAT-2 · sigma0 (dB)",
        "credit": f"RADARSAT-2 Data and Products © Maxar Technologies Ltd. ({', '.join(years)}). All Rights Reserved. "
                  "RADARSAT is an official mark of the Canadian Space Agency.",
        "place": "La Pampa, Madre de Dios",
        "world": {"w": w, "h": h, "m_per_unit": (east - west) * 111_320 * math.cos(math.radians((south + north) / 2)) / w},
        "bounds": {"west": west, "south": south, "east": east, "north": north},
        "la_pampa": meta.get("la_pampa"),
        "drop_db": C.DROP_DB,
        "scenes": scenes,
        "overlay": _uri(overlay.read_bytes(), "image/png") if overlay.exists() else None,
        "overlay_main": _prominent(overlay) if overlay.exists() else None,
        "optical": _uri(optical.read_bytes(), "image/jpeg" if optical.suffix == ".jpg" else "image/png") if optical else None,
        # optional app/assets/<image name>.json: date, bounds_WSEN and credit of the optical image
        "optical_info": json.loads(optical.with_suffix(".json").read_text(encoding="utf8"))
        if optical and optical.with_suffix(".json").exists() else None,
        "alerts": recs,
        "mapped": mapped,
        "crackdown": _crackdown(out, amw),
        "accuracy": accuracy,
    }


if __name__ == "__main__":
    data = build()
    if data is None:
        print(f"No results in {out_dir()}: the page will show sample data. Run python -m tminus.pipeline first.")
    else:
        print(f"{len(data['alerts'])} alerts, {len(data['scenes'])} scenes "
              f"({data['scenes'][0]['date']} to {data['scenes'][-1]['date']}), "
              f"{len(data['accuracy']['tables'])} accuracy tables, "
              f"page data {len(json.dumps(data)) / 1e6:.1f} MB")
