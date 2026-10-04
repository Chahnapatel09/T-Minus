"""Run the whole pipeline on made-up scenes, in a temp folder.   python -m tests.synthetic_run [--embed]

--embed also runs the foundation model on the made-up scenes (downloads its weights once, about 100 MB).

Checks that the lanes fit together and that the detectors find clearings we planted.
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from tminus import config as C
from tminus import rio

DATES = ["20181201", "20190105", "20190301", "20190601", "20191201", "20200301"]


def main(keep=None, embed=False):
    tmp = Path(keep or tempfile.mkdtemp(prefix="tminus_"))
    C.PROCESSED, C.HELPERS, C.OUT = tmp / "processed", tmp / "helpers", tmp / "outputs"
    C.WEB = C.OUT / "web"
    C.AOI = (-70.00, -13.03, -69.90, -12.95)

    profile = rio.target_profile()
    h, w = profile["height"], profile["width"]
    rng = np.random.default_rng(1)

    # planted clearings: (row, col, size, first scene index, kind, in the 2019 mining map)
    plants = []
    for n in range(24):
        plants.append((int(rng.integers(20, h - 40)), int(rng.integers(20, w - 40)), int(rng.integers(12, 22)),
                       int(rng.integers(1, 5)), "pond" if n % 6 == 0 else "clear", True))
    for n in range(4):
        plants.append((int(rng.integers(20, h - 40)), int(rng.integers(20, w - 40)), 16, 5, "clear", False))

    stack = []
    for i, _ in enumerate(DATES):
        s = -7.0 + rng.normal(0, 0.7, (h, w))
        for r, c, size, start, kind, _m in plants:
            if i >= start:
                s[r:r + size, c:c + size] = (-22.0 if kind == "pond" else -13.5) + rng.normal(0, 0.7, (size, size))
        stack.append(s.astype("float32"))
    for d, s in zip(DATES, stack):
        rio.write(C.PROCESSED / f"sigma0_{d}.tif", s, profile)

    # labels in the Amazon Mining Watch format: year mining was confirmed, 0 = none
    amw = np.zeros((h, w), dtype="float32")
    for r, c, size, start, kind, in_map in plants:
        if in_map:
            amw[max(r - 2, 0):r + size + 2, max(c - 2, 0):c + size + 2] = int(DATES[start][:4])
    rio.write(C.HELPERS / "amw_year.tif", amw, profile)
    rio.write(C.HELPERS / "slope.tif", rng.uniform(0, 30, (h, w)).astype("float32"), profile)
    rio.write(C.HELPERS / "worldcover.tif", np.full((h, w), 10, dtype="float32"), profile)
    rio.write(C.HELPERS / "buffer.tif", (np.arange(w)[None, :] < w // 2).astype("float32") * np.ones((h, 1), "float32"), profile)
    rio.write(C.HELPERS / "dist_road.tif", np.tile(np.arange(w, dtype="float32") * C.RES, (h, 1)), profile)

    # a few points "checked by eye": centres of planted clearings, and forest
    from rasterio.transform import xy
    from rasterio.warp import transform
    pts = [(r + 5, c + 5, 1) for r, c, *_ in plants[:20]] + [(5, 5, 0), (h - 5, 5, 0), (5, w - 5, 0), (h - 5, w - 5, 0)]
    xs, ys = xy(profile["transform"], [p[0] for p in pts], [p[1] for p in pts])
    lon, lat = transform(profile["crs"], "EPSG:4326", xs, ys)
    pd.DataFrame({"lon": lon, "lat": lat, "mining": [p[2] for p in pts]}).to_csv(C.HELPERS / "check_points.csv", index=False)

    from tminus import pipeline
    if embed:
        from tminus import embed as emb
        emb.run()
    table = pipeline.run()

    print(table.head(8).to_string())
    print((C.OUT / "accuracy.json").read_text())
    print(pd.read_csv(C.OUT / "crackdown.csv").to_string())
    print(sorted(p.name for p in C.OUT.rglob("*") if p.is_file()))
    assert len(table) >= 20, "expected most planted clearings to become alerts"
    assert (table["type"] == "pond").any()
    print("OK", tmp)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0] if args else None, embed="--embed" in sys.argv)
