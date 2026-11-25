# Analysis code (npj SBA revision)

Runs on the per-tile ROSIE JSON outputs. Unit of replication = slide (n = 16; 8 F + 8 M); sex is a covariate.

| Script | What it does |
|---|---|
| `extract_cells.py` | Per slide: all tile JSONs -> one `.npz` (scores, global coordinates, tile, nucleus area flag). Reads old and new Node3 formats. |
| `common.py` | Marker panels, pooled robust-z reference, lineage scores, positivity, coarse cell states; slide-level tests (age trend with within-sex permutation, stage F-test, hinge change point with bootstrap), BH-FDR. |
| `slide_stats.py` | Composition, hybrid E/M (E+M+), E-M correlation, immune subset and checkpoint scores per slide; age / stage / change-point statistics; threshold sensitivity (q = 70/75/80). |
| `spatial_enrichment.py` | Neighbour enrichment of cell states (radius 20 um; 10/30 um sensitivity) against a within-tile label-shuffle null; age trend of log2(obs/exp). |
| `niche_transitions.py` | Tile-level niches (k-means, silhouette-selected K), niche occupancy vs age, continuous-time Markov model of occupancy with leave-one-slide-out edge stability. |
| `seg_compare.py` | Watershed vs StarDist: nuclei per tile, one-to-one matching (4 um), marker r for matched nuclei, composition agreement, concordance of slide-level results. **All A-vs-B numbers use the shared tiles only** (StarDist tiles independently and keeps 0-25 extra tiles per slide; watershed never has tiles StarDist lacks). Per slide it also reports the StarDist-only tiles and `delta_<state>_b_extra` = how much they shift composition - check M5 (21 extra tiles, 7.7% of its cells, unusually dense). |
| `run_analysis.slurm` | Runs everything on a Vista `gg` node. |
| `slide_meta.csv` | slide, sex, age_wk, stage, mpp. mpp = 0.5027 (Aperio SS7063, 20x; all 16 slides). `run_analysis.slurm` re-reads every SVS header first and aborts on a >1% mismatch. |

Classifier-free by design: the legacy rule-based `Phenotype` field is kept in the `.npz` but not used
(in the old female outputs 77% of cells were "Non_Immune_Unspec" and 8% "NK Cell").

Tested on 6 tiles x 8 female slides from the old pipeline (`test_cells/`, synthetic StarDist for seg_compare).
Those numbers are only a smoke test, not results.

Optional robustness runs: drop a slide (e.g. F4, flagged in QC) by removing it from a copy of
`slide_meta.csv` and passing that file with `--meta`.
