#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 02:00:00
# Cell-centred ROSIE on the prob-0.4 StarDist 2x nuclei, one or more slides in sequence (GPU, Vista gh-dev or gh).
# Node2_stardist2x_p04_out -> Node3_cell_stardist2x_p04_out. Finished tiles are skipped: a timed-out job is
# resumed by resubmitting the same line.
#   cd $ROSIE_ROOT && source rosie_male_kit/config.sh
#   sbatch -J r04_A -A $ROSIE_ACCOUNT -p gh-dev -o $ROSIE_ROOT/logs/%x_%j.out analysis/run_rosie_p04.slurm M10 M12 F12 F5
[ $# -eq 0 ] && { echo "usage: run_rosie_p04.slurm <slide> [<slide> ...]"; exit 1; }
PY=$ROSIE_ENV/bin/python
nvidia-smi -L
$PY -c "import torch, openslide, cv2, skimage, scipy, tifffile; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())" || { echo "DEPS MISSING in $ROSIE_ENV"; exit 2; }
for N in "$@"; do
  cd "$ROSIE_ROOT/$N" || exit 1
  [ -f Node2_stardist2x_p04_out/node2_output.json ] || { echo "no p04 StarDist manifest for $N - skipped"; continue; }
  SVS=$(ls High_${N}_*.svs | head -1)
  echo "== $N Node3 on p04 nuclei $(date)"
  $PY -u node3_cellcentered.py --svs "$SVS" --node2 Node2_stardist2x_p04_out --out Node3_cell_stardist2x_p04_out || exit 6
  echo "$N tiles: $($PY -c "import json;print(len(json.load(open('Node2_stardist2x_p04_out/node2_output.json'))['tiles']))")  phenotype files: $(ls Node3_cell_stardist2x_p04_out/phenotypes/*.json 2>/dev/null | wc -l)"
done
echo "done $(date)"
