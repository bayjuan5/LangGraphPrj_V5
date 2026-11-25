#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 00:40:00
# Part 1: original sliding-window Node3 on 5 F4 tiles -> must reproduce the old F4 predictions (same model?).
# Part 2: cell-centred Node3 on the same tiles -> agreement with the old method for interior vs edge cells.
#   sbatch -J rosie_f4check -A $ROSIE_ACCOUNT -p gpu-a100-dev -o $ROSIE_ROOT/logs/%x_%j.out check_f4.slurm
PY=$ROSIE_ENV/bin/python
cd "$ROSIE_ROOT/F4_check" || exit 1
echo "===== PART 1: same-model check ====="
$PY -u node3_standalone_OFFICIAL.py || exit 5
$PY -u compare_f4.py
echo "===== PART 2: cell-centred vs original ====="
$PY -u node3_cellcentered.py --svs High_F4_366826.svs --model ../best_model_single.pth || exit 6
$PY -u compare_cellcentred.py
