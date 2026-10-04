"""Lane D. Mining labels from Amazon Mining Watch (Earth Genome, CC BY 4.0).

  python -m tminus.labels

Downloads the AMW mining-scar raster (10 m, the whole Amazon basin, about 62 MB) to data/raw/ once,
and puts it on the grid as data/helpers/amw_year.tif: 0 = no mining, else the year mining was first
confirmed (2018 = already mined in 2018 or earlier; quarterly values such as 20251 become 2025).
AMW is mapped from optical Sentinel-2, so it is independent of the radar.
Source: https://source.coop/earthgenome/amazon-mining-watch
"""
import shutil
import urllib.request
from pathlib import Path

import numpy as np

from . import config as C
from . import rio

AMW_URL = ("https://data.source.coop/earthgenome/amazon-mining-watch/"
           "amazon_basin_mining_scar_masks.tif")
AMW_FILE = "amw_mining_scar_masks.tif"


def download(force=False):
    dst = Path(C.RAW) / AMW_FILE
    if dst.exists() and not force:
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    print(f"[labels] downloading {AMW_URL}", flush=True)
    tmp = dst.with_suffix(".part")
    # the host answers 403 to Python's default User-Agent
    req = urllib.request.Request(AMW_URL, headers={"User-Agent": "tminus-labels/1.0"})
    with urllib.request.urlopen(req) as src, open(tmp, "wb") as out:
        shutil.copyfileobj(src, out)
    tmp.replace(dst)
    return dst


def amw_year(src=None):
    """AMW scar mask -> data/helpers/amw_year.tif on the grid. Returns the array."""
    src = Path(src) if src else download()
    dst = Path(C.HELPERS) / "amw_year.tif"
    arr = rio.warp_to_grid(src, dst, "nearest")
    arr = np.nan_to_num(arr)
    arr = np.where(arr > 9999, arr // 10, arr).astype("float32")   # 20251 -> 2025
    rio.write(dst, arr, rio.target_profile())
    return arr


def mining_mask(amw, year):
    """Pixels AMW counts as mined by the end of `year`."""
    return (amw > 0) & (amw <= int(year))


def main():
    arr = amw_year()
    years, counts = np.unique(arr[arr > 0], return_counts=True)
    ha = C.RES * C.RES / 10_000
    print("[labels] data/helpers/amw_year.tif written. Mined area first confirmed per year:")
    for y, n in zip(years.astype(int), counts):
        print(f"  {y}: {n * ha:,.0f} ha")


if __name__ == "__main__":
    main()
