# 🧬 LangGraph Computational Pathology Framework V5

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-v1.1.2-green)](https://github.com/langchain-ai/langgraph)
[![Docker](https://img.shields.io/badge/Docker-Containerized-blue?logo=docker)](https://www.docker.com/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-orange?logo=github-actions)](https://github.com/features/actions)
[![Prometheus](https://img.shields.io/badge/Monitoring-Prometheus%2FGrafana-red?logo=prometheus)](https://prometheus.io/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

> **LLM-orchestrated computational pathology pipeline** for spatiotemporal reconstruction of tumor microenvironments from routine H&E whole-slide images — no specialized staining or molecular assays required.

---

## 📄 Associated Publication

Manuscript under preparation. Details available upon request.
Contact: bbh@imdlab.org

> **Key result:** Analyzed **10,446,317 single-cell profiles** across 8 developmental timepoints, reconstructing a full temporal immune trajectory from early adaptive engagement → mixed immune–stromal transition → stromal-dominant immunosuppression.

---

## 🔬 What This Pipeline Does

This framework transforms **routine H&E whole-slide images (WSIs)** into high-resolution spatial and temporal maps of tumor microenvironmental evolution — entirely without multiplexed staining, sequencing, or specialized equipment.

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
| 🤖 **LLM Orchestration** | LangGraph v1.1.2 state-graph manages node transitions, data-flow, and cyclic execution |
| 🧠 **RAG Knowledge Base** | FAISS-backed retrieval of domain-specific literature for biologically grounded LLM prompts |
| 🔬 **ROSIE Integration** | Deep-learning inference of 50-channel protein expression directly from H&E patches |
| ⏱️ **Temporal Modeling** | Timed Petri Net encodes cell-state transitions across 8 developmental timepoints |
| 🗺️ **Spatial Niche Analysis** | DBSCAN + KMeans clustering maps pathway programs onto spatially resolved microenvironments |
| 📊 **Real-time Monitoring** | Prometheus/Grafana metrics: per-node latency, cell throughput, immune fraction |
| 🐳 **Containerized** | Docker image (~8.5GB) for reproducible, portable deployment |
| ✅ **CI/CD** | GitHub Actions with automated testing and validation gates |
| 👁️ **Human-in-the-Loop** | Interactive dashboard for real-time inspection of intermediate outputs and model selection |

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
│                         │                    │          │
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
         ↑ RAG Knowledge Base (FAISS) informs all nodes
         ↑ Prometheus/Grafana monitors all nodes in real-time
```

---

## 📊 Scientific Results (10.44M Cells)

This pipeline was validated on KSC mouse pancreatic cancer progression (4–12 weeks):

| Stage | Microenvironment | Dominant Programs |
|---|---|---|
| **4–6 weeks (Early)** | Immune-active | CD4⁺/CD8⁺ T cells, NK cells, B cells, antigen presentation |
| **7–9 weeks (Transitional)** | Mixed immune–stromal | Myeloid expansion, rising exhaustion, EMT onset |
| **11–12 weeks (Late)** | Stromal-dominant, immune-silent | Fibrosis Z=1.77, Angiogenesis Z=1.81, EMT, proliferation |

> **Immune Cell Markers** showed the largest dynamic range across progression (range = 1.04), followed by T Cell Activation/Exhaustion (0.61) and Myeloid Antigen Presentation (0.59).

---

## 🚀 Quick Start

### Prerequisites
- Docker installed
- SSH key configured with GitHub
- GPU recommended (ROSIE inference)

### Installation

```bash
# Clone the repository
git clone git@github.com:bayjuan5/LangGraphPrj_V5.git
cd LangGraphPrj_V5

# Build the containerized environment (~8.5GB)
docker build -t langgraph-v5-app .

# Start the pipeline
docker run -d -p 5000:5000 --name langgraph-instance langgraph-v5-app
```

### Access Dashboard
Open `http://localhost:5000` to access the interactive pipeline dashboard.

---

## 📁 Repository Structure

```
LangGraphPrj_V5/
├── app.py                    # Main LangGraph application entry point
├── frontend/                 # Interactive dashboard (WebSocket, real-time outputs)
├── .github/workflows/        # CI/CD pipeline (GitHub Actions)
├── Dockerfile                # Containerized environment
├── requirements.txt          # Python dependencies
└── README.md
```

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | LangGraph v1.1.2, LangChain |
| **LLM Backends** | Claude 3.5 Sonnet (primary), Llama 2 7B (local fallback) |
| **Biomarker Inference** | ROSIE (deep learning, 50-channel protein prediction from H&E) |
| **Vector Store / RAG** | FAISS |
| **Spatial Clustering** | DBSCAN, KMeans |
| **Temporal Modeling** | Timed Petri Net |
| **Monitoring** | Prometheus + Grafana |
| **Containerization** | Docker |
| **CI/CD** | GitHub Actions |
| **Backend** | Python, FastAPI |
| **Frontend** | JavaScript, HTML/CSS, WebSocket |

---

## 📈 Observability

The pipeline is instrumented with **Prometheus/Grafana** monitoring:

- Per-node execution latency
- Cell throughput (cells/sec)
- Immune fraction per timepoint
- Pipeline health and error rates

---

## 🔗 Related Resources

- **ROSIE Framework**: [gitlab.com/enable-medicine-public/rosie](https://gitlab.com/enable-medicine-public/rosie)
- **Personal Portfolio**: [imdlab.org](https://imdlab.org)
- **Corresponding Author**: bbh@imdlab.org | bayjuan5@gmail.com
- **ORCID**: [0000-0003-0555-6924](https://orcid.org/0000-0003-0555-6924)

---

## 📚 Citation

Manuscript under preparation. If you are interested in citing this work or collaborating, please contact: bbh@imdlab.org

---

## 👩‍🔬 Author

**Beibei Huang, Ph.D.**
Senior Data Scientist & ML Engineer | MD Anderson Cancer Center
[github.com/bayjuan5](https://github.com/bayjuan5) | [imdlab.org](https://imdlab.org)
