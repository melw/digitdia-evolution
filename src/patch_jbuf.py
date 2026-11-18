"""Raise the photo app's JPEG bitstream buffer budget (manual JPG buffer mode, param 6).

  python patch_jbuf.py in.rbn out.rbn

Stock (0x801e4588): size = w*h*F/100 + header + 64 KB (+512 KB), with F chosen by UI setting 2:
  setting 2 == 0 : F = 32-2   = 30   (0x801e4604/08)
  setting 2 == 1 : F = 32-8+1 = 25   (0x801e46f8/fc)   <- the scanner uses this one
  otherwise      : F = 16+4   = 20   (0x801e46e8/ec)
Patched shifts give F = 96 / 97 / 96, i.e. ~0.96 bytes per pixel (24M: ~23.8 MB, 16M: ~16 MB).
DBG002 measured >100 MB free in the 180 MB capture pool, so this fits with a wide margin.
w*h*128 stays below 2^32 for both resolutions (24M: 3.07e9).
"""
import struct, sys

BASE = 0x80000000
patches = [
    (0x801e4604, 0x00101140, 0x001011c0),  # sll v0,s0,5 -> sll v0,s0,7   (setting 0: 128-32 = 96)
    (0x801e4608, 0x00108040, 0x00108140),  # sll s0,s0,1 -> sll s0,s0,5
    (0x801e46e8, 0x00101100, 0x00101180),  # sll v0,s0,4 -> sll v0,s0,6   (other: 64+32 = 96)
    (0x801e46ec, 0x00108080, 0x00108140),  # sll s0,s0,2 -> sll s0,s0,5
    (0x801e46f8, 0x001010c0, 0x00101140),  # sll v0,s0,3 -> sll v0,s0,5   (setting 1: 128-32+1 = 97)
    (0x801e46fc, 0x00101940, 0x001019c0),  # sll v1,s0,5 -> sll v1,s0,7
]
d = bytearray(open(sys.argv[1], 'rb').read())
for vma, old, new in patches:
    off = vma - BASE
    cur, = struct.unpack_from('<I', d, off)
    if cur != old:
        sys.exit('unexpected word at %#x: %#010x (expected %#010x)' % (vma, cur, old))
    struct.pack_into('<I', d, off, new)
    print('%#x: %#010x -> %#010x' % (vma, old, new))
open(sys.argv[2], 'wb').write(d)
