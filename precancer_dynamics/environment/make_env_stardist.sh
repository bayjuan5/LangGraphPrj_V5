#!/bin/bash
# One-time (Vista login node): CPU environment for StarDist (TensorFlow), separate from the PyTorch env.
set -e
source "$(dirname "$0")/config.sh"
SD_ENV=${ROSIE_ENV}_stardist
module load python3 2>/dev/null || true
# Vista defaults to the NVIDIA HPC compilers (nvc++), which cannot build stardist -> use gcc
module swap nvidia gcc 2>/dev/null || module load gcc 2>/dev/null || true
export CC=gcc CXX=g++
[ -x "$SD_ENV/bin/python" ] || python3 -m venv "$SD_ENV"
"$SD_ENV/bin/pip" install --upgrade pip
"$SD_ENV/bin/pip" install "tensorflow-cpu; platform_machine=='x86_64'" "tensorflow; platform_machine=='aarch64'" stardist csbdeep openslide-python openslide-bin scikit-image
# download the pretrained model now (compute nodes may have no internet); cached under ~/.keras
"$SD_ENV/bin/python" -c "from stardist.models import StarDist2D; m=StarDist2D.from_pretrained('2D_versatile_he'); print('StarDist OK', m)"
"$SD_ENV/bin/python" -c "import tensorflow as tf, openslide, skimage; print('tf', tf.__version__, 'openslide', openslide.__library_version__)"
