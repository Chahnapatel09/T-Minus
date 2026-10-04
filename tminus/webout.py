"""Lane C. PNG overlays and map bounds for the web page (outputs/web/)."""
import json

import numpy as np
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.warp import reproject, transform_bounds

from . import config as C

MEDIUM_RGBA = (255, 165, 0, 150)
HIGH_RGBA = (220, 20, 20, 210)


def _lonlat_grid(profile):
    """Output grid in lon/lat, at most C.WEB_MAX_PX on the long side, with the right aspect."""
    h, w = profile["height"], profile["width"]
    west, south, east, north = transform_bounds(
        profile["crs"], "EPSG:4326", *rasterio_bounds(profile), densify_pts=21)
    ratio = (east - west) * np.cos(np.radians((south + north) / 2)) / (north - south)
    if ratio >= 1:
        out_w, out_h = C.WEB_MAX_PX, max(1, round(C.WEB_MAX_PX / ratio))
    else:
        out_w, out_h = max(1, round(C.WEB_MAX_PX * ratio)), C.WEB_MAX_PX
    out_w, out_h = min(out_w, w), min(out_h, h)
    return (west, south, east, north), from_bounds(west, south, east, north, out_w, out_h), (out_h, out_w)


def rasterio_bounds(profile):
    t = profile["transform"]
    return (t.c, t.f + t.e * profile["height"], t.c + t.a * profile["width"], t.f)


def _warp(arr, profile, transform, shape, resampling):
    out = np.full(shape, np.nan, dtype="float32")
    reproject(arr.astype("float32"), out, src_transform=profile["transform"], src_crs=profile["crs"],
              dst_transform=transform, dst_crs="EPSG:4326", src_nodata=np.nan, dst_nodata=np.nan,
              resampling=resampling)
    return out


def _gray(db):
    lo, hi = C.DB_STRETCH
    v = (np.nan_to_num(np.clip((db - lo) / (hi - lo), 0, 1)) * 255).astype("uint8")
    rgba = np.dstack([v, v, v, np.where(np.isnan(db), 0, 255).astype("uint8")])
    return Image.fromarray(rgba, "RGBA")


def write(scenes, conf, profile, dates, folder=None):
    """scenes: list of dB arrays, one per date. Writes scene_<date>.png, confidence.png, meta.json."""
    folder = folder or C.WEB
    folder.mkdir(parents=True, exist_ok=True)
    (west, south, east, north), transform, shape = _lonlat_grid(profile)

    for date, arr in zip(dates, scenes):
        _gray(_warp(arr, profile, transform, shape, Resampling.average)).save(folder / f"scene_{date}.png")

    c = np.nan_to_num(_warp(conf, profile, transform, shape, Resampling.max))
    rgba = np.zeros(shape + (4,), dtype="uint8")
    rgba[c == 1] = MEDIUM_RGBA
    rgba[c == 2] = HIGH_RGBA
    Image.fromarray(rgba, "RGBA").save(folder / "confidence.png")

    meta = {"bounds": [[south, west], [north, east]], "dates": list(dates),
            "la_pampa": list(C.LA_PAMPA), "crackdown": C.CRACKDOWN}
    (folder / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf8")
