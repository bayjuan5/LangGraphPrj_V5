#!/usr/bin/env python3
"""K sensitivity for tissue niches: re-cluster the same tile features at K = 3, 4, 5 (same procedure as
niche_transitions.py), then fit (i) a penalised free CTMC with leave-one-slide-out edge stability and
(ii) an age-ordered irreversible chain, with AICc comparison."""
import sys, json
import numpy as np, pandas as pd
from scipy.linalg import expm
from scipy.optimize import minimize
from scipy.stats import spearmanr
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import adjusted_rand_score

T = pd.read_csv(sys.argv[1]); meta = pd.read_csv(sys.argv[2], index_col=0); out = sys.argv[3]
feat = [c for c in T.columns if c.startswith(("frac_", "mean_"))]
Z = StandardScaler().fit_transform(T[feat])
order = [s for s in meta.index if s in set(T.slide)]
ages = meta.loc[order, "age_wk"].values.astype(float); sex = meta.loc[order, "sex"].values

def name_niche(p):
    f = {k[5:]: p[k] for k in p.index if k.startswith("frac_")}
    top = sorted([(v, k) for k, v in f.items() if k != "Other"], reverse=True)
    if f["Other"] > 0.55: return "Low-signal"
    if top[0][1] == "Immune" and top[0][0] > 0.2: return "Immune-rich"
    if top[0][1] == "Endothelial": return "Endothelial-rich"
    a, b = top[0][1], top[1][1]
    if {a, b} == {"Epithelial", "Mesenchymal"} and top[1][0] > 0.6 * top[0][0]: return "Epi/Mes-rich"
    return f"{a[:3]}-rich"

def fit_free(P, a, lam=1e-3, x0=None, edges=None, starts=4, seed=0):
    K = P.shape[1]
    E = edges if edges is not None else [(i, j) for i in range(K) for j in range(K) if i != j]
    rng = np.random.default_rng(seed)
    def pred(th, ag):
        p0 = np.exp(np.r_[0, th[:K - 1]]); p0 /= p0.sum()
        Q = np.zeros((K, K))
        for (i, j), v in zip(E, np.exp(th[K - 1:])): Q[i, j] = v
        Q[np.diag_indices(K)] = -Q.sum(1)
        return np.stack([p0 @ expm(Q * (x - 4)) for x in ag]), Q
    f = lambda th: np.sum((pred(th, a)[0] - P) ** 2) + lam * np.sum(np.exp(th[K - 1:]) ** 2)
    best = None
    for s in range(starts):
        x = np.r_[rng.normal(0, 1, K - 1), np.log(rng.uniform(0.02, 0.4, len(E)))] if (x0 is None or s) else x0
        r = minimize(f, x, method="L-BFGS-B", bounds=[(-8, 8)] * (K - 1) + [(-10, 2)] * len(E))
        if best is None or r.fun < best.fun: best = r
    Pp, Q = pred(best.x, a)
    return Q, best.x, np.sum((Pp - P) ** 2), Pp

def aicc(sse, n, k):
    ll = -n / 2 * np.log(sse / n); return -2 * ll + 2 * k + 2 * k * (k + 1) / max(n - k - 1, 1)

rng = np.random.default_rng(0)
per = int(T.groupby("slide").size().min())
fit_idx = np.concatenate([rng.choice(np.flatnonzero(T.slide == s), per, replace=False) for s in T.slide.unique()])
summary = {}; lines = []
for K in (3, 4, 5):
    km = KMeans(K, n_init=20, random_state=0).fit(Z[fit_idx]); lab = km.predict(Z)
    if K == 3: summary["ARI_vs_original_K3"] = float(adjusted_rand_score(T.niche, lab))
    prof = T.assign(n=lab).groupby("n")[feat].mean(); prof["n_tiles"] = np.bincount(lab)
    occ = pd.crosstab(T.slide, lab, normalize="index").reindex(index=order, columns=range(K), fill_value=0)
    P = occ.values
    names = [name_niche(prof.loc[k]) for k in range(K)]
    # make names unique
    seen = {}
    for i, n in enumerate(names):
        seen[n] = seen.get(n, 0) + 1
        if seen[n] > 1: names[i] = f"{n} {seen[n]}"
    trend = [spearmanr(ages, P[:, k]) for k in range(K)]
    # age-weighted centre of each niche -> order for the irreversible chain
    centre = (P * ages[:, None]).sum(0) / P.sum(0)
    chain_order = list(np.argsort(centre))
    chain = [(chain_order[i], chain_order[i + 1]) for i in range(K - 1)]
    n_obs = P.shape[0] * (K - 1)
    Qc, thc, ssec, _ = fit_free(P, ages, lam=0, edges=chain, starts=6)
    Qf, thf, ssef, predf = fit_free(P, ages, lam=1e-3, starts=4)
    full_edges = [(i, j) for i in range(K) for j in range(K) if i != j]
    _, _, ssef0, _ = fit_free(P, ages, lam=0, starts=4)
    # LOO stability of free-CTMC edges
    R = []
    for i in range(len(P)):
        m = np.arange(len(P)) != i
        Qi, _, _, _ = fit_free(P[m], ages[m], 1e-3, x0=thf, starts=1)
        R.append(Qi)
    R = np.stack(R)
    stable = [(i, j, Qf[i, j], float(np.mean(R[:, i, j] > 0.02))) for i, j in full_edges if np.mean(R[:, i, j] > 0.02) >= 0.8]
    r2 = lambda sse: 1 - sse / np.sum((P - P.mean(0)) ** 2)
    res = dict(K=K, names=names, n_tiles=prof.n_tiles.tolist(),
               spearman_rho=[float(t.correlation) for t in trend], spearman_p=[float(t.pvalue) for t in trend],
               chain=[f"{names[i]} -> {names[j]}" for i, j in chain],
               chain_rates=[float(Qc[i, j]) for i, j in chain],
               chain_R2=float(r2(ssec)), chain_AICc=float(aicc(ssec, n_obs, K - 1 + len(chain))),
               full_R2=float(r2(ssef0)), full_AICc=float(aicc(ssef0, n_obs, K - 1 + len(full_edges))),
               stable_edges=[f"{names[i]} -> {names[j]} ({q:.3f}/wk, LOO {f:.2f})" for i, j, q, f in stable])
    summary[f"K{K}"] = res
    prof.insert(0, "name", names); prof.to_csv(f"{out}/niche_profiles_K{K}.csv")
    occ.columns = names; occ.join(meta[["sex", "age_wk", "stage"]]).to_csv(f"{out}/niche_occupancy_K{K}.csv")
    print(f"\n=== K = {K} ===")
    print(prof[["name", "frac_Epithelial", "frac_Mesenchymal", "frac_Hybrid", "frac_Immune", "frac_Endothelial", "frac_Other", "n_tiles"]].round(2).to_string())
    for k in range(K):
        print(f"  {names[k]:18s} rho with age {trend[k].correlation:+.2f} (p {trend[k].pvalue:.3g}); early {P[ages<=5,k].mean():.2f} -> adult {P[ages>=11,k].mean():.2f}")
    print("  chain:", " | ".join(f"{c} {r:.3f}/wk" for c, r in zip(res["chain"], res["chain_rates"])), f"R2 {res['chain_R2']:.2f} AICc {res['chain_AICc']:.1f}")
    print(f"  free CTMC R2 {res['full_R2']:.2f} AICc {res['full_AICc']:.1f}; stable edges: {res['stable_edges']}")
json.dump(summary, open(f"{out}/k_sensitivity.json", "w"), indent=1)
print("\nARI K3 vs original:", summary["ARI_vs_original_K3"])
