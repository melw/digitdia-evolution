/* Patch-loader entry. The bootloader decompresses FWFS601T.BIN to 0x80000000 and jumps to the word at 0x80000000
 * (= 0x80000100, this code). Everything is linked for RELOC (0x8e000000), so this entry code only uses
 * PC-relative branches and absolute constants: it copies the whole image to RELOC and jumps there.
 * j/jal targets stay in the same 256 MB segment (0x8xxxxxxx), so they are valid from both addresses.
 * Cache maintenance for the copy is done with our own SYNCI loop: no bootloader routine is called before
 * pldr_main has checked the bootloader's signature. */
    .set noreorder
    .set mips32r2
    .section .text.entry, "ax"
    .globl _entry
_entry:
    lui   $t0, 0x8000            /* src = load address */
    lui   $t1, %hi(_reloc_start) /* dst = link address */
    addiu $t1, $t1, %lo(_reloc_start)
    lui   $t2, %hi(_image_size)
    addiu $t2, $t2, %lo(_image_size)
    addu  $t2, $t2, $t0          /* src end */
1:  lw    $t3, 0($t0)
    sw    $t3, 0($t1)
    addiu $t0, $t0, 4
    bne   $t0, $t2, 1b
    addiu $t1, $t1, 4
    /* write back D-cache + invalidate I-cache for [RELOC, RELOC + size), 32-byte lines */
    lui   $t0, %hi(_reloc_start)
    addiu $t0, $t0, %lo(_reloc_start)
2:  synci 0($t0)
    sltu  $t3, $t0, $t1
    bnez  $t3, 2b
    addiu $t0, $t0, 32
    sync
    lui   $sp, %hi(_stack_top)
    addiu $sp, $sp, %lo(_stack_top)
    lui   $t9, %hi(pldr_main)
    addiu $t9, $t9, %lo(pldr_main)
    jr.hb $t9                    /* clears instruction hazards; now running from RELOC */
    nop
