"""Pieces of a DigitDia Evolution flash dump (8 MB W25Q64, firmware 2.0 layout).

  0x000000  bootloader stage 1 (runs at 0x8ff00000; its tail 0x8bc..0xb1c is copied to 0x8ff08000)
  0x000b1c  bootloader body, BCL1 (runs at 0x8ff09000)
  0x008000  main firmware, BCL1 (unpacked to 0x80000000)
"""
import os, struct, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
from bcl_lz import lz_decompress  # noqa: E402

STAGE1_TAIL = (0x8bc, 0xb1c)      # -> 0x8ff08000
LOADER_BODY = 0xb1c               # -> 0x8ff09000
MAIN_FW = 0x8000                  # -> 0x80000000


def unbcl(dump, off):
    assert dump[off:off + 4] == b'BCL1', 'no BCL1 block at %#x' % off
    _, algo, usz, csz = struct.unpack('>HHII', dump[off + 4:off + 16])
    assert algo == 9
    return lz_decompress(dump[off + 16:off + 16 + csz], usz)[:usz]


def load(path):
    d = open(path, 'rb').read()
    if len(d) != 8 * 1024 * 1024:
        sys.exit('%s: expected an 8 MB flash dump, got %d bytes' % (path, len(d)))
    return d
