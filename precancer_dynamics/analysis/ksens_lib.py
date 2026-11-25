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
