# precancer_dynamics

Code and processed results for:

> Huang B, Zhu B. *Virtual multiplexed histology reveals staged immune and stromal state transitions in pancreatic precancer.*

The study applies ROSIE (50 protein markers inferred per cell from H&E) to 16 whole-slide sections of KSC mouse pancreata (8 female, 8 male; 4–12 weeks; 13.0 million nuclei) and models how lineage composition, spatial neighbourhoods and tissue niches change with age.

This folder is version 2 of the workflow. The original version described in the bioRxiv preprint (watershed segmentation, sliding-window ROSIE, timed Petri net) is kept unchanged at the top level of this repository (`nodes/`, `app.py`, `frontend/`).

## Folder layout

| Folder | Contents |
|---|---|
| `environment/` | Conda environment scripts for ROSIE (PyTorch 2.6) and StarDist 0.9.2 (TensorFlow 2.20); `config.sh` sets `ROSIE_ROOT` and `ROSIE_ENV` (edit for your system). |
| `pipeline/` | Per-slide processing: Node 1 tiling (`Node1.py`), Node 2 StarDist detection on 2×-upsampled tiles (`node2_stardist.py`), Node 3 cell-centred ROSIE inference (`node3_cellcentered.py`); SLURM job scripts; `F4_check/` reproduces the equivalence check against the original inference (r = 0.99991). |
| `analysis/` | Pooled analyses with the slide as the unit of replication: lineage scores and states, slide-level statistics and change points, neighbourhood enrichment, tissue niches and continuous-time Markov models, sex interaction, HALO comparison, detection-setting comparison. See `analysis/README.md` and `analysis/RUN_ORDER.md`. |
| `detection_validation/` | Curated nucleus annotations (419 nuclei, three regions), StarDist threshold sweep, recall/precision scripts, QuPath scripts, and whole-slide image QC. |
| `figures/` | Scripts that draw Figs 1–7 and Supplementary Fig. S2. |
| `results/` | Slide-level outputs (CSV/JSON). `sd2x04` = primary setting (StarDist, 2× upsampling, probability threshold 0.4); `sd2x` = default threshold; `sd` = native resolution; `seg_compare*` = comparisons between settings. |

## Inputs not included here

- **ROSIE model weights** (`best_model_single.pth`, MD5 72f896a8f9a8d5571dec401e7055a5b9): see `GET_ROSIE_WEIGHTS.md` at the repository root and https://gitlab.com/enable-medicine-public/rosie.
- **Whole-slide images**: available from the corresponding author on reasonable request.
- **Per-nucleus outputs** (coordinates, 50 inferred markers and lineage scores for 13.0 million nuclei): deposited in Zenodo (DOI to be added).
- **HALO trichrome measurements** used by `analysis/halo_validation.py` come from Sharma et al., *Clin Cancer Res* 2025; contact the authors of that study.

## Running

Processing was run on the Texas Advanced Computing Center systems (Vista, NVIDIA GH200). The order of jobs is in `analysis/RUN_ORDER.md`. No language model is called at run time; the scripts were drafted with language-model assistance and reviewed, tested and frozen before the reported analyses.
