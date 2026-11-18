"""make_ab.py - A/B comparison page for two runs of the same 20 slides (click to flip).

  python tools/make_ab.py <raw folder> <first file run A> <first file run B> <out dir> [labelA] [labelB]

Per slide: whole frame (downscaled) + two 1:1 crops (centre, and the most detailed 512x512 area of run A).
Crops are PNG (lossless) so the page shows exactly what is in the JPEGs.
"""
import os, sys, re, json
import numpy as np
from PIL import Image

raw, a0, b0, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
la = sys.argv[5] if len(sys.argv) > 5 else 'A'
lb = sys.argv[6] if len(sys.argv) > 6 else 'B'
os.makedirs(os.path.join(out, 'img'), exist_ok=True)
C = 512


def busiest(im):
    y = np.asarray(im.convert('L').reduce(8), dtype=np.float32)
    g = np.abs(np.diff(y, axis=1))[:-1, :] + np.abs(np.diff(y, axis=0))[:, :-1]
    k = C // 8
    best, pos = -1, (0, 0)
    for r in range(0, g.shape[0] - k, k // 2):
        for c in range(0, g.shape[1] - k, k // 2):
            v = np.median(g[r:r + k, c:c + k])
            if v > best:
                best, pos = v, (c * 8, r * 8)
    return pos


slides = []
for s in range(20):
    pa = os.path.join(raw, 'PICT%04d.JPG' % (a0 + s))
    pb = os.path.join(raw, 'PICT%04d.JPG' % (b0 + s))
    if not (os.path.exists(pa) and os.path.exists(pb)):
        continue
    A, B = Image.open(pa), Image.open(pb)
    w, h = A.size
    crops = [(w // 2 - C // 2, h // 2 - C // 2), busiest(A)]
    ent = {'n': s + 1, 'fa': os.path.basename(pa), 'fb': os.path.basename(pb),
           'mba': round(os.path.getsize(pa) / 1e6, 1), 'mbb': round(os.path.getsize(pb) / 1e6, 1), 'imgs': []}
    for tag, im in (('a', A), ('b', B)):
        im.resize((1200, 1200 * h // w), Image.LANCZOS).save(os.path.join(out, 'img', 's%02d_full_%s.jpg' % (s + 1, tag)), quality=92)
        for i, (x, y) in enumerate(crops):
            im.crop((x, y, x + C, y + C)).save(os.path.join(out, 'img', 's%02d_c%d_%s.png' % (s + 1, i, tag)))
    slides.append(ent)
    print('slide', s + 1, 'crops', crops)

html = open(os.path.join(os.path.dirname(__file__), 'ab_template.html'), encoding='utf-8').read()
html = html.replace('__DATA__', json.dumps(slides)).replace('__LA__', la).replace('__LB__', lb)
open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(html)
print('->', os.path.abspath(os.path.join(out, 'index.html')))
