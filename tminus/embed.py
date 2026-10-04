"""Lane D. Foundation-model features: radar tiles -> embeddings from a pretrained network.

  python -m tminus.embed

Model: ResNet50 pretrained with MoCo on SSL4EO-S12 Sentinel-1 (Wang et al. 2022), weights published
by TorchGeo. It was trained on Sentinel-1 VV/VH in dB. RADARSAT-2 is the same C band, so HH in dB is
standardised with the VV statistics and fed to both input channels.

Each scene in data/processed/ is cut into C.EMB_TILE_PX tiles (640 m at 10 m), every tile becomes a
2048-number embedding, and the result is cached as data/processed/emb_<date>.npz.
change_layers() turns two dates into per-pixel features for the random forest:
  emb_dist   cosine distance between the before and after embeddings (how much the tile changed)
  emb_d1..   change along the main directions of variation (PCA over all tiles and dates)
"""
from pathlib import Path

import numpy as np

from . import config as C
from . import rio

WEIGHTS_URL = ("https://hf.co/torchgeo/resnet50_sentinel1_all_moco/resolve/"
               "e79862c667853c10a709bdd77ea8ffbad0e0f1cf/resnet50_sentinel1_all_moco-906e4356.pth")
VV_MEAN, VV_STD = -12.59, 5.26     # SSL4EO-S12 Sentinel-1 VV statistics, dB
INPUT_PX = 224
BATCH = 32


def _log(msg):
    print(f"[embed] {msg}", flush=True)


def _device():
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_model():
    import torch
    import torchvision

    model = torchvision.models.resnet50()
    model.conv1 = torch.nn.Conv2d(2, 64, kernel_size=7, stride=2, padding=3, bias=False)
    state = torch.hub.load_state_dict_from_url(WEIGHTS_URL, map_location="cpu", progress=False)
    missing = model.load_state_dict(state, strict=False).missing_keys
    if set(missing) - {"fc.weight", "fc.bias"}:
        raise RuntimeError(f"weights did not load: missing {missing}")
    model.fc = torch.nn.Identity()
    return model.eval().to(_device())


def cache_path(date):
    return Path(C.PROCESSED) / f"emb_{date}.npz"


def embed_scene(db, model):
    """(rows, cols, 2048) float16 embeddings of C.EMB_TILE_PX tiles. Tiles that are mostly nodata are NaN."""
    import torch
    import torch.nn.functional as F

    t = C.EMB_TILE_PX
    h, w = db.shape
    nty, ntx = -(-h // t), -(-w // t)
    padded = np.full((nty * t, ntx * t), np.nan, dtype="float32")
    padded[:h, :w] = db
    tiles = padded.reshape(nty, t, ntx, t).swapaxes(1, 2).reshape(-1, t, t)
    valid = np.isfinite(tiles).mean(axis=(1, 2)) >= 0.5
    z = np.nan_to_num((tiles - VV_MEAN) / VV_STD).astype("float32")

    out = np.full((len(tiles), 2048), np.nan, dtype="float16")
    idx = np.flatnonzero(valid)
    device = next(model.parameters()).device
    with torch.inference_mode():
        for n, i in enumerate(range(0, len(idx), BATCH)):
            batch = idx[i:i + BATCH]
            x = torch.from_numpy(z[batch]).unsqueeze(1).repeat(1, 2, 1, 1).to(device)
            x = F.interpolate(x, size=(INPUT_PX, INPUT_PX), mode="bilinear", align_corners=False)
            out[batch] = model(x).float().cpu().numpy().astype("float16")
            if n % 50 == 0:
                _log(f"  {100 * min(i + BATCH, len(idx)) / max(len(idx), 1):.0f}%")
    return out.reshape(nty, ntx, 2048)


def run(force=False):
    """Embed every scene in data/processed/ that has no cached embedding yet."""
    model = None
    for date, path in rio.scenes():
        dst = cache_path(date)
        if dst.exists() and not force:
            continue
        model = model or load_model()
        _log(f"{date}: embedding on {_device()}")
        db, _ = rio.read(path)
        emb = embed_scene(db, model)
        np.savez_compressed(dst, emb=emb, tile=C.EMB_TILE_PX, shape=np.array(db.shape))
        _log(f"{date}: wrote {dst.name}")


def available(dates):
    return all(cache_path(d).exists() for d in dates)


def _load(date):
    with np.load(cache_path(date)) as f:
        if int(f["tile"]) != C.EMB_TILE_PX:
            raise ValueError(f"{cache_path(date).name} uses another tile size, rerun python -m tminus.embed --force")
        return f["emb"].astype("float32")


def _to_pixels(tile_arr, shape):
    """Tile values -> pixels, each pixel taking its tile's value. (Smooth interpolation between tile
    centres was tried: fewer square edges, but lower F1 and agreement with Hansen on La Pampa.)"""
    t = C.EMB_TILE_PX
    return np.repeat(np.repeat(tile_arr, t, axis=0), t, axis=1)[:shape[0], :shape[1]].astype("float32")


def change_layers(before_date, after_date, shape, all_dates=None):
    """Per-pixel embedding-change features between two dates, as {name: (H, W) float32}."""
    from sklearn.decomposition import PCA

    a, b = _load(before_date), _load(after_date)
    pool = [e.reshape(-1, 2048) for e in (_load(d) for d in (all_dates or [before_date, after_date]))]
    pool = np.concatenate(pool)
    pool = pool[np.isfinite(pool).all(axis=1)]
    if len(pool) > 20_000:
        pool = pool[np.random.default_rng(C.SEED).choice(len(pool), 20_000, replace=False)]
    pca = PCA(n_components=C.EMB_COMPONENTS, random_state=C.SEED).fit(pool)

    def project(e):
        flat = e.reshape(-1, 2048)
        ok = np.isfinite(flat).all(axis=1)
        out = np.full((len(flat), C.EMB_COMPONENTS), np.nan, dtype="float32")
        out[ok] = pca.transform(flat[ok])
        return out.reshape(e.shape[0], e.shape[1], -1)

    na = np.linalg.norm(a, axis=-1)
    nb = np.linalg.norm(b, axis=-1)
    cos = (a * b).sum(axis=-1) / np.maximum(na * nb, 1e-6)
    layers = {"emb_dist": _to_pixels(1 - cos, shape)}
    diff = project(b) - project(a)
    for i in range(C.EMB_COMPONENTS):
        layers[f"emb_d{i + 1}"] = _to_pixels(diff[..., i], shape)
    return layers


def scene_layers(date, shape):
    """Single-date features: the scene's embeddings along their main directions, {name: (H, W)}."""
    from sklearn.decomposition import PCA

    e = _load(date)
    flat = e.reshape(-1, 2048)
    ok = np.isfinite(flat).all(axis=1)
    pca = PCA(n_components=C.EMB_COMPONENTS, random_state=C.SEED).fit(flat[ok])
    out = np.full((len(flat), C.EMB_COMPONENTS), np.nan, dtype="float32")
    out[ok] = pca.transform(flat[ok])
    out = out.reshape(e.shape[0], e.shape[1], -1)
    return {f"emb_pc{i + 1}": _to_pixels(out[..., i], shape) for i in range(C.EMB_COMPONENTS)}


if __name__ == "__main__":
    import sys
    run(force="--force" in sys.argv)
