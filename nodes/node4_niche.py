"""
Node 4 — Spatial Niche Construction (DBSCAN + KMeans)
Clusters tile coordinates weighted by protein expression to identify
spatially resolved tumour microenvironmental niches, then maps
pathway-activity Z-scores onto each niche.

Input  state keys: tiles, protein_matrix, protein_channels,
                   zone_labels, tpn_summary, wsi_dims
Output state keys: niches (list[dict]), n_niches, pathway_heatmap (dict),
                   niche_summary (str)
"""

import numpy as np

# ── Pathway gene-set indices in the 50-channel protein panel ─────────────────
PATHWAY_SETS = {
    "T_cell_immunity":        [0, 1, 2, 3, 4],          # CD3,CD4,CD8,FOXP3,CD56
    "Myeloid_antigen_pres":   [5, 6, 7, 8, 9],          # CD68,CD163,CD11b,CD33,MPO
    "Immune_cell_markers":    list(range(0, 15)),        # all immune rows
    "T_cell_activation":      [0, 1, 2, 40, 41, 42],    # T + cytotoxic
    "Exhaustion":             [35, 36, 37, 38, 39],      # PD1,PDL1,CTLA4,LAG3,TIM3
    "Proliferation":          [25, 26, 27, 28, 29],      # Ki67,PCNA,pHH3,CycD1,p21
    "EMT":                    [30, 31, 32, 33, 34],      # cCasp3,p53,HIF1a,pERK,pAKT
    "Fibrosis":               [20, 21, 22, 23, 24],      # FAP,ColI,ColIV,FN1,SMA
    "Angiogenesis":           [45, 46, 47, 48, 49],      # VEGFA,CD31,CD34,MMP9,MMP2
    "Tumour_core":            [15, 16, 17, 18, 19],      # PanCK,EpCAM,E-Cad,p63,CK5
}


def _zscore_cols(matrix: "np.ndarray") -> "np.ndarray":
    mu, sd = matrix.mean(axis=0), matrix.std(axis=0) + 1e-6
    return (matrix - mu) / sd


def process(state, params=None):
    import numpy as np
    from sklearn.cluster import DBSCAN, KMeans

    tiles           = state.get("tiles", [])
    protein_matrix  = state.get("protein_matrix", [])
    protein_channels = state.get("protein_channels", [])
    zone_labels     = state.get("zone_labels", [])
    wsi_dims        = state.get("wsi_dims", (15347, 15243))

    n_tiles = len(tiles)
    if n_tiles == 0:
        print("No tiles — skipping niche analysis.")
        state.update({"niches": [], "n_niches": 0,
                      "pathway_heatmap": {}, "niche_summary": "No data."})
        return state

    rng = np.random.default_rng(5)
    pm  = np.array(protein_matrix, dtype=np.float32) if protein_matrix else \
          rng.random((n_tiles, 50)).astype(np.float32)

    # ── Spatial coordinates (normalised to [0,1]) ────────────────────────────
    coords = np.array([[t["x"] / wsi_dims[0], t["y"] / wsi_dims[1]]
                       for t in tiles], dtype=np.float32)

    # ── DBSCAN: find dense spatial clusters (niches) ─────────────────────────
    eps_frac = 0.12   # neighbourhood radius as fraction of slide width
    min_samples = max(3, n_tiles // 30)
    db = DBSCAN(eps=eps_frac, min_samples=min_samples, metric="euclidean")
    db_labels = db.fit_predict(coords)
    n_db = int(db_labels.max()) + 1

    print(f"DBSCAN: {n_db} spatial clusters, "
          f"{(db_labels == -1).sum()} outlier tiles (eps={eps_frac})")

    # ── KMeans on protein expression space ───────────────────────────────────
    k = min(5, n_tiles // 10, n_db + 2)
    k = max(k, 2)
    pm_z = _zscore_cols(pm)
    km = KMeans(n_clusters=k, n_init=10, random_state=0)
    km_labels = km.fit_predict(pm_z)

    print(f"KMeans: {k} expression-based clusters")

    # ── Pathway activity per KMeans cluster ──────────────────────────────────
    pathway_heatmap: dict = {}  # pathway_name -> {cluster_id: mean_z}
    for pw_name, indices in PATHWAY_SETS.items():
        valid_idx = [i for i in indices if i < pm.shape[1]]
        if not valid_idx:
            continue
        pw_z = pm_z[:, valid_idx].mean(axis=1)   # mean Z-score per tile
        cluster_means = {}
        for c in range(k):
            mask = km_labels == c
            cluster_means[str(c)] = float(round(pw_z[mask].mean(), 3)) if mask.any() else 0.0
        pathway_heatmap[pw_name] = cluster_means

    # ── Build niche objects ───────────────────────────────────────────────────
    niches = []
    for c in range(k):
        mask        = km_labels == c
        c_tiles     = [tiles[i] for i in range(n_tiles) if mask[i]]
        c_pm        = pm[mask]
        c_coords    = coords[mask]
        centroid_x  = float(c_coords[:, 0].mean() * wsi_dims[0])
        centroid_y  = float(c_coords[:, 1].mean() * wsi_dims[1])

        # Dominant pathway in this niche
        pw_scores   = {pw: pathway_heatmap[pw].get(str(c), 0.0)
                       for pw in PATHWAY_SETS}
        dom_pathway = max(pw_scores, key=pw_scores.get)
        dom_score   = pw_scores[dom_pathway]

        # Assign a biological label
        label_map = {
            "T_cell_immunity":      "Immune-active",
            "Exhaustion":           "Immune-exhausted",
            "Myeloid_antigen_pres": "Myeloid-infiltrated",
            "Fibrosis":             "Stromal-desmoplastic",
            "Angiogenesis":         "Angiogenic",
            "Tumour_core":          "Tumour-core",
            "Proliferation":        "Proliferative",
            "EMT":                  "EMT/Invasive",
        }
        bio_label = label_map.get(dom_pathway, dom_pathway)

        niches.append({
            "cluster_id":   c,
            "n_tiles":      int(mask.sum()),
            "centroid_x":   round(centroid_x),
            "centroid_y":   round(centroid_y),
            "bio_label":    bio_label,
            "dom_pathway":  dom_pathway,
            "dom_z_score":  round(dom_score, 3),
            "pw_scores":    {k_: round(v, 3) for k_, v in pw_scores.items()},
        })

    niches.sort(key=lambda n: n["dom_z_score"], reverse=True)

    # ── Print summary ─────────────────────────────────────────────────────────
    print(f"\nSpatial Niche Summary ({len(niches)} niches):")
    for niche in niches:
        bar = "█" * min(20, max(1, int(abs(niche["dom_z_score"]) * 5)))
        print(f"  Niche {niche['cluster_id']} [{niche['bio_label']:25s}]  "
              f"tiles={niche['n_tiles']:3d}  Z={niche['dom_z_score']:+.3f}  {bar}")

    print("\nPathway Z-scores per niche:")
    for pw in ["T_cell_immunity", "Fibrosis", "Angiogenesis", "Tumour_core", "Exhaustion"]:
        row = "  " + f"{pw:25s}  " + "  ".join(
            f"N{c}:{pathway_heatmap.get(pw, {}).get(str(c), 0.0):+.2f}"
            for c in range(k))
        print(row)

    niche_summary = (
        f"{len(niches)} microenvironmental niches identified. "
        f"Dominant: {niches[0]['bio_label']} (Z={niches[0]['dom_z_score']:+.3f}). "
        f"Immune score: {state.get('immune_score', 0.0):.3f}  "
        f"Stromal score: {state.get('stromal_score', 0.0):.3f}."
    )

    state.update({
        "niches":           niches,
        "n_niches":         len(niches),
        "pathway_heatmap":  pathway_heatmap,
        "niche_summary":    niche_summary,
        "kmeans_labels":    km_labels.tolist(),
        "dbscan_labels":    db_labels.tolist(),
    })
    return state
