#!/usr/bin/env python3
"""
extract_cells.py - collapse per-tile ROSIE JSON outputs of one slide into one compact .npz.

Works for both output formats used in this project:
  * old  Node3 (sliding window):   <slide>/Node3_official_out/phenotypes/patch_..._xNNNNNN_yNNNNNN_phenotypes.json
  * new  Node3 (cell-centred):      <slide>/Node3_cell_out/*.json  or  <slide>/Node3_cell_stardist_out/*.json
Cell x,y in the JSON are tile-local; the tile origin is taken from "tile_origin" if present,
otherwise parsed from the tile name (_x<digits>_y<digits>). Output coordinates are level-0 slide pixels.

Output arrays (npz):
  X        float32 [n_cells, n_markers]  ROSIE scores
  xy       int32   [n_cells, 2]          global level-0 pixel coordinates
  tile     int32   [n_cells]             index into tile_names
  area     float32 [n_cells]             nucleus area in px (NaN if not recorded)
  area_ok  bool    [n_cells]             area within 20-1000 px (True if area not recorded)
  pheno    int16   [n_cells]             index into pheno_names (legacy rule-based label; not used in analysis)
  markers, tile_names, tile_origin, pheno_names

Usage:
  python extract_cells.py --slide F4 --dir /path/F4/Node3_official_out/phenotypes --out cells/F4__ws_old.npz [--workers 8]
"""
import argparse, glob, json, os, re, sys
from multiprocessing import Pool
import numpy as np

ORIGIN_RE = re.compile(r"_x(\d+)_y(\d+)")
AREA_MIN, AREA_MAX = 20, 1000


def parse_tile(path):
    with open(path) as fh:
        d = json.load(fh)
    name = d.get("tile_name") or os.path.basename(path)
    if "tile_origin" in d and d["tile_origin"] is not None:
        to = d["tile_origin"]
        ox, oy = (int(to["x"]), int(to["y"])) if isinstance(to, dict) else (int(to[0]), int(to[1]))
    else:
        m = ORIGIN_RE.search(name) or ORIGIN_RE.search(os.path.basename(path))
        if m is None:
            return None, f"no tile origin in {path}"
        ox, oy = int(m.group(1)), int(m.group(2))
    cells = d.get("cells", [])
    if not cells:
        return (name, (ox, oy), None, None, None, None), None
    markers = list(cells[0]["Signals"].keys())
    X = np.array([[c["Signals"][k] for k in markers] for c in cells], dtype=np.float32)
    xy = np.array([[c["x"] + ox, c["y"] + oy] for c in cells], dtype=np.int32)
    area = np.array([c.get("area", np.nan) for c in cells], dtype=np.float32)
    ph = [c.get("Phenotype", "NA") for c in cells]
    return (name, (ox, oy), markers, X, xy, (area, ph)), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slide", required=True)
    ap.add_argument("--dir", required=True, help="folder holding per-tile JSONs (searched recursively)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--max_tiles", type=int, default=0, help="debug: only first N tiles")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.dir, "**", "*.json"), recursive=True))
    files = [f for f in files if not os.path.basename(f).startswith(("node2_output", "summary", "run_"))]
    if a.max_tiles:
        files = files[: a.max_tiles]
    if not files:
        sys.exit(f"no JSON files under {a.dir}")
    print(f"[{a.slide}] {len(files)} tile files", flush=True)

    with Pool(max(1, a.workers)) as pool:
        res = pool.map(parse_tile, files, chunksize=4)

    markers = None
    Xs, XYs, Ts, As, Ps, names, origins, errs = [], [], [], [], [], [], [], []
    for r, err in res:
        if err:
            errs.append(err); continue
        name, origin, mk, X, xy, extra = r
        ti = len(names); names.append(name); origins.append(origin)
        if X is None:
            continue
        if markers is None:
            markers = mk
        elif mk != markers:
            X = X[:, [mk.index(k) for k in markers]]
        Xs.append(X); XYs.append(xy); Ts.append(np.full(len(X), ti, np.int32))
        As.append(extra[0]); Ps.extend(extra[1])
    if errs:
        print(f"  WARNING {len(errs)} files skipped, e.g. {errs[0]}")

    X = np.concatenate(Xs); xy = np.concatenate(XYs); tile = np.concatenate(Ts); area = np.concatenate(As)
    area_ok = np.where(np.isnan(area), True, (area >= AREA_MIN) & (area <= AREA_MAX))
    pheno_names, pheno = np.unique(np.array(Ps), return_inverse=True)

    # duplicate cells (same global coordinate) can arise only if tiles overlap; report and keep first
    key = xy[:, 0].astype(np.int64) * 10_000_000 + xy[:, 1]
    _, first = np.unique(key, return_index=True)
    ndup = len(key) - len(first)
    if ndup:
        keep = np.sort(first)
        X, xy, tile, area, area_ok, pheno = X[keep], xy[keep], tile[keep], area[keep], area_ok[keep], pheno[keep]
        print(f"  removed {ndup} duplicate coordinates")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    np.savez_compressed(a.out, X=X, xy=xy, tile=tile, area=area, area_ok=area_ok,
                        pheno=pheno.astype(np.int16), markers=np.array(markers),
                        tile_names=np.array(names), tile_origin=np.array(origins, np.int32),
                        pheno_names=pheno_names, slide=a.slide)
    print(f"[{a.slide}] {len(X):,} cells, {len(names)} tiles, {len(markers)} markers, "
          f"area_ok {area_ok.mean():.3f} -> {a.out}")


if __name__ == "__main__":
    main()
