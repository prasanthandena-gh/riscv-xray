"""accuracy.py - QEMU profiling accuracy warnings."""

from __future__ import annotations

_STATIC_WARNING = """\
  Accuracy Note (static mode)
  -------------------------------------------------------
  Results were collected via static disassembly (in_asm),
  NOT dynamic execution. This means:

    [!] Dead code counts — unreachable branches are included
    [!] Loop counts are NOT weighted — every instruction
        counted once regardless of how many times it runs
    [!] Percentages reflect code density, not runtime cost

  For accurate runtime frequency use dynamic mode:
    Build QEMU with --enable-plugins and rebuild xray_plugin.so
    or use: riscv-xray check  (to see if dynamic mode is available)

  Static mode is still useful for: code size analysis,
  extension presence detection, and quick profiling of
  small standalone binaries."""


def format_accuracy_warning(mode: str) -> str | None:
    """
    Return an accuracy warning section if mode warrants one.

    Returns None for dynamic mode (no warning needed).
    """
    if mode == "static":
        sep = "-" * 58
        return sep + "\n" + _STATIC_WARNING + "\n" + sep
    return None
