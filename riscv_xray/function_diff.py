"""function_diff.py - Per-function extension usage diff between two binaries."""

from __future__ import annotations
import subprocess
import re
import sys

from .classifier import classify
from .extensions import EXTENSION_ORDER

_FUNC_HEADER = re.compile(r'^[0-9a-f]+ <([^>]+)>:$')
_INSN_LINE   = re.compile(r'^\s+[0-9a-f]+:\s+(?:[0-9a-f]+ )+\s*(\w[\w.]*)')


def _parse_functions(binary_path: str) -> dict:
    """
    Run objdump -d on a binary and return {func_name: [mnemonic, ...]}.
    Returns empty dict if objdump is unavailable or fails.
    """
    try:
        r = subprocess.run(
            ["objdump", "-d", binary_path],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        print("  Warning: objdump not found — function diff unavailable.",
              file=sys.stderr)
        return {}
    except subprocess.TimeoutExpired:
        print("  Warning: objdump timed out.", file=sys.stderr)
        return {}

    if r.returncode != 0:
        return {}

    functions = {}
    current = None

    for line in r.stdout.splitlines():
        m = _FUNC_HEADER.match(line)
        if m:
            current = m.group(1)
            functions[current] = []
            continue
        if current:
            m = _INSN_LINE.match(line)
            if m:
                functions[current].append(m.group(1))

    return functions


def analyze_binary_functions(binary_path: str, min_insns: int = 5) -> dict:
    """
    Classify instructions per function in a binary.

    Returns {func_name: classify_data_dict} for functions with
    at least min_insns instructions.
    """
    funcs = _parse_functions(binary_path)
    results = {}
    for name, mnemonics in funcs.items():
        if len(mnemonics) < min_insns:
            continue
        results[name] = classify(mnemonics)
    return results


def diff_functions(
    funcs1: dict,
    funcs2: dict,
    name1: str,
    name2: str,
    min_delta: float = 5.0,
    top_n: int = 20,
) -> str:
    """
    Produce a human-readable per-function extension diff.

    Only shows functions with at least one extension change >= min_delta pp.
    Caps output at top_n most-changed functions.
    """
    sep = "-" * 68
    lines = [
        sep,
        "  Function-Level Extension Diff",
        sep,
        f"  Baseline:    {name1}",
        f"  Comparison:  {name2}",
        f"  Threshold:   changes >= {min_delta:.0f}pp",
        "",
    ]

    all_funcs = sorted(set(funcs1) | set(funcs2))
    added   = [f for f in all_funcs if f not in funcs1]
    removed = [f for f in all_funcs if f not in funcs2]
    changed = []

    for func in all_funcs:
        d1 = funcs1.get(func)
        d2 = funcs2.get(func)
        if d1 is None or d2 is None:
            continue

        func_deltas = []
        for ext in EXTENSION_ORDER:
            if ext in ("Base",):
                continue
            p1 = d1.get(ext, {}).get("percentage", 0.0)
            p2 = d2.get(ext, {}).get("percentage", 0.0)
            delta = p2 - p1
            if abs(delta) >= min_delta:
                func_deltas.append((ext, delta))

        if func_deltas:
            total1 = d1.get("_total", 0)
            total2 = d2.get("_total", 0)
            changed.append((func, func_deltas, total1, total2))

    # Sort by magnitude of largest single change
    changed.sort(key=lambda x: max(abs(d) for _, d in x[1]), reverse=True)

    if added:
        lines.append(f"  New functions ({len(added)}):")
        for f in added[:5]:
            lines.append(f"    [+] {f}")
        if len(added) > 5:
            lines.append(f"        ... and {len(added) - 5} more")
        lines.append("")

    if removed:
        lines.append(f"  Removed functions ({len(removed)}):")
        for f in removed[:5]:
            lines.append(f"    [-] {f}")
        if len(removed) > 5:
            lines.append(f"        ... and {len(removed) - 5} more")
        lines.append("")

    if changed:
        lines.append(f"  Changed functions ({len(changed)} with >= {min_delta:.0f}pp delta):")
        lines.append("")
        for func, deltas, t1, t2 in changed[:top_n]:
            delta_strs = []
            for ext, d in sorted(deltas, key=lambda x: abs(x[1]), reverse=True):
                arrow = "+" if d > 0 else ""
                delta_strs.append(f"{ext} {arrow}{d:.1f}pp")
            lines.append(
                f"  {func[:42]:<42}  {', '.join(delta_strs)}"
            )
            lines.append(
                f"  {'':42}  ({t1:,} → {t2:,} insns)"
            )
            lines.append("")
        if len(changed) > top_n:
            lines.append(
                f"  ... {len(changed) - top_n} more functions changed "
                f"(showing top {top_n} by delta magnitude)"
            )
    elif not added and not removed:
        lines.append(
            f"  No per-function changes >= {min_delta:.0f}pp between binaries."
        )

    lines += ["", sep]
    return "\n".join(lines)
