/* nrscale: wrapper for the ISO interpolation helper 0x8030cb7c(srcLo, srcHi, n, dst, iso, isoLo, isoHi)
 * used by the IFE NR setup 0x803368a0 for RangeA/B_Thr[6] and RangeA/B_Lut[17].
 * Calls the original, then scales dst[0..n-1] by K/256 (K = NRK, set at build time). */
    .set noreorder
    .globl nrscale
nrscale:
    addiu $sp, $sp, -0x28
    lw    $t0, 0x38($sp)      /* forward the 3 stack arguments */
    sw    $t0, 0x10($sp)
    lw    $t0, 0x3c($sp)
    sw    $t0, 0x14($sp)
    lw    $t0, 0x40($sp)
    sw    $t0, 0x18($sp)
    sw    $a2, 0x1c($sp)
    sw    $a3, 0x20($sp)
    sw    $ra, 0x24($sp)      /* before the jal: jal overwrites ra before its delay slot (build 25 hang) */
    jal   0x8030cb7c
    nop
    lw    $a2, 0x1c($sp)
    lw    $a3, 0x20($sp)
    addiu $t1, $zero, NRK
1:  blez  $a2, 2f
    nop
    lw    $t0, 0($a3)
    mul   $t0, $t0, $t1
    sra   $t0, $t0, 8
    sw    $t0, 0($a3)
    addiu $a2, $a2, -1
    b     1b
    addiu $a3, $a3, 4
2:  lw    $ra, 0x24($sp)
    jr    $ra
    addiu $sp, $sp, 0x28
