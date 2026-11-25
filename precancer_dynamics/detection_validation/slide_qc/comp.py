import glob,os,re,sys
exec(open('svsmeta.py').read().split("print('file")[0])
from PIL import Image
import numpy as np
os.makedirs('thumbs',exist_ok=True)
print('file,codec,quality,MB_per_Mpx,thumb_tissue_frac')
for p in sorted(glob.glob(sys.argv[1]+'/*.svs')):
    d=ifds(p); desc=d[0].get(270,'')
    m=re.search(r'\) (J2K/KDU|JPEG/RGB)[^Q]*Q=(\d+)',desc)
    codec,q=(m.group(1),m.group(2)) if m else ('?','?')
    mbpm=os.path.getsize(p)/1e6/(d[0][256]*d[0][257]/1e6)
    tf=''
    try:
        im=Image.open(p); n=getattr(im,'n_frames',1)
        best=None
        for i in range(n):
            im.seek(i); w,h=im.size
            if 800<w<4000 and best is None: best=i
        im.seek(best if best is not None else 1); t=im.convert('RGB'); t.thumbnail((1200,1200))
        a=np.asarray(t).astype(float); sat=a.max(2)-a.min(2)
        tf='%.3f'%((sat>20)&(a.mean(2)<220)).mean()
        t.save('thumbs/'+os.path.basename(p)+'.jpg',quality=80)
    except Exception as ex: tf='ERR '+str(ex)[:60]
    print(f"{os.path.basename(p)},{codec},{q},{mbpm:.3f},{tf}")
