import sys, numpy as np, pandas as pd
from ksens_lib import *
occ = pd.read_csv("ksens/niche_occupancy_K4.csv", index_col=0)
names = ["Epi-rich", "Immune-rich", "Mes-rich", "Low-signal"]; I, L, E, M = 1, 3, 0, 2
P = occ[names].values; ages = occ.age_wk.values.astype(float); K = 4; n = P.shape[0] * (K - 1)
TOP = {"I→L→E→M (chain)": [(I, L), (L, E), (E, M)],
       "I→L→M→E": [(I, L), (L, M), (M, E)],
       "I→L, L→E, L→M (branch)": [(I, L), (L, E), (L, M)],
       "I→E→M, I→L": [(I, E), (E, M), (I, L)],
       "I→L→E, I→M": [(I, L), (L, E), (I, M)],
       "I→E, I→M (direct)": [(I, E), (I, M)],
       "I→L→E→M + E→L": [(I, L), (L, E), (E, M), (E, L)],
       "I→L→E→M + M→E": [(I, L), (L, E), (E, M), (M, E)],
       "branch + E→M": [(I, L), (L, E), (L, M), (E, M)],
       "I→L→E→M + I→E": [(I, L), (L, E), (E, M), (I, E)]}
rows = []
for nm, e in TOP.items():
    Q, th, sse, _ = fit_free(P, ages, lam=0, edges=e, starts=8)
    k = K - 1 + len(e)
    rows.append(dict(model=nm, n_params=k, R2=1 - sse / np.sum((P - P.mean(0)) ** 2), AICc=aicc(sse, n, k),
                     rates="; ".join(f"{names[i][:3]}→{names[j][:3]} {Q[i,j]:.3f}" for i, j in e)))
D = pd.DataFrame(rows); D["dAICc"] = D.AICc - D.AICc.min(); D = D.sort_values("AICc")
pd.set_option("display.width", 220); print(D[["model", "n_params", "R2", "dAICc", "rates"]].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
D.to_csv("ksens/topology_comparison_K4.csv", index=False)
cen = (P * ages[:, None]).sum(0) / P.sum(0); print("age centres", dict(zip(names, cen.round(2))))
