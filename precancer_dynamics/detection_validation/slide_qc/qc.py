import openslide, numpy as np, glob, os, sys, random
from PIL import Image
out=os.path.expanduser('~/mnt/Pancrea Cancer/NPJ SBA/analysis/slide_qc'); os.makedirs(out,exist_ok=True)
def lapvar(g):
    l=-4*g[1:-1,1:-1]+g[:-2,1:-1]+g[2:,1:-1]+g[1:-1,:-2]+g[1:-1,2:]
    return l.var()
def hf(g):  # fraction of energy above half-Nyquist
    F=np.abs(np.fft.rfft2(g-g.mean()))**2; h,w=F.shape
    fy=np.abs(np.fft.fftfreq(g.shape[0]))[:,None]; fx=np.fft.rfftfreq(g.shape[1])[None,:]
    r=np.sqrt(fx**2+fy**2); return F[r>0.25].sum()/F.sum()
files=sys.argv[1:]
for p in files:
    s=openslide.OpenSlide(p); name=os.path.basename(p).replace('.svs','')
    lv=s.level_count-1; t=s.read_region((0,0),lv,s.level_dimensions[lv]).convert('RGB')
    ds=s.level_downsamples[lv]; a=np.asarray(t).astype(float)
    mask=((a.max(2)-a.min(2))>20)&(a.mean(2)<220)
    t.thumbnail((1000,1000)); t.save(f'{out}/{name}_thumb.jpg',quality=85)
    W,H=s.dimensions; tissue_mm2=mask.sum()*(ds*0.5027/1000)**2
    ys,xs=np.nonzero(mask); random.seed(1); idx=random.sample(range(len(ys)),min(30,len(ys)))
    lv_,hf_=[],[]
    for k,i in enumerate(idx):
        x=int(xs[i]*ds)-256; y=int(ys[i]*ds)-256
        r=np.asarray(s.read_region((max(x,0),max(y,0)),0,(512,512)).convert('RGB')).astype(float)
        if ((r.max(2)-r.min(2))>20).mean()<0.5: continue
        g=r.mean(2); lv_.append(lapvar(g)); hf_.append(hf(g))
        if k<2: Image.fromarray(r.astype('uint8')).save(f'{out}/{name}_tile{k}.png')
    print(f"{name},{W}x{H},{tissue_mm2:.1f},{len(lv_)},{np.median(lv_):.1f},{np.median(hf_)*100:.2f}",flush=True)
