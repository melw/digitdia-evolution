"""Apply JPEG quality patches to a decompressed Reflecta DigitDia Evolution FW v2.0 image.

  python patch_q.py in.rbn out.rbn [start_q] [step]

Patches (VMA, file offset = VMA - 0x80000000):
  0x803449bc  lw s3,0(s3)          -> addiu s3,zero,<start_q>   (ImgCap_EncBS fixed-Q path: ignore requested Q)
  0x80344b10  addiu s3,s3,-5        -> addiu s3,s3,-<step>       (retry step when the JPEG does not fit its buffer)
Each original word is verified before patching.
"""
import struct, sys

BASE = 0x80000000
src, dst = sys.argv[1], sys.argv[2]
start_q = int(sys.argv[3]) if len(sys.argv) > 3 else 100
step = int(sys.argv[4]) if len(sys.argv) > 4 else 1
assert 5 <= start_q <= 100 and 1 <= step <= 10

d = bytearray(open(src, 'rb').read())
patches = [
    (0x803449bc, 0x8E730000, 0x24130000 | start_q),
    (0x80344b10, 0x2673FFFB, 0x26730000 | ((-step) & 0xFFFF)),
]
for vma, old, new in patches:
    off = vma - BASE
    cur, = struct.unpack_from('<I', d, off)
    if cur != old:
        sys.exit('unexpected word at %#x: %#010x (expected %#010x)' % (vma, cur, old))
    struct.pack_into('<I', d, off, new)
    print('%#x: %#010x -> %#010x' % (vma, old, new))
open(dst, 'wb').write(d)
print('wrote', dst, '(start Q %d, step -%d)' % (start_q, step))
