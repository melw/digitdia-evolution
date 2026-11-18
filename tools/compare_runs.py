"""compare_runs.py - compare 20-slide test runs (16M, batch mode, fixed slide order).

  python tools/compare_runs.py <dcim_folder_or_copy> [--first N] [--out DIR] [--slides 20]

Scans are grouped into runs of 20 consecutive file numbers (PICTnnnn). Each run is labelled
with its EXIF Software tag (stock = "FIRMWARE VERSION 2.0", builds carry their own tag).
Per slide and run it reports: JPEG luma quality, file size, blockiness (luma / chroma),
texture, and the seconds since the previous scan (from EXIF DateTimeOriginal).
It also writes, per slide, a side-by-side crop sheet (1:1 centre crop, enlarged 2x) of all runs.
"""
import argparse, datetime, os, re, struct, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ZZ = [0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28,
      35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51, 58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63]
STD_L = [16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
         18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92, 49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99]


def jpeg_info(path):
    """Return (luma quality, Software, DateTimeOriginal) by walking the JPEG/EXIF markers."""
    d = open(path, 'rb').read(200000)
    q, sw, dt = None, '', None
    m = re.search(rb'FIRMWARE[ -~]{0,20}', d)
    if m:
        sw = m.group().decode().rstrip()
    m = re.search(rb'(\d{4}):(\d\d):(\d\d) (\d\d):(\d\d):(\d\d)', d)
    if m:
        dt = datetime.datetime(*map(int, m.groups()))
    i = 2
    while i < len(d) - 4 and d[i] == 0xFF:
        mk = d[i + 1]
        ln = struct.unpack('>H', d[i + 2:i + 4])[0]
        if mk == 0xDB:
            seg = d[i + 4:i + 2 + ln]
            if seg[0] & 15 == 0:
                tab = list(seg[1:65])
                nat = [0] * 64
                for k in range(64):
                    nat[ZZ[k]] = tab[k]
                if all(v == 1 for v in nat):
                    q = 100.0
                else:
                    s = sum(nat[k] * 100 / STD_L[k] for k in range(64)) / 64
                    q = (200 - s) / 2 if s <= 100 else 5000 / s
        if mk == 0xDA:
            break
        i += 2 + ln
    return q, sw, dt


def metrics(path):
    ycc = np.asarray(Image.open(path).convert('YCbCr')).astype(np.float32)

    def phase(a, axis, per):
        dd = np.abs(np.diff(a, axis=axis)).mean(axis=1 - axis)
        return np.array([dd[p::per].mean() for p in range(per)])
    py, pv = phase(ycc[..., 0], 1, 8), phase(ycc[..., 0], 0, 8)
    yblk = (py[7] / np.median(py) + pv[7] / np.median(pv)) / 2
    cb, cr = phase(ycc[..., 1], 0, 8), phase(ycc[..., 2], 0, 8)
    return yblk, (cb[7] / np.median(cb) + cr[7] / np.median(cr)) / 2, float(np.median(py))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--first', type=int, help='first file number of the first run (default: lowest found)')
    ap.add_argument('--slides', type=int, default=20)
    ap.add_argument('--runs', help='comma-separated first file numbers of the runs to compare (overrides --first)')
    ap.add_argument('--out', default='compare_out')
    ap.add_argument('--crop', type=int, default=400, help='crop size in pixels (1:1)')
    a = ap.parse_args()

    files = {}
    for fn in os.listdir(a.folder):
        m = re.match(r'PICT(\d{4})\.JPG$', fn, re.I)
        if m:
            files[int(m.group(1))] = os.path.join(a.folder, fn)
    if not files:
        sys.exit('no PICTnnnn.JPG files found')
    runs = []
    if a.runs:
        for n in (int(x) for x in a.runs.split(',')):
            runs.append([files.get(k) for k in range(n, n + a.slides)])
    else:
        n = a.first if a.first is not None else min(files)
        while any(k in files for k in range(n, n + a.slides)):
            runs.append([files.get(k) for k in range(n, n + a.slides)])
            n += a.slides
    os.makedirs(a.out, exist_ok=True)

    rows, labels = [], []
    for r, run in enumerate(runs):
        tags = {jpeg_info(p)[1] for p in run if p}
        label = 'run%d %s' % (r + 1, '/'.join(sorted(tags)) or '?')
        labels.append(label)
        prev = None
        for s, p in enumerate(run):
            if not p:
                rows.append((r, s, None))
                continue
            q, sw, dt = jpeg_info(p)
            yb, cb, tex = metrics(p)
            dts = (dt - prev).total_seconds() if (dt and prev) else None
            prev = dt or prev
            rows.append((r, s, (os.path.basename(p), q, os.path.getsize(p) / 1e6, yb, cb, tex, dts)))

    with open(os.path.join(a.out, 'report.txt'), 'w') as f:
        for r, label in enumerate(labels):
            f.write('\n== %s\n' % label)
            f.write('slide file           Q      MB   Yblk  Cblk  texture  dt[s]\n')
            vals = [x for (rr, s, x) in rows if rr == r and x]
            for (rr, s, x) in rows:
                if rr != r:
                    continue
                if not x:
                    f.write('%5d  (missing)\n' % (s + 1))
                    continue
                fn, q, mb, yb, cb, tex, dts = x
                f.write('%5d %-14s %5.1f %6.2f  %5.2f %5.2f  %6.2f  %s\n' % (
                    s + 1, fn, q or 0, mb, yb, cb, tex, '%.0f' % dts if dts is not None else '-'))
            if vals:
                dt_list = [v[6] for v in vals if v[6] is not None]
                f.write('mean: Q %.1f, %.2f MB, Yblk %.2f, Cblk %.2f, texture %.2f, %.1f s/slide (median)\n' % (
                    np.mean([v[1] or 0 for v in vals]), np.mean([v[2] for v in vals]), np.mean([v[3] for v in vals]),
                    np.mean([v[4] for v in vals]), np.mean([v[5] for v in vals]),
                    np.median(dt_list) if dt_list else float('nan')))
    print(open(os.path.join(a.out, 'report.txt')).read())

    try:
        font = ImageFont.truetype('arialbd.ttf', 22)
    except OSError:
        font = ImageFont.load_default()
    c = a.crop
    for s in range(a.slides):
        tiles = []
        for r, run in enumerate(runs):
            p = run[s]
            if not p:
                continue
            im = Image.open(p)
            w, h = im.size
            box = (w // 2 - c // 2, h // 2 - c // 2, w // 2 + c // 2, h // 2 + c // 2)
            tiles.append((labels[r], im.crop(box).resize((c * 2, c * 2), Image.NEAREST)))
        if not tiles:
            continue
        sheet = Image.new('RGB', (len(tiles) * (2 * c + 10), 2 * c + 40), 'white')
        dr = ImageDraw.Draw(sheet)
        for i, (lab, t) in enumerate(tiles):
            sheet.paste(t, (i * (2 * c + 10), 40))
            dr.text((i * (2 * c + 10) + 6, 8), lab[:48], fill='black', font=font)
        sheet.save(os.path.join(a.out, 'slide%02d.png' % (s + 1)))
    print('crop sheets ->', os.path.abspath(a.out))


if __name__ == '__main__':
    main()
