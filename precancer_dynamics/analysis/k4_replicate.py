"""Replicate the K=4 niche chain with the default StarDist threshold (sd2x tag)."""
import sys
from ksens_lib import *
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
T = pd.read_csv(sys.argv[1]); meta = pd.read_csv(sys.argv[2], index_col=0)
feat = [c for c in T.columns if c.startswith(("frac_", "mean_"))]
Z = StandardScaler().fit_transform(T[feat]); rng = np.random.default_rng(0)
per = int(T.groupby("slide").size().min())
idx = np.concatenate([rng.choice(np.flatnonzero(T.slide == s), per, replace=False) for s in T.slide.unique()])
lab = KMeans(4, n_init=20, random_state=0).fit(Z[idx]).predict(Z)
prof = T.assign(n=lab).groupby("n")[feat].mean()
names = [name_niche(prof.loc[k]) for k in range(4)]
order = [s for s in meta.index if s in set(T.slide)]
occ = pd.crosstab(T.slide, lab, normalize="index").reindex(index=order, columns=range(4), fill_value=0)
P = occ.values; ages = meta.loc[order, "age_wk"].values.astype(float); n = 16 * 3
print(prof[["frac_Epithelial", "frac_Mesenchymal", "frac_Immune", "frac_Other"]].round(2).assign(name=names))
ix = {nm: i for i, nm in enumerate(names)}; I, L, E, M = ix["Immune-rich"], ix["Low-signal"], ix["Epi-rich"], ix["Mes-rich"]
TOP = {"I→L→E→M": [(I, L), (L, E), (E, M)], "I→L, L→E, L→M": [(I, L), (L, E), (L, M)], "I→E, I→M": [(I, E), (I, M)],
       "I→L→M→E": [(I, L), (L, M), (M, E)]}
rows = []
for nm, e in TOP.items():
    Q, th, sse, _ = fit_free(P, ages, lam=0, edges=e, starts=8)
    rows.append(dict(model=nm, AICc=aicc(sse, n, 3 + len(e)), R2=1 - sse / np.sum((P - P.mean(0)) ** 2),
                     rates="; ".join(f"{names[a][:3]}→{names[b][:3]} {Q[a,b]:.3f}" for a, b in e)))
D = pd.DataFrame(rows); D["dAICc"] = D.AICc - D.AICc.min(); print(D.sort_values("AICc").to_string(index=False))
D.to_csv(sys.argv[3], index=False)
