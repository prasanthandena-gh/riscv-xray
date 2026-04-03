"""gen_stub.py - Generates C intrinsic stubs for custom RISC-V instruction candidates."""

from __future__ import annotations
from .patterns import CUSTOM_OPCODE_SPACE

_DOMAIN_PARAMS = {
    "ML inference":      "float *out, const float *a, const float *b, size_t n",
    "signal processing": "float *out, const float *a, const float *b, size_t n",
    "image processing":  "uint8_t *out, const uint8_t *in, uint8_t threshold, size_t n",
    "cryptography":      "uint32_t *state, const uint32_t *key",
    "embedded":          "void *out, const void *in, size_t n",
}
_DEFAULT_PARAMS = "void *out, const void *in, size_t n"

_DOMAIN_INCLUDES = {
    "ML inference":      "#include <stddef.h>\n#include <stdint.h>",
    "signal processing": "#include <stddef.h>\n#include <stdint.h>",
    "image processing":  "#include <stdint.h>\n#include <stddef.h>",
    "cryptography":      "#include <stdint.h>",
    "embedded":          "#include <stddef.h>\n#include <stdint.h>",
}
_DEFAULT_INCLUDES = "#include <stdint.h>"

_OPCODE_NUM = {
    "custom-0": ("0x0B", "0"),
    "custom-1": ("0x2B", "1"),
    "custom-2": ("0x5B", "2"),
    "custom-3": ("0x7B", "3"),
}


def find_function_pattern(binary_path: str, function_name: str):
    """
    Run hotspot.analyze on binary_path and return the HotspotCandidate
    for function_name, or None if not found.
    """
    from .hotspot import analyze
    report = analyze(binary_path)
    for candidate in report.candidates:
        if candidate.function_name == function_name:
            return candidate
    return None


def generate_stub(candidate, opcode_slot: str = "custom-0") -> str:
    """
    Generate a C header string for a custom instruction stub.
    """
    pattern = candidate.pattern
    name_upper = pattern["name"].upper()
    hint_lower = pattern["custom_opcode_hint"].lower()
    hint_upper = pattern["custom_opcode_hint"].upper()
    opcode_desc = CUSTOM_OPCODE_SPACE.get(opcode_slot, opcode_slot)
    opcode_hex, opcode_num = _OPCODE_NUM.get(opcode_slot, ("0x0B", "0"))

    domain = pattern.get("domain", "embedded")
    params = _DOMAIN_PARAMS.get(domain, _DEFAULT_PARAMS)
    includes = _DOMAIN_INCLUDES.get(domain, _DEFAULT_INCLUDES)

    sequence_lines = "\n".join(
        f" *     {step}" for step in pattern["sequence"]
    )

    stub = f"""\
/*
 * riscv-xray custom instruction stub
 * Generated for: {candidate.function_name}
 * Pattern: {pattern['display_name']}
 * Opcode space: {opcode_slot} ({opcode_desc})
 *
 * This stub shows the developer-facing API for a hypothetical
 * custom instruction that fuses the {pattern['name']} pattern.
 *
 * Estimated benefit: ~{candidate.estimated_reduction}% instruction reduction
 *                    in {candidate.function_name}
 *
 * To implement this instruction you need:
 *   1. Architecture description: define in CodAL or Sail
 *   2. Compiler intrinsic: add to GCC/LLVM backend
 *   3. Simulator: patch QEMU to recognise the opcode
 *   4. Verify with: riscv-xray profile --extension ./my_ext.so <binary>
 */

#ifndef RISCV_CUSTOM_{name_upper}_H
#define RISCV_CUSTOM_{name_upper}_H

{includes}

/*
 * {hint_upper}: fused {pattern['display_name']}
 *
 * Fuses this instruction sequence:
{sequence_lines}
 *
 * Into a single opcode, saving ~{pattern['reduction_estimate']}% of instructions
 * in workloads with this pattern.
 */
static inline void __riscv_{hint_lower}(
    {params}
) {{
    /*
     * Inline assembly stub — replace {opcode_hex} with actual encoding
     * after implementing the instruction in your toolchain.
     *
     * .insn r CUSTOM_{opcode_num}, <funct3>, <funct7>, rd, rs1, rs2
     */
    __asm__ volatile (
        ".insn r {opcode_hex}, 0x0, 0x0, zero, zero, zero  /* placeholder */"
        :
        :
        : "memory"
    );
}}

#endif /* RISCV_CUSTOM_{name_upper}_H */
"""
    return stub


def write_stub(candidate, output_path: str, opcode_slot: str = "custom-0") -> str:
    """
    Generate and write a C header stub to output_path.
    Returns the output_path.
    """
    content = generate_stub(candidate, opcode_slot)
    with open(output_path, "w") as f:
        f.write(content)
    print(f"  Written: {output_path}")
    return output_path
