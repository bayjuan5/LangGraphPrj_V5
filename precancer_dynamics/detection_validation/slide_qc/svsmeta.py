import struct,sys,os,re,glob
def ifds(path):
    f=open(path,'rb'); bo=f.read(2); e='<' if bo==b'II' else '>'
    ver=struct.unpack(e+'H',f.read(2))[0]
    big = ver==43
    if big: f.read(4); off=struct.unpack(e+'Q',f.read(8))[0]
    else: off=struct.unpack(e+'I',f.read(4))[0]
    types={1:1,2:1,3:2,4:4,5:8,7:1,16:8,17:8,11:4,12:8,6:1,8:2,9:4,10:8}
    fmt={3:'H',4:'I',16:'Q'}
    out=[]
    while off and len(out)<20:
        f.seek(off)
        n=struct.unpack(e+('Q' if big else 'H'),f.read(8 if big else 2))[0]
        tags={}
        for i in range(n):
            if big: tag,typ,cnt=struct.unpack(e+'HHQ',f.read(12)); val=f.read(8)
            else: tag,typ,cnt=struct.unpack(e+'HHI',f.read(8)); val=f.read(4)
            if tag in (256,257,270,259,322,305):
                size=types.get(typ,1)*cnt
                if size>len(val):
                    p=struct.unpack(e+('Q' if big else 'I'),val)[0]; cur=f.tell(); f.seek(p); data=f.read(size); f.seek(cur)
                else: data=val[:size]
                if typ==2: tags[tag]=data.decode('latin1','ignore').strip('\x00')
                elif typ in fmt: tags[tag]=struct.unpack(e+fmt[typ],data[:struct.calcsize(fmt[typ])])[0]
        out.append(tags)
        off=struct.unpack(e+('Q' if big else 'I'),f.read(8 if big else 4))[0]
    return out
print('file,size_GB,width,height,AppMag,MPP,scanner_info,date,levels')
for p in sorted(glob.glob(sys.argv[1]+'/*.svs')):
    d=ifds(p); t=d[0]; desc=t.get(270,'')
    mag=re.search(r'AppMag = ([\d.]+)',desc); mpp=re.search(r'MPP = ([\d.]+)',desc)
    date=re.search(r'Date = ([\d/]+)',desc); sc=desc.split('|')[0][:60].replace(',',';')
    lv=[f"{x.get(256)}x{x.get(257)}" for x in d if 322 in x]
    print(f"{os.path.basename(p)},{os.path.getsize(p)/1e9:.2f},{t.get(256)},{t.get(257)},{mag.group(1) if mag else ''},{mpp.group(1) if mpp else ''},{sc},{date.group(1) if date else ''},{' '.join(lv)}")
