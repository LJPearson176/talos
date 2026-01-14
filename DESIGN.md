# The Bit-Blind Architecture: An ARM64 Assembly Case Study

> **"If you wish to make an apple pie from scratch, you must first invent the universe." — Carl Sagan**

Writing a calculator in high-level languages is trivial. Writing one in pure ARM64 assembly, without the crutch of a standard library or a heap allocator, forces you to confront the machine as it truly is. This project is not just a calculator; it is an exercise in architectural minimalism.

This document details the three core design decisions that define its architecture: the **System Stack Strategy**, **"Bit-Blind" Polymorphism**, and **Explicit Type Bridging**.

---

## 1. Riding the Metal (The System Stack)

Most RPN implementations allocate a dedicated array on the heap (e.g., `long* stack = malloc(...)`) to manage operands. This is safe, easy, and inefficient. It requires a memory allocator, pointer management, and bounds checking logic that is divorced from the hardware's native capabilities.

We chose a different path: **Use the CPU's own Stack Pointer (`sp`) as the RPN stack.**

### The Mechanism
In ARM64, the stack grows downwards. When we push a number, we subtract 16 bytes (keeping 16-byte alignment) and store the value:

```asm
str x0, [sp, #-16]!  // Pre-index decrement: Push
ldr x0, [sp], #16    // Post-index increment: Pop
```

This effectively makes the "RPN Stack" and the "Call Stack" the same physical entity.

### The Danger: Stack Smashing
The danger is obvious: if a user pops too many items, the stack pointer moves *up* into the stack frame of the `main` function (or `_start`). If the function then tries to return (`ret`), it pops a return address (`lr`) that might be a user input value (e.g., `5`), causing a segmentation fault attempting to jump to address `0x5`.

### The Solution: The Safety Snapshot
To mitigate this, we treat the `sp` at the entry of `main` as a hard "Floor".

1.  **Snapshot**: On entry, we save the initial `sp` into a callee-saved register (`x24`). This is our immutable reference point.
2.  **Underflow Check**: Before any operation that pops `N` items (allocates `N * 16` bytes), we check: `(x24 - sp) >= (N * 16)`. If false, we panic.
3.  **Panic Restoration**: If an error occurs (Underflow, DivZero), we do not simply `exit`. We restore `sp` from `x24` (`mov sp, x24`). This resets the machine state to a safe, clean slate before returning to the OS, ensuring proper teardown.

---

## 2. "Bit-Blind" Polymorphism

How do you support both Integer and Floating Point types in a raw assembly environment without complex structures or object headers?

**Answer**: You don't "support" them. You ignore them.

### Data is just Data
The CPU has General Purpose registers (`x0-x30`) for integers and SIMD/FP registers (`d0-d31`) for floats. Moving data between them is expensive if done via memory. However, we can move raw bits directly:

```asm
fmov d0, x0  // Move 64 bits from Integer Reg to Float Reg (No conversion)
fmov x0, d0  // Move 64 bits from Float Reg to Integer Reg (No conversion)
```

### The Architecture
We store **everything** on the stack as 64-bit chunks. Use `x` registers for storage.
- If the user enters `5`, we store `0x0000000000000005`.
- If the user enters `1.0`, we parse it as a double and store the IEEE 754 bit pattern `0x3FF0000000000000`.

The stack is "Blind" to the type. It just holds 64-bit patterns.

### Operator-Driven Typing
The *operator* decides how to interpret the bits.
- `+` pops 64 bits, treats them as signed integers, adds them (`add`), and pushes the result.
- `f+` pops 64 bits, moves them to float registers (`fmov`), adds them as doubles (`fadd`), moves the result back (`fmov`), and pushes.

This allows for extreme simplicity. We don't need a `Type` tag for every stack item. The user is the type system.

---

## 3. The Price of Power (Explicit Casting)

The Bit-Blind approach creates a problem: Mixed-Mode Arithmetic.

If the stack has `5` (Int) and `2.5` (Float), and you run `f+`:
1.  `2.5` is loaded as `0x4004000000000000` (Valid Float).
2.  `5` is loaded as `0x0000000000000005`.
3.  `fadd` interprets `0x...5` as a sub-normal float (essentially `0.0` or even `NaN`).
4.  Result: Garbage.

### Rejection of Implicit Magic
High-level languages solve this with implicit casting (auto-promoting Int to Float). We rejected this. Implicit casting requires checking type tags (which we don't have) or guessing (which is dangerous).

### The Bridge Operators
Instead, we implemented explicit **Bridge Operators**:
- `flt`: "I know these bits are an Integer. Please convert them to a Float representation."
    - (`scvtf d0, x0`: Signed Convert to Float)
- `int`: "I know these bits are a Float. Please truncate them to an Integer."
    - (`fcvtzs x0, d0`: Float Convert to Zero-Signed)

### The Workflow
To add `5` and `2.5`:
```
5 flt 2.5 f+
```
`5` -> `flt` -> `5.0` (Float Bits) -> Stack.
Stack now has `5.0` (Float Bits) and `2.5` (Float Bits).
`f+` adds them correctly to `7.5`.

This forces the user to understand the difference between *the value 5* and *the floating point representation of 5*. It is less "user-friendly," but infinitely more "system-transparent."

---

## Conclusion

This calculator is not designed to be the easiest to use. It is designed to be the most honest. By exposing the stack pointer, treating data as raw bits, and forcing manual type conversion, it removes the layers of abstraction that usually hide the machine from the programmer.

It is a tool for those who want to see the bits.
