#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 03:00:00
# Cell-centred ROSIE on the 2x-StarDist nuclei of one slide (Node2_stardist2x_out -> Node3_cell_stardist2x_out).
# Node1/Node2 are not touched. Node3 skips finished tiles, so a timed-out job is resumed by resubmitting.
# Usage (after: source config.sh), chained behind the StarDist job of the same slide:
#   SDJ=$(squeue -u $USER -n sd2x_M4 -h -o %i)
#   sbatch --dependency=afterok:$SDJ -J rosie2x_M4 -A $ROSIE_ACCOUNT -p gh -o $ROSIE_ROOT/logs/%x_%j.out -e $ROSIE_ROOT/logs/%x_%j.err run_rosie_sd2x.slurm M4
set -o pipefail
N=$1; [ -z "$N" ] && { echo "usage: run_rosie_sd2x.slurm <M4|M5|...>"; exit 1; }
PY=$ROSIE_ENV/bin/python
cd "$ROSIE_ROOT/$N" || exit 1
echo "$(hostname) | slide $N | $(date)"; nvidia-smi -L
$PY -c "import torch, openslide, cv2, skimage, scipy, tifffile; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())" || { echo "DEPS MISSING in $ROSIE_ENV"; exit 2; }
[ -f Node2_stardist2x_out/node2_output.json ] || { echo "no 2x StarDist manifest for $N"; exit 3; }
SVS=$(ls High_${N}_*.svs | head -1)
echo "== Node3 (cell-centred) on 2x StarDist nuclei $(date)"
$PY -u node3_cellcentered.py --svs "$SVS" --node2 Node2_stardist2x_out --out Node3_cell_stardist2x_out || exit 6
echo "tiles in manifest: $($PY -c "import json;print(len(json.load(open('Node2_stardist2x_out/node2_output.json'))['tiles']))")"
echo "phenotype files:   $(ls Node3_cell_stardist2x_out/phenotypes/*.json 2>/dev/null | wc -l)"
echo "done $(date)"
