"""autovec.py - Detect missed auto-vectorization via static function analysis."""

from __future__ import annotations

# Instruction patterns that suggest vectorizable data processing
VECTORIZABLE_PATTERNS = [
    # Scalar float ops — most reliable signal
    "fadd.s", "fadd.d", "fsub.s", "fsub.d",
    "fmul.s", "fmul.d", "fdiv.s", "fdiv.d",
    "fmadd.s", "fmadd.d", "fmsub.s", "fmsub.d",
    "fnmadd.s", "fnmadd.d",
    "flw", "fld", "fsw", "fsd",
    # Memory patterns suggesting array iteration
    "lw", "ld", "lh", "lb",
    "sw", "sd", "sh", "sb",
]

# Branch mnemonics — presence suggests a loop exists
BRANCH_MNEMONICS = {
    "beq", "bne", "blt", "bge", "bltu", "bgeu",
    "j", "jal", "jalr",
}

# RVV prefix list — if any of these appear, function is already vectorized
VECTOR_PREFIXES = [
    "vadd", "vsub", "vmul", "vdiv", "vle", "vse",
    "vlse", "vsse", "vluxei", "vsuxei", "vset",
    "vmv", "vfadd", "vfsub", "vfmul", "vfdiv",
    "vfmacc", "vfmadd", "vbrev8", "vrev8", "vandn",
    "vghsh", "vaes", "vfncvt", "vfwcvt", "vfwmaccbf16",
    "czero",
]


def _has_vector(mnemonics: list) -> bool:
    return any(
        any(m.startswith(p) for p in VECTOR_PREFIXES)
        for m in mnemonics
    )


def _has_branch(mnemonics: list) -> bool:
    return any(m in BRANCH_MNEMONICS for m in mnemonics)


def _vectorizable_count(mnemonics: list) -> int:
    return sum(
        1 for m in mnemonics
        if any(m.startswith(p) for p in VECTORIZABLE_PATTERNS)
    )


def analyze_function(name: str, mnemonics: list) -> dict | None:
    """
    Analyze a single function for missed vectorization.

    Returns a dict describing the opportunity, or None if clean.
    A function is flagged only when ALL of:
      1. Has >= 10 instructions (small functions not worth flagging)
      2. Has at least one branch (loop potential)
      3. Has float or memory pattern instructions
      4. Has zero vector instructions
    """
    if len(mnemonics) < 10:
        return None
    if _has_vector(mnemonics):
        return None
    if not _has_branch(mnemonics):
        return None

    pat_count = _vectorizable_count(mnemonics)
    if pat_count == 0:
        return None

    if pat_count > 20:
        severity = "high"
    elif pat_count > 8:
        severity = "medium"
    else:
        severity = "low"

    return {
        "function":                  name,
        "instruction_count":         len(mnemonics),
        "has_loop":                  True,
        "vectorizable_pattern_count": pat_count,
        "vector_instruction_count":  0,
        "severity":                  severity,
        "reason": (
            f"{len(mnemonics)} instructions, "
            f"{pat_count} float/memory ops, "
            f"0 vector instructions"
        ),
    }


def analyze_binary(functions: dict) -> dict:
    """
    Analyze all functions from an objdump parse result.

    functions: {name: {"mnemonics": [...], "instruction_count": N}}
    Returns summary with list of opportunities.
    """
    opportunities = []
    clean = 0

    for name, info in functions.items():
        mnemonics = info.get("mnemonics", [])
        result = analyze_function(name, mnemonics)
        if result:
            opportunities.append(result)
        else:
            clean += 1

    # Sort by severity then pattern count
    sev_order = {"high": 0, "medium": 1, "low": 2}
    opportunities.sort(
        key=lambda x: (sev_order[x["severity"]], -x["vectorizable_pattern_count"])
    )

    return {
        "opportunities":    opportunities,
        "clean_functions":  clean,
        "total_functions":  clean + len(opportunities),
        "backend":          "objdump-static",
    }


def format_autovec_report(analysis: dict) -> str:
    """
    Render autovectorization analysis as text.
    Only shows HIGH and MEDIUM severity by default.
    """
    opps = [o for o in analysis["opportunities"]
            if o["severity"] in ("high", "medium")]

    if not opps:
        return ""

    sep = "-" * 58
    lines = [
        sep,
        "  Missed Vectorization Opportunities  (static analysis)",
        sep,
        f"  Analyzed {analysis['total_functions']} functions  "
        f"({len(analysis['opportunities'])} candidates, "
        f"{len(opps)} high/medium shown)",
        "",
    ]

    icons = {"high": "[!]", "medium": "[~]"}
    for opp in opps[:10]:  # cap at 10
        icon = icons[opp["severity"]]
        lines.append(
            f"  {icon}  {opp['function'][:42]:<42}"
            f"  {opp['severity'].upper()}"
        )
        lines.append(
            f"       {opp['reason']}"
        )
        lines.append("")

    if len(opps) > 10:
        lines.append(f"  ... {len(opps) - 10} more candidates not shown")
        lines.append("")

    lines += [
        "  Note: Static analysis only — may have false positives.",
        "  Verify with: gcc -fopt-info-vec-missed -O2 -march=rv64gcv",
        sep,
    ]
    return "\n".join(lines)
