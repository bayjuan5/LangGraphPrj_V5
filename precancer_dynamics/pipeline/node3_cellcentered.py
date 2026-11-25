#!/usr/bin/env python3
"""
Node3 (cell-centred): ROSIE inference with one 128x128 H&E window per detected cell.

ROSIE predicts the mean expression of the central 8x8 pixels of a 128x128 H&E patch
(Wu et al., Nat Commun 2025). Instead of sliding over every 1024x1024 tile with stride 8
and zero-padding windows at tile borders, this script reads each window directly from the
whole-slide image, centred on the cell found by Node2. Every cell therefore gets full tissue
context, including cells within 64 px of a tile edge.

Model, preprocessing (ToTensor -> bilinear antialiased resize to 224 -> ImageNet
normalisation), channel order and the provisional phenotype rule are identical to
node3_standalone_OFFICIAL.py, and the output JSON has the same format.

Usage (run from the slide folder, e.g. M4/):
    python node3_cellcentered.py --svs High_M4_366852.svs
"""
import argparse, json, os, re, sys, time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import numpy as np
import openslide
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models

PATCH = 128            # ROSIE input size (fixed)
HALF = PATCH // 2
TILE = 1024            # Node1 tile size
MARGIN = HALF          # context read around each tile
AREA_MIN, AREA_MAX = 20, 1000   # nucleus-sized objects (px at 0.5027 um/px); others are flagged, not dropped

ML_CHANNELS = ["DAPI", "CD45", "CD68", "CD14", "PD1", "FoxP3", "CD8", "HLA-DR", "PanCK", "CD3e",
               "CD4", "aSMA", "CD31", "Vimentin", "CD45RO", "Ki67", "CD20", "CD11c", "Podoplanin", "PDL1",
               "GranzymeB", "CD38", "CD141", "CD21", "CD163", "BCL2", "LAG3", "EpCAM", "CD44", "ICOS",
               "GATA3", "Gal3", "CD39", "CD34", "TIGIT", "ECad", "CD40", "VISTA", "HLA-A", "MPO",
               "PCNA", "ATM", "TP63", "IFNg", "Keratin8/18", "IDO1", "CD79a", "HLA-E", "CollagenIV", "CD66"]

CELL_CLASSIFICATION_THRESHOLD = 0.2
MIN_POS_PROPORTION_V9 = 0.45
MIN_CLASSIFICATION_SCORE_V9 = 0.05

CLASSIFICATION_RULES = {
    "Treg": {"pos": ["CD45", "CD3e", "CD4", "FoxP3"], "neg": ["CD8", "CD20", "CD68", "PanCK"]},
    "CD8+ T Cell": {"pos": ["CD45", "CD3e", "CD8"], "neg": ["CD4", "FoxP3", "CD20", "CD68", "PanCK"]},
    "CD4+ T Cell": {"pos": ["CD45", "CD3e", "CD4"], "neg": ["CD8", "FoxP3", "CD20", "CD68", "PanCK"]},
    "B Cell": {"pos": ["CD45", "CD20"], "neg": ["CD3e", "CD68", "CD163", "CD66", "CD11c", "PanCK"]},
    "NK Cell": {"pos": ["CD45"], "neg": ["CD3e", "CD20", "CD68", "CD163", "CD66", "CD11c", "PanCK", "CD31"]},
    "Neutrophil": {"pos": ["CD45", "CD66"], "neg": ["CD3e", "CD20", "CD68", "CD163", "CD11c", "PanCK"]},
    "Macrophage (CD163+)": {"pos": ["CD45", "CD163"], "neg": ["CD3e", "CD20", "CD66", "CD11c", "PanCK"]},
    "Myeloid Cell (CD68+)": {"pos": ["CD45", "CD68"], "neg": ["CD3e", "CD20", "CD66", "CD163", "CD11c", "PanCK"]},
    "Dendritic Cell": {"pos": ["CD45", "CD11c"], "neg": ["CD3e", "CD20", "CD66", "CD68", "CD163", "PanCK"]},
    "Monocyte/MDSC-like": {"pos": ["CD45", "CD68"], "neg": ["CD3e", "CD20", "CD31", "PanCK", "Vimentin"]},
    "Epithelial Cell": {"pos": ["PanCK"], "neg": ["CD45", "Vimentin"]},
    "Fibroblast": {"pos": ["Vimentin"], "neg": ["CD45", "PanCK"]},
    "Endothelial Cell": {"pos": ["CD31"], "neg": ["CD45", "PanCK", "Vimentin"]},
    "Non_Immune_Unspec": {"pos": [], "neg": ["CD45", "PanCK", "Vimentin", "CD31"]},
    "Background/Junk": {"pos": [], "neg": ["CD45", "PanCK", "Vimentin", "CD31"]}
}


def fuzzy_classify_primary_label(cell: Dict[str, Any]) -> str:
    signals = cell.get("Signals", {})
    best_relative_score = float('-inf')
    best_type = "Unclassified_By_New_Rules"

    for cell_type, rule in CLASSIFICATION_RULES.items():
        required_pos = rule["pos"]
        pos_count = sum(1 for marker in required_pos if signals.get(marker, 0) > CELL_CLASSIFICATION_THRESHOLD)
        neg_count = sum(1 for marker in rule["neg"] if signals.get(marker, 0) > CELL_CLASSIFICATION_THRESHOLD)

        if required_pos:
            pos_proportion = pos_count / len(required_pos)
            if pos_proportion >= MIN_POS_PROPORTION_V9:
                current_score = pos_proportion - (neg_count * 0.2)
            else:
                current_score = float('-inf')
        else:
            if all(signals.get(marker, 0) <= CELL_CLASSIFICATION_THRESHOLD for marker in rule["neg"]):
                current_score = 1.0
            else:
                current_score = -1.0

        if current_score > best_relative_score:
            best_relative_score = current_score
            best_type = cell_type

    return best_type if best_relative_score >= MIN_CLASSIFICATION_SCORE_V9 else "Unclassified_By_New_Rules"



def get_model(num_outputs: int) -> nn.Module:
    model = models.convnext_small(weights=None)
    model.classifier[2] = nn.Linear(model.classifier[2].in_features, num_outputs)
    return model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--svs", required=True)
    ap.add_argument("--node2", default="Node2_out")
    ap.add_argument("--out", default="Node3_cell_out")
    ap.add_argument("--model", default="../best_model_single.pth")
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--max_tiles", type=int, default=0, help="process only the first N tiles (testing)")
    a = ap.parse_args()

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {dev}" + (f" ({torch.cuda.get_device_name(0)})" if dev.type == "cuda" else " -- WARNING: CPU is very slow"))
    model = get_model(len(ML_CHANNELS))
    ck = torch.load(a.model, map_location=dev, weights_only=False)
    sd = ck["model_state_dict"]
    # checkpoint was saved from nn.DataParallel -> keys start with "module."
    sd = {(k[7:] if k.startswith("module.") else k): v for k, v in sd.items()}
    model.load_state_dict(sd)
    model = model.to(dev).eval()
    print(f"model: {a.model} ({os.path.getsize(a.model) / 2**20:.1f} MB)")
    mean = torch.tensor([0.485, 0.456, 0.406], device=dev).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225], device=dev).view(1, 3, 1, 1)

    slide = openslide.OpenSlide(a.svs)
    tiles = json.load(open(Path(a.node2) / "node2_output.json"))["tiles"]
    if a.max_tiles:
        tiles = tiles[:a.max_tiles]
    out = Path(a.out) / "phenotypes"
    out.mkdir(parents=True, exist_ok=True)
    print(f"slide: {a.svs} | tiles: {len(tiles)} | output: {out}")

    t0, n_cells, n_done, n_flag = time.time(), 0, 0, 0
    for k, tile in enumerate(tiles, 1):
        stem = Path(str(tile.get("png_path") or tile["patch_name"]).replace("\\", "/")).stem
        dst = out / f"{stem}_phenotypes.json"
        if dst.exists():
            continue
        m = re.search(r"_x(\d+)_y(\d+)$", stem)
        if not m:
            print(f"  cannot parse tile origin from {stem}, skipped"); continue
        tx, ty = int(m.group(1)), int(m.group(2))
        cj = Path(a.node2) / "cell_coordinates" / f"{stem}_cells.json"
        cells = json.load(open(cj)).get("cells", []) if cj.exists() else []

        # tile plus a 64-px margin, composited on white outside the slide
        rgba = np.asarray(slide.read_region((tx - MARGIN, ty - MARGIN), 0, (TILE + 2 * MARGIN,) * 2), dtype=np.float32)
        alpha = rgba[..., 3:4] / 255.0
        region = (rgba[..., :3] * alpha + 255.0 * (1 - alpha)).round().astype(np.uint8)

        xs = np.clip(np.array([int(c.get("x", 0)) for c in cells], dtype=int), 0, TILE - 1)
        ys = np.clip(np.array([int(c.get("y", 0)) for c in cells], dtype=int), 0, TILE - 1)
        preds = np.zeros((len(cells), len(ML_CHANNELS)), dtype=np.float32)
        for s in range(0, len(cells), a.batch):
            # window rows [y, y+128) in region coordinates == [y-64, y+64) in tile coordinates
            win = np.stack([region[y:y + PATCH, x:x + PATCH] for x, y in zip(xs[s:s + a.batch], ys[s:s + a.batch])])
            b = torch.from_numpy(win).to(dev).permute(0, 3, 1, 2).float() / 255.0
            b = F.interpolate(b, size=(224, 224), mode="bilinear", align_corners=False, antialias=True)
            b = (b - mean) / std
            with torch.no_grad():
                preds[s:s + a.batch] = model(b).float().cpu().numpy()

        out_cells, counts = [], {}
        for i, c in enumerate(cells):
            area = int(c.get("area", 0))
            cell = {"CellID": c.get("CellID", f"cell_{i}"), "x": int(xs[i]), "y": int(ys[i]),
                    "area": area, "area_ok": bool(AREA_MIN <= area <= AREA_MAX),
                    "Signals": {ch: float(preds[i, j]) for j, ch in enumerate(ML_CHANNELS)}}
            n_flag += not cell["area_ok"]
            cell["Phenotype"] = fuzzy_classify_primary_label(cell)
            counts[cell["Phenotype"]] = counts.get(cell["Phenotype"], 0) + 1
            out_cells.append(cell)
        json.dump({"tile_name": stem, "timestamp": datetime.now().isoformat(), "method": "cell_centred_128",
                   "tile_origin": [tx, ty], "total_cells": len(out_cells), "cells": out_cells,
                   "phenotype_counts": counts}, open(dst, "w"))
        n_cells += len(cells); n_done += 1
        if n_done % 20 == 0 or k == len(tiles):
            el = time.time() - t0
            print(f"  [{k}/{len(tiles)}] {n_cells:,} cells in {el/60:.1f} min ({n_cells/max(el,1e-9):.0f} cells/s); "
                  f"outside {AREA_MIN}-{AREA_MAX} px: {n_flag:,} ({100*n_flag/max(n_cells,1):.1f}%)", flush=True)
    print(f"done: {n_done} tiles, {n_cells:,} cells ({n_flag:,} flagged area_ok=False), {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
