"""Lane A. Raster reading/writing and the one shared grid."""
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds, transform_geom
from shapely.geometry import box, mapping
from shapely import segmentize

from . import config as C


def target_profile():
    """The analysis grid as a rasterio profile: C.AOI in C.CRS at C.RES metres."""
    w, s, e, n = transform_bounds("EPSG:4326", C.CRS, *C.AOI, densify_pts=21)
    left = math.floor(w / C.RES) * C.RES
    bottom = math.floor(s / C.RES) * C.RES
    right = math.ceil(e / C.RES) * C.RES
    top = math.ceil(n / C.RES) * C.RES
    return {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "width": int((right - left) // C.RES),
        "height": int((top - bottom) // C.RES),
        "crs": rasterio.crs.CRS.from_string(C.CRS),
        "transform": from_origin(left, top, C.RES, C.RES),
        "nodata": float("nan"),
        "compress": "deflate",
    }


def read(path):
    """Return (array, profile) for band 1 of a GeoTIFF. Nodata becomes NaN (floats) or 0 (ints)."""
    with rasterio.open(path) as src:
        masked = src.read(1, masked=True)
        profile = src.profile
    if np.issubdtype(masked.dtype, np.floating):
        return masked.astype("float32").filled(np.nan), profile
    return masked.filled(0), profile


def write(path, arr, profile):
    """Write a single-band GeoTIFF."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    prof = dict(profile)
    prof.update(driver="GTiff", count=1, dtype=arr.dtype.name,
                height=arr.shape[0], width=arr.shape[1])
    prof.setdefault("compress", "deflate")
    if np.issubdtype(arr.dtype, np.floating):
        prof["nodata"] = float("nan")
    else:
        prof.pop("nodata", None)
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(arr, 1)


def warp_to_grid(src_path, dst_path, resampling="bilinear"):
    """Put any raster on the analysis grid. Use 'nearest' for class maps and masks."""
    profile = target_profile()
    out = np.full((profile["height"], profile["width"]), np.nan, dtype="float32")
    with rasterio.open(src_path) as src:
        if src.crs is None:
            raise ValueError(f"{src_path} has no CRS, cannot put it on the grid")
        reproject(
            source=rasterio.band(src, 1),
            destination=out,
            src_nodata=src.nodata,
            dst_transform=profile["transform"],
            dst_crs=profile["crs"],
            dst_nodata=np.nan,
            resampling=Resampling[resampling],
        )
    write(dst_path, out, profile)
    return out


def warp_tiles_to_grid(src_paths, dst_path, resampling="nearest"):
    """Several adjoining rasters (e.g. 10 x 10 degree tiles) mosaicked onto the analysis grid."""
    out = None
    for src in src_paths:
        part = warp_to_grid(src, dst_path, resampling)
        out = part if out is None else np.where(np.isnan(out), part, out)
    write(dst_path, out, target_profile())
    return out


def scenes():
    """[(YYYYMMDD, path), ...] for data/processed/sigma0_*.tif, oldest first."""
    found = []
    for p in Path(C.PROCESSED).glob("sigma0_*.tif"):
        date = p.stem.split("_", 1)[1]
        if len(date) == 8 and date.isdigit():
            found.append((date, p))
    return sorted(found)


def has_helper(name):
    return (Path(C.HELPERS) / f"{name}.tif").exists()


def helper(name, profile):
    """Read data/helpers/<name>.tif. A missing helper is read as zeros."""
    p = Path(C.HELPERS) / f"{name}.tif"
    if not p.exists():
        return np.zeros((profile["height"], profile["width"]), dtype="float32")
    arr, _ = read(p)
    return np.nan_to_num(arr.astype("float32"))


def box_mask(lonlat_box, profile):
    """Boolean mask of a (W, S, E, N) lon/lat box on the grid."""
    geom = transform_geom("EPSG:4326", profile["crs"], mapping(segmentize(box(*lonlat_box), 0.001)))
    return rasterize([(geom, 1)], out_shape=(profile["height"], profile["width"]),
                     transform=profile["transform"], fill=0, dtype="uint8").astype(bool)


def la_pampa_mask(profile):
    """La Pampa on the grid: data/helpers/la_pampa.tif if present, else the C.LA_PAMPA box."""
    if has_helper("la_pampa"):
        return helper("la_pampa", profile) > 0
    return box_mask(C.LA_PAMPA, profile)
