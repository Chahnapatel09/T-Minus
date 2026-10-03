"""Lane B. Merge the two detectors into one confidence map."""

NONE, MEDIUM, HIGH = 0, 1, 2


def confidence(rule_fired, model_fired):
    """High when both agree, medium when only one fires. Returns uint8 0/1/2."""
    raise NotImplementedError
