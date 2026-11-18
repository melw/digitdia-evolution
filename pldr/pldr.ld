/* The image is loaded at 0x80000000 by the loader, but linked for RELOC = 0x8e000000 (entry.S copies it there).
 * 0x000-0x0ff: header written by make_pldr.py (entry word, NT96660 id, size, checksum; 0x80-0xab handoff block). */
ENTRY(_entry)
SECTIONS
{
    _reloc_start = 0x8e000000;
    .text 0x8e000100 : {
        *(.text.entry)
        *(.text*)
        *(.rodata*)
        *(.data*)
        *(.sdata*)
        . = ALIGN(4);
    }
    _image_end = .;
    .bss : { *(.bss*) *(.sbss*) *(COMMON) }
    _image_size = _image_end - _reloc_start;
    _stack_top = 0x8e080000;
    /DISCARD/ : { *(.MIPS.abiflags) *(.reginfo) *(.pdr) *(.comment) *(.gnu.attributes) *(.note*) }
}
