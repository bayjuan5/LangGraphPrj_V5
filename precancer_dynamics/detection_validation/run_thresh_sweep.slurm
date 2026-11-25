#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 00:30:00
# StarDist 2x threshold sweep on the 3 QuPath ground-truth crops (CPU, Vista gg).
#   cd $ROSIE_ROOT && source rosie_male_kit/config.sh
#   sbatch -J sd_sweep -A $ROSIE_ACCOUNT -p gg -o $ROSIE_ROOT/logs/%x_%j.out analysis/manual_count/run_thresh_sweep.slurm
SD_PY=${ROSIE_ENV}_stardist/bin/python
module swap nvidia gcc 2>/dev/null || module load gcc 2>/dev/null || true
export LD_LIBRARY_PATH=$(dirname $(gcc -print-file-name=libssp.so.0)):$LD_LIBRARY_PATH
cd "$ROSIE_ROOT/analysis" || exit 1
$SD_PY -u manual_count/stardist_thresh_sweep.py --root "$ROSIE_ROOT" \
  --gt manual_count/qupath/F8_panin_x2432_y11648_qupath.json \
       manual_count/qupath/M4_acinar_x19840_y20864_qupath_v2.json \
       manual_count/qupath/M4_stroma_x16768_y7424_qupath.json \
  --out manual_count/thresh_sweep.csv
echo "done $(date)"
