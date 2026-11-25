#!/usr/bin/env python3
"""
Node2 (StarDist): nucleus detection with the pretrained StarDist '2D_versatile_he' model, as an
independent alternative to the watershed Node2. Uses exactly the same 1024x1024 level-0 tile grid
and the same background filter as Node1 (is_background_patch imported from Node1.py), and writes
the same per-tile JSON format, so node3_cellcentered.py can run on it unchanged:

    python node2_stardist.py --svs High_M4_366852.svs          # -> Node2_stardist_out/
    python node3_cellcentered.py --svs High_M4_366852.svs --node2 Node2_stardist_out --out Node3_cell_stardist_out
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
    a = ap.parse_args()

    spec = importlib.util.spec_from_file_location("node1", a.node1)
    node1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(node1)
    is_bg = node1.is_background_patch

    import tensorflow as tf
    if a.threads:
        tf.config.threading.set_intra_op_parallelism_threads(a.threads)
    from csbdeep.utils import normalize
    from stardist.models import StarDist2D
    model = StarDist2D.from_pretrained("2D_versatile_he")

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
                img = normalize(np.asarray(rgb), 1, 99.8, axis=(0, 1, 2))
                labels, det = model.predict_instances(img)
                cells = []
                for p in regionprops(labels):
                    cy, cx = p.centroid; per = p.perimeter
                    cells.append({"CellID": f"cell_{len(cells)}", "x": int(cx), "y": int(cy), "area": int(p.area),
                                  "circularity": float(4 * np.pi * p.area / per ** 2) if per > 0 else 0.0,
                                  "confidence": float(det["prob"][p.label - 1])})
                json.dump({"patch_metadata": {"tile": stem, "origin": [x, y], "cell_count": len(cells),
                                              "method": "StarDist 2D_versatile_he"}, "cells": cells}, open(cj, "w"))
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
    json.dump({"node": "Node2_StarDist", "model": "2D_versatile_he", "total_patches_processed": kept,
               "skipped_background": skipped, "total_cells_detected": ncell, "tiles": tiles},
              open(out / "node2_output.json", "w"), indent=1)
    print(f"done: {kept} tiles kept, {skipped} background, {ncell:,} nuclei, {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
