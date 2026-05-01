# 🧬 LangGraph Computational Pathology Framework V5

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-v1.1.2-green)](https://github.com/langchain-ai/langgraph)
[![Docker](https://img.shields.io/badge/Docker-Containerized-blue?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/bayjuan5/LangGraphPrj_V5/blob/main/reviewer_colab.ipynb)

> **LLM-orchestrated computational pathology pipeline** for spatiotemporal reconstruction of tumor microenvironments from routine H&E whole-slide images — no specialized staining or molecular assays required.

---

## ▶️ Run instantly — no installation required

Click the badge above, or go directly to:

**👉 [Open in Google Colab](https://colab.research.google.com/github/bayjuan5/LangGraphPrj_V5/blob/main/reviewer_colab.ipynb)**

Then: **Runtime → Run all** — the full pipeline runs in ~4 minutes and produces all figures automatically.

---

## 💻 Run locally — one click

**Windows** — double-click `setup_and_run.bat`
> Installs packages, starts the server, opens the dashboard in your browser automatically.

**macOS / Linux:**
```bash
bash setup_and_run.sh
```

Then open **http://localhost:5000**, select **"TCGA-PAAD Spatiotemporal Pipeline"**, and click **Execute**.

A bundled open-access TCGA-PAAD H&E slide (`TCGA_test/`) is included — no data download needed.

---

## 📄 Associated Publication

Manuscript under preparation. Details available upon request.
Contact: bbh@imdlab.org

> **Key result:** Analyzed **10,446,317 single-cell profiles** across 8 developmental timepoints, reconstructing a full temporal immune trajectory: early adaptive engagement → mixed immune–stromal transition → stromal-dominant immunosuppression.

---

## 🔬 What This Pipeline Does

```
H&E Whole-Slide Image (SVS)
        ↓
  [Node 1] Adaptive WSI Tiling (512×512 patches)
        ↓
  [Node 2.1] ROSIE Biomarker Inference → 50-channel protein feature maps
  [Node 2.2] HED Segmentation → Per-cell morphological descriptors
        ↓
  [Node 3] Timed Petri Net → Temporal immune-state modeling (4–12 weeks)
        ↓
  [Node 4] DBSCAN + KMeans Spatial Niche Analysis → Pathway-activity heatmaps
        ↓
  Spatiotemporal microenvironmental atlas
```

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🤖 **LLM Orchestration** | LangGraph v1.1.2 state-graph manages node transitions and data-flow |
| 🔬 **ROSIE Integration** | 50-channel protein expression inferred directly from H&E colour features |
| ⏱️ **Temporal Modeling** | Timed Petri Net encodes cell-state transitions across 8 developmental timepoints |
| 🗺️ **Spatial Niche Analysis** | DBSCAN + KMeans maps pathway programs onto spatially resolved microenvironments |
| 👁️ **Interactive Dashboard** | Real-time node-by-node execution log, code editor, state diff viewer |
| 🧪 **Test Sample Included** | Open-access TCGA-PAAD H&E slide bundled — run immediately, no download |
| 📓 **Colab Notebook** | Zero-install reproducibility for reviewers |
| 🐳 **Containerized** | Docker image for reproducible, portable deployment |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              LangGraph State Graph Orchestrator          │
│                                                         │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────────┐ │
│  │  Node 1  │──▶│  Node 2.1   │   │    Node 2.2     │ │
│  │WSI Tiling│   │ROSIE Biomark│   │HED Segmentation │ │
│  └──────────┘   └──────┬───────┘   └────────┬────────┘ │
│                         └──────────┬─────────┘          │
│                                    ▼                     │
│                           ┌────────────────┐            │
│                           │    Node 3      │            │
│                           │  Petri Net /   │            │
│                           │Temporal Model  │            │
│                           └───────┬────────┘            │
│                                   ▼                     │
│                           ┌────────────────┐            │
│                           │    Node 4      │            │
│                           │ Spatial Niche  │            │
│                           │   Analysis     │            │
│                           └────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Scientific Results (10.44M Cells)

| Stage | Microenvironment | Dominant Programs |
|---|---|---|
| **4–6 weeks (Early)** | Immune-active | CD4⁺/CD8⁺ T cells, NK cells, B cells, antigen presentation |
| **7–9 weeks (Transitional)** | Mixed immune–stromal | Myeloid expansion, rising exhaustion, EMT onset |
| **11–12 weeks (Late)** | Stromal-dominant, immune-silent | Fibrosis Z=1.77, Angiogenesis Z=1.81, EMT, proliferation |

> Immune Cell Markers showed the largest dynamic range across progression (range = 1.04), followed by T Cell Activation/Exhaustion (0.61) and Myeloid Antigen Presentation (0.59).

---

## 🚀 Installation (manual)

```bash
git clone https://github.com/bayjuan5/LangGraphPrj_V5.git
cd LangGraphPrj_V5
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` → select **TCGA-PAAD Spatiotemporal Pipeline** → **Execute**.

### Docker

```bash
docker build -t langgraph-v5 .
docker run -d -p 5000:5000 langgraph-v5
```

### Custom WSI

```bash
SVS_PATH=/path/to/your_slide.svs python app.py
```

---

## 📁 Repository Structure

```
LangGraphPrj_V5/
├── app.py                    # Main server (Flask + WebSocket)
├── svs_utils.py              # SVS slide utilities
├── nodes/                    # Pipeline node implementations
│   ├── node1_tiling.py       #   Node 1 — Adaptive WSI tiling
│   ├── node2_1_rosie.py      #   Node 2.1 — ROSIE biomarker inference
│   ├── node2_2_hed.py        #   Node 2.2 — HED segmentation
│   ├── node3_petri_net.py    #   Node 3 — Timed Petri Net
│   └── node4_niche.py        #   Node 4 — Spatial niche analysis
├── TCGA_test/                # Bundled test sample (open-access, ~25 MB)
├── reviewer_colab.ipynb      # Zero-install Colab notebook for reviewers
├── REVIEWER_GUIDE.md         # Full reviewer & reproducibility guide
├── setup_and_run.bat         # Windows one-click launcher
├── setup_and_run.sh          # macOS/Linux one-click launcher
├── frontend/                 # Interactive dashboard (WebSocket, real-time)
├── Dockerfile                # Containerized environment
└── requirements.txt          # Python dependencies
```

---

## 📚 For Reviewers

| Resource | Link |
|---|---|
| **Full reproducibility guide** | [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) |
| **Zero-install Colab notebook** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/bayjuan5/LangGraphPrj_V5/blob/main/reviewer_colab.ipynb) |
| **Expected results** | [REVIEWER_GUIDE.md#9](REVIEWER_GUIDE.md#9-expected-results-on-the-included-tcga-paad-sample) |
| **Troubleshooting** | [REVIEWER_GUIDE.md#12](REVIEWER_GUIDE.md#12-troubleshooting) |

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | LangGraph v1.1.2, LangChain |
| **LLM Backends** | Claude 3.5 Sonnet (primary), Llama 2 7B (local fallback) |
| **Biomarker Inference** | ROSIE (50-channel protein prediction from H&E) |
| **Spatial Clustering** | DBSCAN, KMeans |
| **Temporal Modeling** | Timed Petri Net |
| **Containerization** | Docker |
| **Backend** | Python, Flask, WebSocket |
| **Frontend** | JavaScript, HTML/CSS |

---

## 👩‍🔬 Author

**Beibei Huang, Ph.D.**
Senior Data Scientist & ML Engineer | MD Anderson Cancer Center
[github.com/bayjuan5](https://github.com/bayjuan5) | [imdlab.org](https://imdlab.org) | bbh@imdlab.org
ORCID: [0000-0003-0555-6924](https://orcid.org/0000-0003-0555-6924)

---

## 📚 Citation

Manuscript under preparation. Contact: bbh@imdlab.org
