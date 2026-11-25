#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 12:00:00
# StarDist 2x with prob_thresh 0.4 (chosen on the QuPath ground truth) for one slide, CPU node (Vista gg).
# Writes <slide>/Node2_stardist2x_p04_out/ ; the existing Node2_stardist2x_out (prob 0.69) is NOT touched.
# Resumable: tiles already written are skipped, so a timed-out job is resumed by resubmitting the same line.
#   cd $ROSIE_ROOT && source rosie_male_kit/config.sh
#   sbatch -J sdp04_M4 -A $ROSIE_ACCOUNT -p gg -o $ROSIE_ROOT/logs/%x_%j.out rosie_male_kit/run_stardist_p04.slurm M4
N=$1; [ -z "$N" ] && { echo "usage: run_stardist_p04.slurm <slide>"; exit 1; }
SD_PY=${ROSIE_ENV}_stardist/bin/python
module swap nvidia gcc 2>/dev/null || module load gcc 2>/dev/null || true
export LD_LIBRARY_PATH=$(dirname $(gcc -print-file-name=libssp.so.0)):$LD_LIBRARY_PATH
$SD_PY -c "import stardist, tensorflow as tf; print('stardist', stardist.__version__, 'tf', tf.__version__)" || { echo "StarDist env not usable"; exit 2; }
cd "$ROSIE_ROOT/$N" || exit 1
SVS=$(ls High_${N}_*.svs | head -1)
echo "$(hostname) | StarDist 2x prob 0.4 | $N | $(nproc) cores | $(date)"
$SD_PY -u node2_stardist.py --svs "$SVS" --scale 2 --prob 0.4 --out Node2_stardist2x_p04_out || exit 3
echo "done $(date)"
