#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 08:00:00
# Analysis of the prob-0.4 StarDist 2x run (tag sd2x04), in three stages so each fits a short queue slot:
#   stage 1: extract cells, slide stats, HALO validation, recall vs QuPath ground truth  (results/sd2x04/)
#   stage 2: spatial enrichment 20 um, niches, sd2x04-vs-sd2x comparison
#   stage 3: spatial enrichment 10 + 30 um (sensitivity)
# Existing results/sd2x (prob 0.69) are NOT touched.
#   cd $ROSIE_ROOT && source rosie_male_kit/config.sh
#   sbatch -J a04_1 -A $ROSIE_ACCOUNT -p gg -o $ROSIE_ROOT/logs/%x_%j.out analysis/run_analysis_p04.slurm 1
STAGE=${1:-1}; T=sd2x04
set -e
A=$ROSIE_ROOT/analysis; PY=$ROSIE_ENV/bin/python; cd $A
SLIDES="M4 M5 M6 M8 M9 M10 M11 M12 F4 F5 F6 F7 F8 F9 F11 F12"
if [ "$STAGE" = 1 ]; then
  for N in $SLIDES; do
    [ -f cells/${N}__$T.npz ] || $PY -u extract_cells.py --slide $N --dir $ROSIE_ROOT/$N/Node3_cell_stardist2x_p04_out --out cells/${N}__$T.npz --workers 64
  done
  $PY -u slide_stats.py --cells cells --tag $T --meta slide_meta.csv --out results/$T
  $PY -u halo_validation.py --halo Sharma_HALO_trichrome_Classification.xlsx --metrics results/$T/slide_metrics.csv --meta slide_meta.csv --out results/$T/halo_validation.csv
  $PY -u manual_count/manual_recall.py --cells cells --tags sd2x $T --manual manual_count/qupath/F8_panin_x2432_y11648_qupath.json \
      manual_count/qupath/M4_acinar_x19840_y20864_qupath_v2.json manual_count/qupath/M4_stroma_x16768_y7424_qupath.json | tee results/$T/recall_qupath_v2.csv
fi
if [ "$STAGE" = 2 ]; then
  $PY -u spatial_enrichment.py --cells cells --tag $T --meta slide_meta.csv --ref results/$T/pooled_reference.npz --out results/$T/spatial --radii_um 20
  $PY -u niche_transitions.py --cells cells --tag $T --meta slide_meta.csv --ref results/$T/pooled_reference.npz --out results/$T/niches
  $PY -u seg_compare.py --cells cells --tag_a sd2x --tag_b $T --meta slide_meta.csv --ref results/sd2x/pooled_reference.npz \
      --out results/seg_compare_sd2x04_vs_sd2x --stats_a results/sd2x/stats_q75.csv --metrics_a results/sd2x/slide_metrics.csv \
      --stats_b results/$T/stats_q75.csv --metrics_b results/$T/slide_metrics.csv
fi
if [ "$STAGE" = 3 ]; then
  $PY -u spatial_enrichment.py --cells cells --tag $T --meta slide_meta.csv --ref results/$T/pooled_reference.npz --out results/$T/spatial_r10_30 --radii_um 10 30
fi
echo "stage $STAGE DONE $(date)"
