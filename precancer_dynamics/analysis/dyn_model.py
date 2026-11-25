#!/usr/bin/env python3
"""dyn_model.py - population-level state-transition model of tissue-niche occupancy vs age.
Inputs: niche_occupancy.csv (slide x niche fractions, sex, age_wk).
Niches: 0 = Epi/Mes-rich, 1 = Immune-rich, 2 = Low-signal.
Model: p(t) = p0 expm(Q (t - 4)), rates >= 0, p0 free on the simplex (2 params).
1) topology comparison (AICc / BIC), 2) slide bootstrap CIs, 3) leave-one-slide-out prediction,
4) homogeneous vs rate change at 7 wk (change point from the composition analysis)."""
import sys, json, itertools
import numpy as np, pandas as pd
from scipy.linalg import expm
from scipy.optimize import minimize

occ = pd.read_csv(sys.argv[1], index_col=0)
out = sys.argv[2]
NAMES = {0: "Epi/Mes-rich", 1: "Immune-rich", 2: "Low-signal"}
P = occ[["0", "1", "2"]].values.astype(float)
ages = occ.age_wk.values.astype(float)
K, T0 = 3, 4.0

def softmax(z): e = np.exp(np.r_[0.0, z]); return e / e.sum()

def predict(theta, edges, ages, brk=None):
    p0 = softmax(theta[:2]); r = np.exp(theta[2:])
    ne = len(edges)
    def Qm(rv):
        Q = np.zeros((K, K))
        for (i, j), v in zip(edges, rv): Q[i, j] = v
        Q[np.diag_indices(K)] = -Q.sum(1); return Q
    if brk is None:
        Q = Qm(r[:ne]); return np.stack([p0 @ expm(Q * (a - T0)) for a in ages])
    Q1, Q2 = Qm(r[:ne]), Qm(r[ne:2 * ne])
    pb = p0 @ expm(Q1 * (brk - T0))
    return np.stack([p0 @ expm(Q1 * (a - T0)) if a <= brk else pb @ expm(Q2 * (a - brk)) for a in ages])

def fit(Pm, am, edges, brk=None, starts=6, seed=0):
    rng = np.random.default_rng(seed)
    nr = len(edges) * (2 if brk else 1)
    best = None
    for s in range(starts):
        x0 = np.r_[rng.normal(0, 1, 2), np.log(rng.uniform(0.02, 0.4, nr))]
        f = lambda th: np.sum((predict(th, edges, am, brk) - Pm) ** 2)
        r = minimize(f, x0, method="L-BFGS-B", bounds=[(-8, 8)] * 2 + [(-10, 2)] * nr)
        if best is None or r.fun < best.fun: best = r
    return best.x, best.fun

ALL = [(i, j) for i in range(K) for j in range(K) if i != j]
TOPO = {
    "chain I->L->E (selected)": [(1, 2), (2, 0)],
    "chain + direct I->E": [(1, 2), (2, 0), (1, 0)],
    "reversible chain": [(1, 2), (2, 1), (2, 0), (0, 2)],
    "direct I->E only": [(1, 0)],
    "I->E, I->L (no L->E)": [(1, 0), (1, 2)],
    "alt chain I->E->L": [(1, 0), (0, 2)],
    "alt chain L->I->E": [(2, 1), (1, 0)],
    "fully connected": ALL,
}
n_obs = P.shape[0] * (K - 1)
rows = []; fits = {}
for name, e in TOPO.items():
    th, sse = fit(P, ages, e, starts=8)
    kpar = 2 + len(e)
    ll = -n_obs / 2 * np.log(sse / n_obs)
    aicc = -2 * ll + 2 * kpar + 2 * kpar * (kpar + 1) / max(n_obs - kpar - 1, 1)
    bic = -2 * ll + kpar * np.log(n_obs)
    r2 = 1 - sse / np.sum((P - P.mean(0)) ** 2)
    rows.append(dict(model=name, n_rates=len(e), n_params=kpar, SSE=sse, R2=r2, AICc=aicc, BIC=bic,
                     rates=";".join(f"{NAMES[i]}->{NAMES[j]}={np.exp(v):.3f}" for (i, j), v in zip(e, th[2:]))))
    fits[name] = (e, th)
# rate change at 7 wk for the selected chain
e = TOPO["chain I->L->E (selected)"]
th_b, sse_b = fit(P, ages, e, brk=7.0, starts=8)
kpar = 2 + 2 * len(e); ll = -n_obs / 2 * np.log(sse_b / n_obs)
rows.append(dict(model="chain, rates change at 7 wk", n_rates=4, n_params=kpar, SSE=sse_b,
                 R2=1 - sse_b / np.sum((P - P.mean(0)) ** 2),
                 AICc=-2 * ll + 2 * kpar + 2 * kpar * (kpar + 1) / (n_obs - kpar - 1),
                 BIC=-2 * ll + kpar * np.log(n_obs),
                 rates=";".join(f"{lab}{NAMES[i]}->{NAMES[j]}={np.exp(v):.3f}" for lab, ((i, j), v) in
                                zip(["<7:"] * 2 + [">7:"] * 2, zip(e + e, th_b[2:])))))
M = pd.DataFrame(rows)
M["dAICc"] = M.AICc - M.AICc.min(); M["dBIC"] = M.BIC - M.BIC.min()
M = M.sort_values("AICc"); M.to_csv(f"{out}/topology_comparison.csv", index=False)
print(M[["model", "n_params", "R2", "dAICc", "dBIC"]].to_string(index=False, float_format=lambda v: f"{v:.3f}"))

# bootstrap (resample slides within sex) for the selected chain
e, th = fits["chain I->L->E (selected)"]
rng = np.random.default_rng(1); B = 1000; bs = []; curves = []
grid = np.linspace(4, 12, 81)
idxF = np.flatnonzero(occ.sex.values == "F"); idxM = np.flatnonzero(occ.sex.values == "M")
for b in range(B):
    ii = np.r_[rng.choice(idxF, len(idxF)), rng.choice(idxM, len(idxM))]
    thb, _ = fit(P[ii], ages[ii], e, starts=2, seed=b)
    bs.append(np.exp(thb[2:])); curves.append(predict(thb, e, grid))
bs = np.array(bs); curves = np.array(curves)
th_hat = th
pt = np.exp(th_hat[2:])
ci = np.percentile(bs, [2.5, 97.5], axis=0)
R = pd.DataFrame({"edge": [f"{NAMES[i]} -> {NAMES[j]}" for i, j in e], "rate_per_wk": pt,
                  "ci_lo": ci[0], "ci_hi": ci[1], "mean_dwell_wk": 1 / pt,
                  "dwell_ci_lo": 1 / ci[1], "dwell_ci_hi": 1 / ci[0]})
R.to_csv(f"{out}/chain_rates_bootstrap.csv", index=False)
print(R.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
fit_curve = predict(th_hat, e, grid)
C = pd.DataFrame({"age_wk": grid})
for k in range(K):
    C[f"fit_{k}"] = fit_curve[:, k]
    C[f"lo_{k}"] = np.percentile(curves[:, :, k], 2.5, axis=0)
    C[f"hi_{k}"] = np.percentile(curves[:, :, k], 97.5, axis=0)
C.to_csv(f"{out}/chain_fit_curves.csv", index=False)
cross = grid[np.argmax(fit_curve[:, 0] > fit_curve[:, 1])]

# leave-one-slide-out prediction vs baselines
pred_m, pred_mean, pred_lin = [], [], []
for i in range(len(P)):
    m = np.arange(len(P)) != i
    thi, _ = fit(P[m], ages[m], e, starts=4, seed=i)
    pred_m.append(predict(thi, e, ages[i:i + 1])[0])
    pred_mean.append(P[m].mean(0))
    pl = np.array([np.polyval(np.polyfit(ages[m], P[m, k], 1), ages[i]) for k in range(K)])
    pl = np.clip(pl, 0, None); pred_lin.append(pl / pl.sum())
def r2(pr): pr = np.array(pr); return 1 - np.sum((pr - P) ** 2) / np.sum((P - P.mean(0)) ** 2)
def mae(pr): return float(np.mean(np.abs(np.array(pr) - P)))
L = pd.DataFrame([
    dict(predictor="state-transition chain (2 rates)", LOO_R2=r2(pred_m), LOO_MAE=mae(pred_m)),
    dict(predictor="per-niche linear trend in age (6 params)", LOO_R2=r2(pred_lin), LOO_MAE=mae(pred_lin)),
    dict(predictor="mean occupancy, no age", LOO_R2=r2(pred_mean), LOO_MAE=mae(pred_mean))])
L.to_csv(f"{out}/loo_prediction.csv", index=False)
pd.DataFrame(np.array(pred_m), index=occ.index, columns=["pred_0", "pred_1", "pred_2"]).join(occ).to_csv(f"{out}/loo_predicted_occupancy.csv")
print(L.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
json.dump({"p0": softmax(th_hat[:2]).tolist(), "crossing_EpiMes_over_Immune_wk": float(cross),
           "n_boot": B, "n_slides": len(P)}, open(f"{out}/chain_info.json", "w"), indent=1)
print("p0", softmax(th_hat[:2]).round(3), "crossing", cross)
