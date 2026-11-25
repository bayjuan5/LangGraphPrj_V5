"""Fig 1: study design, analysis workflow, nuclei per slide (npj SBA v10)."""
import sys
import numpy as np, pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

meta_f, metrics_f, out = sys.argv[1], sys.argv[2], sys.argv[3]
from PIL import Image
mpl.rcParams.update({"font.family": "Liberation Sans", "font.size": 7, "axes.linewidth": 0.6,
    "axes.edgecolor": "#55554f", "xtick.color": "#55554f", "ytick.color": "#55554f",
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "axes.labelcolor": "#2b2b28", "text.color": "#2b2b28", "pdf.fonttype": 42, "svg.fonttype": "none"})
INK, MUTED, SHADE = "#2b2b28", "#77776f", "#f3f2ee"
CELLS = sys.argv[4]
SEX = {"F": ("#2a78d6", "o", "Female"), "M": ("#eb6834", "^", "Male")}
meta = pd.read_csv(meta_f)
m = pd.read_csv(metrics_f); m = m[m.q == 75][["slide", "n_cells"]].merge(meta, on="slide")

fig = plt.figure(figsize=(7.09, 5.0))
gs = fig.add_gridspec(2, 1, height_ratios=[0.8, 1.0], hspace=0.16,
                      left=0.07, right=0.99, top=0.93, bottom=0.01)
def tag(ax, s, x=-0.08, y=1.02): ax.text(x, y, s, transform=ax.transAxes, fontsize=9, fontweight="bold", va="bottom")

# ---- a: design grid
ax = fig.add_subplot(gs[0, 0]); ax.text(-0.055, 1.12, "a", transform=ax.transAxes, fontsize=9, fontweight="bold")
ax.axvspan(5.5, 10.5, color=SHADE, lw=0, zorder=0)
for x, s in [(4.5, "Early postnatal\n(n = 4)"), (8, "Adolescence (n = 8)"), (11.5, "Adulthood\n(n = 4)")]:
    ax.text(x, 2.05, s, ha="center", va="bottom", fontsize=6.2, color=MUTED, linespacing=1.0)
for r in meta.itertuples():
    y = 1 if r.sex == "F" else 0
    c, mk, _ = SEX[r.sex]
    ax.scatter(r.age_wk, y, marker=mk, s=70, color=c, edgecolor="white", lw=0.8, zorder=3)
    ax.text(r.age_wk, y - 0.27, r.slide, ha="center", va="top", fontsize=5.6, color=INK)
# grade bar
grades = [(3.6, 7.5, "mPanIN-2", "#d9e7f8"), (7.5, 8.5, "2 / 3", "#c2d5ee"), (8.5, 10.5, "mPanIN-3", "#a9c3e6"), (10.5, 12.4, "Invasive PDAC", "#8eadd8")]
for a, b, s, c in grades:
    ax.add_patch(FancyBboxPatch((a + 0.04, -0.98), b - a - 0.08, 0.28, boxstyle="round,pad=0,rounding_size=0.06", fc=c, ec="none", zorder=2))
    ax.text((a + b) / 2, -0.84, s, ha="center", va="center", fontsize=5.8, color=INK, zorder=3)
ax.text(3.45, -0.84, "Grade", ha="right", va="center", fontsize=6, color=MUTED)
ax.set_xlim(3.4, 12.5); ax.set_ylim(-1.1, 2.0)
ax.set_yticks([0, 1]); ax.set_yticklabels(["Male", "Female"]); ax.set_xticks(range(4, 13))
ax.set_xlabel("Age (weeks)", labelpad=1); ax.spines[["top", "right", "left"]].set_visible(False); ax.tick_params(axis="y", length=0)

# ---- b: node graph with annotated outputs under each node
ax = fig.add_subplot(gs[1, 0]); tag(ax, "b", -0.055, 0.97); ax.axis("off"); ax.set_xlim(0, 20); ax.set_ylim(2.0, 10.3)
def box(x, y, w, h, fc, ec="#9d9c95", lw=0.7, z=2):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.25", fc=fc, ec=ec, lw=lw, zorder=z))
def arrow(p, q, c=INK, z=5):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>,head_length=3.6,head_width=2.4", mutation_scale=1.2, color=c, lw=1.0, zorder=z))
xs = [2.45, 7.15, 11.85, 16.75]; Ytop = 8.9; W = 4.1
titles = [("Node 1  Tiling", "1024-px tissue tiles"), ("Node 2  Nuclei", "StarDist, 2× upsampled, p 0.4"),
          ("Node 3  Markers", "ROSIE, 50 markers per nucleus"), ("Node 4  Analysis", "lineage scores; pooled sections")]
fcs = ["#ecebe6", "#d9e7f8", "#d9e7f8", "#fbe3d6"]
# parallel lane behind nodes 1-3
for k in (3, 2, 1):
    box(7.15 + 0.13 * k, 6.05 + 0.13 * k, 14.0, 7.6, "#f8fafd", ec="#cdd9ea", lw=0.6, z=0)
box(7.15, 6.05, 14.0, 7.6, "#f8fafd", ec="#8fb0dc", lw=0.8, z=0)
ax.text(14.05, 10.05, "× 16 sections, in parallel", ha="right", va="center", fontsize=6.2, color="#4a6fa5", style="italic")
for x, (t, sub), fc in zip(xs, titles, fcs):
    box(x, Ytop, W, 1.3, fc, z=3)
    ax.text(x, Ytop + 0.25, t, ha="center", va="center", fontsize=6.8, fontweight="bold", zorder=6)
    ax.text(x, Ytop - 0.33, sub, ha="center", va="center", fontsize=5.5, color=MUTED, zorder=6)
for x1, x2 in zip(xs[:-1], xs[1:]):
    arrow((x1 + W / 2 + 0.05, Ytop), (x2 - W / 2 - 0.05, Ytop))
def thumb(x, img, w=3.6, h=4.6, y0=3.15, **kw):
    axi = ax.inset_axes([x - w / 2, y0, w, h], transform=ax.transData)
    axi.imshow(img, **kw); axi.set_xticks([]); axi.set_yticks([])
    for sp in axi.spines.values(): sp.set_edgecolor("#c9c8c1"); sp.set_linewidth(0.6)
    return axi
he = np.asarray(Image.open("tile_he.png"))
# Node 1: tile with 256-px grid hint
a1 = thumb(xs[0], he)
for g in (128, 256, 384):
    a1.axhline(g, color="white", lw=0.5, alpha=0.8); a1.axvline(g, color="white", lw=0.5, alpha=0.8)
ax.text(xs[0], 2.7, "H&E tile (M4, 4 wk)", ha="center", fontsize=5.6, color=MUTED)
# Node 2: StarDist overlay
thumb(xs[1], np.asarray(Image.open("tile_sd2x.png")))
ax.text(xs[1], 2.7, "detected nuclei (blue outlines)", ha="center", fontsize=5.6, color=MUTED)
# Node 3: nuclei coloured by dominant lineage marker
c = pd.read_csv(CELLS)
epi = c[["PanCK", "ECad", "Keratin8/18"]].mean(axis=1); mes = c[["Vimentin", "aSMA", "Podoplanin"]].mean(axis=1); imm = c[["CD45", "CD3e", "CD68"]].mean(axis=1)
S = np.column_stack([epi, mes, imm]); cls = np.where(S.max(1) > 0.5, S.argmax(1), 3)
colr = np.array(["#e87ba4", "#6250d6", "#1baf7a", "#bdbcb5"])
a3 = thumb(xs[2], he, alpha=0.45)
a3.scatter((c.x - 16384) / 2, (c.y - 7168) / 2, s=7, c=colr[cls], edgecolor="white", lw=0.3)
a3.set_xlim(0, 512); a3.set_ylim(512, 0)
for k, (lab, col) in enumerate([("Epithelial", "#e87ba4"), ("Mesenchymal", "#6250d6"), ("Immune", "#1baf7a")]):
    ax.scatter([xs[2] - 2.0 + k * 1.5 + (0.35 if k == 2 else 0)], [2.72], s=10, color=col, zorder=6)
    ax.text(xs[2] - 1.85 + k * 1.5 + (0.35 if k == 2 else 0), 2.72, lab, ha="left", va="center", fontsize=5.2, color=MUTED)
# Node 4: two analysis thumbnails
t3 = np.asarray(Image.open("thumb_fig3a.png")); t7 = np.asarray(Image.open("thumb_fig7a.png"))
thumb(xs[3], t3, w=3.3, h=3.2, y0=4.55)
thumb(xs[3], t7, w=4.2, h=1.0, y0=3.3)
ax.text(xs[3], 2.95, "Figs 3 and 7 shown; Figs 2, 4–6 alike", ha="center", va="center", fontsize=5.2, color=MUTED)
ax.text(xs[3], 2.45, "change points, spatial, validation", ha="center", fontsize=5.2, color=MUTED, style="italic")

for ext in ("png", "pdf"):
    fig.savefig(f"{out}.{ext}", dpi=300)
print("saved")
