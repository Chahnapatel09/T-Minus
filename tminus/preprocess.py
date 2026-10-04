"""Lane A. Put SNAP outputs and helper maps on the shared grid.

SNAP chain before this: subset, calibrate to sigma0, multilook to ~10 m, Refined Lee,
Range-Doppler terrain correction, convert to dB, export GeoTIFF.
"""
import json
from pathlib import Path

import numpy as np
from rasterio.features import rasterize
from rasterio.warp import transform_geom
from scipy import ndimage
from shapely import from_wkb
from shapely.geometry import mapping, shape

from . import config as C
from . import rio

# Helper rasters that hold classes or years: never average these.
_NEAREST = {"worldcover", "hansen_lossyear"}


def scene(src, date):
    """SNAP GeoTIFF -> data/processed/sigma0_<date>.tif on the grid."""
    dst = Path(C.PROCESSED) / f"sigma0_{date}.tif"
    out = rio.warp_to_grid(src, dst, "bilinear")
    if not np.isfinite(out).any():
        dst.unlink()
        raise ValueError(f"{Path(src).name} does not overlap the AOI {C.AOI}: nothing written")
    return out, dst


def raster(name, src):
    """Helper raster (WorldCover, Hansen, slope) -> data/helpers/<name>.tif on the grid."""
    dst = Path(C.HELPERS) / f"{name}.tif"
    return rio.warp_to_grid(src, dst, "nearest" if name in _NEAREST else "bilinear"), dst


def vector(name, src):
    """Polygons -> 0/1 mask on the grid (mining2019, buffer, indigenous, la_pampa)."""
    profile = rio.target_profile()
    mask = _burn(_geoms(src, profile), profile, all_touched=False)
    dst = Path(C.HELPERS) / f"{name}.tif"
    rio.write(dst, mask.astype("float32"), profile)
    return mask, dst


def dist(name, src):
    """Lines -> distance-in-metres raster on the grid (dist_road, dist_river)."""
    profile = rio.target_profile()
    lines = _burn(_geoms(src, profile), profile, all_touched=True)
    if not lines.any():
        raise ValueError(f"{src}: no line falls inside the grid")
    metres = (ndimage.distance_transform_edt(~lines) * C.RES).astype("float32")
    dst = Path(C.HELPERS) / f"{name}.tif"
    rio.write(dst, metres, profile)
    return metres, dst


def _burn(geoms, profile, all_touched):
    shapes = [(g, 1) for g in geoms]
    if not shapes:
        return np.zeros((profile["height"], profile["width"]), dtype=bool)
    return rasterize(shapes, out_shape=(profile["height"], profile["width"]),
                     transform=profile["transform"], fill=0, dtype="uint8",
                     all_touched=all_touched).astype(bool)


def _geoms(src, profile):
    """Geometries of a vector file, as GeoJSON dicts in the grid CRS.

    .geojson / .json are read directly (EPSG:4326 assumed); anything else (shp, gpkg) goes through pyogrio.
    """
    src = Path(src)
    if src.suffix.lower() in (".geojson", ".json"):
        data = json.loads(src.read_text(encoding="utf8"))
        feats = data["features"] if data.get("type") == "FeatureCollection" else [data]
        geoms = [shape(f["geometry"] if "geometry" in f else f) for f in feats if f]
        crs = "EPSG:4326"
    else:
        from pyogrio.raw import read as ogr_read
        meta, _, wkb, _ = ogr_read(src)
        geoms = [g for g in from_wkb(wkb) if g is not None]
        crs = meta.get("crs") or "EPSG:4326"
    return [transform_geom(crs, profile["crs"], mapping(g)) for g in geoms if not g.is_empty]
