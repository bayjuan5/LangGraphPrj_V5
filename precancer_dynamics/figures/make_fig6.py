"""Figures 2-6 for NAT_Beibei_v8 (primary detection: StarDist 2x, prob 0.4 = sd2x04)."""
import json, sys, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats

D = sys.argv[1] if len(sys.argv) > 1 else "data"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out"
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, D)


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


# =================== Fig 6: spatial + niches ===================
E = pd.read_csv(f"{D}/sd2x04/enrichment_by_slide.csv").merge(meta, on="slide")
order = ["Epithelial", "Hybrid", "Mesenchymal", "Immune", "Endothelial", "Other"]
fig = plt.figure(figsize=(7.2, 2.6))
gs = fig.add_gridspec(1, 4, wspace=0.6, left=0.08, right=0.98, top=0.8, bottom=0.2)


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
cax = fig.add_axes([0.13, 0.02, 0.28, 0.02])
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
    ax.set_title(ttl, loc="left"); ax.set_xlabel("Age (weeks)"); ax.set_ylabel("log$_2$(obs/exp)"); ax.set_xticks(range(4, 13, 2))
    panel_label(ax, "bc"[k], y=1.18)

sex_legend(fig, y=1.0)
save(fig, "Fig6_spatial")
