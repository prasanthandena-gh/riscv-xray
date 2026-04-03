"""hwprobe.py - Generate riscv_hwprobe runtime detection code snippets."""

from __future__ import annotations

# Maps extension name -> RISCV_HWPROBE constant
HWPROBE_CONSTANTS = {
    "RVV":      "RISCV_HWPROBE_EXT_ZVE64X",
    "Zba":      "RISCV_HWPROBE_EXT_ZBA",
    "Zbb":      "RISCV_HWPROBE_EXT_ZBB",
    "Zicond":   "RISCV_HWPROBE_EXT_ZICOND",
    "Zvbb":     "RISCV_HWPROBE_EXT_ZVBB",
    "Zvkng":    "RISCV_HWPROBE_EXT_ZVKNG",
    "Zvfhmin":  "RISCV_HWPROBE_EXT_ZVFHMIN",
    "Zvfh":     "RISCV_HWPROBE_EXT_ZVFH",
    "Zvfbfmin": "RISCV_HWPROBE_EXT_ZVFBFMIN",
    "Zvfbfwma": "RISCV_HWPROBE_EXT_ZVFBFWMA",
    "Zbc":      "RISCV_HWPROBE_EXT_ZBC",
    "Zicntr":   None,   # not exposed via hwprobe
    "Zcb":      None,
    "Zfa":      None,
}

_SNIPPET_TEMPLATE = """\
// Detect {ext} at runtime (Linux 6.4+ / riscv_hwprobe syscall)
#include <sys/riscv_hwprobe.h>
#include <stdbool.h>

bool has_{func_name}(void) {{
    struct riscv_hwprobe probe = {{
        .key = RISCV_HWPROBE_KEY_IMA_EXT_0
    }};
    if (riscv_hwprobe(&probe, 1, 0, NULL, 0) != 0)
        return false;
    return (probe.value & {constant}) != 0;
}}

// Usage:
// if (has_{func_name}()) {{
//     /* fast {ext} path */
// }} else {{
//     /* fallback path */
// }}
"""


def generate_hwprobe_snippet(extension_name: str) -> str | None:
    """
    Return a C code snippet for runtime detection of the given extension.
    Returns None if no hwprobe constant is known.
    """
    constant = HWPROBE_CONSTANTS.get(extension_name)
    if not constant:
        return None
    func_name = extension_name.lower().replace(".", "_").replace("+", "plus")
    return _SNIPPET_TEMPLATE.format(
        ext=extension_name,
        func_name=func_name,
        constant=constant,
    )


def generate_snippets_for_missing(missing_extensions: list) -> str:
    """
    Generate hwprobe snippets for all missing extensions that have constants.
    Returns formatted string with all snippets.
    """
    snippets = []
    for ext in missing_extensions:
        s = generate_hwprobe_snippet(ext)
        if s:
            snippets.append(s)

    if not snippets:
        return ""

    header = (
        "Runtime Detection Code (Linux 6.4+ riscv_hwprobe)\n"
        "-" * 58 + "\n"
        "These snippets let your binary work on both\n"
        "old hardware (fallback) and new hardware (fast path).\n"
    )
    return header + "\n".join(snippets)


def format_hwprobe_section(missing: list) -> str | None:
    """
    Return a formatted hwprobe section for the report, or None if nothing to show.
    """
    content = generate_snippets_for_missing(missing)
    if not content:
        return None

    sep = "-" * 58
    lines = [
        sep,
        "  Runtime Detection Snippets",
        sep,
        "  Require Linux 6.4+ with riscv_hwprobe syscall.",
        "  Enables fast paths on new hardware with graceful fallback.",
        "",
    ]
    for ext in missing:
        s = generate_hwprobe_snippet(ext)
        if s:
            # Indent snippet
            for line in s.splitlines():
                lines.append("  " + line)
            lines.append("")
    lines.append(sep)
    return "\n".join(lines)
