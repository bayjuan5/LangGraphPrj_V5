@echo off
title LangGraph V5 - TCGA-PAAD Pipeline Setup
color 0A

echo.
echo  ============================================================
echo   LangGraph Computational Pathology Framework V5
echo   TCGA-PAAD Spatiotemporal Pipeline
echo  ============================================================
echo.
echo  This script will:
echo    1. Check Python installation
echo    2. Install all required packages
echo    3. Start the pipeline server
echo    4. Open the dashboard in your browser
echo.
echo  Press any key to begin, or Ctrl+C to cancel.
pause >nul

:: ── Check Python ────────────────────────────────────────────────────────────
echo.
echo [1/4] Checking Python...
python --version 2>nul
if errorlevel 1 (
    echo.
    echo  ERROR: Python not found.
    echo  Please install Python 3.9+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
echo  Python OK.

:: ── Install packages ────────────────────────────────────────────────────────
echo.
echo [2/4] Installing required packages (this may take 2-5 minutes)...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo.
    echo  ERROR: Package installation failed.
    echo  Try running: pip install -r requirements.txt
    echo  and check for error messages above.
    echo.
    pause
    exit /b 1
)
echo  All packages installed.

:: ── Verify openslide ────────────────────────────────────────────────────────
echo.
echo [3/4] Verifying SVS reader (OpenSlide)...
python -c "import openslide; print('  OpenSlide OK')"
if errorlevel 1 (
    echo.
    echo  ERROR: OpenSlide could not be loaded.
    echo  Try: pip install openslide-bin openslide-python --force-reinstall
    echo.
    pause
    exit /b 1
)

:: ── Start server ─────────────────────────────────────────────────────────────
echo.
echo [4/4] Starting pipeline server...
echo.
echo  Dashboard will open at: http://localhost:5000
echo  Select "TCGA-PAAD Spatiotemporal Pipeline" and click Execute.
echo.
echo  To stop the server: close this window or press Ctrl+C
echo.

:: Open browser after a short delay
start "" timeout /t 3 /nobreak >nul 2>&1 & start "" "http://localhost:5000"
python app.py

pause
