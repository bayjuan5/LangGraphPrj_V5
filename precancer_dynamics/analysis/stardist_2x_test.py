#!/usr/bin/env python3
"""
stardist_2x_test.py - does StarDist 2D_versatile_he miss small mouse nuclei at 0.5 um/px?
Runs the model on the same tiles at native scale (1x) and after 2x bilinear upsampling
(coordinates divided back by 2), and writes an overlay PNG per tile:
  left = H&E, middle = 1x detections (green), right = 2x detections (blue), counts in the header.
Also prints how many 1x nuclei are matched by a 2x nucleus within 4 um.

Usage (rosie_vista_stardist env, gg node):
  python stardist_2x_test.py --svs <path.svs> --tiles x,y x,y ... --out stardist2x_<slide>
Tiles are level-0 origins of 1024-px tiles (e.g. the ones in overlays/ file names minus 256).
"""
import argparse, os, time
import numpy as np
import openslide
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree
from skimage.measure import regionprops


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--svs", required=True)
    ap.add_argument("--tiles", nargs="+", required=True, help="x,y origins of 1024-px tiles")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mpp", type=float, default=0.5027)
    ap.add_argument("--prob", type=float, default=None, help="override probability threshold (default model's 0.69)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    from csbdeep.utils import normalize
    from stardist.models import StarDist2D
    model = StarDist2D.from_pretrained("2D_versatile_he")
    kw = {} if a.prob is None else {"prob_thresh": a.prob}
    sl = openslide.OpenSlide(a.svs)
    print("tile,n_1x,n_2x,frac_1x_matched_by_2x,sec_1x,sec_2x")
    for t in a.tiles:
        x, y = map(int, t.split(","))
        rgb = sl.read_region((x, y), 0, (1024, 1024)).convert("RGB")
        res = {}
        for scale in (1, 2):
            img = rgb if scale == 1 else rgb.resize((2048, 2048), Image.BILINEAR)
            arr = normalize(np.asarray(img), 1, 99.8, axis=(0, 1, 2))
            t0 = time.time()
            lab, det = model.predict_instances(arr, n_tiles=(scale * 2, scale * 2, 1), **kw)
            pts = np.array([p.centroid[::-1] for p in regionprops(lab)], float).reshape(-1, 2) / scale
            res[scale] = (pts, time.time() - t0)
        p1, p2 = res[1][0], res[2][0]
        if len(p1) and len(p2):
            d, _ = cKDTree(p2).query(p1, distance_upper_bound=4 / a.mpp)
            fm = float(np.isfinite(d).mean())
        else:
            fm = float("nan")
        print(f"{x}_{y},{len(p1)},{len(p2)},{fm:.2f},{res[1][1]:.0f},{res[2][1]:.0f}", flush=True)
        # overlay of the central 512x512
        crop = rgb.crop((256, 256, 768, 768))
        panels = [crop]
        for scale, col in ((1, (0, 200, 0)), (2, (0, 90, 255))):
            ov = crop.copy(); dr = ImageDraw.Draw(ov)
            for px, py in res[scale][0] - 256:
                if 0 <= px < 512 and 0 <= py < 512:
                    dr.ellipse([px - 4, py - 4, px + 4, py + 4], outline=col, width=2)
            panels.append(ov)
        canvas = Image.new("RGB", (512 * 3 + 20, 512 + 24), "white")
        for i, p in enumerate(panels):
            canvas.paste(p, (i * 522, 24))
        ImageDraw.Draw(canvas).text((4, 4), f"{os.path.basename(a.svs)} tile x={x} y={y}   1x (green) {len(p1)}   2x (blue) {len(p2)}", fill="black")
        canvas.save(f"{a.out}/tile_x{x:06d}_y{y:06d}.png")


if __name__ == "__main__":
    main()
