"""Lane B. Turn the confidence map into ranked alert patches and export files."""
from . import config as C


def build(conf, change_idx, dates, first, last, layers, profile):
    """One row per patch of C.MIN_PATCH_HA or more.

    Columns: id, area_ha, first_seen, type (pond / bare sand or tailings / fresh clearing),
    confidence, in_buffer, in_indigenous, dist_road_m, dist_river_m, priority, lon, lat, maps_url.
    """
    raise NotImplementedError


def priority(alert):
    """Score from size, growth, reserve buffer or Indigenous land, distance to road or river."""
    raise NotImplementedError


def export(alerts, folder):
    """Write alerts.geojson, alerts.csv, alerts.kml."""
    raise NotImplementedError
