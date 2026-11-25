#!/usr/bin/env python3
"""
Node3 Standalone - OFFICIAL METHOD with BATCH PROCESSING
Based on official evaluate.py with weighted Gaussian blending
This is the MOST ACCURATE method but slower than spatial upsampling

BATCH PROCESSING:
- Edit batch_config.py to set START_TILE and END_TILE
- Run multiple times with different ranges to process all tiles
- Progress is automatically tracked
"""

import os
import json
import torch
import torch.nn as nn
import numpy as np
import tifffile
from pathlib import Path
from PIL import Image
from torchvision import transforms, models
from datetime import datetime
from typing import Dict, Any, Optional
from scipy.ndimage import gaussian_filter
import matplotlib

# Import batch configuration
try:
    from batch_config import START_TILE, END_TILE, STRIDE_SIZE, BATCH_SIZE, SAVE_TIFF, PROGRESS_FILE, config_info
    BATCH_MODE = True
    print(f"✓ Batch configuration loaded: tiles {START_TILE}-{END_TILE-1}")
except ImportError:
    # Fallback to default settings if batch_config.py not found
    START_TILE = 0
    END_TILE = None  # Process all tiles
    STRIDE_SIZE = 8
    BATCH_SIZE = 32
    SAVE_TIFF = False
    PROGRESS_FILE = "node3_progress.json"
    BATCH_MODE = False
    config_info = None
    print("⚠ batch_config.py not found, using default settings")

matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd

print("=" * 70)
print("NODE3 STANDALONE - OFFICIAL EVALUATE.PY METHOD")
print("Using sliding window + Gaussian weighted blending")
print("=" * 70)

# Fix PyTorch 2.6+ loading security restrictions
import torch.serialization
try:
    # Try new numpy API first
    torch.serialization.add_safe_globals([np.core.multiarray.scalar])
except AttributeError:
    # Fallback for older numpy versions
    pass

ML_CHANNELS = ["DAPI", "CD45", "CD68", "CD14", "PD1", "FoxP3", "CD8", "HLA-DR", "PanCK", "CD3e",
               "CD4", "aSMA", "CD31", "Vimentin", "CD45RO", "Ki67", "CD20", "CD11c", "Podoplanin", "PDL1",
               "GranzymeB", "CD38", "CD141", "CD21", "CD163", "BCL2", "LAG3", "EpCAM", "CD44", "ICOS",
               "GATA3", "Gal3", "CD39", "CD34", "TIGIT", "ECad", "CD40", "VISTA", "HLA-A", "MPO",
               "PCNA", "ATM", "TP63", "IFNg", "Keratin8/18", "IDO1", "CD79a", "HLA-E", "CollagenIV", "CD66"]

# Color mapping for biomarkers (for visualization)
TARGET_CHANNEL_COLORS = {
    "PDL1": [1.0, 0.0, 0.0],  # Red
    "CD8": [0.0, 0.5, 0.0],  # Dark Green
    "CD163": [0.0, 0.0, 1.0],  # Blue
    "PanCK": [0.0, 1.0, 1.0],  # Cyan
    "EpCAM": [1.0, 0.0, 1.0],  # Magenta
    "Ki67": [1.0, 1.0, 0.0],  # Yellow
    "CD4": [1.0, 0.5, 0.0],  # Orange
    "FoxP3": [0.0, 0.0, 0.0],  # Black
    "CD31": [0.5, 0.5, 0.5],  # Gray
    "Vimentin": [1.0, 0.65, 0.0],  # Orange
}

# Cell classification colors
CLASSIFICATION_COLORS_MAP = {
    "Treg": "purple",
    "CD8+ T Cell": "green",
    "CD4+ T Cell": "lightgreen",
    "B Cell": "blue",
    "NK Cell": "cyan",
    "Neutrophil": "yellow",
    "Macrophage (CD163+)": "orange",
    "Myeloid Cell (CD68+)": "red",
    "Dendritic Cell": "pink",
    "Monocyte/MDSC-like": "brown",
    "Epithelial Cell": "magenta",
    "Fibroblast": "lime",
    "Endothelial Cell": "gray",
    "Non_Immune_Unspec": "white",
    "Background/Junk": "black",
    "Unclassified_By_New_Rules": "silver"
}


def create_visualization_and_save_rgb(
        prediction_50ch: np.ndarray,
        markers: list,
        colors: dict,
        output_path_png: Path,
        cell_data: Optional[pd.DataFrame] = None,
        original_image: Optional[np.ndarray] = None
) -> None:
    """
    Creates an RGB image where color is determined by the most dominant marker
    and includes cell centroids (colored by their classification) and a legend.

    Args:
        prediction_50ch: (H, W, C) array with C=50 channels
        markers: List of marker names (should match ML_CHANNELS)
        colors: Dictionary mapping marker names to RGB colors
        output_path_png: Path to save the visualization
        cell_data: Optional DataFrame with cell information
        original_image: Optional original H&E image for context
    """
    H, W, C = prediction_50ch.shape
    if C != 50:
        print(f"❌ Visualization failed: Prediction has {C} channels, not 50.")
        return

    # --- 1. Create Color Composite Image based on Dominant Channel (PIXEL COLOR) ---
    global_max = np.max(prediction_50ch)
    if global_max == 0:
        print("❌ Visualization failed: All prediction values are zero.")
        return

    normalized_pred = prediction_50ch / global_max
    max_channel_index = np.argmax(normalized_pred, axis=-1)
    rgb_image = np.zeros((H, W, 3), dtype=np.float32)

    # Create color array for all channels
    color_array = np.zeros((C, 3), dtype=np.float32)
    for i, marker in enumerate(markers):
        if marker in colors:
            color_array[i] = colors[marker]
        else:
            # Default random color for unlisted markers
            np.random.seed(i)
            color_array[i] = np.random.rand(3)

    # Apply colors based on dominant channel
    for i in range(C):
        mask = (max_channel_index == i)
        rgb_image[mask] = normalized_pred[mask, i][:, np.newaxis] * color_array[i]

    # Normalize to [0, 1] range
    vmax = np.percentile(rgb_image, 99.5)
    if vmax > 0:
        rgb_image = np.clip(rgb_image / vmax, 0, 1)

    # --- 2. Create Matplotlib Figure ---
    fig, ax = plt.subplots(figsize=(12, 12), dpi=150, facecolor='black')
    ax.imshow(rgb_image)
    ax.axis('off')
    ax.set_title('Combined Biomarker Expression', color='white', fontsize=16, pad=10)

    # --- 3. Overlay Cell Centroids (CENTROID COLOR) ---
    if cell_data is not None and not cell_data.empty:
        try:
            if 'Phenotype' not in cell_data.columns:
                print("⚠️ Warning: 'Phenotype' column missing in cell_data. Using default color.")
                cell_colors = 'lime'
            else:
                cell_colors = cell_data['Phenotype'].map(
                    lambda x: CLASSIFICATION_COLORS_MAP.get(x, 'white')
                ).to_numpy()

            # Determine marker size based on available data
            if 'area' in cell_data.columns:
                marker_sizes = cell_data['area'] * 0.05
            else:
                marker_sizes = 20  # Default size

            ax.scatter(
                cell_data['x'], cell_data['y'],
                s=marker_sizes,
                c=cell_colors,
                marker='o',
                alpha=0.7,
                edgecolors='black',
                linewidths=0.5
            )
            print(f"✅ Overlaid {len(cell_data)} cell centroids on visualization.")

            # Add a separate legend for cell classifications
            unique_phenotypes = cell_data['Phenotype'].unique()
            classification_legend_elements = [
                Patch(facecolor=CLASSIFICATION_COLORS_MAP.get(label, 'white'),
                      edgecolor='black', label=label)
                for label in unique_phenotypes
            ]
            if classification_legend_elements:
                ax.legend(handles=classification_legend_elements,
                          loc='upper left',
                          bbox_to_anchor=(-0.15, 1.0),
                          title="Cell Classifications",
                          title_fontsize='medium',
                          labelcolor='white',
                          facecolor='black',
                          edgecolor='grey',
                          framealpha=0.8,
                          fontsize='small')
        except KeyError as e:
            print(f"⚠️ Error drawing cell centroids: Required column missing ({e})")
        except Exception as e:
            print(f"⚠️ Error drawing cell centroids: {e}")

    # --- 4. Add Marker Legend (PIXEL COLOR LEGEND) ---
    try:
        # Only show markers that are in the color map
        legend_markers = [m for m in markers if m in colors]
        legend_elements = [
            Patch(facecolor=colors[marker], edgecolor='w', label=marker)
            for marker in legend_markers[:10]  # Limit to top 10 to avoid clutter
        ]
        ax.legend(handles=legend_elements,
                  loc='upper right',
                  bbox_to_anchor=(1.25, 1.0),
                  title="Dominant Marker",
                  title_fontsize='medium',
                  labelcolor='white',
                  facecolor='black',
                  edgecolor='grey',
                  framealpha=0.8,
                  fontsize='small')
    except Exception as e:
        print(f"⚠️ Warning: Could not create marker legend: {e}")

    # --- 5. Save the Figure ---
    plt.savefig(output_path_png, bbox_inches='tight', pad_inches=0.1, dpi=300, facecolor='black')
    plt.close(fig)
    print(f"✅ Saved visualization to {output_path_png}")


# Configuration is imported from batch_config.py
# If batch_config.py is not found, these defaults are used:
# PATCH_SIZE = 128 (fixed)
# STRIDE_SIZE = 8 (default, can be changed in batch_config.py)
# BATCH_SIZE = 32 (default, can be changed in batch_config.py)
# SAVE_TIFF = False (default, can be changed in batch_config.py)

PATCH_SIZE = 128  # This is fixed and should not be changed

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"\n✓ Using device: {device}")

if device.type == "cpu":
    print("⚠️  Running on CPU - this will be SLOW!")
    print("   Estimated time: 30-60 minutes per image on CPU")
    print("   Recommended: Use GPU for 50-100x speedup")
else:
    print("✓ GPU detected - much faster!")


# Define the OFFICIAL model architecture (standard ConvNeXt classifier)
def get_model(num_outputs: int) -> nn.Module:
    """
    Official model architecture - standard ConvNeXt with modified classifier
    This is NOT a spatial upsampling model!
    """
    model = models.convnext_small(weights=None)  # Don't load ImageNet weights
    model.classifier[2] = nn.Linear(model.classifier[2].in_features, num_outputs)
    return model


# Paths
node2_in = Path("Node2_out")
node3_out = Path("Node3_official_out")

tiff_dir = node3_out / "v_mIF_tiffs"
classification_dir = node3_out / "phenotypes"
visualization_dir = node3_out / "visualizations"
for d in [tiff_dir, classification_dir, visualization_dir]:
    d.mkdir(parents=True, exist_ok=True)
print("✓ Output directories created")

# Load model
# NOTE: Model path is relative to the working directory where this script runs
# If running from F5/ directory, model should be at ../best_model_single.pth (i.e., in NewROSIE/)
model_path = "../best_model_single.pth"
if not os.path.exists(model_path):
    print(f"✗ ERROR: Model not found: {model_path}")
    print(f"   Current directory: {os.getcwd()}")
    print(f"   Looking for model at: {os.path.abspath(model_path)}")
    exit(1)

print(f"\n⏳ Loading model ({os.path.getsize(model_path) / (1024 ** 2):.1f} MB)...")
num_channels = 50
model = get_model(num_outputs=num_channels)
model = nn.DataParallel(model)

try:
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint['model_state_dict'])
    print("✓ Model loaded successfully!")
except Exception as e:
    print(f"✗ Error loading model: {e}")
    exit(1)

model = model.to(device).eval()

# Load Node2 manifest
node2_manifest_path = node2_in / "node2_output.json"
if not node2_manifest_path.exists():
    print(f"✗ ERROR: Node2 manifest not found: {node2_manifest_path}")
    exit(1)

with open(node2_manifest_path, "r") as f:
    node2_manifest = json.load(f)

tiles = node2_manifest.get("tiles", [])
if not tiles:
    print("✗ ERROR: No tiles in manifest")
    exit(1)

total_tiles = len(tiles)
print(f"✓ Found {total_tiles} tiles in manifest")

# =============================================================================
# BATCH PROCESSING: Select subset of tiles
# =============================================================================
if BATCH_MODE:
    # Validate batch range
    if START_TILE < 0 or START_TILE >= total_tiles:
        print(f"✗ ERROR: START_TILE={START_TILE} is out of range (0-{total_tiles-1})")
        exit(1)
    
    if END_TILE is None:
        END_TILE = total_tiles
    
    if END_TILE > total_tiles:
        print(f"⚠ WARNING: END_TILE={END_TILE} exceeds total tiles, adjusting to {total_tiles}")
        END_TILE = total_tiles
    
    if START_TILE >= END_TILE:
        print(f"✗ ERROR: START_TILE ({START_TILE}) must be less than END_TILE ({END_TILE})")
        exit(1)
    
    # Select the batch of tiles to process
    tiles = tiles[START_TILE:END_TILE]
    
    print(f"\n{'='*70}")
    print(f"BATCH PROCESSING MODE")
    print(f"{'='*70}")
    print(f"Processing tiles: {START_TILE} to {END_TILE-1}")
    print(f"Total tiles in this batch: {len(tiles)}")
    print(f"Remaining tiles: {total_tiles - END_TILE}")
    print(f"STRIDE_SIZE: {STRIDE_SIZE}")
    print(f"BATCH_SIZE: {BATCH_SIZE}")
    
    # Load existing progress if available
    progress_path = Path(PROGRESS_FILE)
    if progress_path.exists():
        with open(progress_path, 'r') as f:
            progress = json.load(f)
        print(f"✓ Loaded existing progress file")
        print(f"  Previously completed batches: {len(progress.get('completed_batches', []))}")
    else:
        progress = {
            "total_tiles": total_tiles,
            "completed_batches": [],
            "start_date": datetime.now().isoformat()
        }
    
    # Add this batch info
    config_info["total_tiles_in_dataset"] = total_tiles
    
    print(f"{'='*70}\n")
else:
    print(f"\n{'='*70}")
    print(f"PROCESSING ALL {len(tiles)} TILES")
    print(f"Using STRIDE={STRIDE_SIZE}, PATCH={PATCH_SIZE}")
    print(f"{'='*70}\n")

# Patch transform (official method)
patch_transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Resize(224, antialias=True),  # 128x128 → 224x224
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Classification rules
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


import time

# Start processing tiles
batch_start_time = time.time()
successful_tiles = []
failed_tiles = []

for tile_idx, tile in enumerate(tiles, 1):
    actual_tile_idx = START_TILE + tile_idx - 1 if BATCH_MODE else tile_idx - 1
    png_path = Path(tile["png_path"])
    if (classification_dir / f"{png_path.stem}_phenotypes.json").exists():
        print(f"  -> already done, skipping {png_path.name}")
        continue
    print(f"[Tile {actual_tile_idx+1}/{total_tiles if BATCH_MODE else len(tiles)}] {png_path.name}")

    if not png_path.exists():
        print(f"  ✗ Image not found: {png_path}")
        continue

    # Load image
    print(f"  ⏳ Loading image...")
    img_pil = Image.open(png_path).convert("RGB")
    img_array = np.array(img_pil)
    height, width = img_array.shape[:2]
    print(f"  ✓ Image size: {width} x {height}")

    # Initialize output arrays (official method: weighted blending)
    raw_output = np.zeros((num_channels, height, width), dtype=np.float32)
    weight_map = np.zeros((height, width), dtype=np.float32)

    # Create Gaussian weight kernel for smooth blending
    kernel_size = STRIDE_SIZE * 2
    y_grid, x_grid = np.mgrid[0:kernel_size, 0:kernel_size]
    center = kernel_size // 2
    weight_kernel = np.exp(-((x_grid - center) ** 2 + (y_grid - center) ** 2) / (2 * (kernel_size / 4) ** 2))

    # Generate patch coordinates with overlap
    # Use STRIDE_SIZE directly for reasonable performance
    # STRIDE_SIZE=8 gives good accuracy/speed balance
    overlap_stride = STRIDE_SIZE
    coords = []
    for y in range(0, height, overlap_stride):
        for x in range(0, width, overlap_stride):
            coords.append((x, y))

    total_patches = len(coords)
    print(f"  ℹ️  Total patches: {total_patches} (with overlap_stride={overlap_stride})")
    print(f"  ℹ️  Batch size: {BATCH_SIZE}")
    print(f"  ⏳ Running inference...")

    start_time = time.time()

    # Process in batches
    num_batches = (total_patches + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx, batch_start in enumerate(range(0, total_patches, BATCH_SIZE)):
        batch_coords = coords[batch_start:batch_start + BATCH_SIZE]
        batch_patches = []

        # Extract patches
        for x, y in batch_coords:
            half_patch = PATCH_SIZE // 2
            t = max(0, y - half_patch)
            b = min(height, y + half_patch)
            l = max(0, x - half_patch)
            r = min(width, x + half_patch)

            patch = img_array[t:b, l:r]

            # Pad if necessary
            if patch.shape[0] < PATCH_SIZE or patch.shape[1] < PATCH_SIZE:
                pad_h = max(0, PATCH_SIZE - patch.shape[0])
                pad_w = max(0, PATCH_SIZE - patch.shape[1])
                patch = np.pad(patch, ((0, pad_h), (0, pad_w), (0, 0)), mode='constant')

            patch = patch[:PATCH_SIZE, :PATCH_SIZE]
            patch_tensor = patch_transform(patch)
            batch_patches.append(patch_tensor)

        # Run inference on batch
        batch_tensor = torch.stack(batch_patches).to(device)
        with torch.no_grad():
            predictions = model(batch_tensor).cpu().numpy()

        # Apply weighted blending (OFFICIAL METHOD)
        for pred, (x, y) in zip(predictions, batch_coords):
            half_size = kernel_size // 2
            t = np.clip(y - half_size, 0, height)
            b = np.clip(y + half_size, 0, height)
            l = np.clip(x - half_size, 0, width)
            r = np.clip(x + half_size, 0, width)

            kernel_h, kernel_w = b - t, r - l
            weight = weight_kernel[:kernel_h, :kernel_w]

            # Weighted accumulation
            for c in range(num_channels):
                raw_output[c, t:b, l:r] += pred[c] * weight
            weight_map[t:b, l:r] += weight

        # Progress update
        if (batch_idx + 1) % 10 == 0 or (batch_idx + 1) == num_batches:
            elapsed = time.time() - start_time
            avg_time = elapsed / (batch_idx + 1)
            remaining = avg_time * (num_batches - batch_idx - 1)
            print(
                f"    Progress: {batch_idx + 1}/{num_batches} batches ({100 * (batch_idx + 1) // num_batches}%) - ETA: {int(remaining // 60)}m {int(remaining % 60)}s",
                end='\r')

    print()  # Newline after progress
    elapsed = time.time() - start_time
    print(f"  ✓ Inference complete! ({elapsed:.1f}s)")

    # Normalize by weights (official method)
    print(f"  ⏳ Normalizing weighted predictions...")
    weight_map = np.maximum(weight_map, 1e-8)
    for c in range(num_channels):
        raw_output[c] /= weight_map

    fmap = raw_output

    # Save TIFF (optional - can be disabled to save disk space)
    if SAVE_TIFF:
        tiff_path = tiff_dir / f"{png_path.stem}.tiff"
        print(f"  ⏳ Saving TIFF...")
        tifffile.imwrite(
            str(tiff_path),
            fmap.astype('float32'),
            imagej=True,
            metadata={'axes': 'CYX', 'Labels': ML_CHANNELS}
        )
        tiff_size_mb = os.path.getsize(tiff_path) / (1024 ** 2)
        print(f"  ✓ TIFF saved ({tiff_size_mb:.1f} MB)")
    else:
        print(f"  ⏭️  TIFF saving disabled (SAVE_TIFF=False)")

    # Classify cells (same as before)
    cells_json_path = node2_in / "cell_coordinates" / f"{png_path.stem}_cells.json"

    if cells_json_path.exists():
        print(f"  ⏳ Classifying cells...")
        with open(cells_json_path, "r") as cf:
            cells_data = json.load(cf)

        classified_cells = []

        for cell in cells_data.get("cells", []):
            x = int(cell.get("x", 0))
            y = int(cell.get("y", 0))
            x = min(max(x, 0), fmap.shape[2] - 1)
            y = min(max(y, 0), fmap.shape[1] - 1)

            signals = {}
            for i, channel_name in enumerate(ML_CHANNELS):
                signals[channel_name] = float(fmap[i, y, x])

            cell_with_signals = {
                "CellID": cell.get("CellID", f"cell_{len(classified_cells)}"),
                "x": x,
                "y": y,
                "Signals": signals
            }

            phenotype = fuzzy_classify_primary_label(cell_with_signals)
            cell_with_signals["Phenotype"] = phenotype
            classified_cells.append(cell_with_signals)

        classification_output = {
            "tile_name": png_path.stem,
            "timestamp": datetime.now().isoformat(),
            "method": "official_weighted_blending",
            "total_cells": len(classified_cells),
            "cells": classified_cells,
            "phenotype_counts": {}
        }

        for cell in classified_cells:
            phenotype = cell["Phenotype"]
            classification_output["phenotype_counts"][phenotype] = \
                classification_output["phenotype_counts"].get(phenotype, 0) + 1

        classification_json_path = classification_dir / f"{png_path.stem}_phenotypes.json"
        with open(classification_json_path, "w") as outf:
            json.dump(classification_output, outf, indent=2)

        print(f"  ✓ Classified {len(classified_cells)} cells")
        print(f"  ✓ Top phenotypes:")
        for phenotype, count in sorted(classification_output["phenotype_counts"].items(),
                                       key=lambda x: x[1], reverse=True)[:10]:
            print(f"      {phenotype}: {count}")

        # --- Generate Visualization ---
        print(f"  ⏳ Creating visualization...")
        try:
            # Convert fmap from (C, H, W) to (H, W, C) for visualization
            prediction_hwc = np.transpose(fmap, (1, 2, 0))

            # Convert classified cells to DataFrame for visualization
            cell_df = pd.DataFrame([
                {
                    'x': cell['x'],
                    'y': cell['y'],
                    'Phenotype': cell['Phenotype'],
                    'area': 100  # Default area if not available
                }
                for cell in classified_cells
            ])

            # Create visualization
            vis_path = visualization_dir / f"{png_path.stem}_visualization.png"
            create_visualization_and_save_rgb(
                prediction_50ch=prediction_hwc,
                markers=ML_CHANNELS,
                colors=TARGET_CHANNEL_COLORS,
                output_path_png=vis_path,
                cell_data=cell_df,
                original_image=img_array
            )

            vis_size_mb = os.path.getsize(vis_path) / (1024 ** 2)
            print(f"  ✓ Visualization saved ({vis_size_mb:.1f} MB)")
            
            # Track successful processing
            successful_tiles.append({
                "tile_index": actual_tile_idx,
                "tile_name": png_path.stem,
                "cells_classified": len(classified_cells)
            })

        except Exception as e:
            print(f"  ⚠️  Visualization failed: {e}")
            import traceback

            traceback.print_exc()

    else:
        print(f"  ⚠️  Cell data not found: {cells_json_path}")
        print(f"  ⚠️  Skipping visualization (no cell data)")
        failed_tiles.append({
            "tile_index": actual_tile_idx,
            "tile_name": png_path.stem,
            "reason": "cell_data_not_found"
        })

# =============================================================================
# SAVE PROGRESS AND SUMMARY
# =============================================================================
batch_end_time = time.time()
batch_duration = batch_end_time - batch_start_time

print(f"\n{'=' * 70}")
print(f"✅ BATCH COMPLETE!")
print(f"{'=' * 70}")
print(f"Batch duration: {batch_duration/60:.1f} minutes")
print(f"Successful tiles: {len(successful_tiles)}")
print(f"Failed tiles: {len(failed_tiles)}")

if BATCH_MODE:
    # Update progress file
    progress_path = Path(PROGRESS_FILE)
    if progress_path.exists():
        with open(progress_path, 'r') as f:
            progress = json.load(f)
    else:
        progress = {
            "total_tiles": total_tiles,
            "completed_batches": [],
            "start_date": datetime.now().isoformat()
        }
    
    # Add this batch to completed batches
    batch_record = {
        "batch_start": START_TILE,
        "batch_end": END_TILE,
        "tiles_processed": len(successful_tiles),
        "tiles_failed": len(failed_tiles),
        "successful_tiles": successful_tiles,
        "failed_tiles": failed_tiles,
        "stride_size": STRIDE_SIZE,
        "duration_minutes": batch_duration / 60,
        "timestamp": datetime.now().isoformat()
    }
    
    progress["completed_batches"].append(batch_record)
    progress["last_update"] = datetime.now().isoformat()
    
    # Calculate overall progress
    all_completed = set()
    for batch in progress["completed_batches"]:
        for tile in batch["successful_tiles"]:
            all_completed.add(tile["tile_index"])
    
    progress["tiles_completed"] = len(all_completed)
    progress["tiles_remaining"] = total_tiles - len(all_completed)
    progress["percent_complete"] = (len(all_completed) / total_tiles) * 100
    
    # Save progress
    with open(progress_path, 'w') as f:
        json.dump(progress, f, indent=2)
    
    print(f"\n{'=' * 70}")
    print(f"OVERALL PROGRESS")
    print(f"{'=' * 70}")
    print(f"Total tiles: {total_tiles}")
    print(f"Completed: {progress['tiles_completed']} ({progress['percent_complete']:.1f}%)")
    print(f"Remaining: {progress['tiles_remaining']}")
    print(f"Progress saved to: {PROGRESS_FILE}")
    print(f"\nTo process next batch, edit batch_config.py:")
    print(f"  START_TILE = {END_TILE}")
    print(f"  END_TILE = {min(END_TILE + (END_TILE - START_TILE), total_tiles)}")
    print(f"{'=' * 70}")

print(f"\nOutput files:")
print(f"  TIFF: {tiff_dir}/")
print(f"  Phenotypes: {classification_dir}/")
print(f"  Visualizations: {visualization_dir}/")
print(f"\nThis version uses the OFFICIAL evaluate.py method:")
print(f"  - Sliding window with overlap")
print(f"  - Gaussian weighted blending")
print(f"  - Standard ConvNeXt classifier")
print(f"  - RGB composite visualization with cell overlays")
print(f"  - Batch processing with progress tracking")