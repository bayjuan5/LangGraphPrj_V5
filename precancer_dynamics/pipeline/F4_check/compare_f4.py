# Compares re-run ROSIE marker predictions with the original F4 predictions, cell by cell.
import json, glob, os
import numpy as np
diffs, a_all, b_all, same_label, n = [], [], [], 0, 0
for ref in sorted(glob.glob('reference_phenotypes/*_phenotypes.json')):
    new = os.path.join('Node3_official_out/phenotypes', os.path.basename(ref))
    if not os.path.exists(new): print('missing re-run output:', new); continue
    A = {c['CellID']: c for c in json.load(open(ref))['cells']}
    B = {c['CellID']: c for c in json.load(open(new))['cells']}
    for k in A.keys() & B.keys():
        a = np.array(list(A[k]['Signals'].values())); b = np.array([B[k]['Signals'][m] for m in A[k]['Signals']])
        a_all.append(a); b_all.append(b); diffs.append(np.abs(a - b).max())
        same_label += A[k].get('Phenotype') == B[k].get('Phenotype'); n += 1
a_all, b_all = np.concatenate(a_all), np.concatenate(b_all)
print(f'cells compared: {n}')
print(f'max |difference| in any marker: {max(diffs):.2e}   median per cell: {np.median(diffs):.2e}')
print(f'Pearson r over all marker values: {np.corrcoef(a_all, b_all)[0,1]:.6f}')
print(f'same cell-type label: {same_label}/{n} ({100*same_label/n:.2f}%)')
print('VERDICT:', 'SAME MODEL (differences are numerical noise)' if np.corrcoef(a_all, b_all)[0,1] > 0.9999 and same_label/n > 0.99
      else 'DIFFERENT - do not mix male and female results until this is explained')
