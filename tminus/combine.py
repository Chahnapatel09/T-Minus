"""Lane B. Merge the two detectors into one confidence map."""
import numpy as np

NONE, MEDIUM, HIGH = 0, 1, 2


def confidence(rule_fired, model_fired):
    """High when both agree, medium when only one fires. Returns uint8 0/1/2."""
    rule = np.asarray(rule_fired).astype(bool)
    model = np.asarray(model_fired).astype(bool)
    return (rule.astype("uint8") + model.astype("uint8")).astype("uint8")
