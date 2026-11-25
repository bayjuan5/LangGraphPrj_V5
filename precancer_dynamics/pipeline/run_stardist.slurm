#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 08:00:00
# StarDist nucleus detection for one slide on a CPU node (Vista: -p gg).
#   source config.sh
#   sbatch -J sd_M4 -A $ROSIE_ACCOUNT -p gg -o $ROSIE_ROOT/logs/%x_%j.out run_stardist.slurm M4
N=$1; [ -z "$N" ] && { echo "usage: run_stardist.slurm <slide>"; exit 1; }
SD_PY=${ROSIE_ENV}_stardist/bin/python
# stardist's C extension was built with gcc and needs gcc's runtime libs (libssp.so.0)
module swap nvidia gcc 2>/dev/null || module load gcc 2>/dev/null || true
export LD_LIBRARY_PATH=$(dirname $(gcc -print-file-name=libssp.so.0)):$LD_LIBRARY_PATH
$SD_PY -c "import stardist, tensorflow as tf; print('stardist', stardist.__version__, 'tf', tf.__version__)" || { echo "StarDist env not usable"; exit 2; }
cd "$ROSIE_ROOT/$N" || exit 1
SVS=$(ls High_${N}_*.svs | head -1)
echo "$(hostname) | StarDist | $N | $(nproc) cores | $(date)"
$SD_PY -u node2_stardist.py --svs "$SVS" || exit 3
echo "done $(date)"
