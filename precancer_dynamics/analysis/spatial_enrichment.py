#!/usr/bin/env python3
"""
spatial_enrichment.py - cell-state neighbourhood enrichment with a permutation null.

For every slide:
  1. Cells get a coarse state (common.assign_states, pooled reference from slide_stats.py).
  2. Neighbour pairs = cells closer than r micrometres, counted within tiles (pairs crossing a
     1024-px tile border are not counted, identically for observed and null).
  3. Null: state labels shuffled WITHIN each tile (keeps local cell density and tile composition,
     so enrichment reflects arrangement, not regional abundance). n_perm shuffles.
  4. Output per state pair: observed count, null mean/sd, z-score, log2(obs/expected), empirical p.
Radius sensitivity: run for several r (default 10, 20, 30 um).
Slide-level log2(obs/exp) for each pair is then tested against age (+ sex) as in slide_stats
(z is reported per slide only: it scales with the number of cells, so it is not compared across slides).

Usage:
  python spatial_enrichment.py --cells cells --tag ws --meta slide_meta.csv \
         --ref results/ws/pooled_reference.npz --out results/ws/spatial
"""
import argparse, os
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import common as C

K = len(C.STATES)


def load_ref(path, files, fa):
    z = np.load(path)
    ref = {"markers": [str(m) for m in z["markers"]], "median": z["median"], "iqr": z["iqr"]}
    # rebuild score quantiles exactly as in pooled_reference
    full = C.pooled_reference(files, filter_area=fa)
    assert np.allclose(full["median"], ref["median"]), "reference mismatch: rerun slide_stats.py"
    return full


def tile_pairs(xy, tile, r_px):
    """within-tile neighbour pairs (i<j), indices into the arrays"""
    out = []
    order = np.argsort(tile, kind="stable")
    t_sorted = tile[order]
    bounds = np.flatnonzero(np.diff(t_sorted)) + 1
    for blk in np.split(order, bounds):
        if len(blk) < 2:
            continue
        pr = cKDTree(xy[blk]).query_pairs(r_px, output_type="ndarray")
        if len(pr):
            out.append(blk[pr])
    return np.concatenate(out) if out else np.empty((0, 2), int)


def pair_counts(lab, pairs):
    a, b = lab[pairs[:, 0]], lab[pairs[:, 1]]
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    return np.bincount(lo * K + hi, minlength=K * K).reshape(K, K)


def within_tile_shuffle(lab, tile, rng):
    order = np.lexsort((rng.random(len(lab)), tile))      # cells grouped by tile, random order inside
    base = np.argsort(tile, kind="stable")                # cells grouped by tile, original order
    out = np.empty_like(lab)
    out[base] = lab[order]
    return out


def enrichment(lab, tile, pairs, n_perm, rng):
    obs = pair_counts(lab, pairs)
    null = np.stack([pair_counts(within_tile_shuffle(lab, tile, rng), pairs) for _ in range(n_perm)])
    mu, sd = null.mean(0), null.std(0)
    z = (obs - mu) / np.where(sd > 0, sd, np.nan)
    l2 = np.log2((obs + 1) / (mu + 1))
    p_hi = (1 + (null >= obs).sum(0)) / (1 + n_perm)
    p_lo = (1 + (null <= obs).sum(0)) / (1 + n_perm)
    return obs, mu, sd, z, l2, np.minimum(1, 2 * np.minimum(p_hi, p_lo))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--radii_um", type=float, nargs="+", default=[20, 10, 30])
    ap.add_argument("--q", type=int, default=75)
    ap.add_argument("--n_perm", type=int, default=200)
    ap.add_argument("--max_tiles", type=int, default=0, help="random subset of tiles per slide (0 = all)")
    ap.add_argument("--no_area_filter", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    fa = not a.no_area_filter
    meta = C.load_meta(a.meta)
    files = {s: p for s, p in C.find_cells(a.cells, a.tag).items() if s in meta.index}
    ref = load_ref(a.ref, files, fa)
    rng = np.random.default_rng(a.seed)

    rows = []
    for s, p in files.items():
        d = C.load_cells(p, fa)
        if a.max_tiles and len(np.unique(d["tile"])) > a.max_tiles:
            keep_t = rng.choice(np.unique(d["tile"]), a.max_tiles, replace=False)
            m = np.isin(d["tile"], keep_t)
            d = {k: (v[m] if isinstance(v, np.ndarray) and len(v) == len(m) else v) for k, v in d.items()}
        lab = C.assign_states(C.positives(C.lineage_scores(d["X"], d["markers"], ref), ref, a.q))
        mpp = float(meta.loc[s, "mpp"])
        for r_um in a.radii_um:
            pairs = tile_pairs(d["xy"].astype(float), d["tile"], r_um / mpp)
            obs, mu, sd, z, l2, pv = enrichment(lab, d["tile"], pairs, a.n_perm, rng)
            for i in range(K):
                for j in range(i, K):
                    rows.append({"slide": s, "radius_um": r_um, "a": C.STATES[i], "b": C.STATES[j],
                                 "pair": f"{C.STATES[i]}-{C.STATES[j]}", "obs": int(obs[i, j]),
                                 "exp": mu[i, j], "z": z[i, j], "log2_oe": l2[i, j], "p": pv[i, j]})
            print(f"  {s} r={r_um:g}um: {len(lab):,} cells, {len(pairs):,} pairs", flush=True)
    E = pd.DataFrame(rows)
    E.to_csv(os.path.join(a.out, "enrichment_by_slide.csv"), index=False)

    # slide-level trend of each pair's z-score (primary radius)
    r0 = a.radii_um[0]
    res = []
    for pair, g in E[E.radius_um == r0].groupby("pair"):
        g = g.set_index("slide").loc[[s for s in meta.index if s in files]]
        # trend is tested on log2(obs/exp): z grows with the number of cells, log2 O/E does not
        y = g["log2_oe"].values.astype(float)
        if np.any(~np.isfinite(y)) or np.std(y) == 0:
            continue
        md = meta.loc[g.index]
        r = {"pair": pair, "mean_log2_oe": float(np.mean(y)), "n_slides_z>2": int(np.sum(g["z"] > 2)),
             "n_slides_z<-2": int(np.sum(g["z"] < -2))}
        r.update(C.age_test(y, md, 5000))
        r.update(C.stage_test(y, md))
        res.append(r)
    R = pd.DataFrame(res)
    R["q_perm"] = C.bh(R["p_perm"].values)
    R.to_csv(os.path.join(a.out, f"enrichment_trend_r{r0:g}.csv"), index=False)
    # radius sensitivity: do pair z-scores keep their sign across radii?
    piv = E.pivot_table(index=["slide", "pair"], columns="radius_um", values="z")
    piv["same_sign"] = (np.sign(piv).nunique(axis=1) == 1)
    piv.groupby("pair")["same_sign"].mean().rename("frac_slides_sign_stable").to_csv(
        os.path.join(a.out, "radius_sensitivity.csv"))
    print(R.sort_values("p_perm")[["pair", "mean_log2_oe", "n_slides_z>2", "slope_per_wk", "p_perm", "q_perm"]]
          .head(12).to_string(index=False, float_format=lambda v: f"{v:.3g}"))


if __name__ == "__main__":
    main()
