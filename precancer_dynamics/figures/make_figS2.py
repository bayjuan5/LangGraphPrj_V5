"""Supplementary Fig S2: nucleus-detection QC overlays (watershed vs StarDist 1x; StarDist 1x vs 2x)."""
import sys
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
mpl.rcParams.update({"font.family": "Liberation Sans", "font.size": 7})
O = sys.argv[1]
rows = [(f"{O}/overlays/F8_x002304_y011520.png", "a  F8 (8 wk), PanIN — watershed (red) vs StarDist 1× (green)"),
        (f"{O}/overlays/M4_x016640_y007424.png", "b  M4 (4 wk), acinar tissue and stroma — watershed (red) vs StarDist 1× (green)"),
        (f"{O}/overlays/M11_x029952_y021760.png", "c  M11 (11 wk) — watershed (red) vs StarDist 1× (green)"),
        (f"{O}/stardist2x_M4/tile_x016384_y007168.png", "d  M4, same region — H&E, StarDist 1× (green) and StarDist on 2×-upsampled tiles (blue)")]
fig, axs = plt.subplots(4, 1, figsize=(7.09, 9.6))
for ax, (f, t) in zip(axs, rows):
    im = plt.imread(f)
    ax.imshow(im[28:] if im.shape[0] > 400 else im); ax.axis("off")
    ax.set_title(t, loc="left", fontsize=7.5, fontweight="bold", pad=3)
plt.subplots_adjust(left=0.01, right=0.99, top=0.975, bottom=0.01, hspace=0.12)
fig.savefig(sys.argv[2] + ".png", dpi=250); fig.savefig(sys.argv[2] + ".pdf")
print("saved")
