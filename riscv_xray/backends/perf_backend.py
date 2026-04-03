"""perf_backend.py - Parse perf annotate --stdio output from real RISC-V hardware."""

from __future__ import annotations
import re
from pathlib import Path

# perf annotate --stdio line formats:
#   " 15.08  │       vadd.vv v8,v8,v16"
#   "  0.00  │       addi    sp,sp,-48"
#   "        │ 0000000000012340 <json_parse>:"
_FUNC_LINE = re.compile(r'│\s+[0-9a-f]+\s+<([^>]+)>:')
_INSN_LINE = re.compile(r'^(\s*[\d.]*)\s*│\s+(\w[\w.]*)')
_PERCENT   = re.compile(r'^\s*([\d.]+)')

_RISCV_MNEMONICS = {
    "addi", "add", "sub", "and", "or", "xor", "sll", "srl", "sra",
    "ld", "sd", "lw", "sw", "lh", "sh", "lb", "sb",
    "beq", "bne", "blt", "bge", "bltu", "bgeu",
    "jal", "jalr", "auipc", "lui",
    "vadd.vv", "vsetvli", "vle32.v", "vse32.v",
}

_X86_HINTS = {"mov", "push", "pop", "call", "ret", "lea", "xor", "cmp", "jmp", "je", "jne"}
_ARM_HINTS = {"ldr", "str", "ldp", "stp", "bl", "blr", "cbz", "cbnz"}


def parse_perf_annotate(text: str) -> dict:
    """
    Parse `perf annotate --stdio --no-source` output.

    Returns:
        {
          "backend": "perf-annotate",
          "mnemonics": [...],           # all mnemonics (unweighted)
          "weighted_mnemonics": [...],  # [(mnemonic, pct), ...]
          "functions": {
              name: {
                  "mnemonics": [...],
                  "weighted": [(mnemonic, pct), ...],
                  "total_samples": float,
              }
          },
          "total_sample_percent": float,
        }
    """
    functions = {}
    all_mnemonics = []
    all_weighted = []
    current = None

    for line in text.splitlines():
        # Function boundary
        m = _FUNC_LINE.search(line)
        if m:
            current = m.group(1)
            if current not in functions:
                functions[current] = {
                    "mnemonics": [],
                    "weighted": [],
                    "total_samples": 0.0,
                }
            continue

        if "│" not in line:
            continue

        # Instruction line
        m = _INSN_LINE.match(line)
        if not m:
            continue

        pct_str = m.group(1).strip()
        mnemonic = m.group(2)

        pct = 0.0
        if pct_str:
            pm = _PERCENT.match(pct_str)
            if pm:
                try:
                    pct = float(pm.group(1))
                except ValueError:
                    pct = 0.0

        all_mnemonics.append(mnemonic)
        all_weighted.append((mnemonic, pct))

        if current:
            functions[current]["mnemonics"].append(mnemonic)
            functions[current]["weighted"].append((mnemonic, pct))
            functions[current]["total_samples"] += pct

    total_pct = sum(p for _, p in all_weighted)

    return {
        "backend":             "perf-annotate",
        "mnemonics":           all_mnemonics,
        "weighted_mnemonics":  all_weighted,
        "functions":           functions,
        "total_sample_percent": round(total_pct, 2),
    }


def get_hot_mnemonics(parsed: dict, threshold: float = 0.1) -> list:
    """Return only mnemonics with sample percent >= threshold."""
    return [m for m, p in parsed["weighted_mnemonics"] if p >= threshold]


def get_all_mnemonics(parsed: dict) -> list:
    """
    Return all mnemonics weighted by sample percentage.

    A mnemonic at 15% appears ~15x more than one at 1%.
    Minimum 1 occurrence per mnemonic.
    """
    result = []
    for mnemonic, pct in parsed["weighted_mnemonics"]:
        count = max(1, round(pct))
        result.extend([mnemonic] * count)
    return result


def validate_perf_file(filepath: str) -> tuple:
    """
    Check if a file looks like valid perf annotate output.
    Returns (True, "") or (False, reason).
    """
    path = Path(filepath)
    if not path.exists():
        return False, f"File not found: {filepath}"

    try:
        text = path.read_text(errors="replace")
    except OSError as e:
        return False, str(e)

    if "│" not in text:
        return False, "No perf annotate separator (│) found — not perf output"

    has_hex = bool(re.search(r'[0-9a-f]{8,}', text))
    if not has_hex:
        return False, "No hex addresses found — not objdump/perf disassembly"

    has_func = bool(_FUNC_LINE.search(text))
    if not has_func:
        return False, "No function symbols found — run: perf annotate --stdio --no-source"

    return True, ""


def detect_risc_v(parsed: dict) -> bool:
    """
    Return True if mnemonics look like RISC-V (not x86 or ARM).
    """
    seen = set(parsed["mnemonics"][:200])  # sample first 200

    riscv_hits = len(seen & _RISCV_MNEMONICS)
    x86_hits   = len(seen & _X86_HINTS)
    arm_hits   = len(seen & _ARM_HINTS)

    if x86_hits > riscv_hits or arm_hits > riscv_hits:
        return False

    # RISC-V specific: addi is very common, jalr is always present
    if "addi" in seen or "jalr" in seen:
        return True

    return riscv_hits > 0
