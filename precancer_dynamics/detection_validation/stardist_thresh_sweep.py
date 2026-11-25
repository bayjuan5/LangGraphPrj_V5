#!/usr/bin/env python3
"""
stardist_thresh_sweep.py - precision/recall of StarDist 2x vs the QuPath ground truth across
probability (prob_thresh) and overlap (nms_thresh) thresholds.

Reproduces the production sd2x setting exactly (node2_stardist.py --scale 2): the full 1024x1024
level-0 tile that contains each crop is read, upsampled 2x (bilinear), normalised (1, 99.8) over the
whole tile, and predicted with n_tiles=(4,4,1). The network is run ONCE per tile; each threshold pair
is then applied to the same prob/dist maps, so the sweep is cheap. Detections inside the 256x256 crop
are matched one-to-one to the ground-truth points (mutual nearest neighbour within 4 um), exactly as
in manual_recall.py.

Usage (StarDist env, gg node; run from $ROSIE_ROOT/analysis):
  python manual_count/stardist_thresh_sweep.py --root $ROSIE_ROOT \
      --gt manual_count/qupath/F8_panin_x2432_y11648_qupath.json \
           manual_count/qupath/M4_acinar_x19840_y20864_qupath_v2.json \
           manual_count/qupath/M4_stroma_x16768_y7424_qupath.json \
      --out manual_count/thresh_sweep.csv
The row prob=0.69, nms=0.3 is the production setting and should reproduce the sd2x line of
manual_recall.py (171 detections, 161 matched) up to tile-edge effects.
"""
import argparse, glob, json, os
import numpy as np
from scipy.spatial import cKDTree

TILE, SC = 1024, 2


def mutual_nn(a, b, dmax):
    if len(a) == 0 or len(b) == 0:
        return 0
    d1, i1 = cKDTree(b).query(a, distance_upper_bound=dmax)
    d2, i2 = cKDTree(a).query(b, distance_upper_bound=dmax)
    ok = np.isfinite(d1)
    return int(np.sum(i2[i1[ok]] == np.flatnonzero(ok)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="$ROSIE_ROOT (contains <slide>/High_<slide>_*.svs)")
    ap.add_argument("--gt", nargs="+", required=True)
    ap.add_argument("--out", default="manual_count/thresh_sweep.csv")
    ap.add_argument("--probs", default="0.10,0.20,0.30,0.40,0.50,0.60,0.69")
    ap.add_argument("--nms", default="0.3,0.4,0.5")
    ap.add_argument("--match_um", type=float, default=4.0)
    a = ap.parse_args()
    probs = [float(x) for x in a.probs.split(",")]
    nmss = [float(x) for x in a.nms.split(",")]

    import openslide
    from PIL import Image
    from csbdeep.utils import normalize
    from skimage.measure import regionprops
    from stardist.models import StarDist2D
    model = StarDist2D.from_pretrained("2D_versatile_he")

    gts = [json.load(open(f)) for f in a.gt]
    cache = {}                                   # (slide, tx, ty) -> (img_shape, prob, dist)
    rows = []
    for g in gts:
        x0, y0, s = g["x0"], g["y0"], g["size_px"]
        tx, ty = (x0 // TILE) * TILE, (y0 // TILE) * TILE
        assert x0 + s <= tx + TILE and y0 + s <= ty + TILE, f"{g['name']} crosses a tile edge"
        key = (g["slide"], tx, ty)
        if key not in cache:
            svs = glob.glob(os.path.join(a.root, g["slide"], f"High_{g['slide']}_*.svs"))[0]
            rgb = openslide.OpenSlide(svs).read_region((tx, ty), 0, (TILE, TILE)).convert("RGB")
            img = normalize(np.asarray(rgb.resize((TILE * SC, TILE * SC), Image.BILINEAR)), 1, 99.8, axis=(0, 1, 2))
            prob, dist = model.predict(img, n_tiles=(2 * SC, 2 * SC, 1))
            cache[key] = (img.shape, prob, dist)
            print(f"predicted {g['slide']} tile {tx},{ty}", flush=True)
        shape, prob, dist = cache[key]
        man = np.array(g["points_crop_px"], float) + [x0, y0]
        dmax = a.match_um / g["mpp"]
        for pt in probs:
            for nt in nmss:
                lab, _ = model._instances_from_prediction(shape, prob, dist, prob_thresh=pt, nms_thresh=nt)
                xy = np.array([[p.centroid[1] / SC + tx, p.centroid[0] / SC + ty] for p in regionprops(lab)]).reshape(-1, 2)
                ins = (xy[:, 0] >= x0) & (xy[:, 0] < x0 + s) & (xy[:, 1] >= y0) & (xy[:, 1] < y0 + s)
                det = xy[ins]
                k = mutual_nn(man, det, dmax)
                rows.append((g["name"], pt, nt, len(man), len(det), k))

    with open(a.out, "w") as fo:
        fo.write("crop,prob,nms,n_gt,n_det,matched,recall,precision,f1\n")
        agg = {}
        for name, pt, nt, n, d, k in rows:
            r, p = k / max(n, 1), k / max(d, 1)
            fo.write(f"{name},{pt},{nt},{n},{d},{k},{r:.3f},{p:.3f},{2*p*r/max(p+r,1e-9):.3f}\n")
            A = agg.setdefault((pt, nt), [0, 0, 0]); A[0] += n; A[1] += d; A[2] += k
        print("\nPOOLED  prob  nms   n_det  recall  precision  F1")
        for (pt, nt), (n, d, k) in sorted(agg.items()):
            r, p = k / n, k / max(d, 1)
            line = f"POOLED,{pt},{nt},{n},{d},{k},{r:.3f},{p:.3f},{2*p*r/max(p+r,1e-9):.3f}"
            fo.write(line + "\n")
            print(f"        {pt:.2f}  {nt:.1f}   {d:5d}  {r:.3f}   {p:.3f}      {2*p*r/max(p+r,1e-9):.3f}")
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
