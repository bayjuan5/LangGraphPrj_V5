import os
import json
import numpy as np
import cv2
import shutil
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt

# Image processing suite
from skimage import filters, measure, morphology, color, segmentation, exposure
from scipy import ndimage


# ---------------------------------------------------------
# Node2: Cell Detection and Tile Data Recording
# All paths are RELATIVE for easy cross-directory use
# ---------------------------------------------------------
def process(state, params=None):
    if "messages" not in state:
        state["messages"] = []

    start_time = datetime.now()

    # Path setup - RELATIVE PATHS
    input_dir = Path("Node1_out")
    output_dir = Path("Node2_out")

    # Clean and create output directory structure
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_dir = output_dir / "cell_coordinates"
    viz_dir = output_dir / "visualizations"
    json_dir.mkdir(exist_ok=True)
    viz_dir.mkdir(exist_ok=True)

    # 1. Scan all PNG files in Node1_out folder
    png_files = list(input_dir.glob("**/*.png"))

    if not png_files:
        state["messages"].append({"role": "assistant", "content": "❌ Node2: No PNG patches found in Node1_out"})
        return state

    total_cells_found = 0
    processed_patches = []

    # 2. Core detection loop
    for png_path in png_files:
        patch_name = png_path.name

        try:
            # Load image
            image_bgr = cv2.imread(str(png_path))
            if image_bgr is None:
                continue
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

            # --- Cell nucleus detection algorithm (HED Deconvolution) ---
            # Extract hematoxylin (purple) channel, ignoring pink background
            hed_image = color.rgb2hed(image_rgb)
            hematoxylin = hed_image[:, :, 0]

            # Enhance contrast and denoise
            h_norm = exposure.equalize_adapthist(hematoxylin, clip_limit=0.03)
            smooth = filters.gaussian(h_norm, sigma=1.0)

            # Local adaptive threshold segmentation
            from skimage.filters import threshold_local
            binary = smooth > threshold_local(smooth, 25, offset=0.05)

            # Remove small objects and holes (compatible with old scikit-image)
            binary = morphology.remove_small_objects(binary, min_size=8)
            binary = morphology.remove_small_holes(binary, area_threshold=50)

            # Watershed algorithm: separate clustered cell nuclei
            distance = ndimage.distance_transform_edt(binary)
            from skimage.feature import peak_local_max
            coords = peak_local_max(distance, min_distance=5, labels=binary)

            mask = np.zeros_like(distance, dtype=bool)
            mask[tuple(coords.T)] = True
            # FIXED: Use dilation instead of binary_dilation
            markers = measure.label(morphology.dilation(mask, morphology.disk(1)))
            labels = segmentation.watershed(-distance, markers, mask=binary)

            # 3. Extract properties and build results for this patch
            regions = measure.regionprops(labels)
            cells_in_patch = []

            for idx, region in enumerate(regions):
                rel_y, rel_x = region.centroid
                area = int(region.area)
                perimeter = getattr(region, "perimeter", 0)
                circularity = (4 * np.pi * area / (perimeter ** 2)) if perimeter > 0 else 0

                # Use field names that Node3 expects
                cells_in_patch.append({
                    "CellID": f"cell_{idx}",
                    "x": int(rel_x),
                    "y": int(rel_y),
                    "area": area,
                    "circularity": circularity,
                    "confidence": min(1.0, circularity * 0.8 + 0.2)
                })

            # 4. Save individual patch detailed JSON (including patch info)
            patch_data = {
                "patch_metadata": {
                    "filename": patch_name,
                    "full_path": str(png_path).replace('\\', '/'),  # Force forward slash
                    "cell_count": len(regions),
                    "timestamp": datetime.now().isoformat()
                },
                "cells": cells_in_patch
            }

            # Use png_path.stem to remove .png extension
            patch_json_file = json_dir / f"{png_path.stem}_cells.json"
            with open(patch_json_file, "w") as f:
                json.dump(patch_data, f, indent=2)

            # 5. Generate visualization comparison
            viz_path = viz_dir / f"viz_{patch_name}"
            create_enhanced_visualization(image_rgb, labels, len(regions), str(viz_path))

            # Record to global manifest - USE RELATIVE PATHS with forward slashes
            processed_patches.append({
                "patch_name": patch_name,
                "png_path": str(png_path).replace('\\', '/'),  # Force forward slash for Linux compatibility
                "cell_count": len(regions),
                "data_json": str(patch_json_file).replace('\\', '/')  # Force forward slash
            })

            total_cells_found += len(regions)

        except Exception as e:
            print(f"⚠️ Error processing {patch_name}: {e}")
            continue

    # 6. Generate Node2 final manifest (node2_output.json)
    # This records all patch information for Node3 to use
    manifest = {
        "node": "Node2",
        "total_patches_processed": len(processed_patches),
        "total_cells_detected": total_cells_found,
        "tiles": processed_patches,  # All patches/tiles info recorded here
        "output_directories": {
            "json_data": str(json_dir).replace('\\', '/'),  # Force forward slash
            "visualizations": str(viz_dir).replace('\\', '/')  # Force forward slash
        }
    }

    manifest_path = output_dir / "node2_output.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    state["messages"].append({"role": "assistant", "content": f"✅ Node2 complete. Total cells: {total_cells_found}."})
    return state


def create_enhanced_visualization(image_rgb, labels, count, output_path):
    """Create side-by-side visualization of original and detected cells"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    axes[0].imshow(image_rgb)
    axes[0].set_title("Original Patch")
    axes[0].axis("off")

    axes[1].imshow(image_rgb)
    axes[1].imshow(labels, cmap="nipy_spectral", alpha=0.4)
    axes[1].set_title(f"Detected: {count} cells")
    axes[1].axis("off")

    plt.savefig(output_path, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    print("="*60)
    print("Starting Node2 Cell Detection")
    print("="*60)
    
    # Check if Node1_out exists
    if not Path("Node1_out").exists():
        print("❌ ERROR: Node1_out directory not found!")
        print(f"   Current directory: {os.getcwd()}")
        print("   Please run Node1.py first to generate tiles.")
        exit(1)
    
    # Check for PNG files
    png_count = len(list(Path("Node1_out").glob("**/*.png")))
    print(f"✓ Found {png_count} PNG files in Node1_out")
    
    if png_count == 0:
        print("❌ ERROR: No PNG files found in Node1_out!")
        print("   Please run Node1.py first to generate tiles.")
        exit(1)
    
    result = process({})
    
    # Verify output
    if Path("Node2_out/node2_output.json").exists():
        print("\n" + "="*60)
        print("✅ SUCCESS! Node2 processing complete")
        print("="*60)
        with open("Node2_out/node2_output.json", "r") as f:
            manifest = json.load(f)
        print(f"Total patches processed: {manifest['total_patches_processed']}")
        print(f"Total cells detected: {manifest['total_cells_detected']}")
        print(f"Output location: Node2_out/node2_output.json")
    else:
        print("\n❌ ERROR: node2_output.json was not created!")
        print("   Check error messages above.")
    
    print("Node2 processing complete.")
