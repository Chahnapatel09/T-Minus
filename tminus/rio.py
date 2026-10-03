"""Lane A. Raster reading/writing and the one shared grid."""
from . import config as C


def target_profile():
    """The analysis grid as a rasterio profile: C.AOI in C.CRS at C.RES metres."""
    raise NotImplementedError


def read(path):
    """Return (array, profile) for band 1 of a GeoTIFF."""
    raise NotImplementedError


def write(path, arr, profile):
    """Write a single-band GeoTIFF."""
    raise NotImplementedError


def warp_to_grid(src_path, dst_path, resampling="bilinear"):
    """Put any raster on the analysis grid. Use 'nearest' for class maps and masks."""
    raise NotImplementedError


def scenes():
    """[(YYYYMMDD, path), ...] for data/processed/sigma0_*.tif, oldest first."""
    raise NotImplementedError


def helper(name, profile):
    """Read data/helpers/<name>.tif."""
    raise NotImplementedError
