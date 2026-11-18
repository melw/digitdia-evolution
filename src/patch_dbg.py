"""Splice the EXIF UserComment debug function into a decompressed image.

  python patch_dbg.py in.rbn dbg/dbg_uc.bin out.rbn

- Code goes to 0x8035cf80 (console-only 'cap dump buf' printer, 400 bytes).
- The EXIF builder's snprintf call at 0x80124f8c is redirected to it.
Original bytes are verified first.
"""
import struct, sys

BASE = 0x80000000
CAVE, CAVE_LEN = 0x8035cf80, 400
CALL_SITE = 0x80124f8c
JAL_SNPRINTF = 0x0c0073c1      # jal 0x8001cf04

d = bytearray(open(sys.argv[1], 'rb').read())
code = open(sys.argv[2], 'rb').read()
assert len(code) <= CAVE_LEN, len(code)

off = CAVE - BASE
first, = struct.unpack_from('<I', d, off)
assert first == 0x27bdffb8, 'cave does not start with the printer prologue: %#x' % first
nxt, = struct.unpack_from('<I', d, off + CAVE_LEN)
assert nxt == 0x27bdfff8, 'unexpected function after the cave: %#x' % nxt
d[off:off + CAVE_LEN] = code + b'\0' * (CAVE_LEN - len(code))

coff = CALL_SITE - BASE
cur, = struct.unpack_from('<I', d, coff)
assert cur == JAL_SNPRINTF, 'call site changed: %#x' % cur
new = 0x0c000000 | ((CAVE & 0x0fffffff) >> 2)
struct.pack_into('<I', d, coff, new)
print('code %d bytes at %#x; %#x: %#010x -> %#010x' % (len(code), CAVE, CALL_SITE, cur, new))
open(sys.argv[3], 'wb').write(d)
