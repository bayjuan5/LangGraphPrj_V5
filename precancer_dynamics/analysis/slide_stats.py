#!/usr/bin/env python3
"""
slide_stats.py - slide-level composition, hybrid E/M state and age/stage statistics.

Unit of replication = slide. Sex enters every model as a covariate (when both sexes are present).
For each slide-level metric:
  * age trend:     y ~ age_wk + sex  (t-test, and permutation test with ages shuffled within sex)
  * stage effect:  y ~ stage + sex vs y ~ sex  (F-test; stages early 4-5, adolescence 6-10, adulthood 11-12 wk)
  * change point:  hinge model vs linear (parametric-bootstrap p, bootstrap CI on the break week)
  * BH-FDR across metrics, separately for each test family.
Threshold sensitivity: metrics are recomputed for q = 70, 75, 80.

Usage:
  python slide_stats.py --cells cells --tag ws --meta slide_meta.csv --out results/ws
"""
import argparse, json, os
import numpy as np
import pandas as pd
import common as C


def slide_metrics(d, ref, q):
    sc = C.lineage_scores(d["X"], d["markers"], ref)
    pos = C.positives(sc, ref, q)
    lab = C.assign_states(pos)
    E, M, I = pos["Epi"], pos["Mes"], pos["Imm"]
    out = {"n_cells": len(lab)}
    for i, s in enumerate(C.STATES):
        out[f"frac_{s}"] = float(np.mean(lab == i))
    out["frac_E+M-"] = float(np.mean(E & ~M))
    out["frac_E-M+"] = float(np.mean(~E & M))
    out["frac_E+M+"] = float(np.mean(E & M))
    out["hybrid_share_of_E+"] = float(np.mean(M[E])) if E.any() else np.nan
    out["corr_E_M"] = float(np.corrcoef(sc["Epi"], sc["Mes"])[0, 1])
    for k in ("Prolif", "ECM", "Endo", "Imm"):
        out[f"frac_{k}+"] = float(np.mean(pos[k]))
    for k, v in sc.items():
        out[f"mean_score_{k}"] = float(np.mean(v))
    # immune composition among immune-state cells (continuous subset scores)
    im = lab == C.STATES.index("Immune")
    for k in ("T", "Myeloid", "B", "Checkpoint"):
        out[f"immune_mean_{k}"] = float(np.mean(sc[k][im])) if im.any() else np.nan
    ep = lab == C.STATES.index("Epithelial")
    out["epi_mean_Prolif"] = float(np.mean(sc["Prolif"][ep])) if ep.any() else np.nan
    out["epi_mean_Checkpoint"] = float(np.mean(sc["Checkpoint"][ep])) if ep.any() else np.nan
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", required=True)
    ap.add_argument("--tag", required=True, help="file tag: cells/<slide>__<tag>.npz")
    ap.add_argument("--meta", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--q", type=int, nargs="+", default=[75, 70, 80])
    ap.add_argument("--n_perm", type=int, default=10000)
    ap.add_argument("--n_boot", type=int, default=2000)
    ap.add_argument("--no_area_filter", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    meta = C.load_meta(a.meta)
    files = C.find_cells(a.cells, a.tag)
    files = {s: p for s, p in files.items() if s in meta.index}
    print(f"{len(files)} slides: {', '.join(files)}")
    fa = not a.no_area_filter
    ref = C.pooled_reference(files, filter_area=fa)
    np.savez(os.path.join(a.out, "pooled_reference.npz"), markers=np.array(ref["markers"]),
             median=ref["median"], iqr=ref["iqr"])

    rows = []
    for s, p in files.items():
        d = C.load_cells(p, fa)
        for q in a.q:
            r = slide_metrics(d, ref, q); r.update(slide=s, q=q); rows.append(r)
        print(f"  {s}: {rows[-1]['n_cells']:,} cells")
    M = pd.DataFrame(rows)
    M.to_csv(os.path.join(a.out, "slide_metrics.csv"), index=False)

    # statistics on the primary threshold
    q0 = a.q[0]
    mm = M[M.q == q0].set_index("slide").loc[[s for s in meta.index if s in files]]
    md = meta.loc[mm.index]
    metrics = [c for c in mm.columns if c not in ("n_cells", "q")]
    res = []
    for c in metrics:
        y = mm[c].values.astype(float)
        if np.any(~np.isfinite(y)) or np.std(y) == 0:
            continue
        r = {"metric": c}
        r.update(C.age_test(y, md, a.n_perm))
        r.update(C.stage_test(y, md))
        r.update(C.changepoint(y, md, n_boot=a.n_boot, n_null=a.n_boot))
        res.append(r)
    R = pd.DataFrame(res)
    for col in ("p_perm", "p_stage", "p_bend"):
        R[col.replace("p_", "q_")] = C.bh(R[col].values)
    R.to_csv(os.path.join(a.out, f"stats_q{q0}.csv"), index=False)

    # sensitivity: sign agreement of the age slope across thresholds
    sens = []
    for c in metrics:
        sl = {}
        for q in a.q:
            m2 = M[M.q == q].set_index("slide").loc[mm.index]
            y = m2[c].values.astype(float)
            if np.std(y) == 0 or np.any(~np.isfinite(y)):
                continue
            X, _ = C._design(md, {"age": md["age_wk"].values.astype(float)})
            sl[q] = C.ols(y, X)[0][1]
        if sl:
            sens.append({"metric": c, **{f"slope_q{q}": v for q, v in sl.items()},
                         "same_sign": len({np.sign(v) for v in sl.values()}) == 1})
    pd.DataFrame(sens).to_csv(os.path.join(a.out, "threshold_sensitivity.csv"), index=False)

    with open(os.path.join(a.out, "run_info.json"), "w") as fh:
        json.dump({"slides": list(mm.index), "tag": a.tag, "q": a.q, "area_filter": fa,
                   "n_perm": a.n_perm, "n_boot": a.n_boot, "panels": C.PANELS}, fh, indent=1)
    show = R.sort_values("p_perm")[["metric", "slope_per_wk", "p_perm", "q_perm", "p_stage", "tau_wk", "p_bend"]]
    print(show.head(15).to_string(index=False, float_format=lambda v: f"{v:.3g}"))


if __name__ == "__main__":
    main()
