"""Put the SNAP outputs on one shared grid, measure/correct leftover shift, save the stack.

  .venv/bin/python scripts/align_stack.py

Reads   data/processed/snap_YYYYMMDD.tif   (dB, UTM 19S, one per date, from snap/run_scene.sh)
Writes  data/processed/sigma0_YYYYMMDD.tif (same grid for every date)
        data/processed/stack_db.tif        (bands in date order)
        data/processed/stack.json          (dates + grid details)
        outputs/qa/aligned_YYYYMMDD.png    (quick-look per date)
"""
import glob
import json
import re
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds
from scipy.ndimage import shift as nd_shift
from skimage.registration import phase_cross_correlation

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
QA = ROOT / "outputs" / "qa"

# Final box (W, S, E, N) in lon/lat, grid in UTM 19S at 12 m. Change here, not below.
BOX = (-70.15, -13.07, -69.85, -12.80)
CRS = "EPSG:32719"
RES = 12.0
SHIFT_FIX_PX = 0.5      # correct a date if it is more than this many pixels off the reference
DB_STRETCH = (-25.0, 0.0)


def grid():
    l, b, r, t = transform_bounds("EPSG:4326", CRS, *BOX, densify_pts=21)
    left, top = np.floor(l / RES) * RES, np.ceil(t / RES) * RES   # snap to multiples of RES
    w, h = int(np.ceil((r - left) / RES)), int(np.ceil((top - b) / RES))
    return from_origin(left, top, RES, RES), w, h


def to_grid(path, transform, w, h):
    with rasterio.open(path) as ds:
        src = ds.read(1).astype("float32")
        src[src == 0] = np.nan                      # SNAP writes 0 where there is no data
        dst = np.full((h, w), np.nan, "float32")
        reproject(src, dst, src_transform=ds.transform, src_crs=ds.crs, dst_transform=transform,
                  dst_crs=CRS, resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
    return dst


def fill(a):
    return np.where(np.isfinite(a), a, np.nanmedian(a))


def main():
    files = sorted(glob.glob(str(PROC / "snap_*.tif")))
    dates = [re.search(r"snap_(\d{8})", f).group(1) for f in files]
    transform, w, h = grid()
    print(f"grid: {w} x {h} px at {RES} m, origin ({transform.c:.0f}, {transform.f:.0f}), {CRS}")
    arrs = [to_grid(f, transform, w, h) for f in files]

    ref = arrs[0]
    shifts = {dates[0]: (0.0, 0.0)}
    for d, a in zip(dates[1:], arrs[1:]):
        both = np.isfinite(ref) & np.isfinite(a)
        # empty pixels are filled with the median so they carry no structure to match on
        sh, err, _ = phase_cross_correlation(fill(ref), fill(a), upsample_factor=20, normalization=None)
        shifts[d] = (float(sh[0]), float(sh[1]))
        print(f"{d}: shift vs {dates[0]} = {sh[0]:+.2f} rows, {sh[1]:+.2f} cols  (valid overlap {both.mean():.0%})")

    for i, d in enumerate(dates):
        dy, dx = shifts[d]
        if d != dates[0] and max(abs(dy), abs(dx)) > SHIFT_FIX_PX:
            arrs[i] = nd_shift(arrs[i], (dy, dx), order=1, mode="constant", cval=np.nan)
            print(f"{d}: corrected by {dy:+.2f}, {dx:+.2f} px")
        elif d != dates[0]:
            print(f"{d}: shift within {SHIFT_FIX_PX} px, left as is")

    prof = dict(driver="GTiff", dtype="float32", count=1, width=w, height=h, crs=CRS, transform=transform,
                nodata=np.nan, compress="deflate", tiled=True, blockxsize=256, blockysize=256)
    QA.mkdir(parents=True, exist_ok=True)
    for d, a in zip(dates, arrs):
        with rasterio.open(PROC / f"sigma0_{d}.tif", "w", **prof) as dst:
            dst.write(a, 1)
        lo, hi = DB_STRETCH
        img = np.clip((a - lo) / (hi - lo), 0, 1)
        img[~np.isfinite(a)] = 0
        Image.fromarray((img * 255).astype("uint8")).save(QA / f"aligned_{d}.png")
    prof.update(count=len(arrs))
    with rasterio.open(PROC / "stack_db.tif", "w", **prof) as dst:
        for i, a in enumerate(arrs, 1):
            dst.write(a, i)
            dst.set_band_description(i, dates[i - 1])
    (PROC / "stack.json").write_text(json.dumps({
        "dates": dates, "crs": CRS, "pixel_size_m": RES, "width": w, "height": h,
        "origin_x": transform.c, "origin_y": transform.f, "box_lonlat_WSEN": BOX,
        "measured_shift_px_row_col": shifts, "unit": "dB (sigma0)", "nodata": "NaN",
        "snap": {"looks_range": 3, "looks_azimuth": 4, "speckle": "Refined Lee",
                 "dem": "Copernicus 30m Global DEM"}}, indent=2))
    print("saved", [Path(f).name for f in sorted(glob.glob(str(PROC / "*.tif")))])


if __name__ == "__main__":
    main()
