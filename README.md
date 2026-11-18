# DigitDia Evolution: better scans from the Reflecta slide scanner

Unofficial firmware patches for the **Reflecta DigitDia Evolution** magazine slide scanner (Novatek NT96660,
Sony IMX206 sensor, firmware 2.0). Patch solves the scanner's main image-quality issues:

| | stock firmware 2.0 | patched |
|---|---|---|
| JPEG quality | Q95, drops to Q90 on detailed slides | **Q100** |
| JPEG buffer | 0.25 bytes/pixel | ~0.97 bytes/pixel |
| Noise reduction | strong ("watercolor" look, film grain erased) | **3/4 strength** |
| Sharpening | halos around high-contrast edges | **1/2 strength** |
| File size (16M) | ~3.4 MB | ~11–13 MB |
| Scan time | ~5 s/slide | ~5 s/slide |

On a fixed set of 20 real slides, measured texture/detail rose from 1.27 to 2.05, and JPEG blockiness (1.0 = none)
dropped from 1.36 / 2.48 (luma / chroma) to 1.01 / 1.10.

**Nothing is flashed.** The patches run from the SD card as a tiny *patch-loader* that contains no Reflecta code.

## How it works

The scanner's bootloader runs a file named `FWFS601T.BIN` from the card **in RAM, without writing it to flash**.
This project's `FWFS601T.BIN` is a ~1.3 KB program that, at every power-on:

1. checks that the bootloader routines it will call are exactly the expected ones (hashes; otherwise it stops)
2. reads the scanner's own firmware from flash and unpacks it with the bootloader's decompressor
3. checks that it is exactly stock firmware 2.0 (size + checksum). **Anything else boots unpatched.**
4. applies the patch in RAM and starts the firmware as a normal flash boot

Details: [pldr/README.md](pldr/README.md) and [docs/TECHNICAL.md](docs/TECHNICAL.md).

## Install

1. Check your firmware version: the EXIF "Software" field of any scan must be `FIRMWARE VERSION 2.0`.
2. Use a **FAT32** card (not exFAT). Copy `FWFS601T.BIN` (from the releases page, or built with
   `python make_pldr.py`) to the **root** of the card.
3. Insert the card into the **powered-off** scanner and power on. Scan as usual.
4. Scans made with it say `FIRMWARE V2.0 PLV1.1` in the EXIF "Software" field.

To go back to stock, delete the file (or use another card) and power-cycle.

Use at your own risk. The patch-loader only reads the flash, and removing the card always gives you the stock
scanner back, but this is unofficial software with no warranty.

## Build

- **The patch-loader** (`FWFS601T.BIN`): `python make_pldr.py`. Needs only a MIPS cross compiler; no firmware.
  The result should match the release SHA256 exactly.
- **Your own patch set** (e.g. a different noise-reduction strength): needs a dump of your scanner's flash.
  See [docs/BUILDING.md](docs/BUILDING.md).

## Repository

| path | what |
|---|---|
| `make_pldr.py` | builds the patch-loader; `--regen` makes `pldr/patches.h` from a patched image |
| `build.py` | builds a patched firmware image from your base firmware (`base/fw_main.rbn`) |
| `deploy.ps1` | copies `FWFS601T.BIN` to a card with safety checks (Windows) |
| `pldr/` | patch-loader source (C + MIPS assembly), generated `patches.h` and `sig.h` |
| `src/` | the patches (each verifies the original instruction words first), the two code-cave wrappers, the EXIF debug channel, our BCL1 compressor and the checksum code |
| `tools/` | flash-dump helpers, the emulator test, disassembly helpers, scan comparison tools |
| `base/` | where your own firmware goes (not distributed) |
| `docs/` | building and technical reference |

## Credits

Thanks to the Kodak Reels hacking community on tinkerdifferent.com: the Novatek knowledge from that project made
this one possible.

## License

MIT for the code and documentation in this repository (see [LICENSE](LICENSE)). Reflecta's firmware is not
included, and this project is not affiliated with Reflecta.
