"""
Node 2.1 — ROSIE Biomarker Inference
=====================================================================
Predicts 50-channel protein expression maps from H&E patches using
the ROSIE (Rapid On-Slide Immunofluorescence Emulation) deep-learning
model (Enable Medicine, gitlab.com/enable-medicine-public/rosie).

To use the real ROSIE model:
  1. Register at https://gitlab.com/enable-medicine-public/rosie
  2. Request model weights from Rick (Enable Medicine) — approval required
  3. Place the downloaded weights file at one of:
       • Path set via environment variable:  ROSIE_WEIGHTS=/path/to/rosie.pth
       • Default location in repo root:      rosie_weights.pth
  4. Re-run this node — it will automatically use real ROSIE inference.

Without weights this node runs a COLOR-FEATURE SURROGATE (demo only).
The surrogate produces plausible-looking values for pipeline testing
but has NO biological validity and must NOT be used for publication.

The manuscript results (10.4 M cells) were produced with the real
ROSIE model on proprietary KSC mouse H&E images, not on this sample.

Input  state keys : tiles, svs_path, patch_size
Output state keys : protein_matrix, protein_channels, zone_labels,
                    immune_score, stromal_score, n_channels, rosie_mode
=====================================================================
"""

# ── 50-channel protein panel (matches ROSIE output order) ──────────────────
PROTEIN_CHANNELS = [
    # Immune / T-cell
    "CD3",   "CD4",   "CD8",   "FOXP3",  "CD56",
    # Macrophage / myeloid
    "CD68",  "CD163", "CD11b", "CD33",   "MPO",
    # B-cell / NK
    "CD20",  "CD19",  "CD16",  "NKp46",  "CD57",
    # Tumour / epithelial
    "PanCK", "EpCAM", "E-Cad", "p63",    "CK5",
    # Stromal / fibroblast
    "FAP",   "ColI",  "ColIV", "FN1",    "SMA",
    # Proliferation / cell-cycle
    "Ki67",  "PCNA",  "pHH3",  "CycD1",  "p21",
    # Apoptosis / stress
    "cCasp3","p53",   "HIF1a", "pERK",   "pAKT",
    # Checkpoint / exhaustion
    "PD1",   "PDL1",  "CTLA4", "LAG3",   "TIM3",
    # Cytokines
    "GZMB",  "Perf",  "IFNg",  "TNFa",   "IL6",
    # Angiogenesis / vascular
    "VEGFA", "CD31",  "CD34",  "MMP9",   "MMP2",
]
assert len(PROTEIN_CHANNELS) == 50


# ── Locate ROSIE weights ────────────────────────────────────────────────────

def _find_weights() -> "str | None":
    import os
    from pathlib import Path
    candidates = [
        os.environ.get("ROSIE_WEIGHTS", ""),
        str(Path(__file__).parent.parent / "rosie_weights.pth"),
        str(Path(__file__).parent.parent / "rosie" / "rosie_weights.pth"),
    ]
    for p in candidates:
        if p and Path(p).exists():
            return p
    return None


# ── Real ROSIE inference ────────────────────────────────────────────────────

def _rosie_predict_batch(patches: "list[np.ndarray]",
                          weights_path: str) -> "np.ndarray":
    """
    Run real ROSIE CNN inference on a list of RGB patches.

    ROSIE model API (Enable Medicine):
      from rosie import ROSIE
      model = ROSIE(weights=weights_path, device='cpu')
      output = model.predict(patch_rgb)  # np.ndarray shape (50,)

    The wrapper below follows the ROSIE GitLab interface as of v1.x.
    If the API has changed in your version, adjust accordingly.
    """
    import numpy as np
    import torch

    try:
        # Primary: use the official rosie package if installed
        from rosie import ROSIE  # pip install rosie (or from GitLab clone)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model  = ROSIE(weights=weights_path, device=device)
        results = np.stack([model.predict(p) for p in patches])
        return results.astype(np.float32)

    except ImportError:
        # Fallback: load as a generic torchvision model (adjust arch if needed)
        import torch.nn as nn
        from torchvision import transforms, models

        device = "cuda" if torch.cuda.is_available() else "cpu"
        ckpt   = torch.load(weights_path, map_location=device)

        # Reconstruct model — adjust if ROSIE uses a different backbone
        backbone = models.efficientnet_b0(weights=None)
        backbone.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(backbone.classifier[1].in_features, 50),
            nn.Sigmoid(),
        )
        # Load weights (handle DataParallel wrappers)
        state = ckpt.get("model_state_dict", ckpt)
        state = {k.replace("module.", ""): v for k, v in state.items()}
        backbone.load_state_dict(state, strict=False)
        backbone.eval().to(device)

        tf = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406],
                                  [0.229, 0.224, 0.225]),
        ])
        from PIL import Image
        out = []
        with torch.no_grad():
            for rgb in patches:
                img  = Image.fromarray(rgb)
                t    = tf(img).unsqueeze(0).to(device)
                pred = backbone(t).squeeze(0).cpu().numpy()
                out.append(pred)
        return np.stack(out).astype(np.float32)


# ── Demo surrogate (no weights) ─────────────────────────────────────────────

def _surrogate_predict(feat_matrix: "np.ndarray",
                        rng: "np.random.Generator") -> "np.ndarray":
    """
    COLOR-FEATURE SURROGATE — FOR PIPELINE DEMO ONLY.
    NOT biologically valid. NOT suitable for publication.

    Projects 9-D H&E colour/texture features to a 50-channel matrix
    using a fixed random linear map + sigmoid.  Results are plausible
    in range and structure but carry no quantitative meaning.
    """
    import numpy as np
    W = rng.normal(0, 0.15, size=(9, 50)).astype(np.float32)
    W[0, [0,1,2,3,5,6]]    += 0.3   # haematoxylin -> immune
    W[1, [15,16,20,21,24]] += 0.3   # eosin        -> tumour/stroma
    W[2, [25,26,27,28]]    += 0.2   # saturation   -> proliferation
    out = feat_matrix @ W
    return (1.0 / (1.0 + np.exp(-out))).astype(np.float32)


def _extract_color_features(rgb: "np.ndarray") -> "np.ndarray":
    import numpy as np
    r = rgb[..., 0] / 255. + 1e-6
    g = rgb[..., 1] / 255. + 1e-6
    b = rgb[..., 2] / 255. + 1e-6
    hem   = 0.644*(-np.log(r).mean()) + 0.717*(-np.log(g).mean()) + 0.267*(-np.log(b).mean())
    eosin = 0.093*(-np.log(r).mean()) + 0.954*(-np.log(g).mean()) + 0.284*(-np.log(b).mean())
    arr   = rgb.astype(np.float32)
    sat   = (arr.max(2) - arr.min(2)) / (arr.max(2) + 1e-6)
    tex   = arr.std(axis=(0, 1)) / 255.
    return np.array([hem, eosin, sat.mean(), sat.std(),
                     tex[0], tex[1], tex[2],
                     r.mean(), g.mean()], dtype=np.float32)


# ── Main process function ────────────────────────────────────────────────────

def process(state, params=None):
    import numpy as np, os
    from sklearn.cluster import KMeans

    tiles      = state.get("tiles", [])
    svs_path   = state.get("svs_path", "")
    patch_size = int(state.get("patch_size", 512))
    n_tiles    = len(tiles)

    if n_tiles == 0:
        print("No tiles in state — skipping ROSIE inference.")
        state.update({"protein_matrix": [], "protein_channels": PROTEIN_CHANNELS,
                      "zone_labels": [], "immune_score": 0.0,
                      "stromal_score": 0.0, "n_channels": 50,
                      "rosie_mode": "skipped"})
        return state

    rng          = np.random.default_rng(42)
    weights_path = _find_weights()
    have_slide   = bool(svs_path and os.path.exists(svs_path))

    # ── Choose inference mode ─────────────────────────────────────────────────
    if weights_path:
        print(f"ROSIE mode   : REAL MODEL  ({os.path.basename(weights_path)})")
        print(f"Processing   : {n_tiles} tiles x 50 protein channels")
        rosie_mode = "real_rosie"

        if have_slide:
            import openslide
            slide   = openslide.OpenSlide(svs_path)
            patches = []
            for tile in tiles:
                p = np.array(slide.read_region(
                        (tile["x"], tile["y"]), 0,
                        (patch_size, patch_size)).convert("RGB"), dtype=np.uint8)
                patches.append(p)
                if len(patches) % 50 == 0:
                    print(f"  loaded {len(patches)}/{n_tiles} patches")
            slide.close()
        else:
            print("  No SVS found — generating synthetic patches for weight test")
            patches = [rng.integers(0, 255, (patch_size, patch_size, 3),
                                    dtype=np.uint8) for _ in range(n_tiles)]

        protein_matrix = _rosie_predict_batch(patches, weights_path)

    else:
        # ── SURROGATE MODE ────────────────────────────────────────────────────
        print("=" * 62)
        print("  ROSIE mode : DEMO SURROGATE (color-feature proxy)")
        print("  Results below are for pipeline testing ONLY.")
        print("  They are NOT biologically valid.")
        print("  To use real ROSIE inference, provide model weights:")
        print("    1. Register: gitlab.com/enable-medicine-public/rosie")
        print("    2. Request approval from Enable Medicine (Rick)")
        print("    3. Set env var: ROSIE_WEIGHTS=/path/to/rosie_weights.pth")
        print("=" * 62)
        rosie_mode = "surrogate_demo"

        feat_matrix = np.zeros((n_tiles, 9), dtype=np.float32)
        if have_slide:
            import openslide
            slide = openslide.OpenSlide(svs_path)
            for i, tile in enumerate(tiles):
                p = np.array(slide.read_region(
                        (tile["x"], tile["y"]), 0,
                        (patch_size, patch_size)).convert("RGB"), dtype=np.uint8)
                feat_matrix[i] = _extract_color_features(p)
                if (i + 1) % 50 == 0:
                    print(f"  processed {i+1}/{n_tiles} patches")
            slide.close()
        else:
            for i, tile in enumerate(tiles):
                tf = tile.get("tissue_fraction", 0.7)
                feat_matrix[i] = rng.normal(
                    [tf*0.4, tf*0.2, tf*0.3, 0.1, 0.15, 0.12, 0.18, 0.6, 0.7], 0.05)

        protein_matrix = _surrogate_predict(feat_matrix, rng)

    # ── Shared post-processing ────────────────────────────────────────────────
    km = KMeans(n_clusters=3, n_init=10, random_state=0)
    km.fit(protein_matrix)
    zone_labels = km.labels_.tolist()

    means         = protein_matrix.mean(axis=0)
    immune_score  = float(means[[0,1,2,3,4]].mean())
    stromal_score = float(means[[20,21,22,23,24]].mean())

    top5 = means.argsort()[-5:][::-1]
    print(f"\nTop 5 expressed proteins ({rosie_mode}):")
    for idx in top5:
        print(f"  {PROTEIN_CHANNELS[idx]:8s}: {means[idx]:.3f}")
    print(f"Immune score  (T-cell panel) : {immune_score:.3f}")
    print(f"Stromal score (fibrosis panel): {stromal_score:.3f}")
    if rosie_mode == "surrogate_demo":
        print("[NOTE] Scores above are from the demo surrogate — not publication quality.")

    state.update({
        "protein_matrix":   protein_matrix.tolist(),
        "protein_channels": PROTEIN_CHANNELS,
        "zone_labels":      zone_labels,
        "immune_score":     round(immune_score, 4),
        "stromal_score":    round(stromal_score, 4),
        "n_channels":       50,
        "rosie_mode":       rosie_mode,
    })
    return state
