"""profiler.py - Bridge to riscv-application-profiler (optional backend)."""

from __future__ import annotations
import importlib.util
import subprocess
import sys
from pathlib import Path


def check_available() -> bool:
    """Return True if riscv-application-profiler is installed."""
    return importlib.util.find_spec("riscv_application_profiler") is not None


def get_backend() -> str:
    """Return the name of the active analysis backend."""
    if check_available():
        return "riscv-application-profiler"
    return "riscv-xray-builtin"


def run_profiler(log_path: str) -> dict | None:
    """
    Run riscv-application-profiler on a log file if available.

    Returns its output as a dict, or None if not installed.
    """
    if not check_available():
        print(
            "  Note: riscv-application-profiler not installed. "
            "Using built-in analysis.\n"
            "  For deeper metrics: pip install riscv-application-profiler"
        )
        return None

    print(
        "  Using riscv-application-profiler for instruction analysis.\n"
        "  See: https://github.com/mahendraVamshi/riscv-application-profiler"
    )

    log = Path(log_path)
    if not log.exists():
        return None

    try:
        result = subprocess.run(
            [sys.executable, "-m", "riscv_application_profiler", str(log)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            text=True,
        )
        if result.returncode == 0:
            # Parse the profiler output - return raw stdout for now
            return {"raw_output": result.stdout, "source": "riscv-application-profiler"}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None
