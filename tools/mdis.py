"""Disassemble a range of the firmware image. Usage: python tools/mdis.py fw_main.rbn 0x801c1d00 0x801c1f00"""
import sys
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

import os
BASE = int(os.environ.get("BASE", "0x80000000"), 16)
d = open(sys.argv[1], 'rb').read()
start, end = int(sys.argv[2], 16), int(sys.argv[3], 16)
md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
off = start - BASE
for ins in md.disasm(d[off:end - BASE], start):
    print(f"{ins.address:08x}: {ins.bytes[::-1].hex()}  {ins.mnemonic:8s} {ins.op_str}")
