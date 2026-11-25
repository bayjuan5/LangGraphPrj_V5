# Rerun with StarDist 2x prob_thresh 0.4 (tag sd2x04) — submit commands
Why: threshold sweep vs QuPath GT (manual_count/thresh_sweep.csv): prob 0.69 -> recall 0.39 / precision 0.93;
prob 0.4 -> 0.63 / 0.85 (leave-one-crop-out 0.60 / 0.86). Rule: highest recall with precision >= 0.85.
Nothing existing is overwritten: new folders Node2_stardist2x_p04_out, Node3_cell_stardist2x_p04_out, cells/*__sd2x04.npz, results/sd2x04/.

Upload first (WinSCP): rosie_male_kit/run_stardist_p04.slurm, analysis/run_rosie_p04.slurm, analysis/run_analysis_p04.slurm

    cd $WORK/Pancrea_Cancer && source rosie_male_kit/config.sh

## Step 1 — StarDist (16 CPU jobs on gg, all at once)
    for N in M4 M5 M6 M8 M9 M10 M11 M12 F4 F5 F6 F7 F8 F9 F11 F12; do
      sbatch -J sdp04_$N -A $ROSIE_ACCOUNT -p gg -o $ROSIE_ROOT/logs/%x_%j.out rosie_male_kit/run_stardist_p04.slurm $N
    done
Check:  grep -h "^done\|nuclei," logs/sdp04_*.out | tail -20      (16 x "done:" lines)

## Step 2 — ROSIE (GPU), after ALL step-1 jobs are done. Same grouping as last time (gh-dev, one job runs at a time):
    sbatch -J r04_A -A $ROSIE_ACCOUNT -p gh-dev -o $ROSIE_ROOT/logs/%x_%j.out analysis/run_rosie_p04.slurm M10 M12 F12 F5 M6
    sbatch -J r04_B -A $ROSIE_ACCOUNT -p gh-dev -o $ROSIE_ROOT/logs/%x_%j.out analysis/run_rosie_p04.slurm M11 F11 M5 F7 F8 F4
    sbatch -J r04_C -A $ROSIE_ACCOUNT -p gh-dev -o $ROSIE_ROOT/logs/%x_%j.out analysis/run_rosie_p04.slurm M9 F9 M8 M4 F6
~1.7x more nuclei than sd2x, so a group may hit the 2 h limit: just resubmit the same line (finished tiles are skipped).
Check:  grep -h "phenotype files" logs/r04_*.out      (tiles == phenotype files for all 16)

## Step 3 — analysis (CPU), after step 2. Stage 1 first (~30-60 min), then 2 and 3 can run together.
    sbatch -J a04_1 -A $ROSIE_ACCOUNT -p gg -o $ROSIE_ROOT/logs/%x_%j.out analysis/run_analysis_p04.slurm 1
    sbatch -J a04_2 -A $ROSIE_ACCOUNT -p gg -o $ROSIE_ROOT/logs/%x_%j.out analysis/run_analysis_p04.slurm 2
    sbatch -J a04_3 -A $ROSIE_ACCOUNT -p gg -o $ROSIE_ROOT/logs/%x_%j.out analysis/run_analysis_p04.slurm 3
Check:  tail -n 2 logs/a04_*.out    (each ends "stage N DONE")
Stage 1 prints the recall table: sd2x04 should give roughly recall 0.62 / precision 0.85 (pipeline check).
