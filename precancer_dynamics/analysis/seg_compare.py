#!/usr/bin/env python3
"""
seg_compare.py - agreement between the two nucleus segmentations (watershed vs StarDist),
both fed through the same cell-centred ROSIE inference.

Per slide:
  * nuclei per tile in each method (tiles matched by origin), Pearson r and median ratio
  * one-to-one matching of nuclei: mutual nearest neighbours within d um (default 4 um)
    -> fraction of watershed nuclei matched, fraction of StarDist nuclei matched, median offset
  * for matched nuclei: per-marker Pearson r of ROSIE outputs (expected high: windows overlap)
  * slide-level state composition from each method (same pooled reference, from the watershed run)
Tile sets: the two Node2 runs tile independently, so StarDist keeps a few extra tiles (0-25 per slide).
All A-vs-B numbers are computed on the SHARED tiles. Per slide the script also reports the B-only tiles,
their share of B's cells, and delta_<state>_b_extra = frac_<state>_b_all - frac_<state>_b, i.e. how much
the tiles missing from the watershed (primary) analysis shift composition.
Across slides: the slide-level metrics from slide_stats.py run on each method are compared
(Spearman r across slides, and whether the age-trend sign agrees) - use --stats_a/--stats_b.

Usage:
  python seg_compare.py --cells cells --tag_a ws --tag_b sd --meta slide_meta.csv \
       --ref results/ws/pooled_reference.npz --out results/seg_compare \
       [--stats_a results/ws/stats_q75.csv --metrics_a results/ws/slide_metrics.csv
        --stats_b results/sd/stats_q75.csv --metrics_b results/sd/slide_metrics.csv]
"""
import argparse, os
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy import stats
import common as C


def mutual_nn(xa, xb, dmax):
    ta, tb = cKDTree(xa), cKDTree(xb)
    dab, iab = tb.query(xa, distance_upper_bound=dmax)
    dba, iba = ta.query(xb, distance_upper_bound=dmax)
    ok = np.isfinite(dab)
    ia = np.flatnonzero(ok)
    ib = iab[ok]
    mutual = iba[ib] == ia
    return ia[mutual], ib[mutual], dab[ok][mutual]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", required=True)
    ap.add_argument("--tag_a", default="ws")
    ap.add_argument("--tag_b", default="sd")
    ap.add_argument("--meta", required=True)
    ap.add_argument("--ref", required=True, help="pooled_reference.npz of method A")
    ap.add_argument("--out", required=True)
    ap.add_argument("--match_um", type=float, default=4.0)
    ap.add_argument("--q", type=int, default=75)
    ap.add_argument("--stats_a"); ap.add_argument("--stats_b")
    ap.add_argument("--metrics_a"); ap.add_argument("--metrics_b")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    meta = C.load_meta(a.meta)
    fa_, fb_ = C.find_cells(a.cells, a.tag_a), C.find_cells(a.cells, a.tag_b)
    slides = [s for s in meta.index if s in fa_ and s in fb_]
    ref = C.pooled_reference({s: fa_[s] for s in fa_ if s in meta.index})

    tile_rows, slide_rows, marker_rows = [], [], []
    for s in slides:
        # no area filter here: compare raw detections; the flag rate is reported separately
        A, B = C.load_cells(fa_[s], False), C.load_cells(fb_[s], False)
        mpp = float(meta.loc[s, "mpp"])
        # tiles by origin
        oa = {tuple(o): i for i, o in enumerate(A["tile_origin"])}
        ob = {tuple(o): i for i, o in enumerate(B["tile_origin"])}
        ca = np.bincount(A["tile"], minlength=len(A["tile_origin"]))
        cb = np.bincount(B["tile"], minlength=len(B["tile_origin"]))
        common_t = sorted(set(oa) & set(ob))
        for o in common_t:
            tile_rows.append({"slide": s, "x": o[0], "y": o[1], "n_a": int(ca[oa[o]]), "n_b": int(cb[ob[o]])})
        # The two Node2 runs tile the slide independently (watershed: Node1 background filter;
        # StarDist: its own), so the tile sets differ slightly. A-vs-B comparisons use SHARED tiles only.
        a_only_t, b_only_t = sorted(set(oa) - set(ob)), sorted(set(ob) - set(oa))
        sha = np.isin(A["tile"], [oa[o] for o in common_t])
        shb = np.isin(B["tile"], [ob[o] for o in common_t])
        As = {k: A[k][sha] for k in ("X", "xy", "area_ok")}
        Bs = {k: B[k][shb] for k in ("X", "xy", "area_ok")}
        ia, ib, dist = mutual_nn(As["xy"].astype(float), Bs["xy"].astype(float), a.match_um / mpp)
        cols_b = [B["markers"].index(m) for m in A["markers"]]
        Xa, Xb = As["X"][ia], Bs["X"][ib][:, cols_b]
        for j, m in enumerate(A["markers"]):
            r = np.corrcoef(Xa[:, j], Xb[:, j])[0, 1] if len(ia) > 2 else np.nan
            marker_rows.append({"slide": s, "marker": m, "r_matched": r})
        def states(D, mk):
            ok = D["area_ok"].astype(bool)
            return C.assign_states(C.positives(C.lineage_scores(D["X"][ok], mk, ref), ref, a.q))
        la = states(As, A["markers"])        # watershed, shared tiles
        lb = states(Bs, B["markers"])        # StarDist, shared tiles
        lb_all = states(B, B["markers"])     # StarDist, all of its tiles
        row = {"slide": s, "n_a": len(As["X"]), "n_b": len(Bs["X"]),
               "n_a_all": len(A["X"]), "n_b_all": len(B["X"]),
               "flag_rate_a": 1 - As["area_ok"].mean(), "flag_rate_b": 1 - Bs["area_ok"].mean(),
               "tiles_a": len(oa), "tiles_b": len(ob), "tiles_common": len(common_t),
               "tiles_a_only": len(a_only_t), "tiles_b_only": len(b_only_t),
               "cells_b_only": int(len(B["X"]) - len(Bs["X"])),
               "frac_cells_b_only": float(1 - len(Bs["X"]) / max(len(B["X"]), 1)),
               "frac_a_matched": len(ia) / max(len(As["X"]), 1), "frac_b_matched": len(ib) / max(len(Bs["X"]), 1),
               "median_offset_um": float(np.median(dist) * mpp) if len(dist) else np.nan,
               "median_marker_r": float(np.nanmedian([r["r_matched"] for r in marker_rows if r["slide"] == s]))}
        for i, st in enumerate(C.STATES):
            row[f"frac_{st}_a"] = float(np.mean(la == i)); row[f"frac_{st}_b"] = float(np.mean(lb == i))
            # how much StarDist's extra (B-only) tiles shift its own composition
            row[f"frac_{st}_b_all"] = float(np.mean(lb_all == i))
            row[f"delta_{st}_b_extra"] = row[f"frac_{st}_b_all"] - row[f"frac_{st}_b"]
        slide_rows.append(row)
        mx = max(C.STATES, key=lambda st: abs(row[f"delta_{st}_b_extra"]))
        print(f"  {s}: tiles shared {len(common_t)}  A-only {len(a_only_t)}  B-only {len(b_only_t)} "
              f"({row['frac_cells_b_only']:.1%} of B cells); largest shift from B-only tiles: "
              f"{mx} {row[f'delta_{mx}_b_extra']:+.4f}", flush=True)
        print(f"  {s}: A {row['n_a']:,}  B {row['n_b']:,}  matched {row['frac_a_matched']:.2f}/{row['frac_b_matched']:.2f}"
              f"  offset {row['median_offset_um']:.2f} um  marker r {row['median_marker_r']:.3f}", flush=True)

    T, S, Mk = pd.DataFrame(tile_rows), pd.DataFrame(slide_rows), pd.DataFrame(marker_rows)
    T.to_csv(os.path.join(a.out, "nuclei_per_tile.csv"), index=False)
    S.to_csv(os.path.join(a.out, "slide_agreement.csv"), index=False)
    Mk.pivot(index="marker", columns="slide", values="r_matched").to_csv(os.path.join(a.out, "marker_r_matched.csv"))
    summ = {"tile_count_pearson_r": stats.pearsonr(T.n_a, T.n_b)[0] if len(T) > 2 else np.nan,
            "tile_count_median_ratio_b_over_a": float(np.median(T.n_b / T.n_a.clip(lower=1))) if len(T) else np.nan}
    summ["tiles_a_only_total"] = int(S.tiles_a_only.sum())
    summ["tiles_b_only_total"] = int(S.tiles_b_only.sum())
    summ["max_frac_cells_b_only"] = float(S.frac_cells_b_only.max())
    summ["max_abs_delta_b_extra"] = float(np.nanmax(np.abs(S[[f"delta_{st}_b_extra" for st in C.STATES]].values)))
    for st in C.STATES:
        x, y = S[f"frac_{st}_a"], S[f"frac_{st}_b"]
        summ[f"composition_r_{st}"] = stats.pearsonr(x, y)[0] if len(S) > 2 and x.std() > 0 and y.std() > 0 else np.nan

    # concordance of slide-level results between methods
    if a.metrics_a and a.metrics_b:
        ma = pd.read_csv(a.metrics_a); mb = pd.read_csv(a.metrics_b)
        ma, mb = ma[ma.q == a.q].set_index("slide"), mb[mb.q == a.q].set_index("slide")
        idx = ma.index.intersection(mb.index)
        conc = []
        for c in ma.columns:
            if c in ("q", "n_cells") or c not in mb:
                continue
            x, y = ma.loc[idx, c].astype(float), mb.loc[idx, c].astype(float)
            if len(idx) > 3 and x.std() > 0 and y.std() > 0:
                conc.append({"metric": c, "spearman_across_slides": stats.spearmanr(x, y)[0]})
        Cc = pd.DataFrame(conc)
        if a.stats_a and a.stats_b:
            sa, sb = pd.read_csv(a.stats_a).set_index("metric"), pd.read_csv(a.stats_b).set_index("metric")
            Cc["age_slope_a"] = Cc.metric.map(sa["slope_per_wk"]); Cc["age_slope_b"] = Cc.metric.map(sb["slope_per_wk"])
            Cc["p_perm_a"] = Cc.metric.map(sa["p_perm"]); Cc["p_perm_b"] = Cc.metric.map(sb["p_perm"])
            Cc["same_sign"] = np.sign(Cc.age_slope_a) == np.sign(Cc.age_slope_b)
        Cc.to_csv(os.path.join(a.out, "method_concordance.csv"), index=False)
    pd.Series(summ).to_csv(os.path.join(a.out, "summary.csv"))
    print(pd.Series(summ).to_string(float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    main()
