"""
common.py - shared definitions for the slide-level and spatial analyses.

Design choices (stated so they can be reported in Methods):
  * No rule-based phenotype classifier. Each cell gets continuous lineage scores = mean of robust
    z-scored ROSIE outputs over a small marker panel.
  * Robust z uses a POOLED reference: an equal-size random sample of cells from every slide
    (so no slide dominates), per-marker median and IQR.
  * A cell is "positive" for a lineage when its score exceeds the pooled q-th percentile of that score
    (default q = 75, sensitivity 70/80). Because the threshold is pooled, slide-to-slide differences
    in positive fractions are interpretable; the absolute level is threshold-dependent.
  * Cells with area_ok == False (nucleus area outside 20-1000 px) are excluded by default.
"""
import glob, os
import numpy as np
import pandas as pd

PANELS = {
    "Epi":    ["PanCK", "ECad", "EpCAM", "Keratin8/18"],
    "Mes":    ["Vimentin", "aSMA", "Podoplanin"],
    "Imm":    ["CD45"],
    "T":      ["CD3e", "CD4", "CD8"],
    "Myeloid": ["CD68", "CD14", "CD163", "CD11c"],
    "B":      ["CD20", "CD79a"],
    "Endo":   ["CD31", "CD34"],
    "Prolif": ["Ki67", "PCNA"],
    "ECM":    ["CollagenIV"],
    "Checkpoint": ["PDL1", "PD1", "LAG3", "TIGIT", "VISTA"],
}
STATES = ["Epithelial", "Mesenchymal", "Hybrid", "Immune", "Endothelial", "Other"]


def load_meta(path):
    m = pd.read_csv(path)
    m["slide"] = m["slide"].astype(str)
    if "stage" not in m:
        m["stage"] = pd.cut(m["age_wk"], [0, 5.5, 10.5, 99], labels=["early", "adolescence", "adulthood"]).astype(str)
    if "mpp" not in m:
        m["mpp"] = 0.5
    return m.set_index("slide")


def find_cells(cells_dir, tag):
    """cells_dir/<slide>__<tag>.npz -> {slide: path}"""
    out = {}
    for p in sorted(glob.glob(os.path.join(cells_dir, f"*__{tag}.npz"))):
        out[os.path.basename(p).split("__")[0]] = p
    return out


def load_cells(path, filter_area=True):
    z = np.load(path, allow_pickle=False)
    d = {k: z[k] for k in z.files}
    d["markers"] = [str(m) for m in d["markers"]]
    if filter_area:
        keep = d["area_ok"].astype(bool)
        for k in ("X", "xy", "tile", "area", "area_ok", "pheno"):
            d[k] = d[k][keep]
    return d


def pooled_reference(cell_files, n_per_slide=20000, seed=0, filter_area=True):
    """per-marker median / IQR from an equal-size sample of every slide"""
    rng = np.random.default_rng(seed)
    samples, markers = [], None
    for p in cell_files.values():
        d = load_cells(p, filter_area)
        markers = markers or d["markers"]
        X = d["X"][:, [d["markers"].index(m) for m in markers]]
        idx = rng.choice(len(X), size=min(n_per_slide, len(X)), replace=False)
        samples.append(X[idx])
    S = np.concatenate(samples)
    med = np.median(S, 0)
    iqr = np.subtract(*np.percentile(S, [75, 25], 0))
    iqr[iqr <= 0] = np.std(S, 0)[iqr <= 0] + 1e-12
    ref = {"markers": markers, "median": med, "iqr": iqr}
    # pooled score distribution -> thresholds
    sc = lineage_scores(S, markers, ref)
    ref["score_quantiles"] = {k: np.percentile(v, np.arange(101)) for k, v in sc.items()}
    return ref


def robust_z(X, markers, ref):
    cols = [markers.index(m) for m in ref["markers"]]
    return (X[:, cols] - ref["median"]) / ref["iqr"]


def lineage_scores(X, markers, ref):
    Z = robust_z(X, markers, ref)
    rm = ref["markers"]
    return {k: Z[:, [rm.index(m) for m in v if m in rm]].mean(1) for k, v in PANELS.items()}


def positives(scores, ref, q=75):
    return {k: v > ref["score_quantiles"][k][q] for k, v in scores.items()}


def assign_states(pos):
    """mutually exclusive coarse states used for composition and neighborhood analysis"""
    E, M, I, N = pos["Epi"], pos["Mes"], pos["Imm"], pos["Endo"]
    lab = np.full(len(E), STATES.index("Other"), np.int8)
    lab[N & ~E & ~I] = STATES.index("Endothelial")
    lab[M & ~E & ~I] = STATES.index("Mesenchymal")
    lab[E & ~M & ~I] = STATES.index("Epithelial")
    lab[E & M & ~I] = STATES.index("Hybrid")
    lab[I & ~E] = STATES.index("Immune")
    return lab


# ---------------- slide-level statistics (n = slides; numpy only) ----------------
from scipy import stats as _st


def _design(meta, extra=None, use_sex=True):
    cols = [np.ones(len(meta))]
    names = ["intercept"]
    if extra is not None:
        for n, v in extra.items():
            cols.append(v); names.append(n)
    if use_sex and meta["sex"].nunique() > 1:
        cols.append((meta["sex"].values == "M").astype(float)); names.append("sexM")
    return np.column_stack(cols), names


def ols(y, X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    dof = len(y) - X.shape[1]
    s2 = res @ res / dof
    se = np.sqrt(np.diag(s2 * np.linalg.pinv(X.T @ X)))
    t = beta / se
    p = 2 * _st.t.sf(np.abs(t), dof)
    return beta, se, p, res @ res, dof


def age_test(y, meta, n_perm=10000, seed=0):
    """y ~ age + sex. Returns slope, t-test p and a permutation p (ages permuted within sex)."""
    age = meta["age_wk"].values.astype(float)
    X, _ = _design(meta, {"age": age})
    b, se, p, _, _ = ols(y, X)
    rng = np.random.default_rng(seed)
    sex = meta["sex"].values
    null = np.empty(n_perm)
    for i in range(n_perm):
        a2 = age.copy()
        for s in np.unique(sex):
            m = sex == s
            a2[m] = rng.permutation(a2[m])
        X2, _ = _design(meta, {"age": a2})
        null[i] = np.linalg.lstsq(X2, y, rcond=None)[0][1]
    p_perm = (1 + np.sum(np.abs(null) >= abs(b[1]))) / (1 + n_perm)
    rho, p_rho = _st.spearmanr(age, y)
    return {"slope_per_wk": b[1], "p_t": p[1], "p_perm": p_perm, "spearman_rho": rho, "p_spearman": p_rho}


def stage_test(y, meta):
    """y ~ stage + sex vs y ~ sex: F-test for the stage effect"""
    st = meta["stage"].values
    lv = [s for s in ["early", "adolescence", "adulthood"] if s in set(st)]
    dummies = {f"stage_{s}": (st == s).astype(float) for s in lv[1:]}
    Xf, _ = _design(meta, dummies)
    Xr, _ = _design(meta)
    _, _, _, rss_f, dof_f = ols(y, Xf)
    _, _, _, rss_r, _ = ols(y, Xr)
    k = Xf.shape[1] - Xr.shape[1]
    F = ((rss_r - rss_f) / k) / (rss_f / dof_f)
    means = {s: float(np.mean(y[st == s])) for s in lv}
    return {"F_stage": F, "p_stage": _st.f.sf(F, k, dof_f), **{f"mean_{s}": v for s, v in means.items()}}


def changepoint(y, meta, grid=None, n_boot=2000, n_null=2000, seed=0):
    """
    Hinge (broken-stick) model y = a + b*age + c*max(0, age - tau) [+ sex]
    tau chosen on a grid by least squares. Significance of the bend: parametric bootstrap
    under the linear null (residual resampling), because tau is estimated. Uncertainty of tau:
    case bootstrap over slides, stratified by sex.
    """
    age = meta["age_wk"].values.astype(float)
    grid = np.arange(5.5, 11.0, 0.5) if grid is None else grid
    rng = np.random.default_rng(seed)

    def fit(yv, m, ag):
        Xl, _ = _design(m, {"age": ag})
        _, _, _, rss_lin, _ = ols(yv, Xl)
        best = (np.inf, None, None)
        for tau in grid:
            h = np.maximum(0, ag - tau)
            if h.max() == 0 or (ag < tau).sum() < 2:
                continue
            Xh, _ = _design(m, {"age": ag, "hinge": h})
            b, _, _, rss, _ = ols(yv, Xh)
            if rss < best[0]:
                best = (rss, tau, b)
        return rss_lin, best

    rss_lin, (rss_h, tau, b) = fit(y, meta, age)
    n = len(y)
    stat = (rss_lin - rss_h) / rss_h
    bic_lin = n * np.log(rss_lin / n) + 3 * np.log(n)
    bic_h = n * np.log(rss_h / n) + 5 * np.log(n)  # + slope change + tau
    # null: linear model + resampled residuals
    Xl, _ = _design(meta, {"age": age})
    bl = np.linalg.lstsq(Xl, y, rcond=None)[0]
    fitted, res = Xl @ bl, y - Xl @ bl
    null = []
    for _ in range(n_null):
        yb = fitted + rng.choice(res, n, replace=True)
        rl, (rh, _, _) = fit(yb, meta, age)
        null.append((rl - rh) / rh)
    p_bend = (1 + np.sum(np.array(null) >= stat)) / (1 + n_null)
    # tau CI
    taus, sex = [], meta["sex"].values
    for _ in range(n_boot):
        idx = np.concatenate([rng.choice(np.where(sex == s)[0], (sex == s).sum(), replace=True) for s in np.unique(sex)])
        if len(np.unique(age[idx])) < 4:
            continue
        _, (_, tb, _) = fit(y[idx], meta.iloc[idx], age[idx])
        if tb is not None:
            taus.append(tb)
    lo, hi = (np.percentile(taus, [2.5, 97.5]) if taus else (np.nan, np.nan))
    return {"tau_wk": tau, "tau_ci_lo": lo, "tau_ci_hi": hi,
            "slope_before": b[1] if b is not None else np.nan,
            "slope_after": (b[1] + b[2]) if b is not None else np.nan,
            "dBIC_lin_minus_hinge": bic_lin - bic_h, "p_bend": p_bend}


def bh(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    q = p[o] * len(p) / np.arange(1, len(p) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty_like(q); out[o] = np.minimum(q, 1)
    return out
