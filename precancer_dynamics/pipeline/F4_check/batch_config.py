#!/usr/bin/env python3
"""
Batch Processing Configuration for Node3
=========================================

This script helps you process tiles in batches and track progress.

USAGE:
------
1. Edit the BATCH_CONFIG section below
2. Run: python node3_standalone_OFFICIAL.py

The script will:
- Only process tiles in the specified range
- Save progress to a tracking file
- Allow you to resume later with different ranges

EXAMPLE BATCHES:
----------------
Batch 1: START_TILE=0,  END_TILE=10   (tiles 0-9)
Batch 2: START_TILE=10, END_TILE=20   (tiles 10-19)
Batch 3: START_TILE=20, END_TILE=30   (tiles 20-29)
...
"""

# =============================================================================
# BATCH CONFIGURATION - EDIT THIS SECTION
# =============================================================================

# Which tiles to process in this run
START_TILE = 0      # whole slide in one job; finished tiles are skipped on resubmit
END_TILE = 5
                    # So START_TILE=0, END_TILE=10 processes tiles 0-9

# Processing parameters
STRIDE_SIZE = 8    # 8=slower/accurate, 16=faster/good, 32=fastest/risky
BATCH_SIZE = 32     # GPU batch size (32 is good for most GPUs)
SAVE_TIFF = False   # Set to True if you need TIFF outputs

# Progress tracking file
PROGRESS_FILE = "node3_progress.json"

# =============================================================================
# END OF CONFIGURATION
# =============================================================================

print(f"""
{'='*70}
BATCH PROCESSING CONFIGURATION
{'='*70}
Processing tiles: {START_TILE} to {END_TILE-1} (total: {END_TILE-START_TILE} tiles)
STRIDE_SIZE: {STRIDE_SIZE}
Progress file: {PROGRESS_FILE}
{'='*70}
""")

# Save this configuration
import json
from pathlib import Path
from datetime import datetime

config_info = {
    "batch_start": START_TILE,
    "batch_end": END_TILE,
    "stride_size": STRIDE_SIZE,
    "batch_size": BATCH_SIZE,
    "timestamp": datetime.now().isoformat(),
    "status": "ready_to_run"
}

# Export for main script to use
__all__ = ['START_TILE', 'END_TILE', 'STRIDE_SIZE', 'BATCH_SIZE', 'SAVE_TIFF', 'PROGRESS_FILE', 'config_info']
