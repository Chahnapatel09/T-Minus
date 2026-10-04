"""Lane D. Points checked by eye in Google Earth (KMZ / KML pins) -> data/helpers/check_points.csv.

  python -m tminus.checkpoints [file.kmz ...]      (default: every .kmz / .kml in data/raw/)

Each pin's name sets its class:
  mining = 1   MINE, MINING PONDS (anything with "MIN" or "POND" in the name)
  mining = 0   SETTLEMENT, CLEARED LAND, FOREST, ROAD, ...
The pipeline then grades every model on these points (outputs/check_points_result.csv).
"""
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pandas as pd

from . import config as C

KML = "{http://www.opengis.net/kml/2.2}"


def _is_mining(name):
    n = name.upper()
    return int(("MIN" in n or "POND" in n) and "NOT" not in n)


def read(path):
    """[(name, lon, lat), ...] for every Point placemark in a .kmz or .kml file."""
    path = Path(path)
    if path.suffix.lower() == ".kmz":
        with zipfile.ZipFile(path) as z:
            docs = [z.read(n) for n in z.namelist() if n.lower().endswith(".kml")]
    else:
        docs = [path.read_bytes()]
    out = []
    for doc in docs:
        for pm in ET.fromstring(doc).iter(f"{KML}Placemark"):
            coords = pm.find(f".//{KML}Point/{KML}coordinates")
            if coords is None:
                continue
            lon, lat = map(float, re.split(r"[,\s]+", coords.text.strip())[:2])
            out.append(((pm.findtext(f"{KML}name") or "").strip(), lon, lat))
    return out


def build(paths=None):
    paths = paths or sorted([*Path(C.RAW).glob("*.kmz"), *Path(C.RAW).glob("*.kml")])
    rows = [{"lon": lon, "lat": lat, "mining": _is_mining(name), "name": name, "source": Path(p).name}
            for p in paths for name, lon, lat in read(p)]
    df = pd.DataFrame(rows, columns=["lon", "lat", "mining", "name", "source"])
    dst = C.HELPERS / "check_points.csv"
    dst.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dst, index=False)
    print(f"[checkpoints] {len(df)} points ({int(df.mining.sum())} mining, {int((df.mining == 0).sum())} not) "
          f"from {len(paths)} file(s) -> {dst}")
    print(df.to_string(index=False))
    return df


if __name__ == "__main__":
    build(sys.argv[1:] or None)
