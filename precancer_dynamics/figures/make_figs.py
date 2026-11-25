"""Figures 2-6 for NAT_Beibei_v8 (primary detection: StarDist 2x, prob 0.4 = sd2x04)."""
import json, sys, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats

D = "/home/claude/figs/data"
OUT = "/home/claude/figs/out"
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, D)
from halo_validation import load_halo

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7,
    "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.labelcolor": "#0b0b0b", "text.color": "#0b0b0b", "savefig.dpi": 300,
    "axes.grid": False, "pdf.fonttype": 42, "svg.fonttype": "none",
})
INK2 = "#52514e"; GRID = "#e6e5e0"
SEX = {"F": dict(c="#2a78d6", m="o", label="Female"), "M": dict(c="#eb6834", m="^", label="Male")}
NICHE_C = {"Immune-rich": "#1baf7a", "Low-signal": "#eda100", "Epi/Mes-rich": "#e87ba4"}
STAGES = [(3.5, 5.5, "Early\npostnatal"), (5.5, 10.5, "Adolescence"), (10.5, 12.5, "Adulthood")]
DIV = LinearSegmentedColormap.from_list("div", ["#184f95", "#6da7ec", "#f0efec", "#ec835a", "#a33c12"])

meta = pd.read_csv(f"{D}/slide_meta.csv")


def load_metrics(tag):
    m = pd.read_csv(f"{D}/{tag}/slide_metrics.csv")
    m = m[m.q == 75].merge(meta, on="slide")
    return m


M = load_metrics("sd2x04")
S = pd.read_csv(f"{D}/sd2x04/stats_q75.csv").set_index("metric")


def pfmt(p):
    if p < 1e-3:
        e = int(np.floor(np.log10(p))); b = p / 10 ** e
        return f"P = {b:.0f}×10$^{{{e}}}$" if round(b) != 10 else f"P = 1×10$^{{{e+1}}}$"
    return f"P = {p:.3f}" if p < 0.01 else f"P = {p:.2f}"


def stage_bands(ax, label=True):
    for i, (a, b, lab) in enumerate(STAGES):
        if i % 2 == 1:
            ax.axvspan(a, b, color="#f3f2ee", zorder=0, lw=0)
        if label:
            ax.text((a + b) / 2, 1.0, lab, transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                    fontsize=5.8, color=INK2, linespacing=0.9)
    ax.set_xlim(3.5, 12.5); ax.set_xticks(range(4, 13))


def scatter_sex(ax, d, x, y, scale=1.0, s=18):
    for sx, st in SEX.items():
        q = d[d.sex == sx]
        ax.scatter(q[x], q[y] * scale, s=s, c=st["c"], marker=st["m"], edgecolors="#fcfcfb", linewidths=0.8,
                   zorder=3, label=st["label"])


def fit_line(ax, d, y, scale=1.0, hinge=None):
    age = d.age_wk.values.astype(float); sex = (d.sex == "M").astype(float).values; Y = d[y].values
    cols = [np.ones_like(age), age, sex]
    if hinge is not None:
        cols.append(np.maximum(0, age - hinge))
    b = np.linalg.lstsq(np.c_[tuple(cols)], Y, rcond=None)[0]
    g = np.linspace(4, 12, 200)
    G = [np.ones_like(g), g, np.full_like(g, 0.5)]
    if hinge is not None:
        G.append(np.maximum(0, g - hinge))
    ax.plot(g, (np.c_[tuple(G)] @ b) * scale, color="#0b0b0b", lw=1.2, zorder=2)
    return b


def panel_label(ax, s, x=-0.28, y=1.12):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=9, fontweight="bold", va="top", ha="left")


def save(fig, name):
    fig.savefig(f"{OUT}/{name}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(f"{OUT}/{name}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def sex_legend(fig, y=1.0):
    h = [plt.Line2D([], [], ls="", marker=st["m"], color=st["c"], markersize=4.5, label=st["label"]) for st in SEX.values()]
    fig.legend(handles=h, loc="upper right", bbox_to_anchor=(0.99, y), frameon=False, ncol=2, handletextpad=0.2,
               columnspacing=0.8)


# =================== Fig 2: detection accuracy + HALO concordance + detection-setting agreement ===================
rec = pd.read_csv(f"{D}/recall_qupath_v2_sd_sd2x_ws.csv")
sd2x04 = pd.DataFrame({"crop": ["F8_panin_x2432_y11648", "M4_acinar_x19840_y20864", "M4_stroma_x16768_y7424", "POOLED"],
                       "tag": "sd2x04", "recall": [0.747, 0.511, 0.614, 0.630], "precision": [0.865, 0.800, 0.910, 0.860]})
rec = pd.concat([rec, sd2x04], ignore_index=True)
rec["region"] = rec.crop.str.extract(r"_(panin|acinar|stroma)_")[0].fillna("pooled")

fig = plt.figure(figsize=(7.2, 5.0))
gs = fig.add_gridspec(2, 4, hspace=0.75, wspace=0.95)
TAGC = {"ws": "#e34948", "sd": "#6250d6", "sd2x": "#86b6ef", "sd2x04": "#2a78d6"}
TAGL = {"ws": "Watershed (deprecated)", "sd": "StarDist 1×", "sd2x": "StarDist 2×, p 0.69", "sd2x04": "StarDist 2×, p 0.4 (primary)"}
ax = fig.add_subplot(gs[0, 0:2])
for t in ["ws", "sd", "sd2x", "sd2x04"]:
    q = rec[rec.tag == t]
    pooled = q[q.region == "pooled"].iloc[0]
    reg = q[q.region != "pooled"]
    ax.scatter(reg.recall, reg.precision, s=10, c=TAGC[t], alpha=0.55, edgecolors="none", zorder=2)
    ax.scatter(pooled.recall, pooled.precision, s=34, c=TAGC[t], edgecolors="#fcfcfb", linewidths=1.0, zorder=3,
               label=TAGL[t])
ax.axhline(0.85, color=INK2, lw=0.6, ls=(0, (3, 2)), zorder=1)
ax.text(0.02, 0.855, "precision 0.85", fontsize=5.8, color=INK2, va="bottom")
ax.set_xlim(0, 0.85); ax.set_ylim(0.25, 1.04)
ax.set_xlabel("Recall (419 curated nuclei)"); ax.set_ylabel("Precision")
ax.legend(loc="lower left", frameon=False, handletextpad=0.2, borderaxespad=0.2)
ax.set_title("Nucleus detection vs curated ground truth\n(large = pooled; small = PanIN, acinar, stroma)", loc="left")
panel_label(ax, "a", x=-0.15)

halo = load_halo(f"{D}/Sharma_HALO_trichrome_Classification.xlsx")[["acinar_pct", "duct_pct", "stroma_pct"]]
H = M.set_index("slide").join(halo).reset_index()


def resid(v, a):
    X = np.c_[np.ones_like(a), a]; return v - X @ np.linalg.lstsq(X, v, rcond=None)[0]


pairs = [("stroma_pct", "frac_Mesenchymal", 100, "HALO stroma (% tissue)", "ROSIE mesenchymal (%)", "b"),
         ("acinar_pct", "frac_Mesenchymal", 100, "HALO acinar (% tissue)", "ROSIE mesenchymal (%)", "c"),
         ("duct_pct", "mean_score_Epi", 1, "HALO ductal lesions (% tissue)", "Mean epithelial score", "d")]
for k, (hx, ry, sc, xl, yl, lab) in enumerate(pairs):
    ax = fig.add_subplot(gs[0, 2 + k]) if k < 2 else fig.add_subplot(gs[1, 0])
    scatter_sex(ax, H, hx, ry, scale=sc, s=14)
    r, p = stats.spearmanr(H[hx], H[ry])
    ra, pa = stats.spearmanr(resid(H[hx].values, H.age_wk.values.astype(float)), resid(H[ry].values, H.age_wk.values.astype(float)))
    pos = {0: (0.97, 0.04, "right", "bottom"), 1: (0.97, 0.97, "right", "top"), 2: (0.03, 0.97, "left", "top")}[k]
    ax.text(pos[0], pos[1], f"ρ = {r:.2f}\nage-adj. ρ = {ra:.2f}\n({pfmt(pa)})", transform=ax.transAxes,
            ha=pos[2], va=pos[3], fontsize=5.6)
    ax.set_xlabel(xl); ax.set_ylabel(yl)
    panel_label(ax, lab)

ALT = {"sd2x": load_metrics("sd2x"), "sd": load_metrics("sd")}
states = ["frac_Epithelial", "frac_Mesenchymal", "frac_Hybrid", "frac_Immune", "frac_Endothelial", "frac_Other"]
SC = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
for k, (alt, ttl) in enumerate([("sd2x", "vs StarDist 2×, p 0.69"), ("sd", "vs StarDist 1×")]):
    ax = fig.add_subplot(gs[1, 1 + k])
    A = M.set_index("slide"); B = ALT[alt].set_index("slide").loc[A.index]
    for s_, c in zip(states, SC):
        ax.scatter(B[s_] * 100, A[s_] * 100, s=9, c=c, edgecolors="none", alpha=0.9, label=s_.replace("frac_", ""))
    lim = [0, 70]; ax.plot(lim, lim, color=INK2, lw=0.6, ls=(0, (3, 2)), zorder=0)
    ax.set_xlim(lim); ax.set_ylim(lim); ax.set_aspect("equal")
    rr = [stats.pearsonr(A[s_], B[s_])[0] for s_ in states]
    ax.text(0.97, 0.04, f"per-state r {min(rr):.2f}–{max(rr):.2f}", transform=ax.transAxes, ha="right", fontsize=5.8)
    ax.set_xlabel(ttl.split('vs ')[1] + " (%)"); ax.set_ylabel("Primary (%)")
    panel_label(ax, "ef"[k])
ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False, handletextpad=0.1, markerscale=1.4)
sex_legend(fig, y=1.01)
save(fig, "Fig2_validation")

# =================== Fig 3: composition vs age ===================
fig, axs = plt.subplots(2, 3, figsize=(7.2, 4.4))
plt.subplots_adjust(hspace=0.75, wspace=0.42)
spec = [("frac_Mesenchymal", "Mesenchymal (% nuclei)", 100), ("frac_Immune", "Immune (% nuclei)", 100),
        ("frac_Epithelial", "Epithelial (% nuclei)", 100), ("mean_score_T", "Mean T-cell score", 1),
        ("mean_score_B", "Mean B-cell score", 1), ("mean_score_Myeloid", "Mean myeloid score", 1)]
for ax, (y, yl, sc), lab in zip(axs.flat, spec, "abcdef"):
    stage_bands(ax)
    scatter_sex(ax, M, "age_wk", y, scale=sc)
    fit_line(ax, M, y, scale=sc)
    r = S.loc[y]
    unit = " pts/wk" if sc == 100 else "/wk"
    ax.text(0.03 if r.slope_per_wk < 0 else 0.97, 0.05 if r.slope_per_wk > 0 else 0.05,
            f"{r.slope_per_wk*sc:+.1f}{unit}\n{pfmt(r.p_perm)}" if sc == 100 else f"{r.slope_per_wk:+.3f}{unit}\n{pfmt(r.p_perm)}",
            transform=ax.transAxes, ha="left" if r.slope_per_wk < 0 else "right", va="bottom", fontsize=5.8)
    ax.set_xlabel("Age (weeks)"); ax.set_ylabel(yl)
    panel_label(ax, lab, y=1.2)
sex_legend(fig, y=1.04)
save(fig, "Fig3_composition")

# =================== Fig 4: change point ===================
fig, axs = plt.subplots(1, 2, figsize=(6.0, 2.5))
plt.subplots_adjust(wspace=0.38)
ax = axs[0]; stage_bands(ax)
scatter_sex(ax, M, "age_wk", "frac_Mesenchymal", 100)
r = S.loc["frac_Mesenchymal"]
fit_line(ax, M, "frac_Mesenchymal", 100, hinge=r.tau_wk)
ax.axvline(r.tau_wk, color=INK2, lw=0.7, ls=(0, (3, 2)))
ax.axvspan(r.tau_ci_lo, r.tau_ci_hi, ymin=0, ymax=0.04, color=INK2, alpha=0.6, lw=0)
ax.text(r.tau_wk + 0.15, 0.62, f"break {r.tau_wk:.1f} wk\n95% CI {r.tau_ci_lo:.1f}–{r.tau_ci_hi:.1f}\n"
        f"bend {pfmt(r.p_bend)}\nΔBIC {r.dBIC_lin_minus_hinge:.1f}", transform=ax.get_xaxis_transform(), fontsize=5.8)
for wk, lab in [(8, "first\nmPanIN-3"), (11, "invasive\nPDAC")]:
    ax.annotate(lab, xy=(wk, 0), xytext=(wk, 0.45 if wk == 8 else 0.2), xycoords=("data", "axes fraction"), textcoords=("data", "axes fraction"),
                ha="center", fontsize=5.5, color=INK2, arrowprops=dict(arrowstyle="-|>", color=INK2, lw=0.6, mutation_scale=5))
ax.set_xlabel("Age (weeks)"); ax.set_ylabel("Mesenchymal (% nuclei)"); panel_label(ax, "a", y=1.2)
ax = axs[1]; stage_bands(ax)
scatter_sex(ax, M, "age_wk", "frac_Immune", 100)
fit_line(ax, M, "frac_Immune", 100)
ri = S.loc["frac_Immune"]
ax.text(0.97, 0.95, f"linear; bend {pfmt(ri.p_bend)}", transform=ax.transAxes, ha="right", va="top", fontsize=5.8)
ax.set_xlabel("Age (weeks)"); ax.set_ylabel("Immune (% nuclei)"); panel_label(ax, "b", y=1.2)
sex_legend(fig, y=1.08)
save(fig, "Fig4_changepoint")

# =================== Fig 5: hybrid ===================
fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.4))
plt.subplots_adjust(wspace=0.45)
spec = [("frac_E+M+", "E+M+ (% nuclei)", 100), ("hybrid_share_of_E+", "E+M+ share of E+ cells (%)", 100),
        ("corr_E_M", "Epithelial–mesenchymal\nscore correlation (r)", 1)]
for ax, (y, yl, sc), lab in zip(axs, spec, "abc"):
    stage_bands(ax); scatter_sex(ax, M, "age_wk", y, sc); fit_line(ax, M, y, sc)
    r = S.loc[y]
    ax.text(0.97 if r.slope_per_wk < 0 else 0.03, 0.95, pfmt(r.p_perm) + ("" if r.p_perm < 0.05 else " (n.s.)"),
            transform=ax.transAxes, ha="right" if r.slope_per_wk < 0 else "left", va="top", fontsize=5.8)
    ax.set_xlabel("Age (weeks)"); ax.set_ylabel(yl); panel_label(ax, lab, y=1.2)
sex_legend(fig, y=1.1)
save(fig, "Fig5_hybrid")

# =================== Fig 6: spatial + niches ===================
E = pd.read_csv(f"{D}/sd2x04/enrichment_by_slide.csv").merge(meta, on="slide")
order = ["Epithelial", "Hybrid", "Mesenchymal", "Immune", "Endothelial", "Other"]
fig = plt.figure(figsize=(7.2, 5.4))
gs = fig.add_gridspec(2, 4, hspace=0.7, wspace=0.6, height_ratios=[1, 1])


def oe_matrix(stage):
    q = E[E.stage == stage].groupby(["a", "b"]).log2_oe.mean()
    mat = np.full((6, 6), np.nan)
    for (a, b), v in q.items():
        i, j = order.index(a), order.index(b); mat[i, j] = mat[j, i] = v
    return mat


vmax = 3
for k, (st, ttl) in enumerate([("early", "Early postnatal"), ("adulthood", "Adulthood")]):
    ax = fig.add_subplot(gs[0, k])
    im = ax.imshow(oe_matrix(st), cmap=DIV, vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(6)); ax.set_yticks(range(6))
    ax.set_xticklabels([o[:3] for o in order], rotation=90); ax.set_yticklabels([o[:3] for o in order] if k == 0 else [])
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title(ttl, loc="left");
    if k == 0: panel_label(ax, "a", x=-0.45, y=1.18)
cax = fig.add_axes([0.16, 0.50, 0.25, 0.010])
cb = fig.colorbar(im, cax=cax, orientation="horizontal"); cb.set_label("log$_2$(obs/exp), 20 µm", fontsize=6); cb.ax.tick_params(labelsize=5.5, length=2)
cb.outline.set_visible(False)

T = pd.read_csv(f"{D}/sd2x04/enrichment_trend_r20.csv").set_index("pair")
for k, (pair, ttl) in enumerate([("Epithelial-Mesenchymal", "Epithelial–mesenchymal"), ("Mesenchymal-Immune", "Mesenchymal–immune")]):
    ax = fig.add_subplot(gs[0, 2 + k]); stage_bands(ax, label=False)
    q = E[E.pair == pair]
    scatter_sex(ax, q, "age_wk", "log2_oe", s=14); fit_line(ax, q, "log2_oe")
    t = T.loc[pair]
    ax.text(0.97 if t.slope_per_wk < 0 else 0.03, 0.95 if t.slope_per_wk < 0 else 0.95,
            f"{t.slope_per_wk:+.2f}/wk\nq = {t.q_perm:.3f}", transform=ax.transAxes,
            ha="right" if t.slope_per_wk < 0 else "left", va="top", fontsize=5.8)
    ax.axhline(0, color=INK2, lw=0.5)
    ax.set_title(ttl, loc="left"); ax.set_xlabel("Age (weeks)"); ax.set_ylabel("log$_2$(obs/exp)")
    panel_label(ax, "bc"[k], y=1.18)

prof = pd.read_csv(f"{D}/sd2x04/niche_profiles.csv").set_index("niche")
NAME = {1: "Immune-rich", 2: "Low-signal", 0: "Epi/Mes-rich"}
niche_order = [1, 2, 0]
ax = fig.add_subplot(gs[1, 0:2])
cols = ["frac_Epithelial", "frac_Mesenchymal", "frac_Hybrid", "frac_Immune", "frac_Endothelial", "frac_Other"]
mat = prof.loc[niche_order, cols].values * 100
im2 = ax.imshow(mat, cmap=LinearSegmentedColormap.from_list("seq", ["#f6f9fe", "#9ec5f4", "#2a78d6", "#0d366b"]), vmin=0, vmax=70, aspect="auto")
for i in range(3):
    for j in range(6):
        ax.text(j, i, f"{mat[i, j]:.0f}", ha="center", va="center", fontsize=6, color="#0b0b0b" if mat[i, j] < 40 else "#fcfcfb")
ax.set_xticks(range(6)); ax.set_xticklabels([c.replace("frac_", "") for c in cols], rotation=30, ha="right")
ax.set_yticks(range(3)); ax.set_yticklabels([NAME[n] for n in niche_order])
for yl, n in zip(ax.get_yticklabels(), niche_order):
    yl.set_color("#0b0b0b")
for s in ax.spines.values(): s.set_visible(False)
ax.tick_params(length=0)
ax.set_title("Niche composition (% of nuclei; K = 3 by silhouette)", loc="left")
panel_label(ax, "d", x=-0.28, y=1.25)

occ = pd.read_csv(f"{D}/sd2x04/niche_occupancy.csv")
fit = pd.read_csv(f"{D}/sd2x04/ctmc_fitted_occupancy.csv").rename(columns={"Unnamed: 0": "slide"}).merge(meta, on="slide")
ax = fig.add_subplot(gs[1, 2:4]); stage_bands(ax)
for n in niche_order:
    c = NICHE_C[NAME[n]]
    ax.scatter(occ.age_wk, occ[str(n)] * 100, s=12, c=c, edgecolors="#fcfcfb", linewidths=0.7, zorder=3)
    f = fit.groupby("age_wk")[str(n)].mean()
    ax.plot(f.index, f.values * 100, color=c, lw=1.6, zorder=2, label=NAME[n])
    ax.text(12.6, f.values[-1] * 100, NAME[n], color="#0b0b0b", fontsize=5.8, va="center")
ax.set_ylim(-3, 103); ax.set_xlabel("Age (weeks)"); ax.set_ylabel("Tiles in niche (%)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=3, frameon=False, handlelength=1.2)
info = json.load(open(f"{D}/sd2x04/ctmc_info.json"))
ax.text(0.5, -0.52, "CTMC: Immune-rich → Low-signal (0.20/wk) → Epi/Mes-rich (0.18/wk); both stable in all leave-one-slide-out refits; "
        f"R² = {info['r2']:.2f}", transform=ax.transAxes, ha="center", fontsize=5.6, color=INK2, wrap=True)
panel_label(ax, "e", y=1.18)
sex_legend(fig, y=1.01)
save(fig, "Fig6_spatial_niches")
print("done", os.listdir(OUT))
