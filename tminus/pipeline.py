"""End to end: scenes on the grid -> detectors -> confidence -> alerts -> files for the web page.

  python -m tminus.pipeline

Reads  data/processed/sigma0_YYYYMMDD.tif and data/helpers/*.tif
Writes outputs/
"""
from . import accuracy, alerts, combine, crackdown, model, rio, rules
from . import config as C


def run():
    # 1. load scenes and helper maps                     (lane A: rio)
    # 2. rule detector on each pair of dates             (lane B: rules)
    # 3. train random forest, predict probability        (lane D: model)
    # 4. combine into confidence                         (lane B: combine)
    # 5. alert patches, priority, export files           (lane B: alerts)
    # 6. crackdown table                                 (lane B: crackdown)
    # 7. accuracy check                                  (lane D: accuracy)
    # 8. PNG overlays for the web page                   (lane C)
    raise NotImplementedError


if __name__ == "__main__":
    run()
