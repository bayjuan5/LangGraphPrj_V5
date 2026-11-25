#!/usr/bin/env python3
"""
manual_recall.py - precision / recall of nucleus detection against manual counts.

Inputs: the *_manual.json files saved from the counting pages (points in crop pixels, level-0 scale,
crop origin x0,y0) and the per-slide cells/<slide>__<tag>.npz files produced by extract_cells.py.
For every crop and every tag: detections inside the crop are matched one-to-one to manual points
(mutual nearest neighbour within --match_um, default 4 um). Reports recall (manual nuclei found),
precision (detections that are real nuclei) and F1, per crop and pooled.

Usage (login node, rosie_vista env):
  python manual_recall.py --cells cells --tags sd sd2x ws --manual manual_count/*_manual.json
"""
import argparse, glob, json
import numpy as np
from scipy.spatial import cKDTree


def mutual_nn(a, b, dmax):
    if len(a) == 0 or len(b) == 0:
        return 0
    ta, tb = cKDTree(a), cKDTree(b)
    d1, i1 = tb.query(a, distance_upper_bound=dmax)
    d2, i2 = ta.query(b, distance_upper_bound=dmax)
    ok = np.isfinite(d1)
    return int(np.sum(i2[i1[ok]] == np.flatnonzero(ok)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", default="cells")
    ap.add_argument("--tags", nargs="+", default=["sd", "sd2x"])
    ap.add_argument("--manual", nargs="+", required=True)
    ap.add_argument("--match_um", type=float, default=4.0)
    a = ap.parse_args()
    print("crop,tag,n_manual,n_detected,matched,recall,precision,f1")
    pooled = {t: [0, 0, 0] for t in a.tags}
    for mf in sorted(a.manual):
        m = json.load(open(mf))
        man = np.array(m["points_crop_px"], float) + [m["x0"], m["y0"]]
        x0, y0, s = m["x0"], m["y0"], m["size_px"]
        dmax = a.match_um / m["mpp"]
        for t in a.tags:
            f = glob.glob(f"{a.cells}/{m['slide']}__{t}.npz")
            if not f:
                continue
            xy = np.load(f[0])["xy"].astype(float)
            inside = (xy[:, 0] >= x0) & (xy[:, 0] < x0 + s) & (xy[:, 1] >= y0) & (xy[:, 1] < y0 + s)
            det = xy[inside]
            k = mutual_nn(man, det, dmax)
            r = k / max(len(man), 1); p = k / max(len(det), 1); f1 = 2 * p * r / max(p + r, 1e-9)
            print(f"{m['name']},{t},{len(man)},{len(det)},{k},{r:.3f},{p:.3f},{f1:.3f}")
            pooled[t][0] += len(man); pooled[t][1] += len(det); pooled[t][2] += k
    for t, (nm, nd, k) in pooled.items():
        if nm:
            r, p = k / nm, k / max(nd, 1)
            print(f"POOLED,{t},{nm},{nd},{k},{r:.3f},{p:.3f},{2*p*r/max(p+r,1e-9):.3f}")


if __name__ == "__main__":
    main()
