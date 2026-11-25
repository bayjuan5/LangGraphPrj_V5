#!/bin/bash
# One-time: build the ROSIE Python environment on $WORK (run on a Lonestar6 login node, ~10 min).
set -e
source "$(dirname "$0")/config.sh"
module load python3 2>/dev/null || true
python3 -m venv "$ROSIE_ENV"
"$ROSIE_ENV/bin/pip" install --upgrade pip
if [ "$(uname -m)" = "aarch64" ]; then IDX=https://download.pytorch.org/whl/cu126; else IDX=https://download.pytorch.org/whl/cu121; fi
"$ROSIE_ENV/bin/pip" install torch torchvision --index-url $IDX
"$ROSIE_ENV/bin/pip" install openslide-python openslide-bin opencv-python-headless scikit-image scipy tifffile matplotlib pandas pillow
"$ROSIE_ENV/bin/python" -c "import torch, torchvision, openslide, cv2, skimage, scipy, tifffile, matplotlib, pandas; print('env OK', torch.__version__, 'cuda build', torch.version.cuda, 'openslide', openslide.__library_version__)"
echo "model md5 (must be 72f896a8f9a8d5571dec401e7055a5b9):"; md5sum "$ROSIE_ROOT/best_model_single.pth"
