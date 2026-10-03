"""Lane A. Put SNAP outputs and helper maps on the shared grid.

SNAP chain before this: subset, calibrate to sigma0, multilook to ~10 m, Refined Lee,
Range-Doppler terrain correction, convert to dB, export GeoTIFF.
"""
from . import config as C
from . import rio


def scene(src, date):
    """SNAP GeoTIFF -> data/processed/sigma0_<date>.tif on the grid."""
    raise NotImplementedError


def raster(name, src):
    """Helper raster (WorldCover, Hansen, slope) -> data/helpers/<name>.tif on the grid."""
    raise NotImplementedError


def vector(name, src):
    """Polygons -> 0/1 mask on the grid (mining2019, buffer, indigenous, la_pampa)."""
    raise NotImplementedError


def dist(name, src):
    """Lines -> distance-in-metres raster on the grid (dist_road, dist_river)."""
    raise NotImplementedError
