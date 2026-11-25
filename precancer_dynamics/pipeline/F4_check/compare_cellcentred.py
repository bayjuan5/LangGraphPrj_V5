# Agreement between cell-centred and original sliding-window predictions, split by distance to the tile edge.
import json, glob, os
import numpy as np
res = {'interior (>=72 px from edge)': ([], []), 'edge band (<64 px from edge)': ([], [])}
lab = {k: [0, 0] for k in res}
for ref in sorted(glob.glob('reference_phenotypes/*_phenotypes.json')):
    new = os.path.join('Node3_cell_out/phenotypes', os.path.basename(ref))
    if not os.path.exists(new): print('missing', new); continue
    A = {c['CellID']: c for c in json.load(open(ref))['cells']}
    B = {c['CellID']: c for c in json.load(open(new))['cells']}
    for k in A.keys() & B.keys():
        x, y = A[k]['x'], A[k]['y']; d = min(x, y, 1023 - x, 1023 - y)
        grp = 'interior (>=72 px from edge)' if d >= 72 else ('edge band (<64 px from edge)' if d < 64 else None)
        if grp is None: continue
        res[grp][0].append(list(A[k]['Signals'].values())); res[grp][1].append([B[k]['Signals'][m] for m in A[k]['Signals']])
        lab[grp][0] += A[k]['Phenotype'] == B[k]['Phenotype']; lab[grp][1] += 1
for g, (a, b) in res.items():
    if not a: continue
    a, b = np.array(a), np.array(b)
    per_marker = [np.corrcoef(a[:, j], b[:, j])[0, 1] for j in range(a.shape[1]) if a[:, j].std() > 0 and b[:, j].std() > 0]
    print(f'{g}: {len(a)} cells | median per-marker Pearson r {np.median(per_marker):.3f} '
          f'(min {np.min(per_marker):.3f}) | same provisional label {100*lab[g][0]/lab[g][1]:.1f}%')
print('Expected: interior r close to 1 (windows identical up to the 8-px blending of the old method); '
      'edge band lower, because the old method zero-padded those windows.')
