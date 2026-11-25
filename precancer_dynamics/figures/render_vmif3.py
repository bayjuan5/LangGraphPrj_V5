"""Vivid v-mIF rendering. Colour = ROSIE prediction of the nearest StarDist nucleus (smoothly blended
between neighbours); brightness = H&E-derived structure (hematoxylin -> nuclear 'DAPI-like' signal,
eosin -> cytoplasm). Black background outside tissue."""
import sys, numpy as np, pandas as pd
from PIL import Image
from scipy.spatial import cKDTree
from scipy import ndimage
from skimage.color import rgb2hed
c = pd.read_csv(sys.argv[1]); rgb = np.asarray(Image.open(sys.argv[2]).convert("RGB")); out = sys.argv[3]
N = rgb.shape[0]
hed = rgb2hed(rgb); H = hed[..., 0]; E = hed[..., 1]
def norm(a, lo, hi): return np.clip((a - np.percentile(a, lo)) / (np.percentile(a, hi) - np.percentile(a, lo)), 0, 1)
Hn = norm(H, 50, 99.5); En = norm(E, 20, 99)
gray = rgb.mean(2) / 255
tissue = ndimage.binary_opening(gray < 0.84, iterations=2)
tissue = ndimage.gaussian_filter(tissue.astype(float), 1.5)
def z(cols):  # lineage score = mean of markers, re-standardised so single- and multi-marker channels are comparable
    v = c[cols].mean(axis=1).values; v = (v - np.median(v)) / (v.std() + 1e-9)
    return np.clip(v, 0, 2.0) / 2.0
P = {"epi": (z(["PanCK", "ECad", "Keratin8/18"]), (0.0, 0.9, 1.0)),
     "mes": (z(["Vimentin", "aSMA", "Podoplanin"]), (1.0, 0.45, 0.0)),
     "imm": (z(["CD45", "CD3e", "CD20"]), (0.45, 0.35, 1.0)),
     "mac": (z(["CD68"]), (1.0, 0.1, 0.75)),
     "ki":  (z(["Ki67"]), (1.0, 0.95, 0.1))}
W = np.column_stack([v[0] for v in P.values()]) ** 3.5
C = np.array([v[1] for v in P.values()])
base = np.array((0.25, 1.0, 0.55))                       # mint for low-expression cells
s = W.sum(1)
col = (W @ C + 0.02 * base) / (s + 0.02)[:, None]
amp = np.clip(0.55 + 0.8 * s ** 0.3, 0.55, 1.25)
yy, xx = np.mgrid[0:N, 0:N]
d, idx = cKDTree(c[["x", "y"]].values).query(np.column_stack([xx.ravel(), yy.ravel()]), k=4)
w = np.exp(-(d / 14.0) ** 2) + 1e-9; w /= w.sum(1, keepdims=True)
field = (w[..., None] * (col * amp[:, None])[idx]).sum(1).reshape(N, N, 3)
field = ndimage.gaussian_filter(field, sigma=(2, 2, 0))
dmin = d[:, 0].reshape(N, N)
reach = np.clip(1.4 - dmin / 45, 0.35, 1)                # fade far from any detected nucleus
cyto = (0.18 + 0.75 * En ** 0.8) * tissue * reach
img = field * cyto[..., None]
img += (Hn ** 1.6 * tissue)[..., None] * np.array((0.35, 0.55, 1.0)) * 0.55   # DAPI-like nuclei
img = 1 - np.exp(-2.2 * img)
img = ndimage.gaussian_filter(img, sigma=(0.6, 0.6, 0))
Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(out); print("saved")
