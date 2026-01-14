.global _main
.align 2
.data
    fmt: .asciz "%ld\n"
.text
_main:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    
    mov x8, #15
    str x8, [sp]
    
    adrp x0, fmt@PAGE
    add x0, x0, fmt@PAGEOFF
    bl _printf
    
    ldp x29, x30, [sp], #32
    mov x0, #0
    ret
