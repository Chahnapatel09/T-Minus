"""End to end: scenes on the grid -> detectors -> confidence -> alerts -> files for the web page.

  python -m tminus.pipeline

Reads  data/processed/sigma0_YYYYMMDD.tif and data/helpers/*.tif
Writes outputs/
"""
import json

import numpy as np

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
    conf = combine.confidence(rule_fired, model_fired)

    # 5. alert patches, priority, export files           (lane B: alerts)
    C.OUT.mkdir(parents=True, exist_ok=True)
    table = alerts.build(conf, change_idx, dates, first, last, layers, profile)
    alerts.export(table, C.OUT)
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
