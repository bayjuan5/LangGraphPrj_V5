#!/usr/bin/env python3
"""
Node2 (StarDist): nucleus detection with the pretrained StarDist '2D_versatile_he' model. Uses the
same 1024x1024 level-0 tile grid as Node1 and Node1's is_background_patch with its four basic thresholds
(white > 85%, tissue < 15%, tissue s.d. < 10; NOT the corner-confinement and grey-level-span rules that
Node1 also applies), and writes the same per-tile JSON format, so node3_cellcentered.py runs on it unchanged.

--scale 2 upsamples each tile 2x (bilinear) before detection and divides coordinates back; the pretrained
model expects ~40x human nuclei (25-40 px), while mouse nuclei at 0.5 um/px are 10-12 px and are under-detected
at native scale. Area is reported in level-0 pixels (divided by scale^2).

    python node2_stardist.py --svs High_M4_366852.svs --scale 2 --out Node2_stardist2x_out
    python node3_cellcentered.py --svs High_M4_366852.svs --node2 Node2_stardist2x_out --out Node3_cell_stardist2x_out
"""
import argparse, importlib.util, json, os, time
from pathlib import Path
import numpy as np
import openslide
from skimage.measure import regionprops

TILE = 1024
BG = dict(threshold=235, max_white_ratio=0.85, std_threshold=10.0, min_tissue_ratio=0.15)   # Node1 settings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--svs", required=True)
    ap.add_argument("--node1", default="Node1.py", help="Node1 script providing is_background_patch")
    ap.add_argument("--out", default="Node2_stardist_out")
    ap.add_argument("--threads", type=int, default=0, help="TensorFlow intra-op threads (0 = all cores)")
    ap.add_argument("--max_tiles", type=int, default=0, help="stop after N kept tiles (testing)")
    ap.add_argument("--scale", type=int, default=1, help="upsample factor before detection (2 for 20x mouse slides)")
    ap.add_argument("--prob", type=float, default=None, help="probability threshold (default: model's 0.69)")
    a = ap.parse_args()

    spec = importlib.util.spec_from_file_location("node1", a.node1)
    node1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(node1)
    is_bg = node1.is_background_patch

    import tensorflow as tf
    if a.threads:
        tf.config.threading.set_intra_op_parallelism_threads(a.threads)
    from csbdeep.utils import normalize
    from stardist.models import StarDist2D
    from PIL import Image
    model = StarDist2D.from_pretrained("2D_versatile_he")
    sc = a.scale
    pkw = {"n_tiles": (2 * sc, 2 * sc, 1)}
    if a.prob is not None:
        pkw["prob_thresh"] = a.prob

    slide = openslide.OpenSlide(a.svs)
    W, H = slide.dimensions
    out = Path(a.out); cdir = out / "cell_coordinates"; cdir.mkdir(parents=True, exist_ok=True)
    tiles, kept, skipped, ncell, t0 = [], 0, 0, 0, time.time()
    print(f"slide {a.svs}: {W}x{H}, grid {W // TILE} x {H // TILE}", flush=True)
    for r in range(H // TILE):
        for c in range(W // TILE):
            x, y = c * TILE, r * TILE
            stem = f"tile_x{x:06d}_y{y:06d}"
            cj = cdir / f"{stem}_cells.json"
            if cj.exists():                                     # resume
                n = len(json.load(open(cj))["cells"])
            else:
                rgb = slide.read_region((x, y), 0, (TILE, TILE)).convert("RGB")
                if is_bg(rgb, **BG):
                    skipped += 1
                    continue
                src = rgb if sc == 1 else rgb.resize((TILE * sc, TILE * sc), Image.BILINEAR)
                img = normalize(np.asarray(src), 1, 99.8, axis=(0, 1, 2))
                labels, det = model.predict_instances(img, **pkw)
                cells = []
                for p in regionprops(labels):
                    cy, cx = p.centroid; per = p.perimeter
                    cells.append({"CellID": f"cell_{len(cells)}", "x": int(cx / sc), "y": int(cy / sc),
                                  "area": int(round(p.area / sc ** 2)),
                                  "circularity": float(4 * np.pi * p.area / per ** 2) if per > 0 else 0.0,
                                  "confidence": float(det["prob"][p.label - 1])})
                json.dump({"patch_metadata": {"tile": stem, "origin": [x, y], "cell_count": len(cells),
                                              "method": f"StarDist 2D_versatile_he scale={sc}"
                                              + (f" prob={a.prob}" if a.prob is not None else "")},
                           "cells": cells}, open(cj, "w"))
                n = len(cells)
            tiles.append({"patch_name": f"{stem}.png", "png_path": f"{stem}.png", "cell_count": n,
                          "data_json": str(cj)})
            kept += 1; ncell += n
            if kept % 25 == 0:
                print(f"  {kept} tiles, {ncell:,} nuclei, {(time.time() - t0) / 60:.1f} min", flush=True)
            if a.max_tiles and kept >= a.max_tiles:
                break
        if a.max_tiles and kept >= a.max_tiles:
            break
    json.dump({"node": "Node2_StarDist", "model": "2D_versatile_he", "scale": sc, "prob_thresh": a.prob,
               "total_patches_processed": kept,
               "skipped_background": skipped, "total_cells_detected": ncell, "tiles": tiles},
              open(out / "node2_output.json", "w"), indent=1)
    print(f"done: {kept} tiles kept, {skipped} background, {ncell:,} nuclei, {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
