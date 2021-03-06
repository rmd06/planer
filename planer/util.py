import numpy as np

def pad(img, shp, mode='constant', constant_values=0):
    if shp[2][0]==shp[2][1]==shp[3][0]==shp[3][1]==0: return img
    (n, c, h, w), (mn, mc, mh, mw) = img.shape, shp
    newimg = np.zeros((n, c, h+mh[0]*2, w+mw[0]*2), dtype=img.dtype)
    newimg[:,:,mh[0]:-mh[1],mw[0]:-mw[1]] = img
    return newimg

def conv(img, core, group=1, stride=(1, 1), dilation=(1, 1)):
    (strh, strw), (dh, dw) = stride, dilation
    (n, c, h, w), (ni, ci, hi, wi)  = core.shape, img.shape
    cimg_w = c * h * w * group
    cimg_h, i = ni*(hi//strh)*(wi//strw), 0
    shp = ((0, 0), (0, 0), (dh*(h//2),)*2, (dw*(w//2),)*2)
    img = pad(img, shp, 'constant', constant_values=0)
    img = img.transpose((2,3,0,1)).copy()
    col_img = np.zeros((w*h, hi//strh, wi//strw, ni, ci), img.dtype)
    for r in range(0, h*dh, dh):
        for c in range(0, w*dw, dw):
            col_img[i], i = img[0+r:hi+r:strh, 0+c:wi+c:strw], i+1
    col_img.shape = (w*h, cimg_h, -1, ni, group, ci)
    col_img = col_img.transpose((3,4,1,2,5,0))
    col_core = core.reshape((group, core.shape[0]//group, -1))
    col_img = col_img.reshape((group, -1, cimg_w//group))
    rst = [i.dot(j.T) for i, j in zip(col_core, col_img)]
    rst = rst[0] if group==1 else np.concatenate(rst)
    return rst.reshape((ni, n, hi//strh, wi//strw))

def pool_nxn(img, f, s):
    n, c, h, w = img.shape
    rshp = img.reshape(n,c,h//s,s,w//s,s)
    rshp = rshp.transpose((0,1,2,4,3,5))
    if f == 'max': return rshp.max(axis=(4,5))
    if f == 'mean': return rshp.mean(axis=(4,5))

def pool(img, f, core=(2, 2), stride=(2, 2)):
    if core[0] == core[1] == stride[0] == stride[1]:
        return pool_nxn(img, f, core[0])
    (n, c, h, w), (ch, cw), (strh, strw) = img.shape, core, stride
    shp = ((0, 0), (0, 0), ((ch-1)//2,)*2, ((cw-1)//2,)*2)
    img = pad(img, shp, 'constant', constant_values=0)
    (imn, ic, ih, iw), imgs = img.shape, []
    for r in range(0, ch, 1):
        for c in range(0, cw, 1):
            imgs.append(img[:,:,r:h+r:strh,c:w+c:strw])
    imgs = [i[:,:,:,:,None] for i in imgs]
    col_img = np.concatenate(imgs, axis=-1)
    if f == 'max': return col_img.max(axis=-1)
    if f == 'mean': return col_img.mean(axis=-1)

def maxpool(i, c=(2, 2), s=(2, 2)): return pool(i, 'max', c, s)

def avgpool(i, c=(2, 2), s=(2, 2)): return pool(i, 'mean', c, s)
    
def resize(img, size):
    nc, (h, w) = img.shape[:-2], img.shape[-2:]
    kh, kw = size[0]/h, size[1]/w
    slicer = -0.5+0.5/kh, h-0.5-0.5/kh, size[0]
    rs = np.linspace(*slicer, dtype=np.float32)
    slicec = -0.5+0.5/kw, w-0.5-0.5/kw, size[1]
    cs = np.linspace(*slicec, dtype=np.float32)
    np.clip(rs, 0, h-1, out=rs)
    np.clip(cs, 0, w-1, out=cs)
    ra = np.floor(np.clip(rs, 0, h-1.5))
    ca = np.floor(np.clip(cs, 0, w-1.5))
    ra, ca = ra.astype(int), ca.astype(int)
    rs -= ra; cs -= ca; rb = ra+1; cb = ca+1;
    rs.shape, img.shape = (-1,1), (-1, h, w)
    buf = img[:,:,ca]*(1-cs) + img[:,:,cb]*cs
    result = buf[:,ra,:]*(1-rs) + buf[:,rb,:]*rs
    return result.reshape(nc + size)

def make_upmat(k):
    xs = np.linspace(0.5/k, 1-0.5/k, k*1)
    rs, cs = xs[:,None], xs[None,:]
    klt = ((1-cs)*(1-rs)).reshape((1,-1))
    krt = (cs * (1-rs)).reshape((1,-1))
    klb = ((1-cs) * rs).reshape((1,-1))
    krb = (cs * rs).reshape((1,-1))
    return np.vstack([klt, krt, klb, krb])
    
def upsample(img, k, matbuf={}):    
    n, c, h, w = img.shape
    img = (img[:,:,:1,:], img, img[:,:,-1:,:])
    img = np.concatenate(img, axis=2)
    img = (img[:,:,:,:1], img, img[:,:,:,-1:])
    img = np.concatenate(img, axis=3)
    if not k in matbuf: matbuf[k] = make_upmat(k)    
    imgs = [img[:,:,:-1,:-1], img[:,:,:-1,1:],
            img[:,:,1:,:-1], img[:,:,1:,1:]]
    imgs = [i[:,:,:,:,None] for i in imgs]
    rst = np.concatenate(imgs, axis=-1)
    rst = np.dot(rst.reshape((-1,4)), matbuf[k])
    rst = rst.reshape((-1, w+1, k, k))
    rst = rst.transpose((0,2,1,3))
    rst = rst.reshape((n,c,(h+1)*k, (w+1)*k))
    return rst[:,:,k//2:-k//2,k//2:-k//2]

if __name__ == '__main__': print('100 lines util') 