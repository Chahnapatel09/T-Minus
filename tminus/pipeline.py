"""End to end: scenes on the grid -> detectors -> confidence -> alerts -> files for the web page.

  python -m tminus.pipeline

Reads  data/processed/sigma0_YYYYMMDD.tif and data/helpers/*.tif
Writes outputs/
"""
import json

import numpy as np
import pandas as pd

from . import accuracy, alerts, combine, crackdown, embed, labels, model, rio, rules, webout
from . import config as C


def _log(msg):
    print(f"[tminus] {msg}", flush=True)


def _rule_pass(first, scenes, forest):
    """Run the rule detector on every later scene. Returns change_idx (int16, -1 = never)."""
    change_idx = np.full(first.shape, -1, dtype="int16")
    for i in range(1, len(scenes)):
        confirm = scenes[i + 1] if i + 1 < len(scenes) else None
        fired = rules.detect(first, scenes[i], confirm, forest) > 0
        change_idx[fired & (change_idx < 0)] = i
    return change_idx


def _min_later(scenes):
    out = scenes[1].copy()
    for s in scenes[2:]:
        out = np.fmin(out, s)
    return out


def run():
    # 1. load scenes and helper maps                     (lane A: rio)
    found = rio.scenes()
    if len(found) < 2:
        raise SystemExit("Need at least two scenes in data/processed/ (sigma0_YYYYMMDD.tif).")
    dates = [d for d, _ in found]
    scenes, profile = [], None
    for _, path in found:
        arr, prof = rio.read(path)
        profile = profile or prof
        if arr.shape != (profile["height"], profile["width"]):
            raise SystemExit(f"{path} is not on the same grid as the first scene.")
        scenes.append(arr.astype("float32"))
    first, last = scenes[0], scenes[-1]
    layers = {n: rio.helper(n, profile) for n in C.HELPER_NAMES if rio.has_helper(n)}
    _log(f"{len(scenes)} scenes, {dates[0]} to {dates[-1]}, grid {profile['width']} x {profile['height']}")
    _log("helper maps: " + (", ".join(layers) or "none"))

    # 2. rule detector on each pair of dates             (lane B: rules)
    forest = (layers["worldcover"] == 10) if "worldcover" in layers else None
    change_idx = _rule_pass(first, scenes, forest)
    rule_fired = change_idx >= 0
    _log(f"rule detector: {rule_fired.sum() * C.RES ** 2 / 10_000:.0f} ha flagged")

    # 3. train random forest, predict probability        (lane D: model)
    model_fired = np.zeros_like(rule_fired)
    held_out, scores = None, {}
    min_later = _min_later(scenes)
    slope = layers.get("slope", np.zeros_like(first))
    cover = layers.get("worldcover", np.zeros_like(first))
    mining, k = None, len(scenes) - 1
    if "mining2019" in layers:
        k = max([i for i, d in enumerate(dates) if d <= C.LABEL_DATE and i > 0], default=1)
        mining = layers["mining2019"] > 0
        scores["label_source"] = "mining2019 polygons"
    elif "amw_year" in layers:
        mining = labels.mining_mask(layers["amw_year"], dates[k][:4])
        scores["label_source"] = f"Amazon Mining Watch, mined by {dates[k][:4]}"
    if mining is not None and mining.any():
        _log(f"training on scene {dates[k]} ({scores['label_source']})")
        stable = (first > C.FOREST_MIN_DB) & ((first - min_later) < C.DROP_DB)
        rule_k_fired = (change_idx >= 1) & (change_idx <= k)

        # Plain features, and plain + foundation-model features when embeddings exist
        # (python -m tminus.embed). Same held-out blocks for both; the better one is used.
        variants = {"radar features": None}
        if embed.available(dates):
            variants["radar + foundation model"] = lambda d: embed.change_layers(dates[0], d, first.shape, dates)
        else:
            _log("no embeddings: run python -m tminus.embed to add foundation-model features")
        trained, f1 = {}, {}
        for name, extra in variants.items():
            feats = model.features(first, scenes[k], min_later, slope, cover, extra and extra(dates[k]))
            clf, held_out = model.train(feats, mining, stable, rule_fired & ~mining)
            proba_k = model.predict(clf, feats)
            del feats
            # 7. accuracy check, on held-out blocks only     (lane D: accuracy)
            sc = accuracy.evaluate(held_out["truth"], rule_k_fired, proba_k >= C.PROB_THRESHOLD,
                                   where=held_out["mask"])
            trained[name] = (clf, extra, proba_k, sc)
            p, r = sc["model"]["precision"] or 0, sc["model"]["recall"] or 0
            f1[name] = 2 * p * r / (p + r) if p + r else 0.0
            _log(f"model [{name}]: precision {p:.2f}, recall {r:.2f}")
        best = max(f1, key=f1.get)
        clf, extra, proba_k, sc = trained[best]
        proba = proba_k if k == len(scenes) - 1 else model.predict(
            clf, model.features(first, last, min_later, slope, cover, extra and extra(dates[-1])))
        model_fired = proba >= C.PROB_THRESHOLD
        scores.update(held_out=sc, label_date=dates[k], held_out_pixels=int(held_out["mask"].sum()),
                      model_used=best, variants={n: t[3]["model"] for n, t in trained.items()})
    else:
        _log("no labels (mining2019 or amw_year): model skipped, rule detector only")
    points = accuracy.eye_points(profile)
    if points is not None and len(points):
        scores["eye_points"] = accuracy.evaluate_points(points, rule_fired, model_fired)
        scores["eye_points_n"] = int(len(points))

    # 4. combine into confidence                         (lane B: combine)
    # The model recognises mining land, old or new. Alerts are about change, so a model-only pixel
    # counts only where the radar also changed a little (C.MODEL_CHANGE_DB) or is water now.
    model_changed = model_fired & (((first - last) >= C.MODEL_CHANGE_DB) | (last < C.WATER_DB))
    conf = combine.confidence(rule_fired, model_changed)

    # Change detection graded on new mining only: Amazon Mining Watch years after the first scene.
    # (Its first year, 2018, also holds everything mined before monitoring began, so it is left out.)
    if "amw_year" in layers and held_out is not None:
        amw = layers["amw_year"]
        first_year = max(int(dates[0][:4]) + 1, int(amw[amw > 0].min()) + 1)
        new = (amw >= first_year) & (amw <= int(dates[-1][:4]))
        never = (amw == 0) | (amw > int(dates[-1][:4]))
        where = held_out["mask"] & (new | never)
        scores["new_mining"] = accuracy.evaluate(new, rule_fired, model_changed, where=where)
        scores["new_mining_years"] = f"{first_year}-{dates[-1][:4]}"
        _log("new mining %s: rule precision %.2f recall %.2f, combined precision %.2f recall %.2f" % (
            scores["new_mining_years"], scores["new_mining"]["rule"]["precision"] or 0,
            scores["new_mining"]["rule"]["recall"] or 0, scores["new_mining"]["combined"]["precision"] or 0,
            scores["new_mining"]["combined"]["recall"] or 0))

        # Every model side by side against Amazon Mining Watch, on the same held-out blocks.
        outputs = {"Rule-based detector": rule_fired}
        for name, (_, _, proba_v, _) in trained.items():
            outputs[f"Random forest ({name})"] = proba_v >= C.PROB_THRESHOLD
        outputs["Alerts map (rule + chosen random forest)"] = conf > 0
        mined = (amw > 0) & (amw <= int(dates[-1][:4]))
        ha = C.RES * C.RES / 10_000
        rows = []
        for name, fired in outputs.items():
            all_sc = accuracy.score(held_out["truth"], fired, where=held_out["mask"])
            new_sc = accuracy.score(new, fired, where=where)
            rows.append({
                "model": name,
                "all_mining_precision": all_sc["precision"], "all_mining_recall": all_sc["recall"],
                "new_mining_precision": new_sc["precision"], "new_mining_recall": new_sc["recall"],
                "flagged_ha": round(float(fired.sum()) * ha),
                "share_inside_amw_mines": round(float((fired & mined).sum()) / max(float(fired.sum()), 1), 3),
            })
        comp = pd.DataFrame(rows)
        C.OUT.mkdir(parents=True, exist_ok=True)
        comp.to_csv(C.OUT / "comparison_amw.csv", index=False)
        scores["comparison"] = rows
        _log("comparison with Amazon Mining Watch (held-out blocks):\n"
             + comp.round(2).to_string(index=False))

        # Every model at each point checked by eye (data/helpers/check_points.csv, from KMZ pins)
        if points is not None and len(points):
            from scipy import ndimage
            r, c = points["row"].to_numpy(), points["col"].to_numpy()
            res = points[["name", "lon", "lat", "mining"]].copy()
            res["radar_db_" + dates[0]] = np.round(first[r, c], 1)
            res["radar_db_" + dates[-1]] = np.round(last[r, c], 1)
            for name, fired in outputs.items():
                res[name] = (ndimage.maximum_filter(fired.astype("uint8"), size=2 * C.CHECK_POINT_RADIUS_PX + 1) > 0)[r, c]
            res["Amazon Mining Watch year"] = amw[r, c].astype(int)
            if "hansen_lossyear" in layers:
                ly = layers["hansen_lossyear"][r, c].astype(int)
                res["Hansen forest loss year"] = np.where(ly > 0, ly + 2000, 0)
            res.to_csv(C.OUT / "check_points_result.csv", index=False)
            _log("models at the points checked by eye:\n" + res.T.to_string(header=False))

    # 5. alert patches, priority, export files           (lane B: alerts)
    C.OUT.mkdir(parents=True, exist_ok=True)
    table = alerts.build(conf, change_idx, dates, first, last, layers, profile)
    alerts.export(table, C.OUT)
    rio.write(C.OUT / "confidence.tif", conf, profile)   # 0 none, 1 medium, 2 high (for QGIS)
    if held_out is not None:
        rio.write(C.OUT / "model_proba.tif", proba.astype("float32"), profile)   # random forest, probability of mining
    _log(f"{len(table)} alerts")

    # 6. crackdown table                                 (lane B: crackdown)
    crackdown.table(conf, change_idx, dates, profile).to_csv(C.OUT / "crackdown.csv", index=False)
    if "amw_year" in layers:
        crackdown.amw_table(layers["amw_year"], profile).to_csv(C.OUT / "crackdown_amw.csv", index=False)

    (C.OUT / "accuracy.json").write_text(json.dumps(scores, indent=1), encoding="utf8")

    # 8. PNG overlays for the web page                   (lane C)
    webout.write(scenes, conf, profile, dates)
    _log(f"done, files in {C.OUT}")
    return table


if __name__ == "__main__":
    run()
