"""Lane B. Turn the confidence map into ranked alert patches and export files."""
import json
import math
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
from rasterio.transform import xy
from rasterio.warp import transform
from scipy import ndimage

from . import combine
from . import config as C

COLUMNS = ["id", "area_ha", "first_seen", "type", "confidence", "in_buffer", "in_indigenous",
           "dist_road_m", "dist_river_m", "priority", "lon", "lat", "maps_url", "growth"]


def _iso(date):
    return datetime.strptime(date, "%Y%m%d").strftime("%Y-%m-%d")


def build(conf, change_idx, dates, first, last, layers, profile):
    """One row per patch of C.MIN_PATCH_HA or more.

    conf: uint8 0/1/2 confidence map. change_idx: index into `dates` of the scene where each
    pixel was first flagged by the rule detector (-1 = never). first, last: dB arrays of the first
    and last scene. layers: helper arrays by name (buffer, indigenous, dist_road, dist_river);
    a layer that is missing is reported as unknown (False / NaN).

    Columns: id, area_ha, first_seen, type (pond / bare sand or tailings / fresh clearing),
    confidence, in_buffer, in_indigenous, dist_road_m, dist_river_m, priority, lon, lat, maps_url,
    growth (share of the patch first seen in the later half of the scenes).
    """
    labels, n = ndimage.label(conf > 0, structure=np.ones((3, 3), dtype=int))
    min_px = math.ceil(C.MIN_PATCH_HA * 10_000 / (C.RES * C.RES))
    sizes = np.bincount(labels.ravel(), minlength=n + 1)
    ids = np.flatnonzero(sizes >= min_px)
    ids = ids[ids > 0]
    if len(ids) == 0:
        return pd.DataFrame(columns=COLUMNS)

    area_ha = sizes[ids] * C.RES * C.RES / 10_000

    seen = np.where(change_idx >= 0, change_idx, np.iinfo(np.int16).max).astype("int32")
    first_idx = ndimage.minimum(seen, labels, ids).astype(int)
    first_seen = [_iso(dates[i] if i < len(dates) else dates[-1]) for i in first_idx]
    growth = ndimage.mean((change_idx >= len(dates) // 2).astype("float32"), labels, ids)
    high_share = ndimage.mean((conf == combine.HIGH).astype("float32"), labels, ids)

    valid = (np.isfinite(first) & np.isfinite(last)).astype("float32")
    n_valid = np.maximum(ndimage.sum(valid, labels, ids), 1)
    drop = ndimage.sum(np.where(valid > 0, first - last, 0), labels, ids) / n_valid
    wet = ndimage.sum((last < C.WATER_DB).astype("float32"), labels, ids) / n_valid
    types = np.where(wet >= C.POND_WATER_FRACTION, "pond",
                     np.where(drop >= C.TAILINGS_DROP_DB, "bare sand / tailings", "fresh clearing"))

    def flag(name):
        if name not in layers:
            return np.zeros(len(ids), dtype=bool)
        return ndimage.maximum((np.asarray(layers[name]) > 0).astype("uint8"), labels, ids) > 0

    def nearest(name):
        if name not in layers:
            return np.full(len(ids), np.nan)
        return ndimage.minimum(np.asarray(layers[name], dtype="float32"), labels, ids)

    centre = ndimage.center_of_mass(np.ones(conf.shape, dtype="uint8"), labels, ids)
    rows = [int(round(c[0])) for c in centre]
    cols = [int(round(c[1])) for c in centre]
    xs, ys = xy(profile["transform"], rows, cols)
    lons, lats = transform(profile["crs"], "EPSG:4326", list(xs), list(ys))

    df = pd.DataFrame({
        "id": 0,
        "area_ha": np.round(area_ha, 2),
        "first_seen": first_seen,
        "type": types,
        "confidence": np.where(high_share >= C.HIGH_SHARE, "high", "medium"),
        "in_buffer": flag("buffer"),
        "in_indigenous": flag("indigenous"),
        "dist_road_m": np.round(nearest("dist_road"), 0),
        "dist_river_m": np.round(nearest("dist_river"), 0),
        "priority": 0.0,
        "lon": np.round(lons, 5),
        "lat": np.round(lats, 5),
        "maps_url": [f"https://www.google.com/maps?q={la:.5f},{lo:.5f}" for lo, la in zip(lons, lats)],
        "growth": np.round(growth, 3),
    })
    df["priority"] = [priority(r) for _, r in df.iterrows()]
    df = df.sort_values(["priority", "area_ha"], ascending=False).reset_index(drop=True)
    df["id"] = np.arange(1, len(df) + 1)
    return df[COLUMNS]


def priority(alert):
    """Score 0 to 100 from size, growth, reserve buffer or Indigenous land, distance to road or river,
    and confidence, weighted by C.PRIORITY_WEIGHTS."""
    w = C.PRIORITY_WEIGHTS
    gaps = [d for d in (alert["dist_road_m"], alert["dist_river_m"]) if pd.notna(d)]
    access = 1 - min(min(gaps), C.ACCESS_MAX_M) / C.ACCESS_MAX_M if gaps else 0.0
    parts = {
        "size": min(1.0, alert["area_ha"] / C.SIZE_FULL_HA),
        "growth": float(alert["growth"]),
        "protected": 1.0 if (alert["in_buffer"] or alert["in_indigenous"]) else 0.0,
        "access": access,
        "confidence": 1.0 if alert["confidence"] == "high" else 0.5,
    }
    return round(100 * sum(w[k] * parts[k] for k in w) / sum(w.values()), 1)


def _records(alerts):
    out = []
    for rec in alerts.to_dict("records"):
        out.append({k: (None if isinstance(v, float) and math.isnan(v) else
                        v.item() if hasattr(v, "item") else v) for k, v in rec.items()})
    return out


def export(alerts, folder):
    """Write alerts.geojson, alerts.csv, alerts.kml."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    alerts.to_csv(folder / "alerts.csv", index=False)

    recs = _records(alerts)
    features = [{"type": "Feature",
                 "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                 "properties": r} for r in recs]
    (folder / "alerts.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, indent=1), encoding="utf8")

    marks = []
    for r in recs:
        desc = (f"{r['type']}, {r['area_ha']} ha, {r['confidence']} confidence, priority {r['priority']}, "
                f"first seen {r['first_seen']}. {r['maps_url']}")
        marks.append(
            f"  <Placemark>\n    <name>Alert {r['id']}: {escape(str(r['type']))}</name>\n"
            f"    <description>{escape(desc)}</description>\n"
            f"    <Point><coordinates>{r['lon']},{r['lat']},0</coordinates></Point>\n  </Placemark>")
    kml = ('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n'
           '<Document>\n  <name>La Pampa mining alerts</name>\n' + "\n".join(marks) + "\n</Document>\n</kml>\n")
    (folder / "alerts.kml").write_text(kml, encoding="utf8")
