#!/usr/bin/env python3
"""K = 4 niche state-transition figure (Petri-net style). Inputs from analysis/results/sd2x04/dynamics/k_sensitivity/."""
import sys, json
import numpy as np, pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
from ksens_lib import fit_free, expm

d, outp = sys.argv[1], sys.argv[2]
mpl.rcParams.update({"font.family": "Liberation Sans", "font.size": 7, "axes.linewidth": 0.6,
    "axes.edgecolor": "#55554f", "xtick.color": "#55554f", "ytick.color": "#55554f",
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "axes.labelcolor": "#2b2b28", "text.color": "#2b2b28", "pdf.fonttype": 42, "svg.fonttype": "none"})
INK, MUTED, GRID, SHADE = "#2b2b28", "#77776f", "#e4e3de", "#f3f2ee"
NAMES = ["Immune-rich", "Low-signal", "Epi-rich", "Mes-rich"]
COL = {"Immune-rich": "#1baf7a", "Low-signal": "#eda100", "Epi-rich": "#e87ba4", "Mes-rich": "#6250d6"}
DARK = {"Immune-rich": "#0f7a54", "Low-signal": "#9a6800", "Epi-rich": "#b8456f", "Mes-rich": "#43359e"}
TXT = {"Immune-rich": "white", "Low-signal": INK, "Epi-rich": "white", "Mes-rich": "white"}

occ = pd.read_csv(f"{d}/niche_occupancy_K4.csv", index_col=0)
prof = pd.read_csv(f"{d}/niche_profiles_K4.csv", index_col=0).set_index("name")
rates = pd.read_csv(f"{d}/chain_rates_bootstrap_K4.csv")
topo = pd.read_csv(f"{d}/topology_comparison_K4.csv")
loo = pd.read_csv(f"{d}/loo_prediction_K4.csv")
P = occ[NAMES].values; ages = occ.age_wk.values.astype(float); sx = occ.sex.values
e = [(0, 1), (1, 2), (2, 3)]
grid = np.linspace(4, 12, 81)

def curve(th):
    p0 = np.exp(np.r_[0, th[:3]]); p0 /= p0.sum(); Q = np.zeros((4, 4))
    for (a, b), v in zip(e, np.exp(th[3:])): Q[a, b] = v
    Q[np.diag_indices(4)] = -Q.sum(1)
    return np.stack([p0 @ expm(Q * (g - 4)) for g in grid])
_, th, _, _ = fit_free(P, ages, lam=0, edges=e, starts=8)
fit = curve(th)
rng = np.random.default_rng(1); F, M = np.flatnonzero(sx == "F"), np.flatnonzero(sx == "M"); cs = []
for b in range(300):
    ii = np.r_[rng.choice(F, len(F)), rng.choice(M, len(M))]
    _, thb, _, _ = fit_free(P[ii], ages[ii], lam=0, edges=e, starts=2, seed=b); cs.append(curve(thb))
cs = np.array(cs); lo, hi = np.percentile(cs, [2.5, 97.5], 0)
pd.DataFrame(np.column_stack([grid, fit, lo, hi]), columns=["age_wk"] + [f"{p}_{n}" for p in ("fit", "lo", "hi") for n in NAMES]).to_csv(f"{d}/chain_fit_curves_K4.csv", index=False)

fig = plt.figure(figsize=(7.09, 5.0))
gs = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.05, 0.62], height_ratios=[0.78, 1], wspace=0.95, hspace=0.32,
                      left=0.07, right=0.98, top=0.985, bottom=0.115)
def tag(ax, s, x, y): ax.text(x, y, s, transform=ax.transAxes, fontsize=9, fontweight="bold", va="bottom", ha="left")
def stage_bg(ax, top):
    ax.axvspan(5.5, 10.5, color=SHADE, zorder=0, lw=0)
    for x, s in [(4.5, "Early\npostnatal"), (8, "Adolescence"), (11.5, "Adulthood")]:
        ax.text(x, top, s, ha="center", va="bottom", fontsize=6, color=MUTED, linespacing=0.95)

# ---- a: diagram
ax = fig.add_subplot(gs[0, :]); ax.set_xlim(0, 10); ax.set_ylim(-0.1, 3.9); ax.set_aspect("equal"); ax.axis("off")
tag(ax, "a", -0.02, 0.93)
xs = [1.0, 3.67, 6.33, 9.0]; Y = 2.0; R0 = 0.74
sub = {"Immune-rich": f"{prof.loc['Immune-rich','frac_Immune']*100:.0f}% immune",
       "Low-signal": f"{prof.loc['Low-signal','frac_Other']*100:.0f}% unassigned",
       "Epi-rich": f"{prof.loc['Epi-rich','frac_Epithelial']*100:.0f}% epithelial",
       "Mes-rich": f"{prof.loc['Mes-rich','frac_Mesenchymal']*100:.0f}% mesench."}
for n, x in zip(NAMES, xs):
    ax.add_patch(Circle((x, Y), R0, facecolor=COL[n], edgecolor=DARK[n], lw=1.0, alpha=0.92, zorder=3))
    ax.text(x, Y + 0.13, n, ha="center", va="center", fontsize=6.4, fontweight="bold", color=TXT[n], zorder=4)
    ax.text(x, Y - 0.2, sub[n], ha="center", va="center", fontsize=5.2, color=TXT[n], zorder=4)
    ea = occ.loc[occ.stage == "early", n].mean() * 100; ad = occ.loc[occ.stage == "adulthood", n].mean() * 100
    ar = "↑" if ad > ea + 5 else ("↓" if ad < ea - 5 else "→")
    ax.text(x, Y - R0 - 0.12, f"share of tiles\n{ea:.0f}% {ar} {ad:.0f}%", ha="center", va="top", fontsize=6, color=MUTED, linespacing=1.2)
for k, r in enumerate(rates.itertuples()):
    x1, x2 = xs[k] + R0 + 0.06, xs[k + 1] - R0 - 0.06; xm = (x1 + x2) / 2
    ax.add_patch(FancyArrowPatch((x1, Y), (xm - 0.07, Y), arrowstyle="-", lw=1.3, color=INK, zorder=1))
    ax.add_patch(FancyArrowPatch((xm + 0.07, Y), (x2, Y), arrowstyle="-|>,head_length=4,head_width=2.4", mutation_scale=1.5, lw=1.3, color=INK, zorder=1))
    ax.add_patch(Rectangle((xm - 0.055, Y - 0.28), 0.11, 0.56, color=INK, zorder=2))
    ax.text(xm, Y + 0.38, f"{r.rate_per_wk:.2f} wk$^{{-1}}$", ha="center", va="bottom", fontsize=6.6)
    ax.text(xm, Y - 0.38, f"{r.ci_lo:.2f}–{r.ci_hi:.2f}", ha="center", va="top", fontsize=5.6, color=MUTED)
best_alt = topo.sort_values("dAICc").iloc[1]
ax.text(5.0, 3.55, f"one irreversible chain, ~4 weeks per step  ·  nearest alternative topology ΔAICc = {best_alt.dAICc:.1f}; direct routes ΔAICc ≥ 5",
        ha="center", va="center", fontsize=6.2, color=MUTED, style="italic")
ax.annotate("", xy=(9.8, 0.2), xytext=(0.2, 0.2), arrowprops=dict(arrowstyle="-|>", color="#d6d5cf", lw=2.0))
ax.text(5.0, -0.08, "age, 4 → 12 weeks  ·  population-level model fitted to 16 cross-sectional slides  ·  share of tiles: 4–5 wk → 11–12 wk",
        ha="center", va="bottom", fontsize=6, color=MUTED)

# ---- b: occupancy vs age
ax = fig.add_subplot(gs[1, 0]); tag(ax, "b", -0.32, 1.04); stage_bg(ax, 75.5)
for k, n in enumerate(NAMES):
    ax.fill_between(grid, lo[:, k] * 100, hi[:, k] * 100, color=COL[n], alpha=0.16, lw=0, zorder=1)
    ax.plot(grid, fit[:, k] * 100, color=DARK[n], lw=1.6, zorder=3)
    for s_, mk in [("F", "o"), ("M", "^")]:
        m = sx == s_
        ax.scatter(ages[m], P[m, k] * 100, marker=mk, s=15, color=COL[n], edgecolor="white", lw=0.5, zorder=4)
for n, (x, y, ha) in {"Immune-rich": (4.3, 68, "left"), "Low-signal": (6.6, 47, "left"), "Epi-rich": (6.2, 9, "left"), "Mes-rich": (12.0, 62, "right")}.items():
    ax.text(x, y, n, color=DARK[n], fontsize=6, fontweight="bold", ha=ha, va="center", zorder=5)
ax.set_xlim(3.6, 12.3); ax.set_ylim(-2, 75); ax.set_xticks(range(4, 13, 2))
ax.set_xlabel("Age (weeks)"); ax.set_ylabel("Tiles in niche (%)"); ax.spines[["top", "right"]].set_visible(False)
ax.scatter([], [], marker="o", color=MUTED, s=12, label="Female"); ax.scatter([], [], marker="^", color=MUTED, s=12, label="Male")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.19), ncol=2, frameon=False, fontsize=6, handletextpad=0.2, columnspacing=1)

# ---- c: topology comparison
ax = fig.add_subplot(gs[1, 1]); tag(ax, "c", -0.62, 1.04)
lab = {"I→L→E→M (chain)": "I → L → E → M (in a)", "I→L, L→E, L→M (branch)": "I → L → E, L → M",
       "branch + E→M": "I → L → E → M + L → M", "I→L→E→M + M→E": "I → L → E ⇄ M".replace("⇄", "↔"),
       "I→L→E→M + I→E": "I → L → E → M + I → E", "I→L→E→M + E→L": "I → L ↔ E → M",
       "I→L→E, I→M": "I → L → E, I → M", "I→E, I→M (direct)": "I → E, I → M", "I→L→M→E": "I → L → M → E",
       "I→E→M, I→L": "I → E → M, I → L"}
t = topo.sort_values("dAICc").iloc[::-1].reset_index(drop=True); yy = np.arange(len(t))
sel = t.model.eq("I→L→E→M (chain)")
ax.axvspan(0, 2, color=SHADE, lw=0, zorder=0); ax.text(1.0, len(t) - 0.45, "ΔAICc < 2", ha="center", va="bottom", fontsize=5.5, color=MUTED)
ax.hlines(yy, 0, t.dAICc, color=GRID, lw=1.2, zorder=1)
ax.scatter(t.dAICc, yy, s=22, color=np.where(sel, INK, "#a9a8a0"), zorder=3, edgecolor="white", lw=0.5)
for y_, v in zip(yy, t.dAICc): ax.text(v + 0.25, y_, f"{v:.1f}", va="center", fontsize=5.5, color=MUTED)
ax.set_yticks(yy); ax.set_yticklabels(t.model.map(lab), fontsize=6)
for tl, s in zip(ax.get_yticklabels(), sel): tl.set_fontweight("bold" if s else "normal")
ax.set_xlim(0, 7.5); ax.set_xticks([0, 2, 4, 6]); ax.set_xlabel("ΔAICc vs best topology"); ax.set_ylim(-0.6, len(t) + 0.6)
ax.spines[["top", "right"]].set_visible(False); ax.tick_params(axis="y", length=0)
ax.set_title("I Immune · L Low-signal · E Epi · M Mes", fontsize=6, loc="right", color=MUTED, pad=4)

# ---- d: LOO
ax = fig.add_subplot(gs[1, 2]); tag(ax, "d", -0.5, 1.04)
ax.bar(range(3), loo.LOO_R2, width=0.55, color=[INK, "#a9a8a0", "#d6d5cf"], zorder=2); ax.axhline(0, color="#55554f", lw=0.6)
for i, v in enumerate(loo.LOO_R2): ax.text(i, v + (0.02 if v >= 0 else -0.02), f"{v:.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=6.5)
ax.set_xticks(range(3)); ax.set_xticklabels(["Chain\n(3 rates)", "Linear\ntrends", "No age"], fontsize=5.8)
ax.set_ylabel("Held-out R², leave one slide out"); ax.set_ylim(-0.25, 0.5)
ax.yaxis.grid(True, color=GRID, lw=0.5, zorder=0); ax.set_axisbelow(True); ax.spines[["top", "right"]].set_visible(False); ax.tick_params(axis="x", length=0)
for ext in ("png", "pdf", "svg"): fig.savefig(f"{outp}.{ext}", dpi=300)
print("saved")
