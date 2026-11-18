# Technical reference (firmware 2.0)

All addresses are virtual. File offset in the unpacked image = address − `0x80000000`. Confidence:
**[P]** proven on the device, **[S]** static analysis only, **[?]** inferred.

## Hardware

| item | value |
|---|---|
| Board | AFS61N_MAIN_V1.0 2021.09.19 |
| SoC | Novatek NT96660BG-H, MIPS32r2 little-endian (74K-class, DSP ASE) |
| Sensor | Sony IMX206, 16 MP. Menu "16M" = native **4920×3280**; "24M" = 6000×4000 upscaled 1.22× [P] |
| Flash | Winbond 25Q64JVSIQ, 8 MB SPI NOR, wide 208-mil SOIC-8 |
| RAM | DDR3 2 Gbit (256 MB at 0x80000000) |
| UART | GND/TX/RX pads (flat SMD; never needed for this project) |

## Flash map

| offset | content |
|---|---|
| `0x000000` | bootloader stage 1 (runs at `0x8ff00000`) |
| `0x000b1c` | bootloader body, BCL1 (runs at `0x8ff09000`) |
| `0x008000` | **main firmware**, BCL1: 3.4 MB → 22.6 MB, load address `0x80000000` |
| `0x345a78–0x4d6000` | more data; a second BCL1 image at `0x4d5654` ("SJJ_20180205", bad checksum) [?] old leftover |
| `0x6045bc` | end of used data |

## Bootloader [P]

- **Stage 1** (`0x8ff00000`) copies its tail (`0x8bc–0xb1c`) to `0x8ff08000`:
  - `0x8ff08000` stage-1 main (unpack the body to `0x8ff09000`, run it)
  - `0x8ff080b4` I-cache invalidate
  - `0x8ff08110` D-cache write-back + invalidate
  - `0x8ff0815c` BCL LZ decompressor `(src, dst, len)`. It uses the DSP instruction `lbux`.
  - When the body's main function (`0x8ff094c0`) returns, stage 1 jumps to `*(0x80000000)`. Stock firmware
    entry: `0x80000400`.
- **Card files.** The board init (`0x8ff09144`) renames the generic `FW96660x.BIN` names:

  | file | effect |
  |---|---|
  | `FWFS601T.BIN` | load into RAM and run, **no flash write** (boot flag 4) |
  | `FWFS601A.BIN` | write firmware to flash |
  | `LDFS601A.BIN` | write the bootloader to flash |

  The bootloader reads FAT32 only. **The file size must be a multiple of 4**, or it hangs.
- **Normal boot** (`0x8ff0a360–0x8ff0a4f8`):
  1. Storage read `0x8ff0d408(block, bytes, dst, 2)` of block 8 (4 KB blocks; start-block variable `0x8ff0df94`).
  2. If it is BCL1: read the compressed size + 16 bytes, then decompress to `0x80000000`.
  3. Storage init `0x8ff0d984` (SPI controller `0xc0230000`, clock bit `0xc0020074` |= 0x40), deinit `0x8ff0ca88`.
     Erase/program is `0x8ff0cc88`, used only by the A/LD paths.
- **Image check** `0x8ff093d0`: the sum of all LE 16-bit words + n(n−1)/2 must be 0 mod 65536, and the size
  at `+0x68` must match. The same rule covers the BCL1 header checksum at offset 4.
- **Handoff block**, written after the image is loaded (`0x8ff0a5fc–0x8ff0a6a8`):

  | offset | content |
  |---|---|
  | `0x80000080` | 16 B cleared, then a 5-char string |
  | `+0x88` | chip id |
  | `+0x94` | flags: 1 BCL, 2/0x20 update, **4 card boot**, **8 normal flash boot** |
  | `+0x98` | firmware size |
  | `+0x9c`, `+0xa0` (block size × start block), `+0xa4`, `+0xa8/aa` | further values |

## Image format

- Header: `0x00` entry address, `0x50` `"NT96660\0"` + `"10000000"` + `"20100701"`, `0x68` size, `0x6c` `55 AA`,
  `0x6e` checksum.
- BCL1 container: `"BCL1"` | u16 checksum | u16 algorithm (9 = LZ77 of the Basic Compression Library) |
  u32 BE unpacked | u32 BE packed. The LZ stream starts with a marker byte. `marker,0` = literal marker;
  `marker,VLC(len),VLC(off)` = match (7 bits per byte, most significant group first).
- `src/bcl_lz.py` is a compatible compressor (window ≤ 99,999, no overlapping matches). Its output is larger than
  Novatek's (4.6 vs 3.4 MB for the main image).

## Card boot without the patch-loader [P]

With boot flag 4 the firmware uses default settings, never saves ("Boot from temp file…") and aborts scans.
`src/patch_noT.py`: `0x801dc108` and `0x801dc2f4` `andi …,4` → `andi …,0`. The patch-loader doesn't need it: it
hands over with flag 8.

## EXIF [P]

| address | what |
|---|---|
| `0x80124a24` | EXIF Software string, 20 chars (`src/tag.py`) |
| `0x80124f8c` | `jal 0x8001cf04` (snprintf `"EXIF_HDL_ID_%d"`) in the EXIF builder. The debug channel replaces it; the UserComment text is at JPEG file offset `12+0x2f4` |

## JPEG still capture

| address | what | |
|---|---|---|
| `0x801c1d40` | quant tables from quality (IJG; q ≥ 100 → all ones) | S |
| `0x80344874` | `ImgCap_EncBS`; capture encode `0x80344b94` | S |
| `0x803449bc` | fixed-Q path `lw s3,0(s3)` → **`addiu s3,zero,100`** | P |
| `0x80344b10` | retry `addiu s3,s3,-5` (JPEG didn't fit) → **−1** | P |
| `0x80344ce0` / `0x80344bf4` | screennail / thumbnail, fixed Q95 | S |
| `0x815938c0` | ImgCap parameter table (16 B entries). Rate control off; BRC targets 5/4/6 MiB unused | S |
| `0x801e4588` | **JPEG buffer budget** = w·h·F/100 + header + 64 KB (+512 KB), F = 30 / **25** / 20 by UI setting. Shift constants at `0x801e4604/08`, `0x801e46e8/ec`, `0x801e46f8/fc` → F ≈ 96/96/97 (`src/patch_jbuf.py`) | P |
| `0x8035d278` / `0x8035d1a0` | capture buffer set / get by id (JPEG `0x36`, raw `0x15`) | P |
| `0x8035cf48` | capture pool: ~180 MB, of which ~58 MB is used at 16M | P |
| `0x801e3620` | `PhotoExe_OnCaptureStart`: 1 raw buffer + 1 JPEG buffer per capture | S |

The JPEG is always 4:2:2.

## Image pipeline

- Novatek IQS framework:
  - **IFE**: raw-domain outlier, spatial and range (bilateral) filter, i.e. the main noise reduction.
  - **IFE2**: Y/UV filter.
  - **IPE**: edge enhancement.
  - **IME**: chroma adapt/suppress, film grain.
  - Also DRE, DCE and SIE.
- There is one `*_IQparam` function per engine. Capture modes are `0x407/0x408`.
- The **IQ builder `0x803368a0`** interpolates per-ISO tables into the arrays the engines read. Helpers:
  - `0x8030cb7c(srcLo, srcHi, n, dst, iso, isoLo, isoHi)`: array interpolation.
  - `0x8030cacc(iso, lo, hi, isoLo, [sp+0x10] isoHi)`: single value; clobbers v0/v1 only.
- The IQUC ("user control") copy at `0x817bb6xx` is **not** what the IFE reads at capture [P].

### Noise reduction [P]

- `IFE_IQparam` `0x803316a8`. FuncEn at `0x803317a4` (`ori 0x3e`): **bit 0x04 is colour gain**, not the filter
  (clearing it gives a green cast).
- Firmware NR-off path: IPL setting `0x43210025` == 0 → `0x80331bec`. It clears bits 0x22 and zeroes the arrays
  below. Forcing it (`0x8033183c` `beqz` → `b`) removes all smoothing, but shows coloured sensor noise in dark slides.
- The arrays used: **RangeA_Thr[6] `0x8179d350`, RangeB_Thr[6] `d380`, RangeA_Lut[17] `d3b0`, RangeB_Lut[17] `d438`**.
  They are filled by the four `jal 0x8030cb7c` at `0x80336fcc`, `0x8033700c`, `0x80337054` and `0x80337094`,
  which `src/nrs/nrscale.S` wraps to scale by K/256.
- Stock values are tiny integers (thrA ≈ 0–3, lutA ≈ 1–27), so scaling is coarse.
- Texture vs K: 256 → 1.64, 192 → 2.42, 128 → 2.59, off → 2.96.

### Sharpening [P]

- The UI sharpness (IPL selector `0x43210002`, `Get_SharpnessValue` `0x801da6a4`) is live, but **does not reach
  capture**.
- The real control is the **edge gains `0x8179d5a8` / `d5ac`** (stock 80). They are interpolated by `jal 0x8030cacc`
  at `0x803371dc` / `0x80337214`, which `src/nrs/edgescale.S` wraps to scale by K/256.
- `IPE_IQparam` `0x80332d2c` multiplies the gains by a table factor (`0x815828ec`) `>> 7` and stores them back
  in place (`0x8033317c` / `0x80333190`). Scaling there compounds on every call.
- Texture vs gain: 80 → 2.41, 40 → 2.04, ~20 → 1.90, 0 → 1.80.

## Code cave

`0x8035cf80–0x8035d110` (400 B) is a console-only printer ("cap dump buf", never called in normal use):

| range | use |
|---|---|
| `0x8035cf80–0x8035d060` | debug channel (≤ 224 B with `--edge`, ≤ 288 B with `--nrscale` only) |
| `0x8035d060–0x8035d0a0` | `edgescale` |
| `0x8035d0a0–0x8035d110` | `nrscale` |

## Debug channel

`src/dbg/dbg_uc.c` replaces the snprintf at `0x80124f8c`, so every JPEG carries firmware values in its EXIF
UserComment. No UART is needed.

- Modes (`--dbgmode`):
  - 2: capture memory
  - 3/4: IQUC NR copy
  - 5: the real NR arrays
  - 6: UI sharpness / saturation / contrast
  - 7: edge gains and the sharpness chain
- Rules: the entry function must come first, there must be no `.rodata` (only `.text` is copied), and it must
  stay within the size limit above.

## Experiments that didn't work

| idea | outcome |
|---|---|
| clear IFE FuncEn bit 0x04 | colour gain, green cast |
| halve the IQUC NR thresholds / LUTs | no effect (wrong copy) |
| UI sharpness 25 for all levels | no effect at capture |
| halve the edge gain inside `IPE_IQparam` | compounds (40 → 20) |

## Console (UART only, unused)

Command table `0x80001fd4`: "cap dump buf", "getimgnor" (snapshot, raw/jpg). Module "iqs" at `0x80001eb8`.
