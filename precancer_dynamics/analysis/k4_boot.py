from ksens_lib import *
occ = pd.read_csv("ksens/niche_occupancy_K4.csv", index_col=0)
names = ["Epi-rich", "Immune-rich", "Mes-rich", "Low-signal"]; I, L, E, M = 1, 3, 0, 2
P = occ[names].values; ages = occ.age_wk.values.astype(float); sx = occ.sex.values
e = [(I, L), (L, E), (E, M)]
Q, th, sse, _ = fit_free(P, ages, lam=0, edges=e, starts=8)
rng = np.random.default_rng(1); bs = []
F, Mi = np.flatnonzero(sx == "F"), np.flatnonzero(sx == "M")
for b in range(500):
    ii = np.r_[rng.choice(F, len(F)), rng.choice(Mi, len(Mi))]
    Qb, _, _, _ = fit_free(P[ii], ages[ii], lam=0, edges=e, starts=2, seed=b)
    bs.append([Qb[i, j] for i, j in e])
bs = np.array(bs); lo, hi = np.percentile(bs, [2.5, 97.5], 0)
R = pd.DataFrame({"edge": [f"{names[i]} -> {names[j]}" for i, j in e], "rate_per_wk": [Q[i, j] for i, j in e], "ci_lo": lo, "ci_hi": hi})
R["dwell_wk"] = 1 / R.rate_per_wk; print(R.round(3).to_string(index=False))
R.to_csv("ksens/chain_rates_bootstrap_K4.csv", index=False)
pm, pl, pmean = [], [], []
for i in range(len(P)):
    m = np.arange(len(P)) != i
    def predict_one(th_):
        p0 = np.exp(np.r_[0, th_[:3]]); p0 /= p0.sum(); Qx = np.zeros((4, 4))
        for (a, b), v in zip(e, np.exp(th_[3:])): Qx[a, b] = v
        Qx[np.diag_indices(4)] = -Qx.sum(1); return p0 @ expm(Qx * (ages[i] - 4))
    _, thi, _, _ = fit_free(P[m], ages[m], lam=0, edges=e, starts=4, seed=i)
    pm.append(predict_one(thi)); pmean.append(P[m].mean(0))
    x = np.clip([np.polyval(np.polyfit(ages[m], P[m, k], 1), ages[i]) for k in range(4)], 0, None); pl.append(x / x.sum())
r2 = lambda pr: 1 - np.sum((np.array(pr) - P) ** 2) / np.sum((P - P.mean(0)) ** 2)
print("LOO R2 chain", round(r2(pm), 3), "linear(8 slopes)", round(r2(pl), 3), "mean", round(r2(pmean), 3))
pd.DataFrame([dict(predictor="chain (3 rates)", LOO_R2=r2(pm)), dict(predictor="linear trends", LOO_R2=r2(pl)), dict(predictor="no age", LOO_R2=r2(pmean))]).to_csv("ksens/loo_prediction_K4.csv", index=False)
