# ===== Shared by Lonestar6 (x86_64, A100/H100) and Vista (aarch64, GH200) =====
# $WORK is visible from both systems; each needs its own Python env.
export ROSIE_ROOT=$WORK/Pancrea_Cancer      # contains best_model_single.pth
if [ "$(uname -m)" = "aarch64" ]; then                          # Vista
  export ROSIE_ENV=$WORK/envs/rosie_vista
  export ROSIE_PARTITION=gh                                     # GH200; use gh-dev for short tests
  export ROSIE_DEV_PARTITION=gh-dev
  export ROSIE_ACCOUNT=${ROSIE_ACCOUNT:-MCB25058}              # <-- CHANGE if your Vista allocation differs
else                                                            # Lonestar6
  export ROSIE_ENV=$WORK/envs/rosie
  export ROSIE_PARTITION=gpu-h100
  export ROSIE_DEV_PARTITION=gpu-a100-dev
  export ROSIE_ACCOUNT=${ROSIE_ACCOUNT:-MCB25058}
fi
export SVS_MALE_DIR=$ROSIE_ROOT/svs_male
export SVS_FEMALE_DIR=$ROSIE_ROOT/svs_female
echo "config: $(uname -m) | env $ROSIE_ENV | partition $ROSIE_PARTITION | account $ROSIE_ACCOUNT"
