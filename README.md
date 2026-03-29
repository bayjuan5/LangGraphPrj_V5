# 🕸️ LangGraph Workflow Project V5

A professional, containerized graph-based workflow application. This project leverages **LangGraph** to manage complex, stateful multi-agent orchestrations, wrapped in a **Docker** environment for seamless "build-once, run-anywhere" deployment.

---

## ✨ Key Features
- **Stateful Orchestration**: Advanced workflow management using LangGraph for cyclic and complex graph logic.
- **Dockerized Architecture**: Pre-configured environment ensuring consistent performance across different machines (Dev/Prod).
- **Real-time Interface**: Interactive frontend with WebSocket support for live workflow tracking.
- **Scalable Backend**: Built with Python, optimized for LLM-based agentic workflows.

---

## 🚀 Quick Start

### 1. Prerequisites
- Docker installed on your machine.
- SSH Key configured with your GitHub account.

### 2. Installation & Run
```bash
# Clone the repository
git clone git@github.com:bayjuan5/LangGraphPrj_V5.git
cd LangGraphPrj_V5

# Build the 8.5GB+ high-performance image locally
docker build -t langgraph-v5-app .

# Start the container
docker run -d -p 5000:5000 --name langgraph-instance langgraph-v5-app
