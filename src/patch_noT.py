"""Make card-booted (FWFS601T.BIN) firmware behave like a normal flash boot.

  python patch_noT.py in.rbn out.rbn

The loader sets boot flag 4 at 0x80000094 when it runs firmware from the SD card.
The firmware then loads default settings ("Boot from temp file, use default flags")
and never saves them ("Boot from temp file, skip Save_MenuInfo"). Both checks are
'andi reg,reg,4' and are turned into 'andi reg,reg,0' (always false).
"""
import struct, sys

BASE = 0x80000000
d = bytearray(open(sys.argv[1], 'rb').read())
patches = [
    (0x801dc108, 0x30420004, 0x30420000),  # skip Save_MenuInfo check
    (0x801dc2f4, 0x32620004, 0x32620000),  # use default flags check
]
for vma, old, new in patches:
    off = vma - BASE
    cur, = struct.unpack_from('<I', d, off)
    if cur != old:
        sys.exit('unexpected word at %#x: %#010x (expected %#010x)' % (vma, cur, old))
    struct.pack_into('<I', d, off, new)
    print('%#x: %#010x -> %#010x' % (vma, old, new))
open(sys.argv[2], 'wb').write(d)
