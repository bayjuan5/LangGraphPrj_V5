#!/usr/bin/env python3
"""Figure: population-level state-transition model of tissue niches (Petri-net style)."""
import sys, json
import numpy as np, pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle

occ_f, d, outp = sys.argv[1], sys.argv[2], sys.argv[3]
mpl.rcParams.update({"font.family": "Liberation Sans", "font.size": 7, "axes.linewidth": 0.6,
    "axes.edgecolor": "#55554f", "xtick.color": "#55554f", "ytick.color": "#55554f",
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "axes.labelcolor": "#2b2b28", "text.color": "#2b2b28", "pdf.fonttype": 42, "svg.fonttype": "none"})
INK, MUTED, GRID, SHADE = "#2b2b28", "#77776f", "#e4e3de", "#f3f2ee"
COL = {1: "#1baf7a", 2: "#eda100", 0: "#e87ba4"}
DARK = {1: "#0f7a54", 2: "#9a6800", 0: "#b8456f"}
NAME = {1: "Immune-rich", 2: "Low-signal", 0: "Epi/Mes-rich"}

occ = pd.read_csv(occ_f, index_col=0)
cur = pd.read_csv(f"{d}/chain_fit_curves.csv")
rates = pd.read_csv(f"{d}/chain_rates_bootstrap.csv")
topo = pd.read_csv(f"{d}/topology_comparison.csv")
loo = pd.read_csv(f"{d}/loo_prediction.csv")
prof = pd.read_csv(sys.argv[4], index_col=0)
info = json.load(open(f"{d}/chain_info.json"))

fig = plt.figure(figsize=(7.09, 5.0))
gs = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.05, 0.62], height_ratios=[0.78, 1], wspace=0.95, hspace=0.32,
                      left=0.07, right=0.98, top=0.985, bottom=0.115)

def tag(ax, s, x=-0.12, y=1.06):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=9, fontweight="bold", va="bottom", ha="left")

def stage_bg(ax, top):
    ax.axvspan(5.5, 10.5, color=SHADE, zorder=0, lw=0)
    for x, s in [(4.5, "Early\npostnatal"), (8, "Adolescence"), (11.5, "Adulthood")]:
        ax.text(x, top, s, ha="center", va="bottom", fontsize=6, color=MUTED, linespacing=0.95)

# ---------------- a: Petri-net style diagram ----------------
ax = fig.add_subplot(gs[0, :]); ax.set_xlim(0, 10); ax.set_ylim(-0.1, 3.9); ax.set_aspect("equal"); ax.axis("off")
tag(ax, "a", x=-0.02, y=0.93)
pos = {1: (1.35, 2.0), 2: (5.0, 2.0), 0: (8.65, 2.0)}
R0 = 0.9
comp = {k: prof.loc[k] for k in (0, 1, 2)}
for k, (x, y) in pos.items():
    ax.add_patch(Circle((x, y), R0 + 0.05, color="white", zorder=2))
    ax.add_patch(Circle((x, y), R0, facecolor=COL[k], edgecolor=DARK[k], lw=1.0, alpha=0.9, zorder=3))
    ax.text(x, y + 0.12, NAME[k].replace("/", "/​"), ha="center", va="center", fontsize=7,
            fontweight="bold", color="white" if k != 2 else INK, zorder=4)
    p = comp[k]
    sub = {1: f"{p.frac_Immune*100:.0f}% immune", 2: f"{p.frac_Other*100:.0f}% unassigned",
           0: f"{p.frac_Epithelial*100:.0f}% epi, {p.frac_Mesenchymal*100:.0f}% mes"}[k]
    ax.text(x, y - 0.2, sub, ha="center", va="center", fontsize=5.8, color="white" if k != 2 else INK, zorder=4)
    # occupancy early vs adult under the place
    e = occ.loc[occ.stage == "early", str(k)].mean() * 100; a = occ.loc[occ.stage == "adulthood", str(k)].mean() * 100
    arrow = "↑" if a > e + 5 else ("↓" if a < e - 5 else "→")
    ax.text(x, y - R0 - 0.12, f"share of tiles\n{e:.0f}% (4–5 wk) {arrow} {a:.0f}% (11–12 wk)",
            ha="center", va="top", fontsize=6, color=MUTED, linespacing=1.2)
# transitions (Petri-net bars) with rates
rr = {r.edge: r for r in rates.itertuples()}
for (i, j), key in [((1, 2), "Immune-rich -> Low-signal"), ((2, 0), "Low-signal -> Epi/Mes-rich")]:
    x1, y1 = pos[i]; x2, y2 = pos[j]; xm = (x1 + x2) / 2
    ax.add_patch(FancyArrowPatch((x1 + R0 + 0.08, y1), (xm - 0.09, y1), arrowstyle="-", lw=1.4, color=INK, zorder=1))
    ax.add_patch(FancyArrowPatch((xm + 0.09, y1), (x2 - R0 - 0.08, y2), arrowstyle="-|>,head_length=4,head_width=2.4",
                                 lw=1.4, color=INK, zorder=1, mutation_scale=1.6))
    ax.add_patch(Rectangle((xm - 0.07, y1 - 0.32), 0.14, 0.64, color=INK, zorder=2))
    r = rr[key]
    ax.text(xm, y1 + 0.45, f"k = {r.rate_per_wk:.2f} wk$^{{-1}}$", ha="center", va="bottom", fontsize=7, color=INK)
    ax.text(xm, y1 - 0.45, f"95% CI {r.ci_lo:.2f}–{r.ci_hi:.2f}\nmean dwell {r.mean_dwell_wk:.1f} wk",
            ha="center", va="top", fontsize=6, color=MUTED, linespacing=1.15)
# alternative direct route
dI = topo.set_index("model").loc["direct I->E only", "dAICc"]
ax.add_patch(FancyArrowPatch((pos[1][0] + 0.35, pos[1][1] + R0 - 0.05), (pos[0][0] - 0.35, pos[0][1] + R0 - 0.05),
             connectionstyle="arc3,rad=-0.2", arrowstyle="->,head_length=5,head_width=3", mutation_scale=1,
             lw=0.9, color=MUTED, ls=(0, (3, 2)), capstyle="butt", zorder=0))
ax.text(5.0, 3.78, f"alternative direct route, statistically indistinguishable (ΔAICc = {dI:.1f})",
        ha="center", va="top", fontsize=6, color=MUTED, style="italic")
# time axis
ax.annotate("", xy=(9.8, 0.2), xytext=(0.2, 0.2), arrowprops=dict(arrowstyle="-|>", color="#d6d5cf", lw=2.0))
ax.text(5.0, -0.08, f"age, 4 → 12 weeks  ·  population-level model fitted to 16 cross-sectional slides  ·  Epi/Mes-rich overtakes Immune-rich at ≈ {info['crossing_EpiMes_over_Immune_wk']:.1f} wk",
        ha="center", va="bottom", fontsize=6, color=MUTED)

# ---------------- b: occupancy vs age ----------------
ax = fig.add_subplot(gs[1, 0]); tag(ax, "b", x=-0.32, y=1.04)
stage_bg(ax, 100.5)
for k in (1, 2, 0):
    ax.fill_between(cur.age_wk, cur[f"lo_{k}"] * 100, cur[f"hi_{k}"] * 100, color=COL[k], alpha=0.18, lw=0, zorder=1)
    ax.plot(cur.age_wk, cur[f"fit_{k}"] * 100, color=DARK[k], lw=1.6, zorder=3)
    for sx, mk in [("F", "o"), ("M", "^")]:
        s = occ[occ.sex == sx]
        ax.scatter(s.age_wk, s[str(k)] * 100, marker=mk, s=16, color=COL[k], edgecolor="white", lw=0.5, zorder=4)
ends = {k: cur[f"fit_{k}"].iloc[-1] * 100 for k in (0, 1, 2)}
for k, (xx, yy_, ha) in {0: (8.6, 66, "right"), 2: (11.9, 22, "right"), 1: (4.4, 3, "left")}.items():
    ax.text(xx, yy_, NAME[k], color=DARK[k], fontsize=6, va="center", ha=ha, fontweight="bold", zorder=5)
ax.set_xlim(3.6, 12.3); ax.set_ylim(-2, 100); ax.set_xticks(range(4, 13, 2))
ax.set_xlabel("Age (weeks)"); ax.set_ylabel("Tiles in niche (%)")
ax.spines[["top", "right"]].set_visible(False)
ax.scatter([], [], marker="o", color=MUTED, s=12, label="Female"); ax.scatter([], [], marker="^", color=MUTED, s=12, label="Male")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.19), ncol=2, frameon=False, fontsize=6, handletextpad=0.2, columnspacing=1)

# ---------------- c: topology comparison ----------------
ax = fig.add_subplot(gs[1, 1]); tag(ax, "c", x=-0.62, y=1.04)
lab = {"chain I->L->E (selected)": "I → L → E (in a)",
       "direct I->E only": "I → E",
       "chain, rates change at 7 wk": "I → L → E, break 7 wk",
       "alt chain L->I->E": "L → I → E",
       "chain + direct I->E": "I → L → E  +  I → E",
       "I->E, I->L (no L->E)": "I → E  +  I → L",
       "alt chain I->E->L": "I → E → L",
       "reversible chain": "I ↔ L ↔ E",
       "fully connected": "all 6 transitions"}
t = topo.copy(); t["label"] = t.model.map(lab); t = t.iloc[::-1]
yy = np.arange(len(t))
ax.axvspan(0, 2, color=SHADE, lw=0, zorder=0)
ax.text(1.0, len(t) - 0.45, "ΔAICc < 2", ha="center", va="bottom", fontsize=5.5, color=MUTED)
sel = t.model.str.contains("selected")
ax.hlines(yy, 0, t.dAICc, color=GRID, lw=1.2, zorder=1)
ax.scatter(t.dAICc, yy, s=22, color=np.where(sel, INK, "#a9a8a0"), zorder=3, edgecolor="white", lw=0.5)
for y_, (v, n) in zip(yy, zip(t.dAICc, t.n_params)):
    ax.text(v + 0.35, y_, f"{v:.1f}", va="center", fontsize=5.5, color=MUTED)
ax.set_yticks(yy); ax.set_yticklabels(t.label, fontsize=6)
for tl, s in zip(ax.get_yticklabels(), sel): tl.set_fontweight("bold" if s else "normal")
ax.set_xlim(0, 14.5); ax.set_xticks([0, 2, 5, 10]); ax.set_xlabel("ΔAICc vs best topology")
ax.set_ylim(-0.6, len(t) + 0.6)
ax.spines[["top", "right"]].set_visible(False); ax.tick_params(axis="y", length=0)
ax.set_title("I Immune-rich · L Low-signal · E Epi/Mes-rich", fontsize=6, loc="right", color=MUTED, pad=4)

# ---------------- d: leave-one-slide-out prediction ----------------
ax = fig.add_subplot(gs[1, 2]); tag(ax, "d", x=-0.5, y=1.04)
L = loo.copy()
short = {"state-transition chain (2 rates)": "Chain\n(2 rates)",
         "per-niche linear trend in age (6 params)": "Linear\ntrends",
         "mean occupancy, no age": "No age"}
L["s"] = L.predictor.map(short)
cols = [INK, "#a9a8a0", "#d6d5cf"]
ax.bar(range(3), L.LOO_R2, width=0.55, color=cols, zorder=2)
ax.axhline(0, color="#55554f", lw=0.6)
for i, v in enumerate(L.LOO_R2):
    ax.text(i, v + (0.02 if v >= 0 else -0.02), f"{v:.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=6.5)
ax.set_xticks(range(3)); ax.set_xticklabels(L.s, fontsize=5.8)
ax.set_ylabel("Held-out R², leave one slide out"); ax.set_ylim(-0.25, 0.5)
ax.yaxis.grid(True, color=GRID, lw=0.5, zorder=0); ax.set_axisbelow(True)
ax.spines[["top", "right"]].set_visible(False); ax.tick_params(axis="x", length=0)

for ext in ("png", "pdf", "svg"):
    fig.savefig(f"{outp}.{ext}", dpi=300)
print("saved")
