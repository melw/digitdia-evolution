# base/: your own stock firmware (not distributed)

`build.py` and `make_pldr.py --regen` patch a copy of the stock firmware. It is Reflecta's code, so it is not in
this repository, and Reflecta doesn't publish firmware downloads. You only need it to **change** the patches;
building the released patch-loader (`python make_pldr.py`) doesn't need it.

## Get it from your scanner

1. **Dump the 8 MB SPI flash** (Winbond 25Q64JVSIQ, the *wide* 208-mil SOIC-8 package) with the scanner unplugged.
   A Raspberry Pi with an SOIC-8 clip and flashrom works without soldering:
   ```
   flashrom -p linux_spi:dev=/dev/spidev0.0,spispeed=500 -c W25Q64JV-.Q -r dump.bin
   ```
   Wiring (flash pin → Pi header pin): 1 CS → 24, 2 DO → 21, 3 WP → not connected, 4 GND → 25, 5 DI → 19,
   6 CLK → 23, 7 HOLD → 17 (3.3 V), 8 VCC → 1 (3.3 V). Read twice and compare. **Don't** use a "black" CH341A
   programmer in-circuit without the 3.3 V fix: it drives 5 V on the signal lines.
2. **Unpack it:**
   ```
   python tools/extract_base.py dump.bin
   ```
   This writes `base/fw_main.rbn` (the main firmware from flash offset 0x8000, unpacked) and checks it.

Keep the dump: it's also your recovery image.

## Check it

| file | size | SHA256 |
|---|---|---|
| `fw_main.rbn` (firmware 2.0, unpacked) | 22,666,932 | `907b2267c65ef7629d308a789d93f4056ac61a64c6619db78a5868a10aada4c7` |

The whole dump may differ between units, but the unpacked firmware should be identical for every
scanner with firmware 2.0. `build.py` refuses any other image. Set `DIGITDIA_ANYBASE=1` to skip the check, but the
patches still assert every original instruction word, so a different firmware fails at build time.
