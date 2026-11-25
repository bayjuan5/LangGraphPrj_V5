#!/usr/bin/env python3
"""
seg_overlay.py - visual check of watershed vs StarDist detections on the same tissue.

Watershed reports ~10x more objects than StarDist (median ratio 0.10 per tile; only 5-10% of watershed
objects have a StarDist partner within 4 um, while 81-89% of StarDist nuclei have a watershed partner).
One of the two is badly wrong and the numbers alone cannot say which. This script draws both sets of
centroids on 512x512-px crops (level 0) so the eye can decide, and prints nuclear density per mm2.

Usage (rosie_vista env, login node is fine):
  cd $ROSIE_ROOT/analysis
  $ROSIE_ENV/bin/python seg_overlay.py --root $ROSIE_ROOT --slides M4 F8 M11 --n 3 --out overlays
Output: overlays/<slide>_x<...>_y<...>.png  (red = watershed, green = StarDist; left panel raw H&E)
        overlays/density.csv
"""
import argparse, glob, os
import numpy as np
import openslide
from PIL import Image, ImageDraw

CROP = 512


def load(p):
    z = np.load(p, allow_pickle=False)
    return {k: z[k] for k in z.files}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--cells", default="cells")
    ap.add_argument("--slides", nargs="+", default=["M4", "F8", "M11"])
    ap.add_argument("--n", type=int, default=3, help="crops per slide")
    ap.add_argument("--mpp", type=float, default=0.5027)
    ap.add_argument("--out", default="overlays")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    tile_mm2 = (1024 * a.mpp / 1000) ** 2
    rows = ["slide,method,n_tiles,n_cells,cells_per_tile,cells_per_mm2"]
    for s in a.slides:
        W, S = load(f"{a.cells}/{s}__ws.npz"), load(f"{a.cells}/{s}__sd.npz")
        svs = (glob.glob(f"{a.root}/{s}/*.svs") + glob.glob(f"{a.root}/svs_*/*_{s}_*.svs"))[0]
        sl = openslide.OpenSlide(svs)
        for tag, D in (("watershed", W), ("stardist", S)):
            nt = len(D["tile_origin"]); nc = len(D["X"])
            rows.append(f"{s},{tag},{nt},{nc},{nc / nt:.0f},{nc / (nt * tile_mm2):.0f}")
        # pick dense shared tiles (upper half of watershed counts) so the crop is not empty
        ow = {tuple(o): i for i, o in enumerate(W["tile_origin"])}
        os_ = {tuple(o): i for i, o in enumerate(S["tile_origin"])}
        cw = np.bincount(W["tile"], minlength=len(ow))
        shared = [o for o in ow if o in os_]
        dense = [o for o in shared if cw[ow[o]] >= np.median([cw[ow[q]] for q in shared])]
        for o in rng.choice(len(dense), size=min(a.n, len(dense)), replace=False):
            ox, oy = dense[o]
            cx, cy = ox + 256, oy + 256  # central 512x512 of the tile
            img = sl.read_region((cx, cy), 0, (CROP, CROP)).convert("RGB")
            ov = img.copy(); d = ImageDraw.Draw(ov)
            counts = {}
            for tag, D, col in (("ws", W, (255, 0, 0)), ("sd", S, (0, 200, 0))):
                xy = D["xy"]; m = (xy[:, 0] >= cx) & (xy[:, 0] < cx + CROP) & (xy[:, 1] >= cy) & (xy[:, 1] < cy + CROP)
                counts[tag] = int(m.sum())
                r = 3 if tag == "ws" else 5
                for x, y in xy[m] - [cx, cy]:
                    d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=2)
            canvas = Image.new("RGB", (CROP * 2 + 10, CROP + 24), "white")
            canvas.paste(img, (0, 24)); canvas.paste(ov, (CROP + 10, 24))
            ImageDraw.Draw(canvas).text((4, 4), f"{s} x={cx} y={cy}   watershed (red) {counts['ws']}   StarDist (green) {counts['sd']}", fill="black")
            canvas.save(f"{a.out}/{s}_x{cx:06d}_y{cy:06d}.png")
            print(f"{s} x={cx} y={cy}: ws {counts['ws']}  sd {counts['sd']}", flush=True)
    open(f"{a.out}/density.csv", "w").write("\n".join(rows) + "\n")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
