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

ASSETS = Path(__file__).resolve().parent / "assets"
NODATA_GREY = 30          # areas outside a scene, on the page
TYPES = {"pond": "pond", "bare sand / tailings": "bare", "fresh clearing": "clearing"}
SCORE_NAMES = {"rule": "Rule only", "model": "Model only", "combined": "Either detector (all alerts)",
               "both": "Both agree (high confidence)"}


def out_dir():
    """outputs/, or another results folder named in TMINUS_OUT (handy for a teammate's copy)."""
    return Path(os.environ.get("TMINUS_OUT") or C.OUT)


def stamp(out=None):
    """Changes whenever the pipeline rewrites its results, so callers can cache build()."""
    out = Path(out or out_dir())
    files = [out / n for n in ("alerts.csv", "crackdown.csv", "crackdown_amw.csv", "accuracy.json")]
    files += sorted((out / "web").glob("*")) + sorted(ASSETS.glob("*"))
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
    """A scene PNG as (dB array with NaN where there is no data, JPEG data URI)."""
    rgba = np.asarray(Image.open(path).convert("RGBA"))
    grey, alpha = rgba[..., 0], rgba[..., 3]
    lo, hi = C.DB_STRETCH
    db = np.where(alpha > 0, lo + grey.astype("float32") / 255 * (hi - lo), np.nan)
    buf = io.BytesIO()
    Image.fromarray(np.where(alpha > 0, grey, NODATA_GREY).astype("uint8"), "L").save(buf, "JPEG", quality=85)
    return db, _uri(buf.getvalue(), "image/jpeg")


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


def _crackdown(out):
    path = out / "crackdown.csv"
    if not path.exists():
        return None
    tbl = pd.read_csv(path)
    summ = crackdown_mod.summary(tbl)
    summary = {phase: {"inside": _clean(summ.loc[phase, "inside_ha_per_month"]),
                       "outside": _clean(summ.loc[phase, "outside_ha_per_month"])} for phase in ("before", "after")}
    amw = None
    if (out / "crackdown_amw.csv").exists():
        a = pd.read_csv(out / "crackdown_amw.csv")
        amw = [{"label": str(int(r.year)), "inside": float(r.inside_ha), "outside": float(r.outside_ha)}
               for r in a.itertuples()] or None
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

    overlay = web / "confidence.png"
    optical = next((p for pat in ("sentinel2*.png", "sentinel2*.jpg", "optical*.png", "optical*.jpg")
                    for p in sorted(ASSETS.glob(pat))), None)
    acc_path = out / "accuracy.json"
    years = sorted({d[:4] for d in dates})
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
        "optical": _uri(optical.read_bytes(), "image/jpeg" if optical.suffix == ".jpg" else "image/png") if optical else None,
        "alerts": recs,
        "crackdown": _crackdown(out),
        "accuracy": _accuracy(json.loads(acc_path.read_text(encoding="utf8")) if acc_path.exists() else None),
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
