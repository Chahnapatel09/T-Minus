"""Lane D. Accuracy check. Never graded on the pixels the model was trained on."""
from . import config as C


def score(truth, fired):
    """Hits, misses, false alarms, precision, recall."""
    raise NotImplementedError


def evaluate(truth, rule_fired, model_fired):
    """Scores for rule only, model only and combined."""
    raise NotImplementedError


def eye_points(profile):
    """Load data/helpers/check_points.csv (lon, lat, mining): the ~60 points checked by eye."""
    raise NotImplementedError
