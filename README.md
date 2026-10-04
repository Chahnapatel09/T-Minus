# T-Minus

Gold-mining monitor for La Pampa, Peru, built on RADARSAT-2 Tropical Forests data.
Mission Accepted Space Hackathon, Challenge 1.

## Setup (Windows, once)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run it

```powershell
python -m tminus.pipeline      # detectors -> alerts -> files in outputs/
streamlit run app/app.py       # the web page
```

## Who owns what

| Lane | Files | Job |
|---|---|---|
| A | `tminus/preprocess.py`, `tminus/rio.py` | SNAP outputs and helper maps onto the shared grid |
| B | `tminus/rules.py`, `combine.py`, `alerts.py`, `crackdown.py` | Rule detector, confidence, alert patches, priority, crackdown table, exports |
| C | `app/app.py` | The web page |
| D | `tminus/model.py`, `tminus/accuracy.py` | Labels, random forest, accuracy check |
| all | `tminus/config.py` | Every threshold and the AOI. Change numbers here, not in the code |
| all | `tminus/pipeline.py` | Wires the lanes together |

## The file contract between lanes

Everything is a single-band GeoTIFF on the same grid: UTM 19S (EPSG:32719), 10 m.

- `data/raw/`: EODMS downloads and SNAP outputs
- `data/processed/sigma0_YYYYMMDD.tif`: radar scene in dB, on the grid (lane A)
- `data/helpers/<name>.tif`: helper maps on the grid, names listed in `tminus/config.py` (lane A)
- `data/helpers/check_points.csv`: columns `lon,lat,mining`, the points checked by eye (lane D)
- `app/assets/`: screenshots for the first screen (lane C)
- `outputs/`: everything the pipeline writes and the web page reads

Data folders and `outputs/` are not in git. Share rasters on a USB stick or shared drive.

## Radar preprocessing (lane A)

Raw RADARSAT-2 SLC scenes (XF0W3, HH, ascending, relative orbit 219) are turned into clean, aligned dB images.
Raw zips stay in `data/raw/` and are never committed.

```bash
snap/run_scene.sh 20170215          # one scene: subset, calibrate, multilook 3x4, Refined Lee, terrain-correct (10 m, UTM 19S), dB
.venv/bin/python scripts/align_stack.py   # put all scenes on one grid, check shift, write sigma0_*.tif + stack.json
```

- Needs ESA SNAP 14 (`~/esa-snap/bin/gpt`). Unzip a scene into `data/raw/unzipped/` first, and delete it once its output is checked.
- Output: `data/processed/sigma0_YYYYMMDD.tif` (single band, float32, dB, NaN = no data), all on the same grid; `stack.json` lists the dates and grid.
- The `.tif` files are **not in git** (RADARSAT-2 licence, public repo). Get them from the team's shared drive, or rebuild them with the two commands above from the raw zips.
- Grid: taken from `tminus/config.py` (EPSG:32719, 10 m, AOI W -70.60, S -13.15, E -69.85, N -12.85), so the images need no resampling by the pipeline.
- Dates processed so far: 2017-02-15, 2021-08-29 (the only scenes covering the La Pampa box). Measured shift between them: 0.1 px.

RADARSAT-2 Data and Products © Maxar Technologies Ltd. (2017, 2021) – All Rights Reserved.
RADARSAT is an official mark of the Canadian Space Agency.
