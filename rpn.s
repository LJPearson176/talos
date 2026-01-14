// ============================================================================
// FILE: rpn.s
// ARCH: separate ARM64 (Apple Silicon)
// DESC: Reverse Polish Notation Calculator (Daemon Mode)
// AUTHOR: Antigravity
// ============================================================================

// DAEMON MODE IMPLEMENTATION:
// 1. _main sets up stack snapshot (x24).
// 2. _read_loop: Resets sp -> x24. Sets Mode Flag (x28=0).
// 3. sys_read: Reads stdin into input_buf.
// 4. Tokenizer: construct argc/argv from input_buf.
// 5. arg_loop: Process tokens.
// 6. Print result.
// 7. Check Mode Flag. If 0, Loop back. If 1, Exit.

.global _main
.align 2

.bss
    input_buf:  .skip 4096      // Raw input buffer
    argv_buf:   .skip 2048      // Array of pointers (simulated argv)

.data
    fmt_result: .asciz "%ld\n"
    fmt_str:    .asciz "Parsing: %s\n"
    fmt_debug:  .asciz "[DEBUG] Stack: %ld | %ld | %ld\n"
    msg_panic:  .asciz "Error: Invalid operation or insufficient arguments.\n"
    fmt_hex:    .asciz "0x%lX\n"
    fmt_bin_pre: .asciz "0b"
    fmt_bit:    .asciz "%d"
    fmt_nl:     .asciz "\n"
    fmt_float:  .asciz "%f\n"
    
    // Command Strings
    cmd_flt:    .asciz "flt"
    cmd_int:    .asciz "int"
    cmd_sqrt:   .asciz "sqrt"
    cmd_fabs:   .asciz "fabs"
    cmd_fneg:   .asciz "fneg"
    cmd_fmin:   .asciz "fmin"
    cmd_fmax:   .asciz "fmax"


.text

_main:
    // Prologue
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    sub     sp, sp, #48
    stp     x19, x20, [sp, #0]
    stp     x21, x22, [sp, #16]
    stp     x23, x24, [sp, #32]
    // Note: Callee-saved regs x19-x28 must be preserved. We save x19-x24.
    // If we use x28, we SHOULD save it. 
    // Let's create more space. 
    sub     sp, sp, #16
    stp     x27, x28, [sp]  // Save x27, x28

    // Capture ARGV logic from start (x0=argc, x1=argv)
    // We only use this if argc > 1 (Legacy One-Shot Mode)
    mov     x19, x0
    mov     x20, x1
    
    // SAFETY: Snapshot stack pointer (x24) for reset
    mov     x24, sp

    cmp     x0, #1
    b.gt    legacy_mode_setup

    // DAEMON MODE START
_read_loop:
    // 1. Reset Stack to Safety Snapshot
    mov     sp, x24
    
    // Set Daemon Flag (0)
    mov     x28, #0

    // 2. Read Packet Header (5 Bytes: 4 Len + 1 Type)
    mov     x0, #0              // fd = stdin
    adrp    x1, input_buf@PAGE
    add     x1, x1, input_buf@PAGEOFF
    mov     x2, #5              // Header Length
    bl      _read_n_bytes       // Read Exactly 5 bytes
    
    // Check EOF (If read returns <= 0)
    cmp     x0, #5
    b.ne    daemon_exit

    // Parse Header
    adrp    x1, input_buf@PAGE
    add     x1, x1, input_buf@PAGEOFF
    
    // Header Format: [Len:4 (BE)] [Type:1]
    
    // Load Length (First 4 bytes)
    ldr     w3, [x1]            // Load 32-bit (Little Endian load of BE data)
    rev     w3, w3              // Reverse Byte Order -> Correct Value
    
    // Load Type (5th byte) is skipped for now (assuming Type 1)
    
    // Safety Limit Check (Max 4095 to allow null terminator)
    cmp     w3, #4095
    b.gt    daemon_exit         // Too big -> disconnect
    
    // 3. Read Body (Len bytes)
    // We overwrite input_buf with body (reusing buffer)
    mov     x19, x3             // Save Body Len to x19
    mov     x0, #0              // fd
    // x1 is still input_buf
    mov     x2, x19             // Len
    bl      _read_n_bytes
    
    // Check Body Read
    cmp     x0, x19
    b.ne    daemon_exit

    // Null-terminate
    adrp    x1, input_buf@PAGE
    add     x1, x1, input_buf@PAGEOFF
    strb    wzr, [x1, x19]      // Null terminator at [base + len]

    // 3. Tokenizer (Build argc/argv)
    // x1 = current char pointer
    // x2 = argv_buf pointer
    // x19 = argc (counter)
    adrp    x2, argv_buf@PAGE
    add     x2, x2, argv_buf@PAGEOFF
    mov     x19, #0         // argc = 0

tokenize_loop:
    ldrb    w3, [x1]        // Load char
    cbz     w3, tokenize_done // End of string

    // Skip whitespace (space=32, tab=9, newline=10)
    cmp     w3, #32
    b.eq    skip_char
    cmp     w3, #9
    b.eq    skip_char
    cmp     w3, #10
    b.eq    skip_char

    // Found token start
    // Store pointer (x1) into argv_buf[argc]
    str     x1, [x2, x19, lsl #3] // argv_buf[argc] = x1
    add     x19, x19, #1          // argc++

find_token_end:
    add     x1, x1, #1
    ldrb    w3, [x1]
    cbz     w3, tokenize_done     // End of string
    
    // Check for delimiter
    cmp     w3, #32
    b.eq    terminate_token
    cmp     w3, #10
    b.eq    terminate_token
    b       find_token_end

terminate_token:
    strb    wzr, [x1]       // Replace delim with \0
skip_char:
    add     x1, x1, #1      // Next char
    b       tokenize_loop

tokenize_done:
    // Check if we found any args
    cbz     x19, _read_loop // Empty line, retry

    // Setup for arg_loop
    // x19 is already argc
    // x20 needs to be argv (argv_buf)
    adrp    x20, argv_buf@PAGE
    add     x20, x20, argv_buf@PAGEOFF
    
    // Fall through to arg_loop logic
    b       arg_loop

// -----------------------------------------------------------

legacy_mode_setup:
    // Set Legacy Flag (1)
    mov     x28, #1

    // Setup for standard ARGV mode
    // x19 and x20 were saved in Prologue
    sub     x19, x19, #1 // Skip program name
    add     x20, x20, #8
    b       arg_loop

// -----------------------------------------------------------

arg_loop:
    cmp     x19, #0
    ble     print_result    // Logic Done

    ldr     x21, [x20], #8  // Load arg ptr
    sub     x19, x19, #1    // Decrement count

    ldrb    w22, [x21]
    cbz     w22, arg_loop

    cmp     w22, #45
    b.eq    check_minus_context
    cmp     w22, #43
    b.eq    do_add
    cmp     w22, #42
    b.eq    do_mul
    cmp     w22, #47
    b.eq    do_div
    cmp     w22, #37
    b.eq    do_mod
    cmp     w22, #94
    b.eq    do_pow
    cmp     w22, #100
    b.eq    do_dup
    cmp     w22, #115
    b.eq    check_swap_conflict
    cmp     w22, #120
    b.eq    do_drop
    cmp     w22, #38
    b.eq    do_and
    cmp     w22, #124
    b.eq    do_or
    cmp     w22, #126
    b.eq    do_not
    cmp     w22, #60
    b.eq    do_less_than
    cmp     w22, #62
    b.eq    do_greater_than
    cmp     w22, #61
    b.eq    do_equals
    cmp     w22, #108
    b.eq    do_lsl
    cmp     w22, #114
    b.eq    do_asr
    cmp     w22, #103
    b.eq    do_gcd
    cmp     w22, #33
    b.eq    do_fact
    cmp     w22, #104
    b.eq    do_hex
    cmp     w22, #98
    b.eq    do_bin
    
    // Check for 'f' prefix (Float Ops)
    cmp     w22, #102       // 'f'
    b.eq    check_float_op
    
    // Fallback to named ops check
    b       check_named_ops

check_swap_conflict:
    // "s" is swap, but "sqrt" is named op.
    ldrb    w23, [x21, #1]
    cbz     w23, do_swap
    b       check_named_ops

check_float_op:
    ldrb    w23, [x21, #1]
    cmp     w23, #43        // '+'
    b.eq    do_fadd
    cmp     w23, #45        // '-'
    b.eq    do_fsub
    cmp     w23, #42        // '*'
    b.eq    do_fmul
    cmp     w23, #47        // '/'
    b.eq    do_fdiv
    cmp     w23, #112       // 'p'
    b.eq    do_fprint
    b       check_named_ops

check_named_ops:
    // Check "flt"
    mov     x0, x21
    adrp    x1, cmd_flt@PAGE
    add     x1, x1, cmd_flt@PAGEOFF
    bl      _strcmp
    cbz     x0, do_flt

    // Check "int"
    mov     x0, x21
    adrp    x1, cmd_int@PAGE
    add     x1, x1, cmd_int@PAGEOFF
    bl      _strcmp
    cbz     x0, do_int

    // Check "sqrt"
    mov     x0, x21
    adrp    x1, cmd_sqrt@PAGE
    add     x1, x1, cmd_sqrt@PAGEOFF
    bl      _strcmp
    cbz     x0, do_sqrt

    // Check "fabs"
    mov     x0, x21
    adrp    x1, cmd_fabs@PAGE
    add     x1, x1, cmd_fabs@PAGEOFF
    bl      _strcmp
    cbz     x0, do_fabs

    // Check "fneg"
    mov     x0, x21
    adrp    x1, cmd_fneg@PAGE
    add     x1, x1, cmd_fneg@PAGEOFF
    bl      _strcmp
    cbz     x0, do_fneg

    // Check "fmin"
    mov     x0, x21
    adrp    x1, cmd_fmin@PAGE
    add     x1, x1, cmd_fmin@PAGEOFF
    bl      _strcmp
    cbz     x0, do_fmin

    // Check "fmax"
    mov     x0, x21
    adrp    x1, cmd_fmax@PAGE
    add     x1, x1, cmd_fmax@PAGEOFF
    bl      _strcmp
    cbz     x0, do_fmax

    // Default to Number
    b       do_number

do_fadd:
    bl      pop_two_args
    fmov    d0, x0
    fmov    d1, x1
    fadd    d0, d0, d1
    fmov    x0, d0
    b       push_result

do_fsub:
    bl      pop_two_args
    fmov    d0, x0
    fmov    d1, x1
    fsub    d0, d0, d1
    fmov    x0, d0
    b       push_result

do_fmul:
    bl      pop_two_args
    fmov    d0, x0
    fmov    d1, x1
    fmul    d0, d0, d1
    fmov    x0, d0
    b       push_result

do_fdiv:
    bl      pop_two_args
    fmov    d0, x0
    fmov    d1, x1
    fdiv    d0, d0, d1
    fmov    x0, d0
    b       push_result

do_fprint:
    mov     x9, sp
    sub     x9, x24, x9
    cmp     x9, #16
    b.lt    panic

    ldr     x0, [sp], #16
    fmov    d0, x0
    sub     sp, sp, #16
    str     d0, [sp]
    adrp    x0, fmt_float@PAGE
    add     x0, x0, fmt_float@PAGEOFF
    bl      _printf
    add     sp, sp, #16
    b       arg_loop

check_minus_context:
    ldrb    w23, [x21, #1]
    cbz     w23, do_sub
    b       do_number

do_add:
    bl      pop_two_args
    add     x0, x0, x1
    b       push_result

do_sub:
    bl      pop_two_args
    sub     x0, x0, x1
    b       push_result

do_mul:
    bl      pop_two_args
    mul     x0, x0, x1
    b       push_result

do_div:
    bl      pop_two_args
    cbz     x1, panic
    sdiv    x0, x0, x1
    b       push_result

do_mod:
    bl      pop_two_args
    cbz     x1, panic
    sdiv    x2, x0, x1
    msub    x0, x2, x1, x0
    b       push_result

do_pow:
    bl      pop_two_args
    cbz     x1, pow_zero
    cmp     x1, #0
    b.lt    pow_neg
    mov     x2, #1
    // add     x1, x1, #1 <-- Removed erroneous increment
pow_loop:
    cbz     x1, pow_done
    mul     x2, x2, x0
    sub     x1, x1, #1
    b       pow_loop
pow_done:
    mov     x0, x2
    b       push_result
pow_zero:
    mov     x0, #1
    b       push_result
pow_neg:
    mov     x0, #0
    b       push_result

do_dup:
    mov     x9, sp
    sub     x9, x24, x9
    cmp     x9, #16
    b.lt    panic
    ldr     x0, [sp]
    b       push_result

do_swap:
    mov     x9, sp
    sub     x9, x24, x9
    cmp     x9, #32
    b.lt    panic
    ldr     x0, [sp]
    ldr     x1, [sp, #16]
    str     x1, [sp]
    str     x0, [sp, #16]
    b       arg_loop

do_drop:
    mov     x9, sp
    sub     x9, x24, x9
    cmp     x9, #16
    b.lt    panic
    add     sp, sp, #16
    b       arg_loop

do_and:
    bl      pop_two_args
    and     x0, x0, x1
    b       push_result

do_or:
    bl      pop_two_args
    orr     x0, x0, x1
    b       push_result

do_not:
    mov     x9, sp
    sub     x9, x24, x9
    cmp     x9, #16
    b.lt    panic
    ldr     x0, [sp], #16
    mvn     x0, x0
    b       push_result

do_less_than:
    bl      pop_two_args
    cmp     x0, x1
    cset    x0, lt
    b       push_result

do_greater_than:
    bl      pop_two_args
    cmp     x0, x1
    cset    x0, gt
    b       push_result

do_equals:
    bl      pop_two_args
    cmp     x0, x1
    cset    x0, eq
    b       push_result

do_lsl:
    bl      pop_two_args
    lsl     x0, x0, x1
    b       push_result

do_asr:
    bl      pop_two_args
    asr     x0, x0, x1
    b       push_result

do_gcd:
    bl      pop_two_args
gcd_loop:
    cbz     x1, gcd_done
    sdiv    x2, x0, x1
    msub    x2, x2, x1, x0
    mov     x0, x1
    mov     x1, x2
    b       gcd_loop
gcd_done:
    b       push_result

do_fact:
    mov     x9, sp
    sub     x9, x24, x9
    cmp     x9, #16
    b.lt    panic
    ldr     x0, [sp], #16
    cmp     x0, #0
    b.lt    fact_zero
    mov     x1, #1
fact_loop:
    cmp     x0, #1
    b.le    fact_done
    mul     x1, x1, x0
    sub     x0, x0, #1
    b       fact_loop
fact_done:
    mov     x0, x1
    b       push_result
fact_zero:
    mov     x0, #0
    b       push_result

do_hex:
    mov     x9, sp
    sub     x9, x24, x9
    cmp     x9, #16
    b.lt    panic
    ldr     x0, [sp], #16
    sub     sp, sp, #16
    str     x0, [sp]
    adrp    x0, fmt_hex@PAGE
    add     x0, x0, fmt_hex@PAGEOFF
    bl      _printf
    add     sp, sp, #16
    add     sp, sp, #16
    b       arg_loop

do_flt:
    bl      pop_one_arg
    scvtf   d0, x0
    fmov    x0, d0
    b       push_result

do_int:
    bl      pop_one_arg
    fmov    d0, x0
    fcvtzs  x0, d0
    b       push_result

do_sqrt:
    bl      pop_one_arg
    fmov    d0, x0
    fsqrt   d0, d0
    fmov    x0, d0
    b       push_result

do_fabs:
    bl      pop_one_arg
    fmov    d0, x0
    fabs    d0, d0
    fmov    x0, d0
    b       push_result

do_fneg:
    bl      pop_one_arg
    fmov    d0, x0
    fneg    d0, d0
    fmov    x0, d0
    b       push_result

do_fmin:
    bl      pop_two_args
    fmov    d0, x0
    fmov    d1, x1
    fmin    d0, d0, d1
    fmov    x0, d0
    b       push_result

do_fmax:
    bl      pop_two_args
    fmov    d0, x0
    fmov    d1, x1
    fmax    d0, d0, d1
    fmov    x0, d0
    b       push_result

pop_one_arg:
    mov     x9, sp
    sub     x9, x24, x9
    cmp     x9, #16
    b.lt    panic
    ldr     x0, [sp], #16
    ret

do_bin:
    mov     x9, sp
    sub     x9, x24, x9
    cmp     x9, #16
    b.lt    panic
    ldr     x0, [sp], #16
    sub     sp, sp, #32
    stp     x19, x20, [sp]
    str     x21, [sp, #16]
    mov     x19, x0
    adrp    x0, fmt_bin_pre@PAGE
    add     x0, x0, fmt_bin_pre@PAGEOFF
    bl      _printf
    mov     x20, #63
    mov     x21, #0
bin_loop:
    lsr     x0, x19, x20
    and     x0, x0, #1
    cbnz    x0, print_bit
    cbz     x21, check_last_bit
    b       print_bit
check_last_bit:
    cbz     x20, print_bit
    b       next_bit
print_bit:
    mov     x21, #1
    sub     sp, sp, #16
    str     x0, [sp]
    adrp    x0, fmt_bit@PAGE
    add     x0, x0, fmt_bit@PAGEOFF
    bl      _printf
    add     sp, sp, #16
next_bit:
    sub     x20, x20, #1
    cmn     x20, #1
    b.ne    bin_loop
    adrp    x0, fmt_nl@PAGE
    add     x0, x0, fmt_nl@PAGEOFF
    bl      _printf
    ldp     x19, x20, [sp]
    ldr     x21, [sp, #16]
    add     sp, sp, #32
    b       arg_loop

do_number:
    mov     x25, x21
scan_dot:
    ldrb    w26, [x25], #1
    cbz     w26, call_parse_int
    cmp     w26, #46
    b.eq    call_parse_float
    b       scan_dot

call_parse_float:
    mov     x0, x21
    mov     x1, #0
    bl      _strtod
    fmov    x0, d0
    b       push_result

call_parse_int:
    mov     x0, x21
    bl      parse_int
    b       push_result

push_result:
    str     x0, [sp, #-16]!
    b       arg_loop

pop_two_args:
    mov     x9, sp
    sub     x9, x24, x9
    cmp     x9, #32
    b.lt    panic
    ldr     x1, [sp], #16
    ldr     x0, [sp], #16
    ret

panic:
    adrp    x0, msg_panic@PAGE
    add     x0, x0, msg_panic@PAGEOFF
    bl      _printf
    
    // Panic: Exit with 1 (Legacy & Daemon)
    // To be safer, Daemon Controller will restart on exit(1) anyway.
    mov     x0, #1
    b       real_exit

daemon_exit:
    mov     x0, #0
    b       real_exit

print_result:
    // This replaces loop_done
    
    // Check if stack is empty (sp >= x24)
    cmp     sp, x24
    b.ge    print_done_empty
    
    ldr     x0, [sp], #16
    
    // Arg for printf must be on stack (Variadic convention or legacy requirement)
    sub     sp, sp, #16
    str     x0, [sp]
    
    adrp    x0, fmt_result@PAGE
    add     x0, x0, fmt_result@PAGEOFF
    bl      _printf
    
    add     sp, sp, #16    // Clean up printf arg

print_done_empty:
    // FLUSH STDOUT
    mov     x0, #0
    bl      _fflush

    // Check Mode Flag (x28). If 1 (Legacy), exit. If 0 (Daemon), loop.
    cbnz    x28, legacy_exit
    b       _read_loop

legacy_exit:
    mov     x0, #0
    b       real_exit

real_exit:
    mov     sp, x24
    
    // Restore preserved regs
    ldp     x27, x28, [sp]
    add     sp, sp, #16
    
    ldp     x23, x24, [sp, #32]
    ldp     x21, x22, [sp, #16]
    ldp     x19, x20, [sp, #0]
    add     sp, sp, #48
    ldp     x29, x30, [sp], #16
    ret

parse_int:
    mov     x12, x0
    mov     x11, #0
    mov     x10, #1
    mov     x14, #10
    ldrb    w13, [x12]
    cmp     w13, #45
    b.ne    check_prefix
    mov     x10, # -1
    add     x12, x12, #1
    ldrb    w13, [x12]
check_prefix:
    cmp     w13, #48
    b.ne    atoi_loop
    ldrb    w15, [x12, #1]
    cmp     w15, #120
    b.eq    set_hex
    cmp     w15, #88
    b.eq    set_hex
    cmp     w15, #98
    b.eq    set_bin
    cmp     w15, #66
    b.eq    set_bin
    b       atoi_loop
set_hex:
    mov     x14, #16
    add     x12, x12, #2
    ldrb    w13, [x12]
    b       atoi_loop
set_bin:
    mov     x14, #2
    add     x12, x12, #2
    ldrb    w13, [x12]
    b       atoi_loop
atoi_loop:
    cbz     w13, atoi_done
    sub     w15, w13, #48
    cmp     w15, #9
    b.le    digit_found
    sub     w15, w13, #65
    cmp     w15, #5
    b.gt    try_lower
    add     w15, w15, #10
    b       digit_found
try_lower:
    sub     w15, w13, #97
    cmp     w15, #5
    b.gt    invalid_char
    add     w15, w15, #10
digit_found:
    cmp     w15, w14
    b.ge    atoi_done
    mul     x11, x11, x14
    add     x11, x11, x15
    add     x12, x12, #1
    ldrb    w13, [x12]
    b       atoi_loop
invalid_char:
    b       atoi_done
atoi_done:
    mul     x0, x11, x10
    ret

// -----------------------------------------------------------
// _read_n_bytes: Reads exactly N bytes into buffer
// Inputs: x0=fd, x1=buf_ptr, x2=n_bytes
// Returns: x0 (total read) or 0 on error/eof
// Preserves: x19-x30
// Clobbers: x0-x4, x16
_read_n_bytes:
    mov     x3, #0          // Total Read Accumulator
    mov     x4, x2          // Remaining Bytes needed
    
read_loop_retry:
    // Call sys_read
    // x0=fd (preserved?), x1=curr_ptr, x2=remaining
    // Need to preserve inputs across syscall as x0 gets result
    // We assume x0 (fd) is 0 (stdin) for this specific use case.
    mov     x0, #0          // Force FD 0 (Stdin)
    
    // x1 is current buffer pointer.
    // x2 is remaining count.
    // But we need to update x1 and x2 after syscall.
    // So we use x4 for remaining (logic below).
    // wait, sys_read expects x2 as count.
    mov     x2, x4          // Set read count to remaining
    
    mov     x16, #3         // syscall read
    svc     #0
    
    // Check Result
    cmp     x0, #0
    b.le    read_fail       // EOF or Error
    
    // Update State
    add     x3, x3, x0      // total += read
    add     x1, x1, x0      // buf_ptr += read
    sub     x4, x4, x0      // remaining -= read
    
    // Check if done
    cmp     x4, #0
    b.gt    read_loop_retry
    
    // Success
    mov     x0, x3          // Return total
    ret

read_fail:
    mov     x0, #0          // Return 0
    ret
