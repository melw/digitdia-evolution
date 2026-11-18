"""emu_pldr.py - run the patch-loader in a MIPS emulator (unicorn) against a real flash dump.

  python tools/emu_pldr.py <pldr.rbn> <8 MB flash dump> [<expected image.rbn>]

Simulates what the bootloader does for FWFS601T.BIN: the stub at 0x80000000, the handoff block written, a jump to
*(0x80000000). The bootloader as it sits in RAM (stage-1 tail at 0x8ff08000, body at 0x8ff09000) is loaded from the
dump, so the signature check sees the real code. Storage init/read/deinit are emulated from the dump. The BCL
decompressor is the bootloader's REAL code, and the cache routines are no-ops.
  Test 1: stock flash          -> the image at 0x80000000 must equal the expected image (default: stock + pldr/patches.h)
                                  + handoff block with normal-boot flags
  Test 2: altered firmware     -> must boot UNPATCHED (fingerprint mismatch)
  Test 3: altered bootloader   -> must stop before calling any bootloader routine (signature mismatch)
Fails (exit 1) on any difference, a flash erase/program call, an unexpected halt or an emulator error.
Needs: pip install unicorn (2.1+).
"""
import os, re, struct, sys
from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE, UcError
from unicorn.mips_const import UC_CPU_MIPS32_74KF, UC_MIPS_REG_CP0_STATUS, UC_MIPS_REG_PC, UC_MIPS_REG_RA, \
    UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3, UC_MIPS_REG_V0, UC_MIPS_REG_SP

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flashdump  # noqa: E402
from gen_sig import ram_image  # noqa: E402
from bcl_lz import lz_decompress  # noqa: E402

PHYS = 0x1fffffff                   # kseg0 -> physical
FW_ENTRY = 0x80000400
HANDOFF = bytes(range(0x80, 0xac))  # recognisable fake handoff block
T_FLAGS = 0x5                       # card boot (4) + bit 0, to check that only bit 4 is cleared
LOADER_CALLS = (0x8ff0d984, 0x8ff0d408, 0x8ff0ca88, 0x8ff0815c, 0x8ff08110, 0x8ff080b4)


def p(va):
    return va & PHYS


def run(stub, dump, usz, mutate_fw=False, mutate_loader=False):
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 + UC_MODE_LITTLE_ENDIAN)
    uc.ctl_set_cpu_model(UC_CPU_MIPS32_74KF)          # 74K with DSP ASE: the bootloader's decompressor uses lbux
    uc.reg_write(UC_MIPS_REG_CP0_STATUS, uc.reg_read(UC_MIPS_REG_CP0_STATUS) | (1 << 24))   # Status.MX (DSP on)
    uc.mem_map(0, 0x10000000)                        # 256 MB DRAM at 0x80000000 (kseg0)
    for base, data in ram_image(dump).items():
        uc.mem_write(p(base), data)
    if mutate_loader:
        uc.mem_write(p(0x8ff0d408 + 0x40), b'\x00\x00\x00\x00')
    uc.mem_write(p(0x80000000), stub)
    ho = bytearray(HANDOFF)
    struct.pack_into('<I', ho, 0x94 - 0x80, T_FLAGS)
    struct.pack_into('<I', ho, 0x98 - 0x80, len(stub))
    uc.mem_write(p(0x80000080), bytes(ho))
    log, state = [], {'init': False}

    def ret(v=0):
        uc.reg_write(UC_MIPS_REG_V0, v & 0xffffffff)
        uc.reg_write(UC_MIPS_REG_PC, uc.reg_read(UC_MIPS_REG_RA))

    def hook(uc, addr, size, _):
        try:
            hook2(uc, addr)
        except BaseException as e:      # never let an exception escape into unicorn (it crashes the host)
            state['err'] = repr(e)
            uc.emu_stop()

    def hook2(uc, addr):
        a0, a1, a2, a3 = (uc.reg_read(r) for r in (UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3))
        if addr == 0x8ff0d984:
            state['init'] = True
            log.append('init')
            ret(0)
        elif addr == 0x8ff0d408:
            assert state['init'], 'read before init'
            assert a3 == 2, 'read mode %d' % a3
            uc.mem_write(p(a2), dump[a0 * 4096:a0 * 4096 + a1])
            log.append('read blk %d len %#x' % (a0, a1))
            ret(0)
        elif addr == 0x8ff0ca88:
            log.append('deinit')
            ret(0)
        elif addr == 0x8ff0815c and mutate_fw:          # python decompressor + simulated other firmware
            out = bytearray(lz_decompress(bytes(uc.mem_read(p(a0), a2)), usz)[:usz])
            out[0x200000] ^= 0xff
            uc.mem_write(p(a1), bytes(out))
            log.append('unlz (python, altered)')
            ret(0)
        elif addr == 0x8ff0815c:
            log.append('unlz (real bootloader code)')    # falls through: the real code runs
        elif addr in (0x8ff08110, 0x8ff080b4):
            log.append('dflush' if addr == 0x8ff08110 else 'iinval')
            ret(0)
        elif addr == 0x8ff0cc88:
            raise RuntimeError('flash erase/program routine called!')
    for a in LOADER_CALLS + (0x8ff0cc88,):
        uc.hook_add(UC_HOOK_CODE, hook, begin=a, end=a)
    uc.reg_write(UC_MIPS_REG_SP, 0x8ff0f8e4)
    uc.reg_write(UC_MIPS_REG_RA, 0x8ff00868)
    try:
        uc.emu_start(struct.unpack_from('<I', stub, 0)[0], FW_ENTRY, count=2_000_000_000 if not mutate_loader else 20_000_000)
    except UcError as e:
        raise SystemExit('FAIL: emulator error %s at pc %#x, log %s' % (e, uc.reg_read(UC_MIPS_REG_PC), log))
    if state.get('err'):
        raise SystemExit('FAIL: %s, log %s' % (state['err'], log))
    return uc.reg_read(UC_MIPS_REG_PC) == FW_ENTRY, bytes(uc.mem_read(p(0x80000000), usz)), log


def patches_h():
    s = open(os.path.join(HERE, '..', 'pldr', 'patches.h')).read()
    offs = [int(x, 16) for x in re.search(r'patch_off\[NPATCH\] = \{([^}]*)\}', s).group(1).split(',')]
    vals = [int(x, 16) for x in re.search(r'patch_val\[NPATCH\] = \{([^}]*)\}', s).group(1).split(',')]
    return list(zip(offs, vals))


def main():
    stub = open(sys.argv[1], 'rb').read()
    dump = flashdump.load(sys.argv[2])
    stock = flashdump.unbcl(dump, flashdump.MAIN_FW)
    if len(sys.argv) > 3:
        target = bytearray(open(sys.argv[3], 'rb').read())
    else:
        target = bytearray(stock)
        for o, v in patches_h():
            struct.pack_into('<I', target, o, v)

    def expect(img):
        e = bytearray(img)
        e[0x80:0xac] = HANDOFF
        struct.pack_into('<I', e, 0x94, (T_FLAGS & ~4) | 8)
        struct.pack_into('<I', e, 0x98, len(img))
        return bytes(e)

    ok, got, log = run(stub, dump, len(stock))
    print('test 1 (stock flash): ' + '; '.join(log))
    if not ok:
        raise SystemExit('FAIL: test 1 did not reach the firmware entry')
    if got != expect(target):
        diff = [i for i in range(0, len(got), 4) if got[i:i + 4] != expect(target)[i:i + 4]]
        raise SystemExit('FAIL: image differs from the expected one at %d words, first %s' % (len(diff), [hex(x) for x in diff[:8]]))
    print('test 1 OK: image in RAM == expected (+ handoff, flags %#x -> %#x), entry %#x reached' % (T_FLAGS, (T_FLAGS & ~4) | 8, FW_ENTRY))

    ok, got, log = run(stub, dump, len(stock), mutate_fw=True)
    m = bytearray(stock)
    m[0x200000] ^= 0xff
    if not ok or got != expect(m):
        raise SystemExit('FAIL: test 2, altered firmware was not booted unpatched')
    print('test 2 OK: altered firmware -> booted unpatched')

    ok, got, log = run(stub, dump, len(stock), mutate_loader=True)
    if ok or log:
        raise SystemExit('FAIL: test 3, altered bootloader was not refused (log %s)' % log)
    print('test 3 OK: altered bootloader -> stopped before calling any bootloader routine')


if __name__ == '__main__':
    main()
