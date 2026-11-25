#!/bin/bash
# Usage: ./setup_slides.sh male | female | all
# Creates $ROSIE_ROOT/<slide> folders with identical scripts, links each SVS, checks model and environment.
set -e
KIT=$(cd "$(dirname "$0")" && pwd); source "$KIT/config.sh"
SET=${1:-male}
MALE="M4:366852 M5:366851 M6:366850 M8:366849 M9:366848 M10:366847 M11:366846 M12:366845"
FEMALE="F4:366826 F5:366825 F6:366824 F7:366823 F8:366822 F9:366821 F11:366820 F12:366819"
case $SET in male) L=$MALE;; female) L=$FEMALE;; all) L="$MALE $FEMALE";; *) echo "usage: $0 male|female|all"; exit 1;; esac
PY=$ROSIE_ENV/bin/python
[ -f "$ROSIE_ROOT/best_model_single.pth" ] || { echo "ERROR: $ROSIE_ROOT/best_model_single.pth not found"; exit 1; }
$PY -c "import torch, torchvision, openslide, cv2, skimage, scipy, tifffile, matplotlib, pandas, PIL; print('env OK: torch', torch.__version__, 'skimage', skimage.__version__)" \
  || { echo "ERROR: missing packages in $ROSIE_ENV"; exit 1; }
mkdir -p "$ROSIE_ROOT/logs"
for S in $L; do
  N=${S%%:*}; ID=${S##*:}; SVS=High_${N}_${ID}.svs; D=$ROSIE_ROOT/$N
  case $N in M*) SRC=$SVS_MALE_DIR;; F*) SRC=$SVS_FEMALE_DIR;; esac
  [ -f "$SRC/$SVS" ] || { echo "ERROR: $SRC/$SVS missing"; exit 1; }
  [ -d "$D/Node3_cell_out" ] && echo "NOTE: $D already has Node3 output; finished tiles will be skipped"
  mkdir -p "$D"; cp "$KIT"/common/Node2.py "$KIT"/common/node2_stardist.py "$KIT"/common/node3_cellcentered.py "$KIT"/common/node3_standalone_OFFICIAL.py "$KIT"/common/batch_config.py "$D/"
  sed "s/__SVS__/$SVS/" "$KIT/common/Node1.py" > "$D/Node1.py"
  ln -sf "$SRC/$SVS" "$D/$SVS"
  echo "$N ready -> $D"
done
mkdir -p "$ROSIE_ROOT/F4_check" && cp -r "$KIT"/F4_check/* "$ROSIE_ROOT/F4_check/" && cp "$KIT"/common/node3_cellcentered.py "$ROSIE_ROOT/F4_check/"
[ -f "$SVS_FEMALE_DIR/High_F4_366826.svs" ] && ln -sf "$SVS_FEMALE_DIR/High_F4_366826.svs" "$ROSIE_ROOT/F4_check/High_F4_366826.svs" || echo "WARNING: F4 SVS not found; part 2 of check_f4 will fail"
echo "F4_check ready -> $ROSIE_ROOT/F4_check"
