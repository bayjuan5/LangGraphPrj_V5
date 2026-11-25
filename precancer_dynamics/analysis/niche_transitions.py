#!/usr/bin/env python3
"""
niche_transitions.py - tile-level tissue niches and a continuous-time state-transition model of
niche occupancy across age (replaces the Petri net of the earlier version).

  1. Each 1024-px tile (>= min_cells cells) is described by its cell-state composition
     (fractions of common.STATES) and mean lineage scores.
  2. Tiles from all slides are clustered into K niches (k-means on standardised features, equal
     weight per slide via sampling; K chosen by silhouette over k_range unless --k is given).
  3. Niche occupancy p_s = fraction of tiles of slide s in each niche.
  4. A continuous-time Markov chain dp/dt = p Q is fitted to the age-ordered occupancies:
     p(age) = p(age0) expm(Q (age - age0)), with p(age0) = mean occupancy of the youngest slides.
     Off-diagonal rates >= 0 (log-parameterised), L2 penalty lam on rates, least squares over all slides.
  5. Stability: leave-one-slide-out refits; an edge i->j is reported as stable when its rate exceeds
     min_rate in >= 80% of refits.
This is a population-level (cross-sectional) model of how niche occupancy shifts with age; it does not
track individual tiles through time, and is reported as such.

Usage:
  python niche_transitions.py --cells cells --tag ws --meta slide_meta.csv \
       --ref results/ws/pooled_reference.npz --out results/ws/niches
"""
import argparse, os, json
import numpy as np
import pandas as pd
from scipy.linalg import expm
from scipy.optimize import minimize
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
import common as C


def tile_features(d, ref, q, min_cells):
    sc = C.lineage_scores(d["X"], d["markers"], ref)
    lab = C.assign_states(C.positives(sc, ref, q))
    K = len(C.STATES)
    n = np.bincount(d["tile"], minlength=len(d["tile_names"]))
    comp = np.zeros((len(n), K))
    np.add.at(comp, (d["tile"], lab), 1)
    comp /= np.maximum(n, 1)[:, None]
    keys = ["Epi", "Mes", "Imm", "Endo", "Prolif", "ECM"]
    means = np.column_stack([np.bincount(d["tile"], weights=sc[k], minlength=len(n)) / np.maximum(n, 1) for k in keys])
    ok = n >= min_cells
    cols = [f"frac_{s}" for s in C.STATES] + [f"mean_{k}" for k in keys]
    df = pd.DataFrame(np.hstack([comp, means])[ok], columns=cols)
    df["tile"] = np.flatnonzero(ok); df["n_cells"] = n[ok]
    return df


def fit_ctmc(P, ages, lam=1e-3, x0=None):
    """P: [n_slides, K] occupancies; ages: [n_slides]."""
    K = P.shape[1]
    a0 = ages.min()
    p0 = P[ages == a0].mean(0)
    off = ~np.eye(K, dtype=bool)

    def Q_of(theta):
        Q = np.zeros((K, K)); Q[off] = np.exp(theta)
        Q[np.diag_indices(K)] = -Q.sum(1)
        return Q

    def loss(theta):
        Q = Q_of(theta)
        pred = np.stack([p0 @ expm(Q * (a - a0)) for a in ages])
        return np.sum((pred - P) ** 2) + lam * np.sum(np.exp(theta) ** 2)

    x0 = np.full(off.sum(), np.log(0.05)) if x0 is None else x0
    r = minimize(loss, x0, method="L-BFGS-B", bounds=[(-12, 3)] * off.sum())
    Q = Q_of(r.x)
    pred = np.stack([p0 @ expm(Q * (a - a0)) for a in ages])
    ss_tot = np.sum((P - P.mean(0)) ** 2)
    return Q, r.x, 1 - np.sum((pred - P) ** 2) / ss_tot, pred


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", required=True); ap.add_argument("--tag", required=True)
    ap.add_argument("--meta", required=True); ap.add_argument("--ref", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--q", type=int, default=75)
    ap.add_argument("--k", type=int, default=0)
    ap.add_argument("--k_range", type=int, nargs=2, default=[3, 7])
    ap.add_argument("--min_cells", type=int, default=50)
    ap.add_argument("--lam", type=float, default=1e-3)
    ap.add_argument("--min_rate", type=float, default=0.02, help="per week")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    meta = C.load_meta(a.meta)
    files = {s: p for s, p in C.find_cells(a.cells, a.tag).items() if s in meta.index}
    ref = C.pooled_reference(files)
    rng = np.random.default_rng(a.seed)

    tiles = []
    for s, p in files.items():
        df = tile_features(C.load_cells(p), ref, a.q, a.min_cells); df["slide"] = s; tiles.append(df)
    T = pd.concat(tiles, ignore_index=True)
    feat = [c for c in T.columns if c.startswith(("frac_", "mean_"))]
    scaler = StandardScaler().fit(T[feat])
    Z = scaler.transform(T[feat])
    # equal weight per slide for fitting the clustering
    per = int(T.groupby("slide").size().min())
    fit_idx = np.concatenate([rng.choice(np.flatnonzero(T.slide == s), per, replace=False) for s in T.slide.unique()])
    if a.k:
        k = a.k; sil = {}
    else:
        sil = {}
        for kk in range(a.k_range[0], a.k_range[1] + 1):
            km = KMeans(kk, n_init=10, random_state=a.seed).fit(Z[fit_idx])
            sil[kk] = float(silhouette_score(Z[fit_idx], km.labels_, sample_size=min(5000, len(fit_idx)), random_state=a.seed))
        k = max(sil, key=sil.get)
    km = KMeans(k, n_init=20, random_state=a.seed).fit(Z[fit_idx])
    T["niche"] = km.predict(Z)
    prof = T.groupby("niche")[feat].mean()
    prof["n_tiles"] = T.groupby("niche").size()
    prof.to_csv(os.path.join(a.out, "niche_profiles.csv"))
    T.to_csv(os.path.join(a.out, "tile_niches.csv"), index=False)

    occ = pd.crosstab(T.slide, T.niche, normalize="index").reindex(columns=range(k), fill_value=0)
    order = [s for s in meta.index if s in occ.index]
    occ = occ.loc[order]
    md = meta.loc[order]
    occ.join(md[["sex", "age_wk", "stage"]]).to_csv(os.path.join(a.out, "niche_occupancy.csv"))

    # occupancy vs age (slide-level, sex covariate)
    trend = []
    for j in range(k):
        y = occ[j].values.astype(float)
        if np.std(y) > 0:
            r = {"niche": j}; r.update(C.age_test(y, md, 5000)); r.update(C.stage_test(y, md)); trend.append(r)
    Tr = pd.DataFrame(trend); Tr["q_perm"] = C.bh(Tr.p_perm.values)
    Tr.to_csv(os.path.join(a.out, "niche_occupancy_trend.csv"), index=False)

    # CTMC + leave-one-slide-out stability
    P, ages = occ.values, md["age_wk"].values.astype(float)
    Q, th, r2, pred = fit_ctmc(P, ages, a.lam)
    rates = []
    for i in range(len(order)):
        m = np.arange(len(order)) != i
        # if the youngest slide is left out, p0 comes from the next-youngest slide(s)
        Qi, _, _, _ = fit_ctmc(P[m], ages[m], a.lam, th)
        rates.append(Qi)
    R = np.stack(rates)
    edges = []
    for i in range(k):
        for j in range(k):
            if i != j:
                edges.append({"from": i, "to": j, "rate_per_wk": Q[i, j],
                              "loo_median": float(np.median(R[:, i, j])),
                              "loo_frac_above_min": float(np.mean(R[:, i, j] > a.min_rate)),
                              "stable": bool(np.mean(R[:, i, j] > a.min_rate) >= 0.8)})
    E = pd.DataFrame(edges).sort_values("rate_per_wk", ascending=False)
    E.to_csv(os.path.join(a.out, "ctmc_edges.csv"), index=False)
    pd.DataFrame(pred, index=order).to_csv(os.path.join(a.out, "ctmc_fitted_occupancy.csv"))
    with open(os.path.join(a.out, "ctmc_info.json"), "w") as fh:
        json.dump({"k": k, "silhouette": sil, "r2": r2, "lam": a.lam, "min_rate": a.min_rate,
                   "features": feat, "n_tiles": len(T)}, fh, indent=1)
    print(f"k={k} (silhouette {sil}), CTMC R2={r2:.3f}")
    print(prof.round(2).to_string())
    print(E.head(8).to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    main()
