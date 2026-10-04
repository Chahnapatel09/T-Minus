#!/usr/bin/env bash
# Run the SNAP chain on one unzipped scene.   usage: snap/run_scene.sh YYYYMMDD
# Settings below are the defaults (cut = tminus/config.py AOI + margin, 10 m); override by exporting the variable first.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GPT="${GPT:-$HOME/esa-snap/bin/gpt}"            # SNAP's gpt, NOT /usr/sbin/gpt
DATE="${1:?scene date YYYYMMDD}"
GEOREGION="${GEOREGION:-POLYGON((-70.65 -12.80, -69.80 -12.80, -69.80 -13.20, -70.65 -13.20, -70.65 -12.80))}"
RG_LOOKS="${RG_LOOKS:-3}"; AZ_LOOKS="${AZ_LOOKS:-4}"
SPECKLE="${SPECKLE:-Refined Lee}"
DEM="${DEM:-Copernicus 30m Global DEM}"
PIXEL="${PIXEL:-10.0}"; CRS="${CRS:-EPSG:32719}"
HEAP="${HEAP:-9G}"

SRC=$(ls -d "$ROOT"/data/raw/unzipped/*_"${DATE}"_*_SLC | head -1)
OUT="$ROOT/data/processed/snap_${DATE}.tif"
mkdir -p "$ROOT/data/processed"
if [ -f "$OUT" ] && [ -z "${FORCE:-}" ]; then echo "exists, skipping: $OUT (FORCE=1 to redo)"; exit 0; fi

start=$(date +%s)
"$GPT" "$ROOT/snap/preprocess_slc.xml" -J-Xmx"$HEAP" -q 4 \
  -Pinput="$SRC/product.xml" -Poutput="$OUT" -PgeoRegion="$GEOREGION" \
  -PrgLooks="$RG_LOOKS" -PazLooks="$AZ_LOOKS" -Pspecklefilter="$SPECKLE" \
  -Pdem="$DEM" -Ppixel="$PIXEL" -Pcrs="$CRS" -f GeoTIFF
echo "done $DATE in $(( $(date +%s) - start )) s -> $(du -h "$OUT" | cut -f1) $OUT"
