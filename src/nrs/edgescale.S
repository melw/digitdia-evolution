/* edgescale: wrapper for the single-value ISO interpolation 0x8030cacc(iso, lo, hi, isoLo, [sp+0x10] isoHi), used by
 * the IQ builder 0x803368a0 for the two IPE edge gains (calls 0x803371dc / 0x80337214 -> 0x8179d5a8 / d5ac).
 * Returns interp * EK / 256. Scaling here happens once per IQ refresh (build 35 scaled at IPE_IQparam's in-place
 * store-back, which compounds: readout 20 instead of 40). Uses only v0/v1, which 0x8030cacc clobbers itself. */
    .set noreorder
    .globl edgescale
edgescale:
    addiu $sp, $sp, -0x20
    lw    $v1, 0x30($sp)      /* forward the stack argument (caller sp+0x10) */
    sw    $ra, 0x1c($sp)
    jal   0x8030cacc
    sw    $v1, 0x10($sp)      /* delay slot: stored before the callee reads it */
    addiu $v1, $zero, EK
    mul   $v0, $v0, $v1
    sra   $v0, $v0, 8
    lw    $ra, 0x1c($sp)
    jr    $ra
    addiu $sp, $sp, 0x20
