"""
Node 1 — Adaptive WSI Tiling
Reads the SVS whole-slide image and extracts tissue-containing 512x512 patches.
Input  state keys: svs_path, patch_size (opt), tissue_threshold (opt), max_tiles (opt)
Output state keys: tiles, n_tiles, wsi_dims, patch_size, svs_path
"""

def process(state, params=None):
    import os, sys, numpy as np

    svs_path          = state.get("svs_path", "")
    patch_size        = int(state.get("patch_size", 512))
    tissue_threshold  = float(state.get("tissue_threshold", 0.40))
    max_tiles         = int(state.get("max_tiles", 400))

    # ── locate SVS ─────────────────────────────────────────────────────────
    if not svs_path or not os.path.exists(svs_path):
        # Try SVS_PATH env var, then TCGA_test/ relative to this file
        _svs_fname = ("TCGA-HZ-7926-01Z-00-DX1."
                      "b3bf02d3-bad0-4451-9c39-b0593f19154c.svs")
        default = os.environ.get(
            "SVS_PATH",
            os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         "TCGA_test", _svs_fname),
        )
        if os.path.exists(default):
            svs_path = default
            print(f"Using default TCGA-PAAD sample: {os.path.basename(svs_path)}")
        else:
            print("SVS file not found — running in demo mode.")
            rng = np.random.default_rng(0)
            tiles = [
                {"x": int(x), "y": int(y),
                 "tissue_fraction": float(rng.uniform(0.5, 1.0))}
                for y in range(0, 15243, patch_size)
                for x in range(0, 15347, patch_size)
                if rng.random() > 0.4
            ][:max_tiles]
            state.update({"tiles": tiles, "n_tiles": len(tiles),
                          "wsi_dims": (15347, 15243),
                          "patch_size": patch_size, "svs_path": ""})
            print(f"Demo: {len(tiles)} synthetic tiles")
            return state

    # ── real SVS path ───────────────────────────────────────────────────────
    import openslide

    slide = openslide.OpenSlide(svs_path)
    w, h  = slide.dimensions
    print(f"WSI: {os.path.basename(svs_path)}")
    print(f"Dimensions: {w} x {h} px  |  {slide.level_count} pyramid levels")

    # Tissue detection on lowest-resolution level
    detect_level = slide.level_count - 1
    scale        = slide.level_downsamples[detect_level]
    dim          = slide.level_dimensions[detect_level]
    thumb_arr    = np.array(slide.read_region((0, 0), detect_level, dim).convert("RGB"),
                            dtype=np.float32)

    gray = thumb_arr.mean(axis=2)
    sat  = ((thumb_arr.max(axis=2) - thumb_arr.min(axis=2)) /
            (thumb_arr.max(axis=2) + 1e-6))
    tissue_mask = (gray < 220) & (sat > 0.05)

    # Tile extraction
    tiles = []
    for y in range(0, h - patch_size, patch_size):
        for x in range(0, w - patch_size, patch_size):
            tx, ty = int(x / scale), int(y / scale)
            tw, th = max(1, int(patch_size / scale)), max(1, int(patch_size / scale))
            if ty + th > tissue_mask.shape[0] or tx + tw > tissue_mask.shape[1]:
                continue
            frac = float(tissue_mask[ty:ty+th, tx:tx+tw].mean())
            if frac >= tissue_threshold:
                tiles.append({"x": x, "y": y, "tissue_fraction": round(frac, 4)})

    slide.close()

    tiles.sort(key=lambda t: t["tissue_fraction"], reverse=True)
    tiles = tiles[:max_tiles]

    state.update({
        "tiles":      tiles,
        "n_tiles":    len(tiles),
        "wsi_dims":   (w, h),
        "patch_size": patch_size,
        "svs_path":   svs_path,
    })

    total_px = w * h
    covered  = len(tiles) * patch_size ** 2
    print(f"Extracted {len(tiles)} tissue tiles (threshold >= {tissue_threshold})")
    print(f"Coverage : {covered / total_px * 100:.1f}% of WSI area")
    print(f"Patch size: {patch_size}x{patch_size} px")
    return state
