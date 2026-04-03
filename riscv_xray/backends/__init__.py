"""backends/__init__.py - Unified backend interface for riscv-xray."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BackendResult:
    backend:     str         # "qemu", "objdump-static", "perf-annotate"
    mnemonics:   list        # flat mnemonic list for classifier
    weighted:    list        # [(mnemonic, weight), ...] — empty for QEMU/objdump
    functions:   dict        # {func_name: {...}} per-function breakdown
    source_file: str         # binary path or perf txt path
    warnings:    list = field(default_factory=list)
    is_hardware: bool = False   # True only for perf-annotate


def run_backend(source: str, backend: str = "auto", **kwargs) -> BackendResult:
    """
    Run the appropriate backend for a given source.

    backend="auto":  .txt/.data → perf; executable → objdump, fallback qemu
    backend="perf":  parse perf annotate text file
    backend="objdump": static disassembly
    backend="qemu":  existing QEMU runner
    """
    src = Path(source)

    if backend == "auto":
        if src.suffix in (".txt", ".data") or not _is_elf(source):
            backend = "perf"
        else:
            backend = "objdump"

    if backend == "perf":
        return _run_perf(source, **kwargs)
    elif backend == "objdump":
        return _run_objdump(source, **kwargs)
    elif backend == "qemu":
        return _run_qemu(source, **kwargs)
    else:
        raise ValueError(f"Unknown backend: {backend!r}. "
                         "Choose: auto, perf, objdump, qemu")


def get_backend_info(result: BackendResult) -> str:
    """One-line backend description for report headers."""
    if result.backend == "perf-annotate":
        total_pct = sum(p for _, p in result.weighted)
        return f"perf-annotate (real hardware, {total_pct:.1f}% samples)"
    elif result.backend == "objdump-static":
        return f"objdump-static ({len(result.mnemonics):,} instructions)"
    else:
        return f"{result.backend} ({len(result.mnemonics):,} instructions)"


# ── Internal runners ───────────────────────────────────────────────────────────

def _is_elf(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


def _run_perf(source: str, **kwargs) -> BackendResult:
    from . import perf_backend
    from pathlib import Path

    ok, reason = perf_backend.validate_perf_file(source)
    if not ok:
        raise RuntimeError(f"Invalid perf file: {reason}")

    text = Path(source).read_text(errors="replace")
    parsed = perf_backend.parse_perf_annotate(text)

    warnings = []
    if not perf_backend.detect_risc_v(parsed):
        warnings.append(
            "Warning: instructions do not look like RISC-V. "
            "Verify this profile was collected on a RISC-V system."
        )

    mnemonics = perf_backend.get_all_mnemonics(parsed)

    return BackendResult(
        backend="perf-annotate",
        mnemonics=mnemonics,
        weighted=parsed["weighted_mnemonics"],
        functions=parsed["functions"],
        source_file=source,
        warnings=warnings,
        is_hardware=True,
    )


def _run_objdump(source: str, **kwargs) -> BackendResult:
    from . import objdump_backend

    text = objdump_backend.disassemble(source)
    parsed = objdump_backend.parse_objdump(text)

    # Convert function dicts to classifier-compatible form
    functions = {
        name: {"mnemonics": info["mnemonics"],
               "instruction_count": info["instruction_count"]}
        for name, info in parsed["functions"].items()
    }

    return BackendResult(
        backend="objdump-static",
        mnemonics=parsed["mnemonics"],
        weighted=[],
        functions=functions,
        source_file=source,
        is_hardware=False,
    )


def _run_qemu(source: str, binary_args=None, timeout=60, **kwargs) -> BackendResult:
    import sys
    import os
    # Import from parent package
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
    from riscv_xray import runner

    mnemonics, mode = runner.run(source, binary_args or [], timeout=timeout)

    return BackendResult(
        backend=f"qemu-{mode}",
        mnemonics=mnemonics,
        weighted=[],
        functions={},
        source_file=source,
        is_hardware=False,
    )
