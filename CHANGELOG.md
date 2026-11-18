# Changelog

## v1.1 (2026-11-18) - EXIF tag `FIRMWARE V2.0 PLV1.1`

- The patch-loader checks the bootloader before using it: hashes of the six bootloader routines it calls must
  match (`pldr/sig.h`). On a different bootloader it stops instead of calling unknown code.
- No bootloader routine is called before that check (the entry code does its own cache maintenance).
- Same image settings as v1.0.
- Reproducible build: `python make_pldr.py` gives SHA256
  `7b8fe0f3eac67ef5f905c54041b46c427481d858d437677468694237540182a8` (1,336 bytes) with gcc 12.4.0 / binutils 2.42.
- No external tools: the image and BCL1 checksums are now computed in Python.

## v1.0 (2026-11-15) - EXIF tag `FIRMWARE V2.0 PLREL2`

- First public release (forum post): the patch-loader.
- JPEG Q100 (step −1 instead of −5), JPEG buffer ~0.97 B/px, IFE noise reduction 3/4, IPE edge gain 1/2.
- Normal-boot handoff, so card boot keeps settings and file numbering.
- 1,152 bytes, SHA256 `beff09e2c583827724234b6a2c44e49d4850ae693e67e4e7de5da23851b6a364`.
