"""objdump_backend.py - Static RISC-V binary analysis via objdump."""

from __future__ import annotations
import re
import shutil
import subprocess
import sys
from pathlib import Path

_FUNC_HEADER = re.compile(r'^[0-9a-f]+ <([^>]+)>:$')
_INSN_LINE   = re.compile(r'^\s+[0-9a-f]+:\s+(\w[\w.]*)')

_OBJDUMP_CANDIDATES = [
    "riscv64-linux-gnu-objdump",
    "riscv64-unknown-linux-gnu-objdump",
    "riscv64-unknown-elf-objdump",
    "objdump",
]


def check_objdump() -> tuple:
    """
    Find a RISC-V capable objdump binary.
    Returns (True, path) if found, (False, "") if not.
    """
    for candidate in _OBJDUMP_CANDIDATES:
        path = shutil.which(candidate)
        if path:
            return True, path
    return False, ""


def is_riscv_binary(binary_path: str) -> tuple:
    """
    Check if a binary is a RISC-V ELF.
    Returns (True, arch_string) or (False, actual_arch).
    """
    try:
        r = subprocess.run(
            ["file", binary_path],
            capture_output=True, text=True, timeout=5,
        )
        out = r.stdout.lower()
        if "riscv" in out or "risc-v" in out:
            return True, "riscv64"
        # Try to extract actual arch for better error messages
        for hint in ("x86-64", "x86_64", "arm64", "aarch64", "arm"):
            if hint in out:
                return False, hint
        return False, "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "unknown"


def disassemble(binary_path: str) -> str:
    """
    Run objdump -d on a RISC-V binary.
    Returns stdout string.
    Raises RuntimeError with a clear message on failure.
    """
    if not Path(binary_path).exists():
        raise RuntimeError(f"Binary not found: {binary_path}")

    found, objdump_path = check_objdump()
    if not found:
        raise RuntimeError(
            "No RISC-V objdump found. Install with:\n"
            "  sudo apt install binutils-riscv64-linux-gnu"
        )

    ok, arch = is_riscv_binary(binary_path)
    if not ok:
        raise RuntimeError(
            f"Not a RISC-V binary (detected: {arch}). "
            f"riscv-xray only supports RISC-V ELF binaries."
        )

    try:
        r = subprocess.run(
            [objdump_path, "-d", "--no-show-raw-insn", binary_path],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"objdump timed out on {binary_path}")

    if r.returncode != 0:
        raise RuntimeError(
            f"objdump failed (exit {r.returncode}):\n{r.stderr[:200]}"
        )

    return r.stdout


def parse_objdump(text: str) -> dict:
    """
    Parse objdump -d output into structured data.

    Returns:
        {
          "backend": "objdump-static",
          "mnemonics": [...],
          "functions": {name: {"mnemonics": [...], "instruction_count": N}},
          "total_instructions": N,
          "is_weighted": False,
        }
    """
    functions = {}
    all_mnemonics = []
    current = None

    for line in text.splitlines():
        # Function header: "0000000000012340 <name>:"
        m = _FUNC_HEADER.match(line.strip())
        if m:
            current = m.group(1)
            if current not in functions:
                functions[current] = {"mnemonics": [], "instruction_count": 0}
            continue

        if current is None:
            continue

        # Instruction line: "   12340:   addi   sp,sp,-48"
        m = _INSN_LINE.match(line)
        if m:
            mnemonic = m.group(1)
            functions[current]["mnemonics"].append(mnemonic)
            functions[current]["instruction_count"] += 1
            all_mnemonics.append(mnemonic)

    return {
        "backend":            "objdump-static",
        "mnemonics":          all_mnemonics,
        "functions":          functions,
        "total_instructions": len(all_mnemonics),
        "is_weighted":        False,
    }


def get_mnemonics(parsed: dict) -> list:
    """Return flat list of all mnemonics from a parsed objdump result."""
    return parsed["mnemonics"]
