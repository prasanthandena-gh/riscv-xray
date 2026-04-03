"""runner.py - Run a RISC-V binary under QEMU and capture instruction mnemonics."""

from __future__ import annotations
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Matches lines like:  0x0000000000010380:  fe010113          addi   sp,sp,-32
_IN_ASM_RE = re.compile(r"^\s*0x[0-9a-f]+:\s+[0-9a-f]+\s+(\w+)")


def _find_plugin() -> Path:
    candidates = [
        Path(__file__).parent.parent / "plugin" / "xray_plugin.so",
        Path("plugin/xray_plugin.so"),
        Path("xray_plugin.so"),
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    return None


def _plugin_supported() -> bool:
    """Return True if this QEMU build was compiled with TCG plugin support."""
    result = subprocess.run(
        ["qemu-riscv64", "-d", "help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=5,
    )
    output = result.stdout + result.stderr
    return "plugin" in output


def _run_with_plugin(binary: Path, plugin: Path, args: list, timeout: int):
    """Run binary under QEMU using the TCG plugin. Returns (mnemonics, mode)."""
    cmd = [
        "qemu-riscv64",
        "-plugin", str(plugin),
        "-d", "plugin",
        str(binary),
    ] + args

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        text=True,
    )

    output_lines = result.stdout.splitlines() + result.stderr.splitlines()
    mnemonics = []
    for line in output_lines:
        if line.startswith("XRAY_INSN:"):
            m = line[len("XRAY_INSN:"):]
            if m:
                mnemonics.append(m)
        elif line == "XRAY_DONE":
            break

    return mnemonics, "dynamic"


def _run_with_in_asm(binary: Path, args: list, timeout: int):
    """
    Fallback: run with -d in_asm to capture disassembly.

    Note: -d in_asm logs each translation block once (not per-execution).
    Counts reflect unique instruction occurrences in translated code,
    not runtime execution frequency.
    """
    cmd = [
        "qemu-riscv64",
        "-d", "in_asm",
        "-D", "/dev/stderr",
        str(binary),
    ] + args

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        text=True,
    )

    mnemonics = []
    for line in result.stderr.splitlines():
        m = _IN_ASM_RE.match(line)
        if m:
            mnemonics.append(m.group(1))

    return mnemonics, "static"


def run(binary_path: str, args: list = None, timeout: int = 60):
    """
    Run a RISC-V binary under QEMU and return (mnemonics, mode).

    Tries TCG plugin first; falls back to -d in_asm if plugins are not
    compiled into this QEMU build.

    Returns:
        (list[str], str): mnemonics list and mode ("dynamic" or "static")
    """
    if args is None:
        args = []

    if shutil.which("qemu-riscv64") is None:
        raise RuntimeError(
            "qemu-riscv64 not found. Install with:\n"
            "  sudo apt install qemu-user"
        )

    binary = Path(binary_path)
    if not binary.exists():
        raise RuntimeError(f"Binary not found: {binary_path}")

    print("  Running under QEMU...", file=sys.stderr)

    try:
        plugin = _find_plugin()
        if plugin and _plugin_supported():
            return _run_with_plugin(binary, plugin, [str(a) for a in args], timeout)
        else:
            if plugin is None:
                print("  Note: xray_plugin.so not found, using -d in_asm fallback.", file=sys.stderr)
            else:
                print("  Note: QEMU plugins not compiled in, using -d in_asm fallback.", file=sys.stderr)
            print("        Counts reflect unique instructions in code, not execution frequency.", file=sys.stderr)
            return _run_with_in_asm(binary, [str(a) for a in args], timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"QEMU timed out after {timeout}s. Use --timeout to increase."
        )
