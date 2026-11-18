"""Scale the IPE edge gains (sharpening) by K/256, once per IQ refresh.

  python patch_edgescale.py in.rbn nrs/edgescale.bin out.rbn

The IQ builder 0x803368a0 interpolates the two edge gains (0x8179d5a8 / d5ac, stock 80 / 80) with 0x8030cacc at
0x803371dc and 0x80337214. Both calls are redirected to nrs/edgescale.S (0x8035d060, 64 bytes, in front of the
nrscale wrapper). Build 34 (gains 0) proved these gains are the sharpening; build 35 (srl 7 -> 8 at IPE_IQparam's
in-place store-back) compounded to 20. Apply after patch_dbg.py (shares the printer cave; dbg code max 224 bytes).
"""
import struct, sys

BASE = 0x80000000
WRAP, WRAP_MAX = 0x8035d060, 0x8035d0a0 - 0x8035d060
JAL_INTERP1 = 0x0c000000 | ((0x8030cacc & 0x0fffffff) >> 2)
SITES = [0x803371dc, 0x80337214]

d = bytearray(open(sys.argv[1], 'rb').read())
code = open(sys.argv[2], 'rb').read()
assert len(code) <= WRAP_MAX, len(code)
off = WRAP - BASE
d[off:off + len(code)] = code
new = 0x0c000000 | ((WRAP & 0x0fffffff) >> 2)
for s in SITES:
    cur, = struct.unpack_from('<I', d, s - BASE)
    if cur != JAL_INTERP1:
        sys.exit('unexpected word at %#x: %#010x' % (s, cur))
    struct.pack_into('<I', d, s - BASE, new)
    print('%#x: %#010x -> %#010x' % (s, cur, new))
print('wrapper %d bytes at %#x' % (len(code), WRAP))
open(sys.argv[3], 'wb').write(d)
