"""Novatek image helpers: the two checksums the bootloader checks, in pure Python (no ntkcalc needed).

Both use the same rule as the bootloader's image check (0x8ff093d0): the sum of all little-endian 16-bit words
plus n(n-1)/2 (n = number of words) must be 0 mod 65536.
  - decompressed firmware image: "55 AA" at 0x6c, the checksum word at 0x6e
  - BCL1 container: the checksum word at offset 4 of the header
Verified to give byte-identical results to ntkcalc -cw on stock and on patched images.
"""
import struct


def checksum(d):
    n = len(d) // 2
    return (sum(struct.unpack('<%dH' % n, bytes(d[:n * 2]))) + ((n - 1) * n // 2)) & 0xffff


def fix_image(d):
    """Write 55 AA + checksum at 0x6c/0x6e of a decompressed image (bytearray, in place)."""
    struct.pack_into('<H', d, 0x6c, 0xaa55)
    struct.pack_into('<H', d, 0x6e, 0)
    struct.pack_into('<H', d, 0x6e, (-checksum(d)) & 0xffff)
    assert checksum(d) == 0


def fix_bcl(d):
    """Write the checksum into a BCL1 container's header (bytearray, in place)."""
    assert bytes(d[:4]) == b'BCL1'
    struct.pack_into('<H', d, 4, 0)
    struct.pack_into('<H', d, 4, (-checksum(d)) & 0xffff)
    assert checksum(d) == 0


def pack(rbn, name='image'):
    """Decompressed image -> loader-ready BCL1 file contents (compress, verify round trip, checksum, size % 4)."""
    from bcl_lz import lz_compress, lz_decompress
    body = lz_compress(bytes(rbn))
    body += bytes([0 if body[0] != 0 else 1]) * (-len(body) % 4)   # the loader needs size % 4 == 0
    bcl = bytearray(b'BCL1' + struct.pack('>HHII', 0, 9, len(rbn), len(body)) + body)
    if lz_decompress(body, len(rbn))[:len(rbn)] != bytes(rbn):
        raise SystemExit('%s: compression round trip mismatch' % name)
    fix_bcl(bcl)
    assert len(bcl) % 4 == 0
    return bytes(bcl)
