# ROSIE inference for the KSC slides (8 male, optionally re-run the 8 female)

Same scripts as the female slides (F12 versions of Node1/Node2; Node3 identical across all female slides),
with two changes: Node3 skips tiles that already have a phenotype file (so timed-out jobs resume), and the
old `pkill -u $USER -f python` line is gone.

## 1. Upload
SVS files go to `$ROSIE_ROOT/svs_male/` and `$ROSIE_ROOT/svs_female/`; this whole `rosie_male_kit` folder
and `best_model_single.pth` go to `$ROSIE_ROOT/` (= $WORK/Pancrea_Cancer).

## 2. Configure and set up
    cd rosie_male_kit
    nano config.sh          # set ROSIE_ROOT, ROSIE_ENV, ROSIE_ACCOUNT, ROSIE_PARTITION
    source config.sh
    ./setup_slides.sh male  # or: female | all -- checks model + environment, creates slide folders and F4_check

## 3. Check first (5 F4 tiles, ~10 min): same model + cell-centred vs original
    sbatch -J rosie_f4check -A $ROSIE_ACCOUNT -p gpu-a100-dev -o $ROSIE_ROOT/logs/%x_%j.out check_f4.slurm
Part 1 VERDICT must say SAME MODEL. Part 2 should show interior r close to 1 and lower agreement in the edge band.

## 4. Submit the slides (add F4 F5 F6 F7 F8 F9 F11 F12 to re-run the female slides)
    for N in M4 M5 M6 M8 M9 M10 M11 M12; do
      sbatch -J rosie_$N -A $ROSIE_ACCOUNT -p $ROSIE_PARTITION \
        -o $ROSIE_ROOT/logs/%x_%j.out -e $ROSIE_ROOT/logs/%x_%j.err run_slide.slurm $N
    done
Node3 is cell-centred (node3_cellcentered.py): one 128x128 window per detected cell, read straight from the
SVS, so cells near tile edges get real tissue context instead of zero padding. Expect roughly 5-10x faster than
the old sliding window (~55 s per tile on H100); the first real run will give the exact rate (cells/s in the log).
If a job times out, resubmit the same command; finished steps and tiles are skipped.
