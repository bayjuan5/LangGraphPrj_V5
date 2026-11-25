#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 04:00:00
# Full analysis on Vista CPU node, after all rosie_<slide> GPU jobs have finished.
#   cd $ROSIE_ROOT/rosie_male_kit && source config.sh
#   sbatch -J analysis -A $ROSIE_ACCOUNT -p gg -o $ROSIE_ROOT/logs/%x_%j.out $ROSIE_ROOT/analysis/run_analysis.slurm
set -e
A=$ROSIE_ROOT/analysis; PY=$ROSIE_ENV/bin/python
cd $A
$PY -c "import numpy, scipy, pandas, sklearn" 2>/dev/null || $ROSIE_ENV/bin/pip install -q scipy pandas scikit-learn
SLIDES="M4 M5 M6 M8 M9 M10 M11 M12 F4 F5 F6 F7 F8 F9 F11 F12"

# 0. MPP check: slide_meta.csv must match the SVS headers (abort if any slide differs by >1%)
$PY - <<'EOF'
import glob, os, openslide, pandas as pd
m = pd.read_csv("slide_meta.csv").set_index("slide"); root = os.environ["ROSIE_ROOT"]; bad = []
for s in m.index:
    f = (glob.glob(f"{root}/{s}/*.svs") + glob.glob(f"{root}/svs_*/*_{s}_*.svs"))[0]
    p = openslide.OpenSlide(f).properties
    mx, my = float(p.get("openslide.mpp-x", "nan")), float(p.get("openslide.mpp-y", "nan"))
    print(f"MPP {s}: header {mx:.4f}/{my:.4f}  meta {m.loc[s,'mpp']}")
    if not abs(mx - m.loc[s, "mpp"]) / m.loc[s, "mpp"] < 0.01: bad.append(s)
if bad: raise SystemExit(f"MPP mismatch: {bad} - fix slide_meta.csv")
EOF

# 1. per-slide extraction: ws = watershed + cell-centred ROSIE, sd = StarDist + cell-centred ROSIE
for N in $SLIDES; do
  [ -f cells/${N}__ws.npz ] || $PY -u extract_cells.py --slide $N --dir $ROSIE_ROOT/$N/Node3_cell_out --out cells/${N}__ws.npz --workers 64
  [ -f cells/${N}__sd.npz ] || { [ -d $ROSIE_ROOT/$N/Node3_cell_stardist_out ] && \
    $PY -u extract_cells.py --slide $N --dir $ROSIE_ROOT/$N/Node3_cell_stardist_out --out cells/${N}__sd.npz --workers 64; } || true
done

# 2. slide-level statistics, each segmentation
for T in ws sd; do
  ls cells/*__$T.npz >/dev/null 2>&1 || continue
  $PY -u slide_stats.py --cells cells --tag $T --meta slide_meta.csv --out results/$T
  $PY -u spatial_enrichment.py --cells cells --tag $T --meta slide_meta.csv --ref results/$T/pooled_reference.npz --out results/$T/spatial
  $PY -u niche_transitions.py --cells cells --tag $T --meta slide_meta.csv --ref results/$T/pooled_reference.npz --out results/$T/niches
done

# 3. segmentation agreement
[ -d results/sd ] && $PY -u seg_compare.py --cells cells --tag_a ws --tag_b sd --meta slide_meta.csv \
   --ref results/ws/pooled_reference.npz --out results/seg_compare \
   --stats_a results/ws/stats_q75.csv --metrics_a results/ws/slide_metrics.csv \
   --stats_b results/sd/stats_q75.csv --metrics_b results/sd/slide_metrics.csv
echo "analysis done $(date)"
