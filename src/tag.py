"""Replace the EXIF Software string (20 chars, same length) in a decompressed image.

  python tag.py in.rbn out.rbn "FIRMWARE V2.0 Q100S1"
"""
import sys

d = bytearray(open(sys.argv[1], 'rb').read())
new = sys.argv[3].encode()
old = b'FIRMWARE VERSION 2.0'
assert len(new) == len(old), len(new)
off = 0x80124a24 - 0x80000000
assert d[off:off + 20] == old and d.count(old) == 1
d[off:off + 20] = new
open(sys.argv[2], 'wb').write(d)
print('tagged', new.decode())
