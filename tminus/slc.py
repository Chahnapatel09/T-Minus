"""Lane A. RADARSAT-2 SLC product -> geocoded sigma0 in dB, without SNAP.

  python -m tminus.slc data/raw/RS2_..._SLC [--looks-az 3 --looks-rg 2]

Steps (the same chain as the README, minus terrain correction):
  1. complex I/Q -> intensity, calibrated to sigma0 with the product's lutSigma.xml (DN^2 / A^2)
  2. multilook (default 3 azimuth x 2 range, about 9 x 8 m on the ground)
  3. Lee speckle filter on the linear power
  4. geocode from the ground control points (thin plate spline) onto UTM 19S at C.RES
  5. convert to dB

There is no DEM, so relief is not corrected: fine over flat forest, wrong on steep slopes.
Output: data/raw/sigma0_geo_<date>.tif (whole scene). Then preprocess.scene() puts it on the AOI grid.
"""
import argparse
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import rasterio
import rasterio.windows
from rasterio.control import GroundControlPoint
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds
from scipy import ndimage

from . import config as C
from . import rio

STRIP_BLOCKS = 256   # output rows per strip while reading


def _log(msg):
    print(f"[slc] {msg}", flush=True)


def locate(path):
    """Folder of the product. A .zip is unpacked next to itself first."""
    path = Path(path)
    if path.suffix.lower() == ".zip":
        folder = path.with_suffix("")
        if not (folder / "imagery_HH.tif").exists() and not list(folder.glob("imagery_*.tif")):
            _log(f"unpacking {path.name}")
            zipfile.ZipFile(path).extractall(path.parent)
        path = folder
    if not list(path.glob("imagery_*.tif")):
        raise FileNotFoundError(f"no imagery_*.tif in {path}")
    return path


def product_date(folder):
    m = re.search(r"_(\d{8})_\d{6}_", Path(folder).name)
    if not m:
        raise ValueError(f"cannot find the acquisition date in {folder}")
    return m.group(1)


def _lut(folder, pol_file):
    root = ET.parse(Path(folder) / "lutSigma.xml").getroot()
    offset = float(root.findtext("offset"))
    gains = np.array(root.findtext("gains").split(), dtype="float64")
    return offset, gains


def multilook(folder, looks_az, looks_rg):
    """Calibrated, multilooked sigma0 (linear power, float32) in the original slant-range geometry."""
    img = sorted(Path(folder).glob("imagery_*.tif"))[0]
    offset, gains = _lut(folder, img)
    with rasterio.open(img) as src:
        if src.count != 2:
            raise ValueError("expected an SLC with two bands (I and Q)")
        h, w = src.height, src.width
        if len(gains) < w:
            raise ValueError("calibration table is shorter than the image")
        oh, ow = h // looks_az, w // looks_rg
        # RADARSAT-2 convention: sigma0 = (DN^2 + B) / A^2, A being the lutSigma gain
        gain = (gains[: ow * looks_rg].reshape(ow, looks_rg).mean(axis=1) ** 2).astype("float32")
        out = np.full((oh, ow), np.nan, dtype="float32")
        step = STRIP_BLOCKS
        for r0 in range(0, oh, step):
            r1 = min(oh, r0 + step)
            win = rasterio.windows.Window(0, r0 * looks_az, ow * looks_rg, (r1 - r0) * looks_az)
            i, q = src.read(window=win).astype("float32")
            power = i * i + q * q
            valid = power > 0
            power = (power + offset).reshape(r1 - r0, looks_az, ow, looks_rg)
            cnt = valid.reshape(r1 - r0, looks_az, ow, looks_rg).sum(axis=(1, 3))
            mean = power.sum(axis=(1, 3)) / np.maximum(cnt, 1)
            out[r0:r1] = np.where(cnt > 0, mean / gain[None, :], np.nan)
            if (r0 // step) % 10 == 0:
                _log(f"multilook {100 * r1 / oh:.0f}%")
        gcps, gcp_crs = src.gcps
    scaled = [GroundControlPoint(row=g.row / looks_az, col=g.col / looks_rg, x=g.x, y=g.y, z=g.z) for g in gcps]
    return out, scaled, gcp_crs


def lee(power, looks, size=5, block=1024):
    """Lee filter for multiplicative speckle on linear power. NaN pixels are left as they are."""
    cu2 = 1.0 / looks
    halo = size // 2
    out = np.empty_like(power)
    for r0 in range(0, power.shape[0], block):
        a, b = max(0, r0 - halo), min(power.shape[0], r0 + block + halo)
        x = power[a:b]
        nan = np.isnan(x)
        filled = np.where(nan, 0.0, x).astype("float32")
        ok = (~nan).astype("float32")
        n = np.maximum(ndimage.uniform_filter(ok, size), 1e-6)
        mean = ndimage.uniform_filter(filled, size) / n
        sq = ndimage.uniform_filter(filled * filled, size) / n
        var = np.maximum(sq - mean * mean, 0)
        ci2 = var / np.maximum(mean * mean, 1e-12)
        weight = np.clip((ci2 - cu2) / np.maximum(ci2 * (1 + cu2), 1e-12), 0, 1)
        res = mean + weight * (filled - mean)
        res[nan] = np.nan
        keep = slice(r0 - a, r0 - a + min(block, power.shape[0] - r0))
        out[r0:r0 + block] = res[keep]
    return out


def geocode(power, gcps, gcp_crs, dst_path):
    """Warp slant-range power onto a UTM grid at C.RES using the GCPs, and write dB."""
    lons = [g.x for g in gcps]
    lats = [g.y for g in gcps]
    w, s, e, n = transform_bounds("EPSG:4326", C.CRS, min(lons), min(lats), max(lons), max(lats), densify_pts=21)
    left, bottom = np.floor(w / C.RES) * C.RES, np.floor(s / C.RES) * C.RES
    right, top = np.ceil(e / C.RES) * C.RES, np.ceil(n / C.RES) * C.RES
    transform = from_origin(left, top, C.RES, C.RES)
    shape = (int((top - bottom) // C.RES), int((right - left) // C.RES))
    _log(f"geocoding to {shape[1]} x {shape[0]} px")
    dst = np.full(shape, np.nan, dtype="float32")
    reproject(power, dst, gcps=gcps, src_crs=gcp_crs or "EPSG:4326", src_nodata=np.nan,
              dst_transform=transform, dst_crs=C.CRS, dst_nodata=np.nan,
              resampling=Resampling.bilinear, SRC_METHOD="GCP_TPS", num_threads=4)
    with np.errstate(divide="ignore", invalid="ignore"):
        db = 10 * np.log10(np.where(dst > 0, dst, np.nan))
    profile = rio.target_profile()
    profile.update(width=shape[1], height=shape[0], transform=transform)
    rio.write(dst_path, db.astype("float32"), profile)
    return db


def process(path, looks_az=3, looks_rg=2, looks_eff=6):
    """Full chain. Returns (date, path of the geocoded dB GeoTIFF)."""
    folder = locate(path)
    date = product_date(folder)
    power, gcps, gcp_crs = multilook(folder, looks_az, looks_rg)
    _log("speckle filter")
    power = lee(power, looks_eff)
    dst = Path(C.RAW) / f"sigma0_geo_{date}.tif"
    db = geocode(power, gcps, gcp_crs, dst)
    finite = db[np.isfinite(db)]
    _log(f"wrote {dst.name}: dB median {np.median(finite):.1f}, 2%..98% "
         f"{np.percentile(finite, 2):.1f}..{np.percentile(finite, 98):.1f}")
    quicklook(dst)
    return date, dst


def quicklook(path, max_px=2000):
    """Small grayscale PNG next to a geocoded dB GeoTIFF, with the AOI and La Pampa drawn on it."""
    from PIL import Image, ImageDraw
    from rasterio.warp import transform as warp_xy

    path = Path(path)
    with rasterio.open(path) as src:
        scale = max(src.width, src.height) / max_px
        shape = (max(1, int(src.height / scale)), max(1, int(src.width / scale)))
        db = src.read(1, out_shape=shape, resampling=Resampling.average)
        t = src.transform * src.transform.scale(src.width / shape[1], src.height / shape[0])
        crs = src.crs
    lo, hi = C.DB_STRETCH
    v = (np.nan_to_num(np.clip((db - lo) / (hi - lo), 0, 1)) * 255).astype("uint8")
    img = Image.fromarray(np.dstack([v, v, v, np.where(np.isfinite(db), 255, 0).astype("uint8")]), "RGBA")
    draw = ImageDraw.Draw(img)
    for box_, colour in ((C.AOI, (255, 200, 0, 255)), (C.LA_PAMPA, (255, 60, 60, 255))):
        w, s, e, n = box_
        xs, ys = warp_xy("EPSG:4326", crs, [w, e, e, w, w], [n, n, s, s, n])
        pts = [~t * (x, y) for x, y in zip(xs, ys)]
        draw.line(pts, fill=colour, width=3)
    out = path.with_suffix(".png")
    img.save(out)
    _log(f"quicklook {out.name} (yellow = AOI, red = La Pampa)")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("product", help="product folder or .zip")
    ap.add_argument("--looks-az", type=int, default=3)
    ap.add_argument("--looks-rg", type=int, default=2)
    ap.add_argument("--to-grid", action="store_true",
                    help="also put the result on the AOI grid as data/processed/sigma0_<date>.tif")
    args = ap.parse_args()
    date, dst = process(args.product, args.looks_az, args.looks_rg)
    if args.to_grid:
        from . import preprocess
        preprocess.scene(dst, date)
        _log(f"data/processed/sigma0_{date}.tif written")


if __name__ == "__main__":
    main()
