import os
import json
import numpy as np
from datetime import datetime
from pathlib import Path


def is_background_patch(patch_rgb, threshold=235, max_white_ratio=0.85, std_threshold=10.0, min_tissue_ratio=0.15):
    """
    Enhanced background filtering with multiple criteria:
    1. Check for whiteness ratio (how much is white/empty)
    2. Check for image texture (Standard Deviation)
    3. Check for minimum tissue content (must have enough non-white area)
    4. Check for edge-only tissue (tissue only in corners)

    Args:
        patch_rgb: PIL Image in RGB format
        threshold: Pixel intensity threshold for "white" (default 235)
        max_white_ratio: Maximum allowed ratio of white pixels (default 0.85 = 85%)
        std_threshold: Minimum standard deviation for texture (default 10.0)
        min_tissue_ratio: Minimum ratio of tissue area required (default 0.15 = 15%)

    Returns:
        True if patch should be skipped (background), False if it should be kept
    """
    # Convert to grayscale
    gray = np.array(patch_rgb.convert("L"))
    h, w = gray.shape

    # 1. Whiteness Check - Overall white ratio
    white_mask = gray > threshold
    white_ratio = np.sum(white_mask) / gray.size

    # If more than 85% is white, skip it
    if white_ratio > max_white_ratio:
        return True

    # 2. Tissue ratio check - Must have at least 15% non-white content
    tissue_ratio = 1.0 - white_ratio
    if tissue_ratio < min_tissue_ratio:
        return True

    # 3. Texture Check (Standard Deviation)
    # Background usually has very low variance/std dev
    # Only check std on non-white regions to avoid bias
    tissue_pixels = gray[~white_mask]
    if len(tissue_pixels) > 0:
        tissue_std = np.std(tissue_pixels)
        if tissue_std < std_threshold:
            return True

    # 4. Edge-only tissue check
    # Check if tissue is only concentrated in edges/corners
    # Divide image into 3x3 grid and check center region
    center_y_start = h // 3
    center_y_end = 2 * h // 3
    center_x_start = w // 3
    center_x_end = 2 * w // 3

    center_region = gray[center_y_start:center_y_end, center_x_start:center_x_end]
    center_white_ratio = np.sum(center_region > threshold) / center_region.size

    # If center is > 95% white but overall tissue ratio is low, it's edge-only
    if center_white_ratio > 0.95 and tissue_ratio < 0.25:
        return True

    # 5. Additional check: very uniform non-white regions (likely artifacts)
    if len(tissue_pixels) > 100:  # Need enough pixels to check
        # Check if tissue pixels are too uniform (e.g., all same gray value)
        tissue_range = np.ptp(tissue_pixels)  # peak-to-peak (max - min)
        if tissue_range < 20:  # Very narrow range
            return True

    return False


def process(state, params=None):
    """
    Updated Agent Node 1: Full WSI Tiling with Enhanced Background Filtering.
    All paths are RELATIVE for easy cross-directory use.
    """
    try:
        from openslide import OpenSlide
        from PIL import Image
    except ImportError:
        msg = "❌ Error: Missing dependencies. Please install 'openslide-python' and 'Pillow'."
        state.setdefault("messages", []).append({"role": "assistant", "content": msg})
        return state

    # 1. Configuration parameters
    svs_file = "__SVS__"  # Relative path
    output_dir = Path("Node1_out")
    output_dir.mkdir(exist_ok=True)

    metadata_file = output_dir / "Node1_out.json"
    tile_size = 1024
    level = 0

    # Background filtering settings (more aggressive)
    bg_threshold = 235  # Sensitivity to white
    white_ratio_limit = 0.85  # Skip if > 85% white
    std_threshold = 10.0  # Minimum texture variance
    min_tissue_ratio = 0.15  # Must have at least 15% tissue

    if not os.path.exists(svs_file):
        state.setdefault("messages", []).append({"role": "assistant", "content": f"❌ File not found: {svs_file}"})
        return state

    # 2. Open Slide and Calculate Grid
    slide = OpenSlide(svs_file)
    full_width, full_height = slide.level_dimensions[level]

    cols = full_width // tile_size
    rows = full_height // tile_size

    print(f"Starting Full WSI Processing: {full_width}x{full_height}")
    print(f"Grid Dimensions: {cols} columns x {rows} rows")
    print(
        f"Background filtering: threshold={bg_threshold}, max_white={white_ratio_limit}, min_tissue={min_tissue_ratio}")

    patch_metadata = []
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    processed_count = 0
    skipped_count = 0

    # 3. Iterate through the entire grid
    for r in range(rows):
        for c in range(cols):
            abs_x = c * tile_size
            abs_y = r * tile_size

            # Read region (RGBA) and convert to RGB
            patch_rgba = slide.read_region((abs_x, abs_y), level, (tile_size, tile_size))
            patch_rgb = patch_rgba.convert("RGB")

            # --- Enhanced Background Filtering Logic ---
            if is_background_patch(
                    patch_rgb,
                    threshold=bg_threshold,
                    max_white_ratio=white_ratio_limit,
                    std_threshold=std_threshold,
                    min_tissue_ratio=min_tissue_ratio
            ):
                skipped_count += 1
                continue
            # ------------------------------------------

            # Save Valid Patch
            filename = f"patch_{session_id}_x{abs_x:06d}_y{abs_y:06d}.png"
            filepath = output_dir / filename
            patch_rgb.save(filepath, "PNG")

            # Record detailed metadata for Node 2/3 compatibility
            # USE RELATIVE PATHS for portability
            patch_info = {
                "primary_filename": filename,
                "absolute_position": {
                    "x": abs_x,
                    "y": abs_y,
                    "width": tile_size,
                    "height": tile_size
                },
                "grid_position": {
                    "row": r,
                    "col": c
                },
                "png_path": str(filepath),  # Relative path: Node1_out/patch_xxx.png
                "source_reference": {
                    "svs_file": svs_file,  # Relative path
                    "session_id": session_id
                }
            }
            patch_metadata.append(patch_info)
            processed_count += 1

            if processed_count % 20 == 0:
                print(f"Progress: Processed {processed_count} valid tiles, Skipped {skipped_count} background tiles.")

    # 4. Generate Final Manifest
    full_metadata = {
        "metadata_version": "2.0",
        "session_info": {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        },
        "wsi_info": {
            "source_file": svs_file,  # Relative path
            "total_dimensions": {"width": full_width, "height": full_height},
            "tile_size": tile_size
        },
        "filtering_params": {
            "threshold": bg_threshold,
            "max_white_ratio": white_ratio_limit,
            "std_threshold": std_threshold,
            "min_tissue_ratio": min_tissue_ratio
        },
        "stats": {
            "valid_patches": processed_count,
            "skipped_background": skipped_count,
            "skip_percentage": round(skipped_count / (processed_count + skipped_count) * 100, 2) if (
                                                                                                                processed_count + skipped_count) > 0 else 0
        },
        "tiles": patch_metadata
    }

    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(full_metadata, f, indent=2)

    slide.close()

    # Update State
    summary = (
        f"### Node 1: WSI Tiling Complete\n"
        f"- **Valid Tiles Saved:** {processed_count}\n"
        f"- **Background Tiles Skipped:** {skipped_count} ({full_metadata['stats']['skip_percentage']}%)\n"
        f"- **Metadata File:** `{metadata_file}`"
    )
    state.setdefault("messages", []).append({"role": "assistant", "content": summary})

    # Pass data to next nodes
    state["patch_metadata_file"] = str(metadata_file)
    state["session_id"] = session_id

    print(
        f"✅ Finished! Processed {processed_count} tiles. Skipped {skipped_count} empty areas ({full_metadata['stats']['skip_percentage']}%).")
    return state


if __name__ == "__main__":
    result = process({})
    print("Extraction complete. Metadata generated.")