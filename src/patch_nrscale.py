"""Scale the IFE noise-reduction strength (range-filter thresholds + LUTs) by K/256.

  python patch_nrscale.py in.rbn nrs/nrscale.bin out.rbn

The IFE NR setup 0x803368a0 fills the arrays the IFE really uses (thrA 0x8179d350, thrB 0x8179d380,
lutA 0x8179d3b0, lutB 0x8179d438; zeroed by the firmware's NR-off path, build 19) by ISO interpolation
via 0x8030cb7c. Its four calls for those arrays are redirected to a wrapper (nrs/nrscale.S) that calls the
original and then scales the result. Wrapper lives in the tail of the console-only 'cap dump buf' printer
(0x8035d0a0, after the 288-byte slot used by the debug channel; wrapper ends exactly at the cave end 0x8035d110), so this must be applied after patch_dbg.py.
"""
import struct, sys

BASE = 0x80000000
WRAP, WRAP_MAX = 0x8035d0a0, 0x8035d110 - 0x8035d0a0
JAL_INTERP = 0x0c000000 | ((0x8030cb7c & 0x0fffffff) >> 2)
SITES = [0x80336fcc, 0x8033700c, 0x80337054, 0x80337094]   # thrA, thrB, lutA, lutB

d = bytearray(open(sys.argv[1], 'rb').read())
code = open(sys.argv[2], 'rb').read()
assert len(code) <= WRAP_MAX, len(code)
off = WRAP - BASE
d[off:off + len(code)] = code
new = 0x0c000000 | ((WRAP & 0x0fffffff) >> 2)
for s in SITES:
    cur, = struct.unpack_from('<I', d, s - BASE)
    if cur != JAL_INTERP:
        sys.exit('unexpected word at %#x: %#010x' % (s, cur))
    struct.pack_into('<I', d, s - BASE, new)
    print('%#x: %#010x -> %#010x' % (s, cur, new))
print('wrapper %d bytes at %#x' % (len(code), WRAP))
open(sys.argv[3], 'wb').write(d)
