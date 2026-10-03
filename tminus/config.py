"""Shared settings. Everyone imports from here: change a number once, all lanes follow."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"              # EODMS downloads / SNAP outputs
PROCESSED = ROOT / "data" / "processed"  # sigma0_YYYYMMDD.tif, dB, on the grid
HELPERS = ROOT / "data" / "helpers"      # <name>.tif, on the grid
OUT = ROOT / "outputs"
WEB = OUT / "web"

# --- grid (lock at 12:30 Sat) ---
AOI = (-70.60, -13.15, -69.85, -12.85)   # W, S, E, N
CRS = "EPSG:32719"                       # UTM 19S
RES = 10                                 # metres

# La Pampa box (W, S, E, N). APPROXIMATE: replace with a real outline, or drop
# data/helpers/la_pampa.tif on the grid and it is used instead.
LA_PAMPA = (-70.05, -13.08, -69.85, -12.92)
CRACKDOWN = "20190219"                   # Operation Mercury

# --- rule detector (lane B) ---
FOREST_MIN_DB = -11.0   # first scene brighter than this = forest baseline
DROP_DB = 3.0
WATER_DB = -18.0

# --- random forest (lane D) ---
LABEL_DATE = "20191231"     # mining polygons are from 2019: train on the last scene up to here
NEG_MIN_DIST_M = 1000
BLOCK_M = 2000
TEST_FRACTION = 0.25
MAX_SAMPLES_PER_CLASS = 50_000
PROB_THRESHOLD = 0.5
SEED = 0

# --- alerts (lane B) ---
MIN_PATCH_HA = 0.5
POND_WATER_FRACTION = 0.5   # patch is a pond if this share of it is water now
TAILINGS_DROP_DB = 5.0      # mean drop above this = bare sand / tailings, else fresh clearing
PRIORITY_WEIGHTS = {"size": 30, "growth": 20, "protected": 25, "access": 15, "confidence": 10}
ACCESS_MAX_M = 5000         # further than this from road and river scores 0 for access

# --- web (lane C) ---
WEB_MAX_PX = 2000           # widest PNG sent to the browser
DB_STRETCH = (-25.0, 0.0)

# Helper rasters, all optional except where noted. Missing ones are read as zeros.
#   worldcover       ESA WorldCover class (10 forest, 80 water)
#   mining2019       1 inside a Maus et al. mining polygon   (needed for the model)
#   hansen_lossyear  0, or year minus 2000
#   slope            degrees
#   buffer           1 inside the Tambopata reserve or its buffer zone
#   indigenous       1 inside Indigenous land
#   dist_road, dist_river   metres
#   la_pampa         1 inside La Pampa
