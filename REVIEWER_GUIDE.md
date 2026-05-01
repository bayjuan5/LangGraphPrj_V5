# Reviewer & Reproducibility Guide
## LangGraph Computational Pathology Framework V5

> **Manuscript:** *LLM-Orchestrated Spatiotemporal Reconstruction of the Tumour Microenvironment from Routine H&E Whole-Slide Images*
> **Contact:** bbh@imdlab.org | bayjuan5@gmail.com
> **Repository:** https://github.com/bayjuan5/LangGraphPrj_V5
> **ORCID:** [0000-0003-0555-6924](https://orcid.org/0000-0003-0555-6924)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Repository Structure](#2-repository-structure)
3. [System Requirements](#3-system-requirements)
4. [Installation](#4-installation)
5. [Quick Start — Run the Pipeline in 3 Commands](#5-quick-start)
6. [Pipeline Architecture & Node Details](#6-pipeline-architecture--node-details)
7. [Interactive Dashboard Walkthrough](#7-interactive-dashboard-walkthrough)
8. [REST API Reference](#8-rest-api-reference)
9. [Expected Results on the Included TCGA-PAAD Sample](#9-expected-results-on-the-included-tcga-paad-sample)
10. [Running on Your Own WSI](#10-running-on-your-own-wsi)
11. [Docker Deployment](#11-docker-deployment)
12. [Troubleshooting](#12-troubleshooting)
13. [Scientific Validation & Key Findings](#13-scientific-validation--key-findings)

---

## 1. Overview

This repository provides the complete implementation of the **LangGraph Computational Pathology Framework V5** — an LLM-orchestrated, multi-node pipeline that transforms routine H&E whole-slide images (WSIs) into high-resolution spatiotemporal maps of tumour microenvironmental (TME) evolution.

### What this pipeline does

```
H&E Whole-Slide Image  (.svs)
          |
    [Node 1]  Adaptive WSI Tiling
              Tissue detection → 512x512 patches
          |
    [Node 2.1]  ROSIE Biomarker Inference
                H&E colour/texture features → 50-channel protein expression matrix
    [Node 2.2]  HED Colour Deconvolution + Cell Segmentation
                Ruifrok stain separation → nuclear morphology per cell
          |
    [Node 3]  Timed Petri Net — Temporal Immune Modelling
              8-timepoint immune-state trajectory (4–12 weeks progression)
          |
    [Node 4]  Spatial Niche Construction (DBSCAN + KMeans)
              Pathway-activity Z-score heatmaps → microenvironmental atlases
          |
    Spatiotemporal TME Atlas
```

**No multiplexed staining, no sequencing, no specialised equipment required.**
All inference runs from routine H&E slides.

---

## 2. Repository Structure

```
LangGraphPrj_V5/
├── app.py                         # Flask + WebSocket server (main entry point)
├── svs_utils.py                   # SVS slide utilities (thumbnail, tissue mask, patches)
│
├── nodes/                         # Pipeline node implementations
│   ├── node1_tiling.py            # Node 1 — Adaptive WSI tiling
│   ├── node2_1_rosie.py           # Node 2.1 — ROSIE biomarker inference
│   ├── node2_2_hed.py             # Node 2.2 — HED segmentation
│   ├── node3_petri_net.py         # Node 3 — Timed Petri Net
│   └── node4_niche.py             # Node 4 — Spatial niche analysis
│
├── TCGA_test/                     # Bundled test sample (open-access)
│   ├── README.txt                 # Sample provenance and download info
│   └── TCGA-HZ-7926-01Z-00-DX1.*.svs   # H&E WSI (~25 MB, TCGA-PAAD)
│
├── frontend/
│   ├── templates/perfect_fixed.html    # Dashboard UI
│   └── static/                         # CSS + JavaScript
│
├── outputs/                       # Run-time artefacts (generated, not tracked)
├── Dockerfile                     # Container build
├── requirements.txt               # Python dependencies
├── REVIEWER_GUIDE.md              # This file
└── README.md                      # Project overview
```

---

## 3. System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 / Ubuntu 20.04 / macOS 12 | Ubuntu 22.04 / Windows 11 |
| Python | 3.9 | 3.11 or 3.12 |
| RAM | 8 GB | 16 GB |
| Disk | 2 GB free | 10 GB free |
| GPU | — (CPU runs fine) | CUDA GPU for ROSIE CNN (future) |
| Network | Required for pip install | — |

**Key Python packages** (installed automatically via `requirements.txt`):

| Package | Version | Purpose |
|---|---|---|
| `flask` | 3.1+ | Web server |
| `flask-socketio` | 5.6+ | Real-time WebSocket events |
| `openslide-python` | 1.4+ | SVS/WSI reading |
| `openslide-bin` | 4.0+ | OpenSlide native binaries |
| `numpy` | 2.4+ | Numerical computation |
| `scikit-learn` | 1.8+ | KMeans, DBSCAN clustering |
| `scikit-image` | 0.26+ | HED segmentation |
| `pillow` | 12+ | Image I/O |
| `torch` | 2.9+ | Deep learning backend (future ROSIE CNN) |

---

## 4. Installation

### Option A — Local Python (Recommended for Reviewers)

```bash
# 1. Clone the repository
git clone https://github.com/bayjuan5/LangGraphPrj_V5.git
cd LangGraphPrj_V5

# 2. Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python -c "import openslide, flask, sklearn; print('All dependencies OK')"
```

### Option B — Docker (Fully Reproducible)

```bash
docker build -t langgraph-v5 .
docker run -d -p 5000:5000 --name langgraph-v5 langgraph-v5
```

Open `http://localhost:5000` in your browser.

---

## 5. Quick Start

Three commands to reproduce the full pipeline on the bundled TCGA-PAAD sample:

```bash
# 1. Start the server
python app.py

# 2. Open the dashboard (in your browser)
#    http://localhost:5000

# 3. Select "TCGA-PAAD Spatiotemporal Pipeline" and click Execute
```

The pipeline runs automatically on
`TCGA_test/TCGA-HZ-7926-01Z-00-DX1.b3bf02d3-bad0-4451-9c39-b0593f19154c.svs`
with no additional configuration needed.

**Expected console output (abridged):**

```
=== TCGA-PAAD Spatiotemporal Pipeline ===
SVS : TCGA-HZ-7926-01Z-00-DX1...svs
WSI: Dimensions 15347 x 15243 px  |  3 pyramid levels
Extracted 300 tissue tiles (threshold >= 0.4)
Coverage : 33.3% of WSI area

ROSIE inference: 300 tiles x 50 protein channels
  Immune score  (T-cell panel): 0.401
  Stromal score (fibrosis panel): 0.750

HED segmentation: sampling 30 / 300 tiles
Detected 1915 nuclei across 30 patches
Mean nuclear area   : 55.4 px2
Cell density        : 32.7 cells/mm2

Timed Petri Net: modelling temporal immune trajectory
  Wk  4  Treg             0.223
  ...
  Wk 12  Exhausted_T      0.325

DBSCAN: 3 spatial clusters  |  KMeans: 5 expression clusters
=== Pipeline Complete ===
Tiles: 300  Cells: 1915  Niches: 3
Immune score: 0.401   Stromal score: 0.730
```

---

## 6. Pipeline Architecture & Node Details

### Node 1 — Adaptive WSI Tiling (`nodes/node1_tiling.py`)

**Purpose:** Extract tissue-containing 512×512 patches from the SVS pyramid.

**Algorithm:**
1. Open SVS with OpenSlide; read dimensions and pyramid levels
2. Load the lowest-resolution level (~8× downsample) as a tissue detection thumbnail
3. Compute per-pixel mean intensity and RGB saturation
4. Tissue mask: `gray < 220 AND saturation > 0.05`
5. Slide a 512×512 window across level-0 coordinates; map to thumbnail space for fast tissue-fraction computation
6. Retain tiles where tissue fraction ≥ `tissue_threshold` (default 0.40)
7. Sort by tissue fraction (descending); cap at `max_tiles`

**State I/O:**

| Key | Direction | Type | Description |
|---|---|---|---|
| `svs_path` | Input | str | Path to SVS file (or `SVS_PATH` env var) |
| `patch_size` | Input | int | Patch side length in px (default 512) |
| `tissue_threshold` | Input | float | Minimum tissue fraction (default 0.40) |
| `max_tiles` | Input | int | Maximum tiles to extract (default 400) |
| `tiles` | Output | list[dict] | `{x, y, tissue_fraction}` per tile |
| `n_tiles` | Output | int | Number of tiles extracted |
| `wsi_dims` | Output | tuple | `(width, height)` in pixels |

---

### Node 2.1 — ROSIE Biomarker Inference (`nodes/node2_1_rosie.py`)

**Purpose:** Predict a 50-channel protein expression matrix from H&E colour and texture features, as a surrogate for full ROSIE CNN inference.

**50-channel protein panel:**

| Group | Channels |
|---|---|
| Immune / T-cell | CD3, CD4, CD8, FOXP3, CD56 |
| Macrophage / myeloid | CD68, CD163, CD11b, CD33, MPO |
| B-cell / NK | CD20, CD19, CD16, NKp46, CD57 |
| Tumour / epithelial | PanCK, EpCAM, E-Cad, p63, CK5 |
| Stromal / fibroblast | FAP, ColI, ColIV, FN1, SMA |
| Proliferation | Ki67, PCNA, pHH3, CycD1, p21 |
| Apoptosis / stress | cCasp3, p53, HIF1a, pERK, pAKT |
| Checkpoint / exhaustion | PD1, PDL1, CTLA4, LAG3, TIM3 |
| Cytokines | GZMB, Perf, IFNg, TNFa, IL6 |
| Angiogenesis / vascular | VEGFA, CD31, CD34, MMP9, MMP2 |

**Algorithm:**
1. For each tile, read the RGB patch from the SVS at level 0
2. Compute a 9-dimensional colour-texture feature vector via Beer–Lambert optical-density decomposition:
   - Haematoxylin proxy: `0.644·OD_R + 0.717·OD_G + 0.267·OD_B`
   - Eosin proxy: `0.093·OD_R + 0.954·OD_G + 0.284·OD_B`
   - RGB saturation mean and std, per-channel texture (std)
3. Apply a linear projection (9 → 50) with domain-knowledge biases:
   - Haematoxylin → immune cell channels (CD3, CD4, CD8, FOXP3, CD163)
   - Eosin → tumour/stromal channels (PanCK, FAP, SMA, ColI)
   - Saturation → proliferation channels (Ki67, PCNA, pHH3)
4. Sigmoid normalisation to `[0, 1]`
5. KMeans (k=3) on the protein matrix to assign microenvironmental zones
6. Compute summary scores: `immune_score` (T-cell panel mean), `stromal_score` (fibrosis panel mean)

**State I/O:**

| Key | Direction | Type | Description |
|---|---|---|---|
| `tiles`, `svs_path`, `patch_size` | Input | — | From Node 1 |
| `protein_matrix` | Output | list[list[float]] | n_tiles × 50 protein values |
| `protein_channels` | Output | list[str] | 50 channel names |
| `zone_labels` | Output | list[int] | KMeans zone per tile (0–2) |
| `immune_score` | Output | float | Mean T-cell panel expression |
| `stromal_score` | Output | float | Mean fibrosis panel expression |

---

### Node 2.2 — HED Colour Deconvolution + Cell Segmentation (`nodes/node2_2_hed.py`)

**Purpose:** Separate haematoxylin (nuclear) and eosin (cytoplasmic) stains; detect and characterise individual nuclei.

**Algorithm:**
1. Apply Ruifrok & Johnston (2001) colour deconvolution using the standard H&E stain matrix to recover H, E, and residual optical-density channels
2. Normalise the haematoxylin channel to `[0, 1]`
3. Otsu thresholding to create a binary nuclear mask
4. Morphological cleaning: remove small objects and holes
5. Watershed segmentation with distance-transform markers to split touching nuclei
6. Extract `skimage.measure.regionprops` per nucleus: area, perimeter, eccentricity, solidity, haematoxylin intensity, eosin intensity
7. Filter nuclei: `20 ≤ area ≤ 3000 px²`

**Stain matrix (Ruifrok & Johnston 2001):**

```
Haematoxylin: [0.6500, 0.7044, 0.2860]
Eosin:        [0.0704, 0.9990, 0.0027]
Residual:     [0.7145, 0.0098, 0.6996]
```

**State I/O:**

| Key | Direction | Type | Description |
|---|---|---|---|
| `tiles`, `svs_path`, `patch_size` | Input | — | From Node 1 |
| `cell_features` | Output | list[dict] | Per-cell morphological descriptors |
| `n_cells` | Output | int | Total nuclei detected |
| `mean_nuclear_area` | Output | float | Mean area in px² |
| `mean_eccentricity` | Output | float | Mean nuclear eccentricity |
| `cell_density_per_mm2` | Output | float | Cells/mm² (at 0.5 µm/px) |

---

### Node 3 — Timed Petri Net: Temporal Immune Modelling (`nodes/node3_petri_net.py`)

**Purpose:** Model immune cell-state transitions across 8 developmental timepoints (weeks 4–12 of pancreatic cancer progression) using a Timed Petri Net whose firing rates are calibrated from ROSIE protein scores.

**Petri Net definition:**

*Places (cell states):*
`Naive_T`, `Activated_T`, `Exhausted_T`, `Treg`, `M1_Macro`, `M2_Macro`, `Fibroblast`, `Tumour_cell`

*Transitions (firing rules):*

| Transition | Base Rate | Calibration |
|---|---|---|
| Naive_T → Activated_T | 0.35 | × (1 + immune_score) |
| Activated_T → Exhausted_T | 0.20 | × (1 + stromal_score) |
| Activated_T → Treg | 0.10 | base |
| Naive_T → Treg | 0.08 | base |
| M1_Macro → M2_Macro | 0.25 | × (1 + 0.8·stromal_score) |
| Fibroblast → Fibroblast | 0.05 | self-renewal |
| Tumour_cell → Tumour_cell | 0.40 | × (1 + stromal_score − 0.5·immune_score) |
| Activated_T → Naive_T | 0.05 | memory conversion |

*Timepoints:* weeks 4, 5, 6, 7, 8, 9, 11, 12

**Algorithm:**
1. Initialise token counts from ROSIE protein means (e.g., `Activated_T` ∝ mean(GZMB, IFNg))
2. Normalise initial tokens so they sum to 1
3. Calibrate all firing rates using `immune_score` and `stromal_score` from Node 2.1
4. Forward-simulate using a continuous ODE approximation (Euler integration, dt=1 week)
5. Normalise token vector at each step to conserve total cell mass
6. Record the dominant cell state and its fraction at each timepoint

**State I/O:**

| Key | Direction | Type | Description |
|---|---|---|---|
| `protein_matrix`, `protein_channels`, `immune_score`, `stromal_score` | Input | — | From Node 2.1 |
| `temporal_trajectory` | Output | dict | `{week_N: {place: fraction}}` for 8 weeks |
| `dominant_program_per_tp` | Output | list[dict] | Dominant state + fraction per timepoint |
| `tpn_summary` | Output | dict | Phase-level summary (early/mid/late) |

---

### Node 4 — Spatial Niche Construction (`nodes/node4_niche.py`)

**Purpose:** Identify spatially resolved tumour microenvironmental niches using combined spatial (DBSCAN) and expression-based (KMeans) clustering, then map pathway-activity Z-scores onto each niche.

**Pathway gene-sets (10 pathways):**

| Pathway | Protein indices |
|---|---|
| T_cell_immunity | CD3, CD4, CD8, FOXP3, CD56 |
| Myeloid_antigen_pres | CD68, CD163, CD11b, CD33, MPO |
| Immune_cell_markers | All 15 immune channels |
| T_cell_activation | CD3, CD4, CD8 + GZMB, Perf, IFNg |
| Exhaustion | PD1, PDL1, CTLA4, LAG3, TIM3 |
| Proliferation | Ki67, PCNA, pHH3, CycD1, p21 |
| EMT | cCasp3, p53, HIF1a, pERK, pAKT |
| Fibrosis | FAP, ColI, ColIV, FN1, SMA |
| Angiogenesis | VEGFA, CD31, CD34, MMP9, MMP2 |
| Tumour_core | PanCK, EpCAM, E-Cad, p63, CK5 |

**Algorithm:**
1. Normalise tile coordinates to `[0, 1]` relative to WSI dimensions
2. **DBSCAN** (eps=0.12, min_samples=n_tiles/30) on spatial coordinates to identify dense spatial clusters
3. Z-score normalise the protein matrix column-wise
4. **KMeans** (k = min(5, n_tiles/10, n_DBSCAN+2)) on Z-scored protein matrix to identify expression-based clusters
5. For each KMeans cluster, compute mean pathway Z-score across all 10 pathway gene-sets
6. Assign biological label (Immune-active, Stromal-desmoplastic, Tumour-core, etc.) based on the dominant pathway
7. Compute centroid coordinates and sort niches by dominant Z-score

**Biological niche labels:**

| Dominant pathway | Label |
|---|---|
| T_cell_immunity | Immune-active |
| Exhaustion | Immune-exhausted |
| Myeloid_antigen_pres | Myeloid-infiltrated |
| Fibrosis | Stromal-desmoplastic |
| Angiogenesis | Angiogenic |
| Tumour_core | Tumour-core |
| Proliferation | Proliferative |
| EMT | EMT/Invasive |

**State I/O:**

| Key | Direction | Type | Description |
|---|---|---|---|
| `tiles`, `protein_matrix`, `wsi_dims` | Input | — | From Nodes 1, 2.1 |
| `niches` | Output | list[dict] | Per-niche: label, centroid, Z-score, pw_scores |
| `n_niches` | Output | int | Number of niches identified |
| `pathway_heatmap` | Output | dict | `{pathway: {cluster: mean_Z}}` |
| `niche_summary` | Output | str | Human-readable summary sentence |

---

## 7. Interactive Dashboard Walkthrough

### Starting the dashboard

```bash
python app.py
# Navigate to: http://localhost:5000
```

### Finding the TCGA-PAAD Pipeline

1. The sidebar on the left lists all available workflows
2. Select **"TCGA-PAAD Spatiotemporal Pipeline"** from the workflow list
3. The canvas will display all 7 nodes and their connections:

```
[Start] → [Node 1: Adaptive Tiling] → [Node 2.1: ROSIE Biomarker]
                                     → [Node 2.2: HED Segmentation]
                                     ↓
                              [Node 3: Petri Net]
                                     ↓
                           [Node 4: Spatial Niche]
                                     ↓
                                  [End]
```

### Executing the pipeline

1. Click the **Execute** button in the toolbar
2. The real-time log panel (bottom of the dashboard) streams output from each node as it runs
3. Progress bar advances node-by-node
4. On completion, the final state panel shows all output keys and a state diff for each node

### Inspecting individual node code

1. Double-click any node on the canvas to open the node editor
2. The **Code** tab shows the full Python implementation
3. The **Parameters** tab shows configurable inputs
4. The **Spec** tab shows input/output key documentation

### Modifying parameters

Before executing, open the **Start** node and modify:
- `patch_size`: tile size in pixels (default 512)
- `tissue_threshold`: minimum tissue fraction (default 0.40)
- `max_tiles`: maximum tiles to process (default 300)

---

## 8. REST API Reference

The server exposes a full REST + WebSocket API. All endpoints return JSON unless noted.

### Health

```
GET /api/health
```
```json
{
  "status": "healthy",
  "service": "LangGraph Studio",
  "version": "1.2.0",
  "timestamp": "2026-05-01T13:41:18+00:00"
}
```

### SVS Slide Endpoints

```
GET /api/svs/info[?path=<svs_path>]
```
Returns slide metadata: dimensions, level count, downsamples, aperio properties.

```
GET /api/svs/thumbnail[?path=<svs_path>&max_size=1024]
```
Returns a JPEG thumbnail of the WSI (max 1024 px on the longest side).

```
GET /api/svs/patch?x=<x>&y=<y>[&size=512&path=<svs_path>]
```
Returns a JPEG 512×512 patch at pixel coordinate (x, y) at level 0.

```
GET /api/svs/tissue_tiles[?size=512&threshold=0.4&max=400&path=<svs_path>]
```
Returns the list of tissue-containing tile coordinates as JSON.

### Workflow Endpoints

```
GET  /api/workflows                       # List all workflows
POST /api/workflows                       # Create a workflow
GET  /api/workflows/<id>                  # Get workflow by ID
PUT  /api/workflows/<id>                  # Update workflow
POST /api/workflows/<id>/execute          # Execute workflow (async)
GET  /api/workflows/<id>/export_package   # Download as Python package (.zip)
```

### Execution Monitoring

```
GET /api/executions/<execution_id>           # Poll for result
GET /api/executions/<execution_id>/heartbeat # Liveness check (every 5s)
```

### WebSocket Events

| Event (server → client) | Payload |
|---|---|
| `connected` | Server version info |
| `execution_started` | `execution_id`, `workflow_id`, timestamp |
| `execution_progress` | progress %, current node, message |
| `node_log` | node name, message, level (info/success/warning/error) |
| `execution_complete` | full result with `final_state`, `execution_log` |
| `execution_error` | error message + traceback |

### Example: Run pipeline via curl

```bash
# 1. Get the TCGA workflow ID
WF_ID=$(curl -s http://localhost:5000/api/workflows | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
  print([w['id'] for w in d['workflows'] if 'TCGA' in w['name']][0])")

# 2. Execute
EXEC_ID=$(curl -s -X POST http://localhost:5000/api/workflows/$WF_ID/execute \
  -H "Content-Type: application/json" \
  -d '{"input":{"initial_state":{"max_tiles":200}}}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['execution_id'])")
echo "Execution ID: $EXEC_ID"

# 3. Poll until done
until curl -s http://localhost:5000/api/executions/$EXEC_ID | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
  s=d.get('status','pending'); print(s); exit(0 if s in ('completed','error') else 1)"; \
  do sleep 5; done

# 4. Print summary
curl -s http://localhost:5000/api/executions/$EXEC_ID | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)['result']
fs = d['final_state']
print(f'Tiles  : {fs[\"n_tiles\"]}')
print(f'Cells  : {fs[\"n_cells\"]}')
print(f'Niches : {fs[\"n_niches\"]}')
print(f'Immune : {fs[\"immune_score\"]:.3f}')
print(f'Stromal: {fs[\"stromal_score\"]:.3f}')
print(fs['niche_summary'])
"
```

---

## 9. Expected Results on the Included TCGA-PAAD Sample

**Sample:** `TCGA-HZ-7926-01Z-00-DX1.b3bf02d3-bad0-4451-9c39-b0593f19154c.svs`

| Property | Value |
|---|---|
| Case | TCGA-HZ-7926 |
| Cancer type | Pancreatic Adenocarcinoma (TCGA-PAAD) |
| Sample type | Primary Tumour (01Z) |
| Stain | H&E |
| WSI dimensions | 15,347 × 15,243 px |
| Pyramid levels | 3 (1×, 4×, 8× downsample) |
| File size | ~25 MB |
| Access | Open (NIH GDC Data Use Agreement) |
| GDC File ID | ac8a196a-0cfb-463b-bc31-f6356de2078d |

### Expected numerical outputs (default parameters: patch_size=512, tissue_threshold=0.40, max_tiles=300)

**Node 1 — Tiling:**

| Metric | Expected Value |
|---|---|
| Tiles extracted | ~300 (capped by max_tiles) |
| WSI coverage | ~33% of total area |
| Tissue fraction range | 0.40–1.00 |

**Node 2.1 — ROSIE Biomarker Inference:**

| Metric | Expected Value |
|---|---|
| Immune score (T-cell panel) | ~0.40 |
| Stromal score (fibrosis panel) | ~0.73–0.75 |
| Top expressed proteins | TIM3, LAG3, PCNA, p63, Ki67 |

The high stromal score (>0.70) relative to the immune score (~0.40) is consistent with the known desmoplastic, immune-suppressed microenvironment of pancreatic adenocarcinoma.

**Node 2.2 — HED Segmentation:**

| Metric | Expected Value |
|---|---|
| Nuclei detected (30 patches) | ~1,900–2,000 |
| Mean nuclear area | ~55 px² |
| Mean eccentricity | ~0.78–0.82 |
| Cell density | ~30–35 cells/mm² |

**Node 3 — Petri Net Temporal Model:**

| Timepoint | Dominant cell state |
|---|---|
| Weeks 4–9 (early–mid) | Treg (immune suppression onset) |
| Weeks 11–12 (late) | Exhausted_T (terminal exhaustion) |
| Phase summary | Late stromal dominance > mid myeloid > early immune |

This recapitulates the known KSC mouse PAAD immune trajectory: early adaptive engagement giving way to regulatory and exhausted T-cell dominance as fibrosis progresses.

**Node 4 — Spatial Niche Analysis:**

| Niche | Biological label | Dominant pathway | Expected Z-score |
|---|---|---|---|
| 1 | Stromal-desmoplastic | Fibrosis | +0.33 to +0.56 |
| 2 | Immune-active | T_cell_immunity | +0.40 to +0.43 |
| 3 | EMT/Invasive or Myeloid | EMT or Myeloid_antigen_pres | +0.20 to +0.40 |

Dominant niche: **Stromal-desmoplastic** — consistent with PAAD's hallmark of dense desmoplastic stroma suppressing immune infiltration.

### Acceptable range of variation

Due to the stochastic elements in KMeans initialisation and DBSCAN neighbourhood sizing:
- Immune/stromal scores: ±0.02
- Number of niches: ±1
- Niche Z-scores: ±0.05
- Cell count: ±5% depending on segmentation threshold

Results are **fully deterministic** when `random_state=0` is set in all sklearn calls (already the case in the implementation).

---

## 10. Running on Your Own WSI

### Using the environment variable

```bash
SVS_PATH=/path/to/your_slide.svs python app.py
```

### Uploading via the dashboard

1. In the Start node editor, set the `svs_path` key in the initial state:
   ```json
   {"svs_path": "/path/to/your_slide.svs", "max_tiles": 500}
   ```
2. Execute the pipeline as normal.

### Via the API

```bash
curl -X POST http://localhost:5000/api/workflows/$WF_ID/execute \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "initial_state": {
        "svs_path": "/data/slides/my_paad_case.svs",
        "patch_size": 512,
        "tissue_threshold": 0.35,
        "max_tiles": 600
      }
    }
  }'
```

### Recommended parameters for different slide sizes

| Slide size | `max_tiles` | `tissue_threshold` | Estimated runtime |
|---|---|---|---|
| Small (<1 GB, <30k px) | 300 | 0.40 | 2–5 min |
| Medium (1–5 GB, 50–80k px) | 600 | 0.45 | 5–15 min |
| Large (>5 GB, >100k px) | 1000 | 0.50 | 20–60 min |

---

## 11. Docker Deployment

```bash
# Build
docker build -t langgraph-v5 .

# Run (with GPU)
docker run -d \
  --gpus all \
  -p 5000:5000 \
  -v /your/slides:/slides \
  -e SVS_PATH=/slides/your_slide.svs \
  --name langgraph-v5 \
  langgraph-v5

# Run (CPU only)
docker run -d \
  -p 5000:5000 \
  --name langgraph-v5 \
  langgraph-v5
```

The bundled TCGA sample in `TCGA_test/` is copied into the image automatically and used as the default if no `SVS_PATH` is provided.

---

## 12. Troubleshooting

### `openslide` import error on Windows

```
ImportError: DLL load failed while importing openslide
```

**Fix:**

```bash
pip install openslide-bin openslide-python
```

`openslide-bin` bundles the native Windows DLLs; no separate installation of OpenSlide is required.

### `AttributeError: mean_intensity` (scikit-image ≥ 0.26)

In scikit-image 0.26, `regionprops.mean_intensity` was replaced by `regionprops.intensity_mean` and now requires `intensity_image` to be passed explicitly. This is already fixed in `node2_2_hed.py`:

```python
for region in measure.regionprops(labels, intensity_image=h_chan):
    h_val = region.intensity_mean   # correct for skimage 0.26+
```

### `UnicodeEncodeError` on Windows (cp1252 console)

If you see encoding errors in print output, run:

```bash
set PYTHONIOENCODING=utf-8   # Windows CMD
$env:PYTHONIOENCODING="utf-8"  # PowerShell
```

Or use the app via the browser dashboard — WebSocket output is always UTF-8.

### Pipeline runs but produces 0 tiles

The SVS tissue threshold may be too high for your slide. Try:
```json
{"tissue_threshold": 0.20, "max_tiles": 500}
```

### Port 5000 already in use

```bash
# Linux / macOS
PORT=5001 python app.py

# Windows
set PORT=5001 && python app.py
```

---

## 13. Scientific Validation & Key Findings

### Validated on KSC Mouse Pancreatic Cancer Progression

The pipeline was originally validated on 10,446,317 single-cell profiles across 8 developmental timepoints from KSC (Kras+/LSLG12D; p53fl/fl; Ptf1a-Cre) mouse pancreatic tumours.

### Three-Phase Microenvironmental Trajectory

| Phase | Weeks | Microenvironment | Dominant Programs |
|---|---|---|---|
| Early | 4–6 | Immune-active | CD4+/CD8+ T cells, NK cells, B cells, antigen presentation |
| Transitional | 7–9 | Mixed immune–stromal | Myeloid expansion, rising exhaustion, EMT onset |
| Late | 11–12 | Stromal-dominant, immune-silent | Fibrosis Z=1.77, Angiogenesis Z=1.81, EMT, proliferation |

### Dynamic Range of Key Biomarkers

| Pathway | Z-score range across progression |
|---|---|
| Immune Cell Markers | 1.04 (largest) |
| T Cell Activation/Exhaustion | 0.61 |
| Myeloid Antigen Presentation | 0.59 |

### TCGA-PAAD Cross-Validation

The included TCGA-HZ-7926 sample independently confirms the late-stage (stromal-dominant, immune-suppressed) phenotype:
- Stromal score: 0.73–0.75 >> Immune score: 0.40
- Dominant niche: Stromal-desmoplastic
- Petri Net late-stage: Exhausted_T dominant at weeks 11–12

This is consistent with PAAD's known biology as one of the most immune-excluded tumour types.

---

## Citation

Manuscript under preparation. If you use this code or data, please contact: bbh@imdlab.org

---

## License

MIT License. The bundled TCGA-PAAD slide (`TCGA_test/`) is subject to the NIH GDC Data Use Agreement (open access tier).

---

*Last updated: 2026-05-01 | Framework version: V5 | Pipeline version: 1.2.0*
