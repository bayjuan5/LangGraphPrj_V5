#!/usr/bin/env bash
# LangGraph V5 — one-click setup and launch (macOS / Linux)
set -e

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'

echo ""
echo -e "${BOLD}============================================================${NC}"
echo -e "${BOLD} LangGraph Computational Pathology Framework V5${NC}"
echo -e "${BOLD} TCGA-PAAD Spatiotemporal Pipeline${NC}"
echo -e "${BOLD}============================================================${NC}"
echo ""

# ── Python check ─────────────────────────────────────────────────────────────
echo "[1/4] Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}ERROR: python3 not found.${NC}"
    echo "Install Python 3.9+ from https://www.python.org/downloads/"
    exit 1
fi
python3 --version
echo -e "${GREEN}  Python OK${NC}"

# ── Install packages ──────────────────────────────────────────────────────────
echo ""
echo "[2/4] Installing required packages (may take 2–5 minutes)..."

# macOS: install system OpenSlide if not present
if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew &>/dev/null && ! brew list openslide &>/dev/null 2>&1; then
        echo "  Installing OpenSlide via Homebrew..."
        brew install openslide
    fi
fi

# Linux: install system OpenSlide if not present
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! python3 -c "import openslide" &>/dev/null 2>&1; then
        echo "  Installing OpenSlide system library..."
        sudo apt-get install -y libopenslide0 2>/dev/null || true
    fi
fi

pip install -q -r requirements.txt
echo -e "${GREEN}  All packages installed${NC}"

# ── Verify openslide ──────────────────────────────────────────────────────────
echo ""
echo "[3/4] Verifying SVS reader (OpenSlide)..."
python3 -c "import openslide; print('  OpenSlide OK')"
echo -e "${GREEN}  OpenSlide OK${NC}"

# ── Start server ──────────────────────────────────────────────────────────────
echo ""
echo "[4/4] Starting pipeline server..."
echo ""
echo -e "${BOLD}  Dashboard: http://localhost:5000${NC}"
echo ""
echo "  Select 'TCGA-PAAD Spatiotemporal Pipeline' and click Execute."
echo "  Press Ctrl+C to stop."
echo ""

# Open browser after 3 seconds
(sleep 3 && python3 -c "
import webbrowser, time
time.sleep(0.1)
webbrowser.open('http://localhost:5000')
" &)

python3 app.py
