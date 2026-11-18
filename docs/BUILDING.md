# Building

## Toolchain

| tool | used for | tested version |
|---|---|---|
| Python 3 | all scripts | 3.13 |
| `mipsel-linux-gnu-gcc`, `-ld`, `-objcopy`, `-objdump`, `-nm` | patch-loader, code-cave wrappers, debug channel | gcc 12.4.0, binutils 2.42 (Ubuntu 24.04: `apt install gcc-mipsel-linux-gnu`) |
| `unicorn` (pip) | optional emulator test | 2.1.4 |

On Windows the scripts call the cross compiler through WSL (`wsl -e sh -c …`); elsewhere they call it directly.
No other tools are needed: compression (`src/bcl_lz.py`) and both Novatek checksums (`src/ntk.py`) are in Python.

## 1. The patch-loader from the committed patch set (no firmware needed)

```
python make_pldr.py
```

Output: `out/pldr/FWFS601T.BIN`. With the toolchain versions above, the SHA256 matches the release in
[CHANGELOG.md](../CHANGELOG.md). Other compiler versions give a different but equivalent file.

Copy it to a card: by hand, or on Windows `.\deploy.ps1 -Drive E` (checks FAT32, the file, and refuses cards with
flash-writing files on them).

## 2. Your own patch set

Needs `base/fw_main.rbn` from your own flash dump ([base/README.md](../base/README.md)).

```
python build.py --name mine --release --nrscale 160          # e.g. a bit less noise reduction than the release (192)
python make_pldr.py --regen out/mine/fw.rbn --tag "FIRMWARE V2.0 MINE01" --dump dump.bin
```

- `build.py` applies the patches to a copy of the base and writes `out/mine/fw.rbn` (the patched image) and
  `out/mine/FWFS601T.BIN` (the full image packed for the card). **Both contain Reflecta's code: don't share them.**
- `make_pldr.py --regen` turns the difference between base and patched image into `pldr/patches.h` (without the
  noT words) and builds the patch-loader. That file is shareable: it holds only patch words.
- Give each patch set its own 20-character EXIF tag, so every scan shows what made it.
- `--dump` runs the emulator tests (recommended before any device test).

### build.py options

| option | effect |
|---|---|
| `--release` | the released set: `--q 100 1 --jbuf --nrscale 192 --edge 128`, tag `FIRMWARE V2.0 REL2  ` |
| `--q START STEP` | JPEG quality: start at START, on "doesn't fit" retry STEP lower (stock 95 / 5) |
| `--jbuf` | JPEG buffer budget ~0.96 B/px instead of 0.25 (needed for Q100 at 16M/24M) |
| `--nrscale K` | IFE noise reduction × K/256 (256 = stock; 192 = release; 0 ≈ off, which shows sensor noise in dark slides) |
| `--edge K` | IPE edge gain × K/256 (256 = stock 80; 128 = release 40; 0 = no sharpening) |
| `--noT` | only for full images run from the card: keep settings and numbering |
| `--dbg [--dbgmode M]` | EXIF UserComment debug channel (`src/dbg/dbg_uc.c`), see TECHNICAL.md |

## 3. Regenerating the bootloader signature

Only needed if the bootloader routines or their hash ranges change:

```
python tools/gen_sig.py dump.bin      # writes pldr/sig.h
```

## Testing a build on the scanner

1. Card with `FWFS601T.BIN` in the root, scanner off, power on.
2. Scan, then check the EXIF Software tag of the new files.
3. If it doesn't start: power off, remove the card. Nothing was written to flash.

Comparing builds on real slides: scan the same slides in batch mode for each build, then
`python tools/compare_runs.py <folder>` (JPEG quality, size, blockiness, texture, time per slide, crop sheets) and
`python tools/make_ab.py …` (an A/B flip page).
