"""Convert a QuPath GeoJSON export of one crop into the *_qupath.json schema used by manual_recall.py.
Counts every detection + every hand-drawn annotation (by polygon centroid) + every Point;
the largest annotation (the crop rectangle) is excluded. Image is the 4x upsampled 1024 px crop,
so coordinates are divided by 4 to native 256 px. Points closer than 2 um are merged.
usage: python geojson_to_qupath_json.py in.geojson out.json"""
import json, sys, math
NAT_MPP, UP = 0.5027, 4.0
def centroid(geom):
    t, c = geom['type'], geom['coordinates']
    if t == 'Point': return [tuple(c)]
    if t == 'MultiPoint': return [tuple(p) for p in c]
    ring = c[0] if t == 'Polygon' else max((p[0] for p in c), key=len)
    A = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        k = x0 * y1 - x1 * y0; A += k; cx += (x0 + x1) * k; cy += (y0 + y1) * k
    if abs(A) < 1e-9: return [(sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))]
    return [(cx / (3 * A), cy / (3 * A))]
def area(geom):
    if geom['type'] != 'Polygon': return 0
    r = geom['coordinates'][0]
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]))) / 2
inp, out = sys.argv[1], sys.argv[2]
g = json.load(open(inp)); fs = g['features'] if isinstance(g, dict) else g
ann = [f for f in fs if f['properties'].get('objectType') == 'annotation']
rect = max(ann, key=lambda f: area(f['geometry'])) if ann else None
det = [f for f in fs if f['properties'].get('objectType') == 'detection']
hand = [f for f in ann if f is not rect]
raw = [p for f in det for p in centroid(f['geometry'])]
nh = sum(len(centroid(f['geometry'])) for f in hand)
raw += [p for f in hand for p in centroid(f['geometry'])]
minsep = 2.0 / (NAT_MPP / UP); kept = []
for p in raw:
    if not any(math.hypot(p[0] - q[0], p[1] - q[1]) < minsep for q in kept): kept.append(p)
name = inp.split('/')[-1].replace('crop_', '').split('.geojson')[0].replace('_v2', '')
sl, lab = name.split('_')[0], name.split('_')[1]
x0 = int(name.split('_x')[1].split('_')[0]); y0 = int(name.split('_y')[1])
o = dict(name=name, slide=sl, label=lab, x0=x0, y0=y0, size_px=256, mpp=NAT_MPP,
         source='qupath_cell_detection_reviewed+manual', n_detection=len(det), n_hand=nh, n=len(kept),
         points_crop_px=[[round(x / UP, 2), round(y / UP, 2)] for x, y in kept])
json.dump(o, open(out, 'w')); print(f'{name}: {len(det)} detections + {nh} hand = {len(raw)} raw -> {len(kept)} kept -> {out}')
