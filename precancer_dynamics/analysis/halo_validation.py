#!/usr/bin/env python3
"""
halo_validation.py - external validation of slide-level ROSIE composition against the HALO
trichrome tissue classification used in Sharma et al., Clin Cancer Res 2025 (Fig. 3B-D).

HALO export: one row per trichrome slide (adjacent section to our H&E slide), areas in mm2 for
glass / acinar / duct / stroma / islet. Percent = area / (classified - glass), as in the paper.
Slides are matched by tag (F4..F12, M4..M12). The HALO file has two rows tagged "M5"
(366867 and 366869); 366867 fits the ID sequence (F12..F4 = 366853-366860, M12..M4 = 366861-366868)
and is used; 366869 is excluded pending confirmation.

For each pair (HALO compartment, ROSIE metric): Spearman rho across the 16 slides, and an
age-adjusted rho (both variables residualised on age) to separate shared age trend from
slide-to-slide agreement beyond age.

Usage: python halo_validation.py --halo Sharma_HALO_trichrome_Classification.xlsx \
          --metrics results/sd2x/slide_metrics.csv --meta slide_meta.csv --out results/sd2x/halo_validation.csv
"""
import argparse
import pandas as pd
from scipy import stats

PAIRS = [("stroma_pct", "frac_Mesenchymal"), ("stroma_pct", "frac_E-M+"), ("stroma_pct", "mean_score_Mes"),
         ("duct_pct", "frac_Epithelial"), ("duct_pct", "frac_E+M+"), ("duct_pct", "mean_score_Epi"),
         ("acinar_pct", "frac_Mesenchymal"), ("acinar_pct", "frac_Immune"), ("acinar_pct", "frac_Other"),
         ("acinar_pct", "mean_score_Epi")]


def load_halo(path):
    x = pd.read_excel(path, sheet_name="Classification")
    x["slide"] = x["Image Tag"].str.extract(r"^([FM]\d+)")[0]
    x["svs_id"] = x["Image Location"].str.extract(r"(\d+)\.svs")[0].astype(int)
    x = x[x.svs_id != 366869]
    tissue = x["Classified Area (mm²)"] - x["glass Area (mm²)"]
    for k in ("acinar", "duct", "stroma", "islet"):
        x[f"{k}_pct"] = 100 * x[f"{k} Area (mm²)"] / tissue
    return x.set_index("slide")


def resid(y, age):
    r = stats.linregress(age, y)
    return y - (r.intercept + r.slope * age)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--halo", required=True); ap.add_argument("--metrics", required=True)
    ap.add_argument("--meta", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--q", type=int, default=75)
    a = ap.parse_args()
    h = load_halo(a.halo)
    m = pd.read_csv(a.metrics); m = m[m.q == a.q].set_index("slide")
    meta = pd.read_csv(a.meta).set_index("slide")
    idx = h.index.intersection(m.index)
    age = meta.loc[idx, "age_wk"].astype(float).values
    rows = []
    for hc, rc in PAIRS:
        x, y = h.loc[idx, hc].values, m.loc[idx, rc].values
        rho, p = stats.spearmanr(x, y)
        rho_a, p_a = stats.spearmanr(resid(x, age), resid(y, age))
        rows.append({"halo": hc, "rosie": rc, "n": len(idx), "rho": rho, "p": p, "rho_age_adj": rho_a, "p_age_adj": p_a})
    for hc in ("acinar_pct", "duct_pct", "stroma_pct"):
        rho, p = stats.spearmanr(age, h.loc[idx, hc])
        rows.append({"halo": hc, "rosie": "age_wk", "n": len(idx), "rho": rho, "p": p})
    out = pd.DataFrame(rows); out.to_csv(a.out, index=False)
    h.loc[idx, ["svs_id", "acinar_pct", "duct_pct", "stroma_pct", "islet_pct"]].join(meta[["sex", "age_wk"]]).to_csv(
        a.out.replace(".csv", "_halo_by_slide.csv"))
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
