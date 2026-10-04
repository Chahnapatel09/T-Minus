# T-Minus

Gold-mining monitor for La Pampa, Peru, built on RADARSAT-2 Tropical Forests data.
Mission Accepted Space Hackathon, Challenge 1.

Radar sees through cloud. Forest gives a bright radar echo, cleared ground a darker one, and mining
ponds a very dark one. T-Minus compares RADARSAT-2 images of La Pampa taken on different dates, finds
where forest turned into bare ground or water, ranks those patches as alerts, and checks whether the
February 2019 crackdown (Operation Mercury) slowed the clearing. The results are shown on a web page.

---

## Quick start on a Mac

Everything below is typed in the **Terminal** app (Applications > Utilities > Terminal).
It works on Apple Silicon (M1/M2/M3/M4) and Intel Macs.

### 1. What you need

- **Python 3.12.** Check with `python3 --version`. If it is missing or older, install 3.12 from
  [python.org/downloads](https://www.python.org/downloads/macos/) (the macOS installer), then open a new Terminal window.
- **Disk space:** about 11 GB free per image while it is being processed (the 5 GB zip plus its unzipped copy).
  You can delete both afterwards (see step 8).
- **Memory:** 8 GB of RAM works, 16 GB is comfortable.

### 2. Get the code

Either clone it:

```bash
git clone <repo-url> T-Minus
cd T-Minus
git checkout Dev_Boilerplate
```

or unzip a copy of the project folder and `cd` into it, for example:

```bash
cd ~/Desktop/T-Minus
```

All the commands below are run from inside this `T-Minus` folder.

### 3. Install (once)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

`source .venv/bin/activate` has to be run again **every time you open a new Terminal window**.
You know it is active when the prompt starts with `(.venv)`.

### 4. Check that it works (no images needed, about 1 minute)

```bash
python -m tests.synthetic_run
```

This runs the whole pipeline on made-up images in a temporary folder. It should end with `OK`.

### 5. Preprocess the RADARSAT-2 images

Put the zips exactly as downloaded from EODMS (names like `RS2_..._XF0W3_20210829_..._HH_SLC.zip`)
into `data/raw/`. Then process one:

```bash
python -m tminus.slc data/raw/RS2_OK151230_PK1384737_DK1349543_XF0W3_20210829_231001_HH_SLC.zip --to-grid
```

or every zip in the folder, one after the other:

```bash
for f in data/raw/RS2_*.zip; do python -m tminus.slc "$f" --to-grid; done
```

Each image takes about 10 to 15 minutes. For each one you get:

| File | What it is |
|---|---|
| `data/processed/sigma0_YYYYMMDD.tif` | The image cut to the study area, ready for the pipeline |
| `data/raw/sigma0_geo_YYYYMMDD.tif` | The whole image, calibrated and map-projected |
| `data/raw/sigma0_geo_YYYYMMDD.png` | A preview. **Open it and look.** Yellow box = study area, red box = La Pampa |

If an image does not cover the study area, it stops with
`... does not overlap the AOI ...: nothing written`. That image is outside La Pampa and cannot be used. Nothing is broken.

**Which images to use:**

- They must cover La Pampa, around **13.0 S, 70.0 W**. The `PDS_..._Bounds.txt` file inside each zip lists the four corners.
- Use the **same beam mode** for all of them (the `XF0W3` part of the name), so they are comparable.
- You need **at least two dates**. One from before February 2019 and one or more after it is what
  makes the crackdown question answerable. More dates give a better timeline.
- The order you process them in does not matter. The pipeline sorts by date.

### 6. Labels and foundation-model features (once, then after each new image)

```bash
python -m tminus.labels   # once: downloads Amazon Mining Watch (62 MB) and puts it on the grid
python -m tminus.embed    # after each new image: about 30 to 40 minutes per image on a laptop CPU (faster on Apple Silicon)
```

- **Labels** tell the machine-learning model what mining looks like. They come from
  [Amazon Mining Watch](https://source.coop/earthgenome/amazon-mining-watch) (Earth Genome, CC BY 4.0),
  a map of gold mining across the Amazon made from optical Sentinel-2 images. Without labels the
  pipeline still runs, with the rule detector only.
- **Embeddings** run each image through a radar network pretrained on millions of Sentinel-1 images
  (ResNet50, SSL4EO-S12, weights from TorchGeo, about 100 MB downloaded once). The pipeline trains the
  model with and without these features, scores both on the same held-out areas, and keeps the better one.
  The accuracy tab shows the comparison. Skipping this step is fine.

### 7. Run the analysis and open the web page

Once two or more images are in `data/processed/`:

```bash
python -m tminus.pipeline
streamlit run app/app.py
```

The pipeline writes its results to `outputs/` (a few minutes). Streamlit then opens the web page in
your browser at http://localhost:8501. Stop it with `Ctrl + C` in the Terminal.

If you add another image later, run step 5 for it, `python -m tminus.embed`, then step 7 again.

### 8. Free the disk space (optional)

Once `data/processed/sigma0_YYYYMMDD.tif` exists for an image, the pipeline never needs the original again.
You can delete the zip, its unzipped `RS2_..._SLC` folder, or both. Keep the zip if you might want to reprocess it.

### Common problems

| Problem | Fix |
|---|---|
| `command not found: python` | Run `source .venv/bin/activate` first (step 3). |
| `No module named tminus` | You are not inside the `T-Minus` folder. `cd` into it. |
| `pip install` is slow or huge | PyTorch is about 1 GB. Let it finish once. |
| `Need at least two scenes in data/processed/` | Only one image covers La Pampa so far. Add another (step 5). |
| `does not overlap the AOI` | That image is outside La Pampa. Use a different one. |
| `pip install` fails on rasterio | Run `pip install --upgrade pip` and try again. Use Python 3.12. |
| The Mac gets very slow during step 5 | Close other apps. It needs about 3 GB of free RAM. |
| Web page says "No results yet" | Run `python -m tminus.pipeline` first, then reload the page. |

---

## Optional extra data

The pipeline runs on the radar images alone. These make it better. Put them on the grid with the
functions in `tminus/preprocess.py`, which write to `data/helpers/`:

| Helper | Source | Used for |
|---|---|---|
| `amw_year` | Amazon Mining Watch (`python -m tminus.labels`) | Labels for the model, and an independent crackdown check |
| `mining2019` | Maus et al. global mining polygons | Alternative labels; used instead of `amw_year` if present |
| `worldcover` | ESA WorldCover | Limits detection to forest |
| `slope` | Any DEM | Model feature |
| `buffer`, `indigenous` | Tambopata reserve buffer, Indigenous territories | Alert priority |
| `dist_road`, `dist_river` | Road and river lines | Alert priority (access) |
| `la_pampa` | A real La Pampa outline | Replaces the rough box in `tminus/config.py` |

```bash
python -c "from tminus import preprocess; preprocess.vector('mining2019', 'data/raw/mining_polygons.gpkg')"
python -c "from tminus import preprocess; preprocess.raster('worldcover', 'data/raw/worldcover.tif')"
python -c "from tminus import preprocess; preprocess.dist('dist_road', 'data/raw/roads.geojson')"
```

Polygons and lines can be GeoJSON (in lon/lat) or anything else GDAL reads (shp, gpkg).
`data/helpers/check_points.csv` (columns `lon,lat,mining`) holds points checked by eye, for the accuracy tab.
Screenshots for the first tab of the web page go in `app/assets/` as `sentinel2.png` (cloudy optical) and `radar.png`.

## How the preprocessing works

SNAP is not needed. `tminus/slc.py` does the standard chain in Python:

1. Complex I/Q values to intensity, calibrated to sigma0 with the product's `lutSigma.xml` (DN^2 / A^2)
2. Multilook, 3 azimuth x 2 range, about 9 x 8 m on the ground
3. Lee speckle filter
4. Map projection from the product's ground control points, onto UTM 19S at 10 m
5. Conversion to dB (forest comes out around -8 dB)

There is no elevation model, so slopes are not terrain corrected. That is fine on the flat forest around
La Pampa, but the Andean foothills in the south-west corner of the images are distorted.

## Commands

```bash
python -m tminus.slc data/raw/RS2_..._SLC.zip --to-grid   # one RADARSAT-2 SLC -> data/processed/sigma0_<date>.tif
python -m tminus.pipeline      # detectors -> alerts -> files in outputs/
streamlit run app/app.py       # the web page
python -m tminus.labels        # Amazon Mining Watch labels -> data/helpers/amw_year.tif
python -m tminus.embed         # foundation-model embeddings for each scene in data/processed/
python -m tminus.hansen        # single-date check against Hansen forest loss (Hansen_GFC tiles in data/raw/)
python -m tests.synthetic_run  # whole pipeline on made-up scenes, in a temp folder (no data needed; --embed adds the network)
```

On Windows, activate with `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

## Who owns what

| Lane | Files | Job |
|---|---|---|
| A | `tminus/slc.py`, `tminus/preprocess.py`, `tminus/rio.py` | Raw images and helper maps onto the shared grid |
| B | `tminus/rules.py`, `combine.py`, `alerts.py`, `crackdown.py` | Rule detector, confidence, alert patches, priority, crackdown table, exports |
| C | `app/app.py`, `tminus/webout.py` | The web page and the PNG overlays it reads |
| D | `tminus/model.py`, `labels.py`, `embed.py`, `accuracy.py` | Labels, foundation-model features, random forest, accuracy check |
| all | `tminus/config.py` | Every threshold and the study area. Change numbers here, not in the code |
| all | `tminus/pipeline.py` | Wires the lanes together |

## The file contract between lanes

Everything is a single-band GeoTIFF on the same grid: UTM 19S (EPSG:32719), 10 m.

- `data/raw/`: EODMS downloads and full-scene outputs
- `data/processed/sigma0_YYYYMMDD.tif`: radar scene in dB, on the grid (lane A)
- `data/helpers/<name>.tif`: helper maps on the grid, names listed in `tminus/config.py` (lane A)
- `data/helpers/check_points.csv`: columns `lon,lat,mining`, the points checked by eye (lane D)
- `app/assets/`: screenshots for the first screen (lane C)
- `outputs/`: everything the pipeline writes and the web page reads

Data folders and `outputs/` are not in git. Share rasters on a USB stick or shared drive.
To skip reprocessing on another computer, copy `data/processed/` across: those files are small (about 100 MB each).
