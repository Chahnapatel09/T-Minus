"""Check the detectors against Hansen Global Forest Change (UMD, v1.13), using one radar date.

  python -m tminus.hansen [YYYYMMDD]

Put the Hansen GFC tiles (lossyear, treecover2000, datamask; any tiles covering the AOI) in data/raw/.
They go on the grid as data/helpers/hansen_lossyear.tif, hansen_treecover2000.tif, hansen_datamask.tif.

With a single radar scene there is no "before" image, so the detectors run in single-date form on the
chosen scene (default: the latest one):
  rule           forest in 2000 (Hansen tree cover >= C.HANSEN_FOREST_PCT) and darker than
                 C.FOREST_MIN_DB on radar now = cleared
  random forest  radar brightness and texture (+ ResNet tile features when the scene has embeddings),
                 trained on Amazon Mining Watch, scored on held-out 2 km blocks only
Hansen is then used as the independent reference:
  - rule vs Hansen forest loss up to the scene's year
  - share of the model's mining pixels that Hansen also shows as forest loss (held-out blocks only)
  - the year Hansen says each mining pixel lost its forest: a timeline around the 2019 crackdown
Writes outputs/hansen_check.json, outputs/hansen_timeline.csv and outputs/hansen_model_mining.tif.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import accuracy, embed, labels, model, rio
from . import config as C

LAYERS = ["lossyear", "treecover2000", "datamask"]


def _log(msg):
    print(f"[hansen] {msg}", flush=True)


def prepare():
    """Mosaic the Hansen tiles in data/raw/ onto the grid (skipped when already done)."""
    for layer in LAYERS:
        name = f"hansen_{layer}"
        if rio.has_helper(name):
            continue
        tiles = sorted(Path(C.RAW).glob(f"Hansen_GFC*_{layer}_*.tif"))
        if not tiles:
            raise SystemExit(f"No Hansen {layer} tiles in data/raw/ (Hansen_GFC-..._{layer}_..tif).")
        _log(f"{name}: {len(tiles)} tile(s) onto the grid")
        rio.warp_tiles_to_grid(tiles, Path(C.HELPERS) / f"{name}.tif", "nearest")


def _f1(s):
    p, r = s["precision"] or 0, s["recall"] or 0
    return 2 * p * r / (p + r) if p + r else 0.0


def check(date=None):
    prepare()
    found = dict(rio.scenes())
    if not found:
        raise SystemExit("No scenes in data/processed/.")
    date = date or max(found)
    after, profile = rio.read(found[date])
    year = int(date[:4])
    ha = C.RES * C.RES / 10_000
    _log(f"scene {date}")

    loss = rio.helper("hansen_lossyear", profile)
    cover = rio.helper("hansen_treecover2000", profile)
    land = rio.helper("hansen_datamask", profile) == 1
    valid = np.isfinite(after) & land
    forest2000 = (cover >= C.HANSEN_FOREST_PCT) & valid
    lost_by = forest2000 & (loss >= 1) & (loss <= year - 2000)
    del cover
    out = {"scene": date, "reference": "Hansen GFC v1.13 forest loss 2001-%d" % year,
           "forest2000_ha": round(float(forest2000.sum()) * ha),
           "hansen_loss_ha": round(float(lost_by.sum()) * ha)}

    # 1. rule detector, single-date form
    rule = forest2000 & (after < C.FOREST_MIN_DB)
    out["rule_vs_hansen"] = accuracy.score(lost_by, rule, where=forest2000)
    _log("rule vs Hansen loss: precision %.2f, recall %.2f"
         % (out["rule_vs_hansen"]["precision"] or 0, out["rule_vs_hansen"]["recall"] or 0))

    # 2. random forest, single-date form, trained on Amazon Mining Watch
    if not rio.has_helper("amw_year"):
        raise SystemExit("No labels: run python -m tminus.labels first.")
    mining = labels.mining_mask(rio.helper("amw_year", profile), year) & valid
    base = {"after": after, "texture_5x5": model._texture(after)}
    variants = {"radar features": base}
    if embed.cache_path(date).exists():
        variants["radar + foundation model"] = {**base, **embed.scene_layers(date, after.shape)}
    nothing = np.zeros_like(mining)
    trained = {}
    for name, layers in variants.items():
        feats = np.stack([np.asarray(v, dtype="float32") for v in layers.values()], axis=-1)
        clf, held = model.train(feats, mining, valid & ~mining, nothing)
        proba = model.predict(clf, feats)
        del feats
        fired = proba >= C.PROB_THRESHOLD
        sc = accuracy.score(held["truth"], fired, where=held["mask"])
        trained[name] = (fired, held, sc)
        _log(f"model [{name}] vs Amazon Mining Watch (held out): precision {sc['precision'] or 0:.2f}, "
             f"recall {sc['recall'] or 0:.2f}")
    best = max(trained, key=lambda n: _f1(trained[n][2]))
    fired, held, _ = trained[best]
    out["model_vs_amw"] = {n: t[2] for n, t in trained.items()}
    out["model_used"] = best

    # 3. the model's mining pixels against Hansen, held-out blocks only
    test = held["mask"] & forest2000
    agree = float((fired & test & lost_by).sum()) / max(float((fired & test).sum()), 1)
    amw_agree = float((mining & test & lost_by).sum()) / max(float((mining & test).sum()), 1)
    out["model_mining_confirmed_by_hansen"] = round(agree, 3)
    out["amw_mining_confirmed_by_hansen"] = round(amw_agree, 3)
    _log(f"model mining that Hansen also shows as forest loss: {agree:.1%} "
         f"(Amazon Mining Watch itself: {amw_agree:.1%})")

    # 4. timeline: Hansen loss year under the model's mining pixels
    inside = rio.la_pampa_mask(profile)
    rows = []
    for y in range(1, year - 2000 + 1):
        hit = fired & (loss == y)
        rows.append({"year": 2000 + y, "inside_ha": round(float((hit & inside).sum()) * ha, 1),
                     "outside_ha": round(float((hit & ~inside).sum()) * ha, 1)})
    timeline = pd.DataFrame(rows)
    pre = timeline[(timeline.year >= 2015) & (timeline.year <= 2018)]
    post = timeline[(timeline.year >= 2019) & (timeline.year <= min(year, 2022))]
    out["crackdown"] = {
        "la_pampa_ha_per_year_2015_2018": round(pre.inside_ha.mean(), 1),
        "la_pampa_ha_per_year_2019_on": round(post.inside_ha.mean(), 1),
        "outside_ha_per_year_2015_2018": round(pre.outside_ha.mean(), 1),
        "outside_ha_per_year_2019_on": round(post.outside_ha.mean(), 1),
    }

    C.OUT.mkdir(parents=True, exist_ok=True)
    timeline.to_csv(C.OUT / "hansen_timeline.csv", index=False)
    (C.OUT / "hansen_check.json").write_text(json.dumps(out, indent=1), encoding="utf8")
    rio.write(C.OUT / "hansen_model_mining.tif", fired.astype("uint8"), profile)
    _log("timeline (ha of model-detected mining, by the year Hansen saw the forest go):")
    print(timeline.to_string(index=False))
    print(json.dumps(out["crackdown"], indent=1))
    return out


if __name__ == "__main__":
    check(sys.argv[1] if len(sys.argv) > 1 else None)
