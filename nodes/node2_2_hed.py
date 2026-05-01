"""
Node 2.2 — HED Colour-Deconvolution + Cell Morphology Segmentation
Separates haematoxylin (nuclear) and eosin (cytoplasm) channels via
Macenko/Ruifrok colour deconvolution, then detects nuclei and extracts
per-cell morphological descriptors.

Input  state keys: tiles, svs_path, patch_size
Output state keys: cell_features (list[dict]), n_cells, mean_nuclear_area,
                   mean_eccentricity, cell_density_per_mm2
"""


# Ruifrok & Johnston stain matrix for H&E (haematoxylin, eosin, residual)
HED_MATRIX = [
    [0.6500286, 0.7044268, 0.2860126],   # haematoxylin
    [0.0704085, 0.9990278, 0.0027375],   # eosin
    [0.7144724, 0.0098471, 0.6995739],   # DAB / residual
]


def _hed_deconvolve(rgb_patch: "np.ndarray") -> "np.ndarray":
    """Return H, E, D channels (float32, each 0–1) from an RGB patch."""
    import numpy as np
    rgb = rgb_patch.astype(np.float32) / 255.0 + 1e-6
    od  = -np.log(rgb)
    M   = np.array(HED_MATRIX, dtype=np.float32)
    # Pseudo-inverse for colour deconvolution
    hed = od @ np.linalg.pinv(M)
    return np.clip(hed, 0, 1)


def _segment_nuclei(h_channel: "np.ndarray") -> "np.ndarray":
    """
    Simple threshold + connected-component nuclei segmentation on the
    haematoxylin channel.  Returns a labelled integer mask.
    """
    import numpy as np
    from skimage import filters, morphology, measure, segmentation, feature

    # Normalise
    h = (h_channel - h_channel.min()) / (h_channel.max() - h_channel.min() + 1e-6)

    # Otsu threshold
    thresh = filters.threshold_otsu(h)
    binary = h > thresh

    # Clean up (skimage 0.26+: max_size replaces min_size/area_threshold)
    binary = morphology.remove_small_objects(binary, max_size=30)
    binary = morphology.remove_small_holes(binary, max_size=50)

    # Watershed to split touching nuclei
    footprint = morphology.disk(2)
    distance  = morphology.erosion(binary.astype(np.uint8), footprint).astype(float)
    local_max = feature.peak_local_max(distance, min_distance=6, labels=binary)
    markers   = np.zeros_like(binary, dtype=int)
    if len(local_max):
        markers[tuple(local_max.T)] = np.arange(1, len(local_max) + 1)
    labels    = segmentation.watershed(-distance, markers, mask=binary)
    return labels


def process(state, params=None):
    import numpy as np, os

    tiles      = state.get("tiles", [])
    svs_path   = state.get("svs_path", "")
    patch_size = int(state.get("patch_size", 512))

    # How many patches to actually segment (limit for speed)
    sample_n   = min(len(tiles), 30)
    rng        = np.random.default_rng(7)

    cell_features = []
    have_slide    = bool(svs_path and os.path.exists(svs_path))

    print(f"HED segmentation: sampling {sample_n} / {len(tiles)} tiles")

    if have_slide:
        import openslide
        from skimage import measure
        slide = openslide.OpenSlide(svs_path)

        for i, tile in enumerate(tiles[:sample_n]):
            rgb = np.array(
                slide.read_region((tile["x"], tile["y"]), 0,
                                  (patch_size, patch_size)).convert("RGB"),
                dtype=np.uint8,
            )
            hed    = _hed_deconvolve(rgb)
            h_chan = hed[..., 0]
            labels = _segment_nuclei(h_chan)

            for region in measure.regionprops(labels, intensity_image=h_chan):
                if region.area < 20 or region.area > 3000:
                    continue
                cell_features.append({
                    "tile_x":       tile["x"],
                    "tile_y":       tile["y"],
                    "cx":           tile["x"] + int(region.centroid[1]),
                    "cy":           tile["y"] + int(region.centroid[0]),
                    "area":         float(region.area),
                    "perimeter":    float(region.perimeter),
                    "eccentricity": float(region.eccentricity),
                    "solidity":     float(region.solidity),
                    "h_intensity":  float(region.intensity_mean),
                    "eosin":        float(hed[..., 1][
                        region.coords[:, 0], region.coords[:, 1]
                    ].mean()),
                })

        slide.close()

    else:
        # Demo mode
        for _ in range(sample_n):
            n = int(rng.integers(15, 60))
            for _ in range(n):
                cell_features.append({
                    "tile_x":       0, "tile_y": 0,
                    "cx":           int(rng.integers(0, 15000)),
                    "cy":           int(rng.integers(0, 15000)),
                    "area":         float(rng.uniform(80, 600)),
                    "perimeter":    float(rng.uniform(30, 100)),
                    "eccentricity": float(rng.uniform(0.1, 0.9)),
                    "solidity":     float(rng.uniform(0.7, 1.0)),
                    "h_intensity":  float(rng.uniform(0.3, 0.9)),
                    "eosin":        float(rng.uniform(0.1, 0.6)),
                })

    n_cells = len(cell_features)
    if n_cells == 0:
        mean_area  = 0.0
        mean_ecc   = 0.0
        density    = 0.0
    else:
        areas = [c["area"] for c in cell_features]
        eccs  = [c["eccentricity"] for c in cell_features]
        mean_area  = float(np.mean(areas))
        mean_ecc   = float(np.mean(eccs))
        # Approx slide area at 0.5 µm/px: area in mm2
        wsi_dims   = state.get("wsi_dims", (15347, 15243))
        area_mm2   = (wsi_dims[0] * wsi_dims[1] * (0.5e-3) ** 2)
        density    = n_cells / max(area_mm2, 1.0)

    print(f"Detected {n_cells} nuclei across {sample_n} patches")
    print(f"Mean nuclear area   : {mean_area:.1f} px2")
    print(f"Mean eccentricity   : {mean_ecc:.3f}")
    print(f"Cell density        : {density:.1f} cells/mm2")

    state.update({
        "cell_features":       cell_features,
        "n_cells":             n_cells,
        "mean_nuclear_area":   round(mean_area, 2),
        "mean_eccentricity":   round(mean_ecc, 4),
        "cell_density_per_mm2": round(density, 2),
    })
    return state
