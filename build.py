"""build.py - build a patched firmware image for the Reflecta DigitDia Evolution (firmware 2.0).

Needs your own stock firmware as base/fw_main.rbn (see base/README.md). The result is a full firmware image:
  out/<name>/fw.rbn          decompressed, patched image (input for make_pldr.py --regen)
  out/<name>/FWFS601T.BIN    the same image packed for run-from-SD testing on YOUR scanner
Both contain Reflecta's code: keep them to yourself. To share, use the patch-loader (make_pldr.py).

Pipeline: base check -> optional C/asm (mipsel gcc) -> patches (each verifies the original words first)
-> EXIF Software tag -> image checksum -> BCL1 compress + round trip + header checksum -> size % 4 check.

Examples:
  python build.py --name rel2 --release                     the released settings (Q100, buffer, NR 3/4, edge 1/2)
  python build.py --name rel2-card --release --noT          the same, to run as a full image from the card
  python build.py --name q100 --tag "FIRMWARE V2.0 Q100T1" --q 100 1 --jbuf --noT
"""
import argparse, datetime, hashlib, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
STOCK = os.path.join(ROOT, 'base', 'fw_main.rbn')
STOCK_SHA = '907b2267c65ef7629d308a789d93f4056ac61a64c6619db78a5868a10aada4c7'   # firmware 2.0, unpacked
RELEASE = dict(q=[100, 1], jbuf=True, nrscale=192, edge=128, tag='FIRMWARE V2.0 REL2  ')
sys.path.insert(0, SRC)
import ntk  # noqa: E402


def run(cmd, cwd=SRC):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit('FAILED: %s\n%s%s' % (' '.join(cmd), r.stdout, r.stderr))
    return r.stdout


def sh(cmd, cwd=SRC):
    """Run a toolchain command (mipsel-linux-gnu-*): through WSL on Windows, directly elsewhere."""
    return run(['wsl', '-e', 'sh', '-c', cmd] if os.name == 'nt' else ['sh', '-c', cmd], cwd)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--name', required=True, help='output folder out/<name>/')
    ap.add_argument('--release', action='store_true', help='use the released settings (%s)' % RELEASE)
    ap.add_argument('--tag', help='EXIF Software string, exactly 20 chars')
    ap.add_argument('--q', nargs=2, type=int, metavar=('START', 'STEP'), help='JPEG quality: start value and retry step')
    ap.add_argument('--noT', action='store_true', help='card boot keeps settings and file numbering (needed for a full image on the card; not for the patch-loader)')
    ap.add_argument('--jbuf', action='store_true', help='JPEG buffer budget ~0.96 B/px instead of 0.25')
    ap.add_argument('--nrscale', type=int, metavar='K', help='IFE noise-reduction strength K/256 (256 = stock)')
    ap.add_argument('--edge', type=int, metavar='K', help='IPE edge gain (sharpening) K/256 (256 = stock, 0 = off)')
    ap.add_argument('--dbg', action='store_true', help='EXIF UserComment debug channel (src/dbg/dbg_uc.c)')
    ap.add_argument('--dbgmode', type=int, default=7, help='debug channel variant (see dbg_uc.c)')
    a = ap.parse_args()
    if a.release:
        for k, v in RELEASE.items():
            if getattr(a, k) in (None, False):
                setattr(a, k, v)
    if not a.tag or len(a.tag) != 20:
        sys.exit('--tag must be exactly 20 characters')

    # 0) base
    if not os.path.exists(STOCK):
        sys.exit('base/fw_main.rbn missing - see base/README.md')
    stock = open(STOCK, 'rb').read()
    if sha(stock) != STOCK_SHA and not os.environ.get('DIGITDIA_ANYBASE'):
        sys.exit('base/fw_main.rbn is not the known firmware 2.0 image (SHA256 %s) - see base/README.md' % sha(stock))
    odir = os.path.join(ROOT, 'out', a.name)
    bdir = os.path.join(odir, 'steps')
    os.makedirs(bdir, exist_ok=True)
    cur = os.path.join(bdir, 'step0.rbn')
    shutil.copyfile(STOCK, cur)
    steps = []

    def step(script, *args):
        nonlocal cur
        nxt = os.path.join(bdir, 'step%d.rbn' % (len(steps) + 1))
        if args and args[0].endswith('.bin'):
            out = run([sys.executable, script, cur, args[0], nxt] + list(args[1:]))
        else:
            out = run([sys.executable, script, cur, nxt] + list(args))
        steps.append('%s %s' % (script, ' '.join(args)))
        print(out.strip())
        cur = nxt

    # 1+2) patches
    if a.q:
        step('patch_q.py', str(a.q[0]), str(a.q[1]))
    if a.noT:
        step('patch_noT.py')
    if a.jbuf:
        step('patch_jbuf.py')
    if a.dbg:
        sh('cd dbg && mipsel-linux-gnu-gcc -march=mips32 -EL -ffreestanding -nostdlib -fno-pic -mno-abicalls '
           '-G0 -Os -fno-builtin -DDBG_MODE=%d -c dbg_uc.c -o dbg_uc.o && mipsel-linux-gnu-ld -EL -Ttext=0x8035cf80 -e dbg_uc '
           '--no-dynamic-linker -o dbg_uc.elf dbg_uc.o && mipsel-linux-gnu-objcopy -O binary -j .text dbg_uc.elf dbg_uc.bin' % a.dbgmode)
        dis = sh('mipsel-linux-gnu-objdump -d dbg/dbg_uc.elf')
        if '8035cf80 <dbg_uc>:' not in dis:       # the hook jumps to the cave start
            sys.exit('dbg_uc is not at the cave start 0x8035cf80')
        if '.rodata' in sh('mipsel-linux-gnu-objdump -h dbg/dbg_uc.elf'):
            sys.exit('dbg code has .rodata (only .text is copied into the cave)')
        dmax = 0xe0 if a.edge is not None else 0x120 if a.nrscale is not None else 400
        size = os.path.getsize(os.path.join(SRC, 'dbg', 'dbg_uc.bin'))
        if size > dmax:
            sys.exit('dbg code %d bytes overlaps the wrappers (max %d)' % (size, dmax))
        step('patch_dbg.py', 'dbg/dbg_uc.bin')
    if a.nrscale is not None:        # tail of the code cave: 0x8035d0a0..0x8035d110
        sh('cd nrs && mipsel-linux-gnu-gcc -march=mips32 -EL -fno-pic -mno-abicalls -DNRK=%d -c -x assembler-with-cpp nrscale.S -o nrscale.o && '
           'mipsel-linux-gnu-ld -EL -Ttext=0x8035d0a0 -e nrscale --no-dynamic-linker -o nrscale.elf nrscale.o && '
           'mipsel-linux-gnu-objcopy -O binary -j .text nrscale.elf nrscale.bin' % a.nrscale)
        step('patch_nrscale.py', 'nrs/nrscale.bin')
    if a.edge is not None:           # code cave 0x8035d060..0x8035d0a0
        sh('cd nrs && mipsel-linux-gnu-gcc -march=mips32 -EL -fno-pic -mno-abicalls -DEK=%d -c -x assembler-with-cpp edgescale.S -o edgescale.o && '
           'mipsel-linux-gnu-ld -EL -Ttext=0x8035d060 -e edgescale --no-dynamic-linker -o edgescale.elf edgescale.o && '
           'mipsel-linux-gnu-objcopy -O binary -j .text edgescale.elf edgescale.bin' % a.edge)
        step('patch_edgescale.py', 'nrs/edgescale.bin')
    # 3) tag
    step('tag.py', a.tag)
    # 4) checksum + pack
    rbn = bytearray(open(cur, 'rb').read())
    ntk.fix_image(rbn)
    bcl = ntk.pack(rbn, a.name)
    open(os.path.join(odir, 'fw.rbn'), 'wb').write(rbn)
    open(os.path.join(odir, 'FWFS601T.BIN'), 'wb').write(bcl)
    diff = sum(1 for x, y in zip(stock, rbn) if x != y)
    with open(os.path.join(odir, 'manifest.txt'), 'w') as f:
        f.write('Name=%s\nTag=%s\nSteps=%s\nBytesDifferingFromStock=%d\nStockSHA256=%s\nImageSHA256=%s\nCardFileSHA256=%s\nCardFileSize=%d\nDate=%s\n' % (
            a.name, a.tag, ' | '.join(steps), diff, sha(stock), sha(rbn), sha(bcl), len(bcl), datetime.datetime.now().isoformat()))
    print('out/%s: fw.rbn + FWFS601T.BIN (%d bytes, %d bytes differ from stock). Contains Reflecta code: do not share.' % (a.name, len(bcl), diff))


if __name__ == '__main__':
    main()
