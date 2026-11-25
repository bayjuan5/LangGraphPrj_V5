#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 12:00:00
# Usage (after: source config.sh):
#   sbatch -J rosie_M4 -A $ROSIE_ACCOUNT -p $ROSIE_PARTITION -o $ROSIE_ROOT/logs/%x_%j.out -e $ROSIE_ROOT/logs/%x_%j.err run_slide.slurm M4
# Runs Node1 (tiling) -> Node2 (cells) -> Node3 (cell-centred ROSIE: one 128x128 window per cell, read from the SVS). Each step is skipped if its output exists,
# and Node3 skips tiles already done, so a timed-out job is resumed by resubmitting the same command.
set -o pipefail
N=$1; [ -z "$N" ] && { echo "usage: run_slide.slurm <M4|M5|...>"; exit 1; }
PY=$ROSIE_ENV/bin/python
cd "$ROSIE_ROOT/$N" || exit 1
echo "$(hostname) | slide $N | $(date)"; nvidia-smi -L
$PY -c "import torch, openslide, cv2, skimage, scipy, tifffile; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())" || { echo "DEPS MISSING in $ROSIE_ENV"; exit 2; }
if [ ! -f Node1_out/Node1_out.json ]; then echo "== Node1 $(date)"; $PY -u Node1.py || exit 3; fi
if [ ! -f Node2_out/node2_output.json ]; then echo "== Node2 $(date)"; $PY -u Node2.py || exit 4; fi
SVS=$(ls High_${N}_*.svs | head -1)
echo "== Node3 (cell-centred) $(date)"; $PY -u node3_cellcentered.py --svs "$SVS" || exit 5
if [ -f Node2_stardist_out/node2_output.json ]; then
  echo "== Node3 on StarDist nuclei $(date)"
  $PY -u node3_cellcentered.py --svs "$SVS" --node2 Node2_stardist_out --out Node3_cell_stardist_out || exit 6
else
  echo "NOTE: no StarDist nuclei yet (Node2_stardist_out); run rosie_stardist step later"
fi
echo "tiles in manifest: $($PY -c "import json;print(len(json.load(open('Node2_out/node2_output.json'))['tiles']))")"
echo "phenotype files:   $(ls Node3_cell_out/phenotypes/*.json 2>/dev/null | wc -l)"
echo "done $(date)"
