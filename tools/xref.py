"""Find MIPS code that builds given addresses via lui/addiu (or lui + load/store offset).

Usage: python xref.py fw_main.rbn 0x801c0224 [0x801c0264 ...]
"""
import sys, struct
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

import os
BASE = int(os.environ.get("BASE", "0x80000000"), 16)
d = open(sys.argv[1], 'rb').read()
targets = {int(a, 16) for a in sys.argv[2:]}
words = struct.unpack('<%dI' % (len(d) // 4), d[:len(d) // 4 * 4])

hits = []
lui = {}  # reg -> (hi value, index)
for i, w in enumerate(words):
    op = w >> 26
    rs, rt, imm = (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
    simm = imm - 0x10000 if imm & 0x8000 else imm
    if op == 0x0F:  # lui
        lui[rt] = (imm << 16, i)
        continue
    if rs in lui and i - lui[rs][1] <= 12:
        if op in (0x09, 0x0D, 0x23, 0x21, 0x25, 0x20, 0x24, 0x2B, 0x29, 0x28):  # addiu ori lw lh lhu lb lbu sw sh sb
            val = (lui[rs][0] | imm) if op == 0x0D else (lui[rs][0] + simm) & 0xFFFFFFFF
            if val in targets:
                hits.append((BASE + 4 * lui[rs][1], BASE + 4 * i, val))
    if op in (0x02, 0x03) or (op == 0 and (w & 0x3F) in (8, 9)):
        lui.clear()  # crude: forget across jumps

for v in sorted(targets):
    for i in range(len(words)):
        if words[i] == v:
            hits.append((None, BASE + 4 * i, v))

for a, b, v in sorted(hits, key=lambda h: h[1]):
    print(f"{v:#010x}  {'lui @ %#010x' % a if a else 'data ptr':>18}  use @ {b:#010x}")
