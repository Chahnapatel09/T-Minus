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
