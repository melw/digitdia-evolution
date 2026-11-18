/* Debug channel: replaces snprintf(buf, 20, "EXIF_HDL_ID_%d", id) in the EXIF builder
 * (call site 0x80124f8c) and writes capture memory figures into the EXIF UserComment.
 *
 * Output (19 chars + NUL): "JJJJ PPPP UUUU FFFF", hex, units of 16 KB:
 *   JJJJ = main JPEG bitstream buffer (buffer id 0x36)
 *   PPPP = whole capture memory pool
 *   UUUU = used: furthest end of any registered buffer - pool start
 *   FFFF = free: pool end - furthest buffer end ("NEG!" if the buffers overrun the pool)
 *
 * DBG001 showed (24M / 16M): JPEG 0187 / 010F, pool 2AD2, raw(0x15) 0, work(0) 03A7.
 * Linked at 0x8035cf80, over the console-only "cap dump buf" printer (400 bytes).
 */
typedef unsigned int u32;

#define GETBUF  ((int (*)(u32 id, u32 *addr, u32 *size))0x8035d1a0)
#define GETPOOL ((int (*)(u32 *addr, u32 *size))0x8035cf48)
#define BUFTAB  ((volatile u32 *)0x817bceac)   /* 150 entries x 16 bytes: +4 addr, +8 size */
#define NBUF    150

static void hex4(char *p, u32 v)
{
    int i;
    for (i = 3; i >= 0; i--) {
        u32 n = v & 15;
        p[i] = (char)(n < 10 ? '0' + n : 'A' + n - 10);
        v >>= 4;
    }
}

#if defined(DBG_MODE) && DBG_MODE == 7
/* DBG007: sharpness chain, IPL id 0. "AAA BBB CCC DDD EEE" =
 * final edge values 0x8179d5a8 / d5ac (read by IPE_IQparam 0x80332d2c), UI percentages 0x8179da0c+0x38 / +0x40
 * (100 = neutral, scaled by sharpness in 0x80336604), pre-interpolation value 0x8179dd08. */
void dbg_uc(char *buf, int len, const char *fmt, int id)
{
    volatile u32 *a[5];      /* filled one by one (an initialised array would go to .rodata) */
    char *p = buf;
    int k, i;
    (void)fmt; (void)id;
    if (len < 20)
        return;
    a[0] = (volatile u32 *)0x8179d5a8;
    a[1] = (volatile u32 *)0x8179d5ac;
    a[2] = (volatile u32 *)(0x8179da0c + 0x38);
    a[3] = (volatile u32 *)(0x8179da0c + 0x40);
    a[4] = (volatile u32 *)0x8179dd08;
    for (k = 0; k < 5; k++) {
        u32 v = *a[k];
        if (k)
            *p++ = ' ';
        for (i = 2; i >= 0; i--) {
            u32 n = (v >> (4 * i)) & 15;
            *p++ = (char)(n < 10 ? '0' + n : 'A' + n - 10);
        }
    }
    *p = 0;
}
#elif defined(DBG_MODE) && DBG_MODE == 6
/* DBG006: sharpness path. "U? S??? T??? C???": UI setting 9 (sharpness level 0/1/2, 0x801dadd0) and the
 * live IPL values for IPL id 0 (0x802c7c5c): sharpness 0x43210002, saturation 3, contrast 4. */
#define GETUI  ((u32 (*)(u32 idx))0x801dadd0)
#define GETIPL ((u32 (*)(u32 id, u32 sel))0x802c7c5c)

void dbg_uc(char *buf, int len, const char *fmt, int id)
{
    /* single function, no helper and no tables, so dbg_uc stays at the cave start */
    char *p = buf;
    int k, i;
    (void)fmt; (void)id;
    if (len < 20)
        return;
    for (k = 0; k < 4; k++) {
        u32 v = k == 0 ? GETUI(9) : GETIPL(0, 0x43210000 | (k + 1));
        if (k)
            *p++ = ' ';
        *p++ = (char)((0x43545355u >> (8 * k)) & 0xff);   /* 'U' 'S' 'T' 'C' */
        for (i = 2; i >= 0; i--) {
            u32 n = (v >> (4 * i)) & 15;
            *p++ = (char)(n < 10 ? '0' + n : 'A' + n - 10);
        }
    }
    *p = 0;
}
#elif defined(DBG_MODE) && DBG_MODE == 5
/* DBG005: the NR arrays the IFE really uses (filled by 0x803368a0, ISO-interpolated), IPL id 0:
 * thrA 0x8179d350 [6], lutA 0x8179d3b0 [17]. Prints thrA[1] thrA[5] lutA[1] lutA[8] lutA[16]. */
static void hex3(char *p, u32 v)
{
    int i;
    for (i = 2; i >= 0; i--) {
        u32 n = v & 15;
        p[i] = (char)(n < 10 ? '0' + n : 'A' + n - 10);
        v >>= 4;
    }
}

void dbg_uc(char *buf, int len, const char *fmt, int id)
{
    /* one loop, so gcc inlines hex3 and dbg_uc stays at the cave start (build 26 called hex3 instead).
     * word offsets from thrA: thr[1]=1, thr[5]=5, lut = +24 words (0x8179d3b0): lut[1]=25, lut[8]=32, lut[16]=40 */
    volatile u32 *thr = (volatile u32 *)0x8179d350;
    char *p = buf;
    int k;
    (void)fmt; (void)id;
    if (len < 20)
        return;
    for (k = 0; k < 5; k++) {
        int w = (0x28819141u >> (6 * k)) & 63;   /* packed 1, 5, 25, 32, 40 - no .rodata table */
        hex3(p, thr[w] & 0xfff);
        p += 3;
        if (k < 4)
            *p++ = ' ';
    }
    *p = 0;
}
#elif defined(DBG_MODE) && (DBG_MODE == 3 || DBG_MODE == 4)
#define DBG_LUT (DBG_MODE == 4)
/* DBG003: IFE range-filter thresholds as used by the IQUC apply function (0x8033e5c0, event 0x08):
 * runtime array RangeA_Thr for IPL id 0 at 0x817bb69c (6 words); print elements 1..5, 3 hex digits each:
 * "AAA BBB CCC DDD EEE". All zero = that path never ran. */
static void hex3(char *p, u32 v)
{
    int i;
    for (i = 2; i >= 0; i--) {
        u32 n = v & 15;
        p[i] = (char)(n < 10 ? '0' + n : 'A' + n - 10);
        v >>= 4;
    }
}

void dbg_uc(char *buf, int len, const char *fmt, int id)
{
#if DBG_LUT
    /* DBG004: RangeA_Lut working copy for IPL id 0 at 0x817bb75c (17 words); points 1, 4, 8, 12, 16 */
    volatile u32 *lut = (volatile u32 *)0x817bb75c;
#else
    volatile u32 *thr = (volatile u32 *)0x817bb69c;
#endif
    char *p = buf;
    int k;
    (void)fmt; (void)id;
    if (len < 20)
        return;
    for (k = 1; k <= 5; k++) {
#if DBG_LUT
        hex3(p, lut[k == 1 ? 1 : 4 * (k - 1)] & 0xfff);
#else
        hex3(p, thr[k] & 0xfff);
#endif
        p += 3;
        if (k < 5)
            *p++ = ' ';
    }
    *p = 0;
}
#else
void dbg_uc(char *buf, int len, const char *fmt, int id)
{
    u32 a, s, ps, pa, end = 0, v[4];
    char *p = buf;
    int k;

    (void)fmt; (void)id;
    if (len < 20)
        return;
    a = s = 0; GETBUF(0x36, &a, &s); v[0] = s >> 14;
    pa = ps = 0; GETPOOL(&pa, &ps);  v[1] = ps >> 14;
    for (k = 0; k < NBUF; k++) {
        u32 ba = BUFTAB[k * 4 + 1], bs = BUFTAB[k * 4 + 2];
        if (bs && ba >= pa && ba + bs > end)
            end = ba + bs;
    }
    v[2] = end > pa ? (end - pa) >> 14 : 0;
    v[3] = (pa + ps >= end) ? (pa + ps - end) >> 14 : 0xFFFFFFFF;
    for (k = 0; k < 4; k++) {
        if (k == 3 && v[3] == 0xFFFFFFFF) {
            p[0] = 'N'; p[1] = 'E'; p[2] = 'G'; p[3] = '!';
        } else {
            hex4(p, v[k]);
        }
        p += 4;
        if (k < 3)
            *p++ = ' ';
    }
    *p = 0;
}
#endif
