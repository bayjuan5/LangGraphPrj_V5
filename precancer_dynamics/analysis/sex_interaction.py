"""Age x sex interaction for slide-level metrics (q75) and K=4 niche occupancy.
Model y = a + b*age + c*male + d*age*male; permutation P for d by shuffling sex labels
within age-matched pairs is not possible (unequal ages), so we permute residuals of the
additive model (Freedman-Lane) 10,000 times. Also report sex-specific slopes."""
import numpy as np, pandas as pd
rng = np.random.default_rng(0)
import os
U = os.path.dirname(os.path.abspath(__file__)) + "/"
meta = pd.read_csv(U + "slide_meta.csv", index_col=0)
sm = pd.read_csv(U + "results/sd2x04/slide_metrics.csv"); sm = sm[sm.q == 75].set_index("slide")
occ = pd.read_csv("ksens/niche_occupancy_K4.csv", index_col=0)
df = meta.join(sm).join(occ[["Immune-rich", "Low-signal", "Epi-rich", "Mes-rich"]].add_prefix("niche_"))
age = df.age_wk.values.astype(float); male = (df.sex == "M").values.astype(float)
X0 = np.column_stack([np.ones_like(age), age, male]); X1 = np.column_stack([X0, age * male])
def coef(X, y): return np.linalg.lstsq(X, y, rcond=None)[0]
def tstat(y):
    b = coef(X1, y); r = y - X1 @ b; s2 = r @ r / (len(y) - 4)
    se = np.sqrt(s2 * np.linalg.inv(X1.T @ X1)[3, 3]); return b[3] / se, b
metrics = {"frac_Mesenchymal": "Mesenchymal fraction", "frac_Immune": "Immune fraction", "frac_Epithelial": "Epithelial fraction",
           "frac_E+M+": "E+M+ fraction", "mean_score_T": "T-cell score", "mean_score_B": "B-cell score", "mean_score_Myeloid": "Myeloid score",
           "niche_Immune-rich": "Niche: Immune-rich", "niche_Low-signal": "Niche: Low-signal", "niche_Epi-rich": "Niche: Epi-rich", "niche_Mes-rich": "Niche: Mes-rich"}
rows = []
for c, lab in metrics.items():
    y = df[c].values.astype(float)
    t_obs, b = tstat(y)
    b0 = coef(X0, y); fit0 = X0 @ b0; res0 = y - fit0
    null = np.array([tstat(fit0 + rng.permutation(res0))[0] for _ in range(10000)])
    p = (1 + np.sum(np.abs(null) >= abs(t_obs))) / 10001
    sF = b[1]; sM = b[1] + b[3]
    rows.append(dict(metric=lab, slope_F=sF, slope_M=sM, interaction=b[3], P_interaction=p,
                     same_direction=bool(np.sign(sF) == np.sign(sM))))
R = pd.DataFrame(rows)
p = R.P_interaction.values; o = np.argsort(p); m = len(p); q = np.empty(m)
q[o] = np.minimum.accumulate((p[o] * m / np.arange(1, m + 1))[::-1])[::-1]; R["q"] = np.minimum(q, 1)
pd.set_option("display.width", 200)
print(R.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
R.to_csv("ksens/sex_interaction.csv", index=False)
