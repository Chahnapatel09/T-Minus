# T-Minus: Dev Boilerplate setup guide

Everything you need to get T-Minus running on your own computer, from an empty machine to the
dashboard, plus where each piece of data comes from and what every command does.

**What T-Minus is:** a gold-mining monitor for La Pampa, Madre de Dios, Peru. It compares
RADARSAT-2 radar images from two or more dates (radar sees through the clouds that cover the area
most of the year), finds where forest turned into bare ground or mining ponds, ranks those patches
as alerts, checks itself against Amazon Mining Watch, Hansen forest loss and hand-checked points,
and shows whether the February 2019 crackdown (Operation Mercury) slowed mining.

---

## Contents

1. [What to install](#1-what-to-install)
2. [Get the code](#2-get-the-code)
3. [Set up Python (once)](#3-set-up-python-once)
4. [Check the install (no data needed)](#4-check-the-install-no-data-needed)
5. [Get the data](#5-get-the-data)
6. [Run everything, in order](#6-run-everything-in-order)
7. [Open the dashboard](#7-open-the-dashboard)
8. [What you get (output files)](#8-what-you-get-output-files)
9. [How the models work](#9-how-the-models-work)
10. [Settings you can change](#10-settings-you-can-change)
11. [Project layout](#11-project-layout)
12. [Troubleshooting](#12-troubleshooting)
13. [Rules for the team](#13-rules-for-the-team)

---

## 1. What to install

| What | Version | Where | Needed? |
|---|---|---|---|
| **Python** | **3.12** | [python.org/downloads](https://www.python.org/downloads/) (macOS or Windows installer) | Yes |
| **Git** | any | Mac: comes with Xcode tools (`xcode-select --install`). Windows: [git-scm.com](https://git-scm.com/download/win) | Yes |
| **VS Code** | any | [code.visualstudio.com](https://code.visualstudio.com/) | Optional, handy |
| **QGIS** | any | [qgis.org](https://qgis.org/) | Optional, to look at the `.tif` maps |
| **Google Earth Pro** | any | [google.com/earth/versions](https://www.google.com/earth/versions/#earth-pro) | Optional, to open `alerts.kml` and make check points |
| **ESA SNAP** | 14 | [step.esa.int](https://step.esa.int/main/download/snap-download/) | Only if you preprocess raw radar zips with the SNAP route |

**Computer:**

| | Minimum | Comfortable |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Free disk | 5 GB (code, packages, processed data) | 25 GB if you also handle raw 5 GB radar zips |
| Chip | any | Apple Silicon or an NVIDIA GPU speeds up the foundation model a lot |

**Windows installer note:** tick **"Add python.exe to PATH"** on the first screen of the Python installer.

---

## 2. Get the code

```bash
git clone https://github.com/Chahnapatel09/T-Minus.git
cd T-Minus
git checkout Dev_Boilerplate
git pull
```

Every command in this guide is run **from inside the `T-Minus` folder**.

> The working code is on the **`Dev_Boilerplate`** branch. `main` only has the empty template,
> and `feature/pipeline` only has the SNAP preprocessing scripts (already merged into `Dev_Boilerplate`).

---

## 3. Set up Python (once)

**Mac / Linux (Terminal):**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

- This installs everything in `requirements.txt`: numpy, scipy, pandas, rasterio, shapely, pyogrio,
  scikit-learn, scikit-image, pillow, streamlit, folium, streamlit-folium, torch, torchvision.
- PyTorch is about 1 GB, so the first install takes a while.
- **Activate the environment every time you open a new terminal** (`source .venv/bin/activate` on
  Mac, `.venv\Scripts\activate` on Windows). The prompt then starts with `(.venv)`.
- On Mac use `python3` only to create the environment. After activating, `python` works.

---

## 4. Check the install (no data needed)

```bash
python -m tests.synthetic_run
```

Runs the whole pipeline on made-up images in a temporary folder, in about a minute. It must end
with a line starting with **`OK`**.

To also test the foundation model (downloads its weights once, about 100 MB):
```bash
python -m tests.synthetic_run --embed
```

---

## 5. Get the data

Big files are **not in git**. Some you download yourself, some come from the team.

| Data | Where it goes | How to get it | Size |
|---|---|---|---|
| **Radar images (main)**: `sigma0_20170215.tif`, `sigma0_20210829.tif` | `data/processed/` | **From the team's shared drive** (RADARSAT-2 licence: never post or commit them) | ~95 MB each |
| `stack.json` | `data/processed/` | Already in git | tiny |
| **Amazon Mining Watch labels** | `data/raw/` then `data/helpers/amw_year.tif` | Automatic: `python -m tminus.labels` | 62 MB |
| **Hansen forest loss** (6 tiles) | `data/raw/` | Download links below | ~750 MB |
| **Hand-checked pins** (`.kmz` from Google Earth) | `data/raw/` | From the team, or make your own (section 6, step D) | tiny |
| Raw RADARSAT-2 zips (only to reprocess) | `data/raw/` | EODMS order / team | ~5.5 GB each |

### Hansen Global Forest Change v1.13 tiles

La Pampa sits on the border of two tiles, so you need both for each layer. Download all six into `data/raw/`:

**Mac / Linux:**
```bash
cd data/raw
for L in lossyear treecover2000 datamask; do for T in 10S_070W 10S_080W; do
  curl -O "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2025-v1.13/Hansen_GFC-2025-v1.13_${L}_${T}.tif"
done; done
cd ../..
```

**Windows (PowerShell):**
```powershell
cd data\raw
foreach ($L in "lossyear","treecover2000","datamask") { foreach ($T in "10S_070W","10S_080W") {
  curl.exe -O "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2025-v1.13/Hansen_GFC-2025-v1.13_${L}_${T}.tif"
} }
cd ..\..
```

### After this step your folders should look like

```
data/
  processed/
    sigma0_20170215.tif
    sigma0_20210829.tif
    stack.json
  raw/
    Hansen_GFC-2025-v1.13_datamask_10S_070W.tif      (and the other 5 Hansen tiles)
    MINING.kmz                                       (optional, hand-checked pins)
```

---

## 6. Run everything, in order

Activate the environment first. Times are for a normal laptop CPU.

| Step | Command | What it does | Time | Needed? |
|---|---|---|---|---|
| **A** | *(only with raw zips)* see "Preprocessing raw radar" below | Raw RADARSAT-2 SLC zip to a clean dB image on the 10 m grid | 15 min / image | Only if you don't have the `sigma0_*.tif` files |
| **B** | `python -m tminus.labels` | Downloads Amazon Mining Watch and puts it on the grid (`data/helpers/amw_year.tif`). These are the practice answers the random forest learns from | 2 min | Yes, once |
| **C** | `python -m tminus.embed` | Runs every image through the pretrained ResNet50 radar network and caches the results (`data/processed/emb_<date>.npz`) | 30 to 40 min / image (much faster on Apple Silicon or GPU) | Recommended. It is the best model |
| **D** | `python -m tminus.checkpoints` | Reads every `.kmz`/`.kml` pin file in `data/raw/` into `data/helpers/check_points.csv` | seconds | Optional |
| **E** | `python -m tminus.pipeline` | **The main run.** Rule detector, random forest with and without ResNet, combine, alerts, crackdown, accuracy, comparison against Amazon Mining Watch, web files | 5 to 10 min | Yes |
| **F** | `python -m tminus.hansen` | Extra check against Hansen forest loss, plus a yearly timeline around the 2019 crackdown | 5 to 10 min | Optional (needs the Hansen tiles) |
| **G** | `streamlit run app/app.py` | Opens the dashboard | instant | Yes |

**The short version** (with the two processed images already in `data/processed/`):
```bash
python -m tminus.labels
python -m tminus.embed
python -m tminus.checkpoints
python -m tminus.pipeline
python -m tminus.hansen
streamlit run app/app.py
```

**After adding a new radar image:** run C, then E (and F), then reload the dashboard.
**After changing a setting in `tminus/config.py`:** run E again.

### What a good `pipeline` run prints

```
[tminus] 2 scenes, 20170215 to 20210829, grid 8152 x 3358
[tminus] helper maps: hansen_lossyear, amw_year
[tminus] rule detector: 11981 ha flagged
[tminus] training on scene 20210829 (Amazon Mining Watch, mined by 2021)
[tminus] model [radar features]: precision 0.49, recall 0.71
[tminus] model [radar + foundation model]: precision 0.70, recall 0.88
[tminus] new mining 2019-2021: rule precision 0.54 recall 0.24, combined precision 0.41 recall 0.40
[tminus] comparison with Amazon Mining Watch (held-out blocks): ...
[tminus] 4388 alerts
[tminus] done
```

If the line `no embeddings` appears, step C was skipped and only the radar-only model is used.

### Step D: making hand-checked pins

1. Open Google Earth Pro, go to La Pampa (search `-12.896, -69.996`).
2. Use the history slider (clock icon) to look at the imagery from different years.
3. Add pins (yellow pushpin icon) and **name them** by what you see:
   - `MINE` or `MINING PONDS` count as **mining**
   - `SETTLEMENT`, `CLEARED LAND`, `FOREST`, `ROAD` count as **not mining**
4. Put them in one folder, right-click the folder, **Save Place As...**, choose `.kmz`.
5. Copy the `.kmz` into `data/raw/`, then run steps D and E.

### Preprocessing raw radar (step A)

Only needed to turn new raw RADARSAT-2 zips into `sigma0_YYYYMMDD.tif`. Two routes, either works:

**Route 1: Python only (no SNAP)**
```bash
python -m tminus.slc data/raw/RS2_..._SLC.zip --to-grid
```
Calibration, multilook, Lee speckle filter, geocoding from the image's control points, dB, then cut
to the study area. Writes `data/processed/sigma0_<date>.tif` and a preview
`data/raw/sigma0_geo_<date>.png` (yellow box = study area, red box = La Pampa). Open the preview to check.
No terrain correction (no DEM), which is fine on the flat forest around La Pampa.

**Route 2: SNAP (best quality, terrain corrected; this made the two main images)**
```bash
snap/run_scene.sh 20170215              # needs SNAP 14 at ~/esa-snap/bin/gpt; scene unzipped in data/raw/unzipped/
python scripts/align_stack.py           # puts every scene on one grid, checks shift, writes sigma0_*.tif + stack.json
```

**Which raw images work:** they must cover La Pampa (about 13.0 S, 70.0 W) and use the same beam
mode (`XF0W3`, HH). The `PDS_..._Bounds.txt` inside each zip lists its corners. An image that misses
the area stops with `does not overlap the AOI`: nothing is broken, that image just can't be used.

---

## 7. Open the dashboard

```bash
streamlit run app/app.py
```

It opens http://localhost:8501 in your browser. Stop it with `Ctrl + C` in the terminal.

| Screen | What it shows |
|---|---|
| Landing page (the T-Minus logo) | Cloudy optical image next to the latest radar scene (add `app/assets/sentinel2.png`) |
| Overview | Side-by-side investigation: the alert list on the left; for the selected alert, the before and after radar images, area, priority, type and coordinates, then backscatter analysis, time series and nearby alerts |
| Map | A real map (Satellite, Radar or Street view) with the alert points and the detected change on top, plus the alert list and the selected alert. Radar view has a draggable before/after divider. The basemap needs an internet connection |
| Analytics | Clearing inside vs outside La Pampa, before vs after Feb 2019, the Amazon Mining Watch check, the accuracy scores for every model, and how many alerts land on mining that Amazon Mining Watch has mapped (needs `python -m tminus.labels`; the dashboard reads `data/helpers/amw_year.tif` itself, so this works without rerunning the pipeline) |
| Reports | Download alerts as KML, GeoJSON or CSV |

The Before and After pickers at the top choose which two scenes are compared; the alerts listed are the ones first seen between them.

If it shows a "Sample data" badge, it found no results: run `python -m tminus.pipeline` first and reload.

---

## 8. What you get (output files)

All in `outputs/` (not in git):

| File | What it is | Open with |
|---|---|---|
| `alerts.csv` / `alerts.geojson` / `alerts.kml` | Ranked mining alerts: size, type, confidence, priority, location, Google Maps link | Excel / QGIS / Google Earth |
| `confidence.tif` | Full-resolution map: 0 none, 1 medium, 2 high | QGIS |
| `accuracy.json` | All scores | text editor |
| `comparison_amw.csv` | Every model side by side against Amazon Mining Watch | Excel |
| `check_points_result.csv` | Every model's answer at each hand-checked pin | Excel |
| `crackdown.csv`, `crackdown_amw.csv` | Before/after-crackdown numbers | Excel |
| `hansen_check.json`, `hansen_timeline.csv`, `hansen_model_mining.tif` | Hansen check and yearly timeline | text / Excel / QGIS |
| `web/` | Images the dashboard uses | browser |

---

## 9. How the models work

```
Radar 2017 + Radar 2021
   |
   +--> 1. Rule-based detector --------------------------------+
   |                                                            v
   +--> 2. ResNet50 (pretrained, frozen) --> clues --> 3. Random forest --> Combine --> Alerts
```

**1. Rule-based detector** (`tminus/rules.py`, no training)
A pixel is flagged if it was forest (brighter than -11 dB) and then got at least 3 dB darker or
turned to water (below -18 dB), and stayed that way on the next image (needs a third date).

**2. ResNet50 foundation model** (`tminus/embed.py`, not trained by us)
Pretrained on millions of Sentinel-1 radar images (SSL4EO-S12, MoCo; weights from TorchGeo).
It turns each 640 m tile into 2,048 numbers; the change between dates becomes 5 extra clues.

**3. Random forest** (`tminus/model.py`, trained every run)
200 trees, 7 radar clues per 10 m pixel (+ 5 ResNet clues). Learns from Amazon Mining Watch.
25% of the map (2 x 2 km blocks) is held back for testing. It is trained with and without the ResNet
clues; the better one is kept.

**Combine:** both say mining = **high**, one says mining = **medium**. A model-only pixel needs at
least 1.5 dB of darkening to count, because alerts are about **new** mining.

**Results on the two main images (held-out areas, against Amazon Mining Watch):**

| Model | Precision | Recall | New mining recall |
|---|---|---|---|
| Rule-based detector | 0.82 | 0.21 | 0.24 |
| Random forest (radar only) | 0.49 | 0.71 | 0.60 |
| **Random forest + ResNet** | **0.70** | **0.88** | **0.81** |
| Alerts map | 0.75 | 0.38 | 0.40 |

**Crackdown (Hansen timeline of model-detected mining):** La Pampa fell from 976 ha/year (2015 to
2018) to 161 ha/year (2019 to 2021, -84%), while outside La Pampa rose from 1,201 to 1,346 ha/year.

---

## 10. Settings you can change

All numbers live in `tminus/config.py`. Change them there, then rerun `python -m tminus.pipeline`.

| Setting | Default | What it does |
|---|---|---|
| `AOI` | (-70.60, -13.15, -69.85, -12.85) | Study area (W, S, E, N). Changing it means reprocessing images |
| `LA_PAMPA` | (-70.05, -13.08, -69.85, -12.92) | Rough La Pampa box for inside/outside numbers |
| `CRACKDOWN` | 20190219 | Operation Mercury date |
| `FOREST_MIN_DB` | -11.0 | Brightness a pixel needs at the start to count as forest |
| `DROP_DB` | 3.0 | Darkening that counts as clearing (lower = more detections, more false alarms) |
| `WATER_DB` | -18.0 | Below this a pixel is water |
| `PROB_THRESHOLD` | 0.5 | Random forest cut-off (higher = fewer, surer detections) |
| `MODEL_CHANGE_DB` | 1.5 | Darkening a model-only pixel needs to become an alert |
| `MIN_PATCH_HA` | 0.5 | Smallest alert, in hectares |
| `ALERT_MIN_WIDTH_PX` | 3 | Specks narrower than this (pixels) are removed |
| `EMB_TILE_PX` | 64 | ResNet tile size (64 px = 640 m) |

---

## 11. Project layout

```
T-Minus/
  app/app.py               the dashboard (Streamlit wrapper)
  app/dashboard.py         gathers outputs/ into the data the dashboard shows
  app/web/                 the dashboard itself: HTML, CSS, JS
  app/assets/              sentinel2.png for the landing page
  data/raw/                downloads: radar zips, Hansen tiles, Amazon Mining Watch, .kmz pins   (not in git)
  data/processed/          sigma0_<date>.tif radar images, emb_<date>.npz, stack.json            (only stack.json in git)
  data/helpers/            helper maps on the grid: amw_year, hansen_*, check_points.csv         (not in git)
  outputs/                 everything the pipeline writes                                       (not in git)
  scripts/align_stack.py   SNAP route: put scenes on one grid
  snap/                    SNAP route: processing graph and run script
  tests/synthetic_run.py   end-to-end test on made-up images
  tminus/
    config.py              every setting and threshold
    pipeline.py            runs everything in order
    slc.py                 Python preprocessing of raw RADARSAT-2 zips
    preprocess.py, rio.py  putting rasters and vectors on the shared 10 m grid
    rules.py               rule-based detector
    embed.py               ResNet50 foundation-model features
    model.py               random forest
    labels.py              Amazon Mining Watch labels
    checkpoints.py         Google Earth pins to check points
    combine.py             confidence levels
    alerts.py              alert patches, ranking, KML/GeoJSON/CSV export
    crackdown.py           before/after crackdown tables
    accuracy.py            scoring
    hansen.py              Hansen forest loss check
    webout.py              images for the dashboard
  requirements.txt         Python packages
  README.md                main project README
  DEV_BOILERPLATE_README.md   this guide
```

---

## 12. Troubleshooting

| Problem | Fix |
|---|---|
| `command not found: python` (Mac) | Activate first: `source .venv/bin/activate`. To create the environment use `python3` |
| `'python' is not recognized` (Windows) | Reinstall Python with "Add python.exe to PATH" ticked, then open a new PowerShell |
| PowerShell won't run `activate` ("running scripts is disabled") | Run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then try again |
| `No module named tminus` | You are not in the `T-Minus` folder. `cd` into it |
| `No module named ...` (any package) | The environment is not active, or the install failed. Activate and rerun `pip install -r requirements.txt` |
| `pip install` fails on rasterio or torch | Use Python **3.12**, run `pip install --upgrade pip`, try again |
| `Need at least two scenes in data/processed/` | The `sigma0_*.tif` files are missing. Get them from the team's drive (section 5) |
| `no embeddings: run python -m tminus.embed` | Not an error. Run step C to add the ResNet model |
| `No labels` / model skipped | Run `python -m tminus.labels` |
| `No Hansen ... tiles in data/raw/` | Download the 6 Hansen tiles (section 5) |
| `does not overlap the AOI` | That radar image is outside La Pampa. Use a different one |
| Computer very slow or runs out of memory | Close other apps. The pipeline needs about 4 GB of free RAM |
| `tminus.embed` takes very long | Normal on CPU (30 to 40 min per image). Let it finish; results are cached |
| Dashboard shows a "Sample data" badge | It found no results. Run `python -m tminus.pipeline`, then reload the page |
| Port 8501 already in use | `streamlit run app/app.py --server.port 8502` and open http://localhost:8502 |

---

## 13. Rules for the team

- **Never commit or share radar images** (`.tif` in `data/`). RADARSAT-2 licence. `.gitignore` already blocks them; don't force-add.
- Work on **`Dev_Boilerplate`**. `git pull` before you start, and commit small, clear changes.
- Change thresholds in **`tminus/config.py`** only, not inside the code.
- Run `python -m tests.synthetic_run` before pushing code changes, to check nothing broke.

**Credits:**
RADARSAT-2 Data and Products © Maxar Technologies Ltd. (2017, 2021). All Rights Reserved. RADARSAT is an official mark of the Canadian Space Agency.
Amazon Mining Watch: Earth Genome, Pulitzer Center, Amazon Conservation (CC BY 4.0).
Hansen/UMD/Google/USGS/NASA Global Forest Change v1.13.
SSL4EO-S12 pretrained weights via TorchGeo.
