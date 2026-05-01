"""
svs_utils.py - SVS whole-slide image utilities for LangGraph computational pathology pipeline.
Handles thumbnail generation, tissue detection, and patch extraction for TCGA-PAAD WSIs.
"""

import os
import io
import numpy as np
from pathlib import Path


def get_slide_info(svs_path: str) -> dict:
    """Return basic metadata from an SVS file."""
    import openslide
    slide = openslide.OpenSlide(svs_path)
    info = {
        "path": svs_path,
        "filename": os.path.basename(svs_path),
        "dimensions": slide.dimensions,
        "level_count": slide.level_count,
        "level_dimensions": slide.level_dimensions,
        "level_downsamples": [float(d) for d in slide.level_downsamples],
        "properties": {k: v for k, v in slide.properties.items()
                       if k in ("openslide.mpp-x", "openslide.mpp-y",
                                "aperio.AppMag", "aperio.Date")},
    }
    slide.close()
    return info


def get_thumbnail_bytes(svs_path: str, max_size: int = 1024) -> bytes:
    """Return a JPEG thumbnail of the WSI as bytes."""
    import openslide
    from PIL import Image

    slide = openslide.OpenSlide(svs_path)
    w, h = slide.dimensions
    scale = max_size / max(w, h)
    thumb_w, thumb_h = int(w * scale), int(h * scale)
    thumb = slide.get_thumbnail((thumb_w, thumb_h))
    slide.close()

    buf = io.BytesIO()
    thumb.convert("RGB").save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf.read()


def detect_tissue_mask(svs_path: str, level: int = 2) -> tuple:
    """
    Return (tissue_mask, scale) where tissue_mask is a boolean array at the
    given pyramid level and scale is the downsample factor used.
    """
    import openslide
    from PIL import Image

    slide = openslide.OpenSlide(svs_path)
    level = min(level, slide.level_count - 1)
    scale = slide.level_downsamples[level]
    dim = slide.level_dimensions[level]
    region = slide.read_region((0, 0), level, dim)
    slide.close()

    arr = np.array(region.convert("RGB"), dtype=np.float32)
    # Otsu-like tissue threshold in grayscale
    gray = arr.mean(axis=2)
    # Background = bright (>220) and low saturation
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    sat = (arr.max(axis=2) - arr.min(axis=2)) / (arr.max(axis=2) + 1e-6)
    tissue_mask = (gray < 220) & (sat > 0.05)
    return tissue_mask, float(scale)


def extract_tissue_tiles(svs_path: str, patch_size: int = 512,
                          tissue_threshold: float = 0.4,
                          max_tiles: int = 500) -> list:
    """
    Extract coordinates of tissue-containing tiles from an SVS file.
    Returns list of dicts: {x, y, tissue_fraction}.
    """
    import openslide

    tissue_mask, scale = detect_tissue_mask(svs_path, level=2)
    slide = openslide.OpenSlide(svs_path)
    w, h = slide.dimensions
    slide.close()

    tiles = []
    step = patch_size
    for y in range(0, h - patch_size, step):
        for x in range(0, w - patch_size, step):
            tx = int(x / scale)
            ty = int(y / scale)
            tw = max(1, int(patch_size / scale))
            th = max(1, int(patch_size / scale))
            if ty + th > tissue_mask.shape[0] or tx + tw > tissue_mask.shape[1]:
                continue
            region = tissue_mask[ty:ty + th, tx:tx + tw]
            frac = float(region.mean())
            if frac >= tissue_threshold:
                tiles.append({"x": x, "y": y, "tissue_fraction": round(frac, 4)})

    # Sort by tissue fraction descending and cap
    tiles.sort(key=lambda t: t["tissue_fraction"], reverse=True)
    return tiles[:max_tiles]


def read_patch_rgb(svs_path: str, x: int, y: int,
                   patch_size: int = 512) -> np.ndarray:
    """Read a single RGB patch from the WSI at level 0."""
    import openslide

    slide = openslide.OpenSlide(svs_path)
    region = slide.read_region((x, y), 0, (patch_size, patch_size))
    slide.close()
    return np.array(region.convert("RGB"), dtype=np.uint8)


def patch_to_jpeg_bytes(rgb_array: np.ndarray, quality: int = 85) -> bytes:
    """Convert an RGB numpy array to JPEG bytes."""
    from PIL import Image

    buf = io.BytesIO()
    Image.fromarray(rgb_array).save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return buf.read()
