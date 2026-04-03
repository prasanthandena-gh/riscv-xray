"""security.py - CFI and security extension analysis."""

from __future__ import annotations

SECURITY_EXTENSIONS = ["Zicfilp", "Zicfiss"]

MARKET_CFI_REQUIREMENTS = {
    "automotive": {
        "required": True,
        "standard": "ISO 26262 ASIL-D",
        "note": "CFI required for safety-critical systems",
    },
    "server": {
        "required": True,
        "standard": "Production hardening best practice",
        "note": "Shadow stack recommended for server workloads",
    },
    "embedded": {
        "required": False,
        "standard": "Optional",
        "note": "CFI optional for most embedded workloads",
    },
    "desktop": {
        "required": False,
        "standard": "Recommended",
        "note": "CFI improves security but not strictly required",
    },
}


def analyze_security(data: dict) -> dict:
    """
    Analyze CFI and security extension usage.

    Returns cfi_status, per-market impact, and compile flag.
    """
    filp = data.get("Zicfilp", {}).get("percentage", 0.0) > 0
    fiss = data.get("Zicfiss", {}).get("percentage", 0.0) > 0

    if filp and fiss:
        cfi_status = "full"
    elif filp or fiss:
        cfi_status = "partial"
    else:
        cfi_status = "absent"

    market_impact = {}
    for market, req in MARKET_CFI_REQUIREMENTS.items():
        if req["required"] and cfi_status == "absent":
            status = "FAIL"
        elif req["required"] and cfi_status == "partial":
            status = "WARN"
        else:
            status = "OK"
        market_impact[market] = {
            "required": req["required"],
            "standard": req["standard"],
            "note": req["note"],
            "status": status,
        }

    return {
        "zicfilp_active": filp,
        "zicfiss_active": fiss,
        "cfi_status":     cfi_status,
        "compile_flag":   "-mbranch-protection=standard",
        "market_impact":  market_impact,
    }


def format_security_report(analysis: dict) -> str:
    """Render the security analysis as text."""
    sep = "-" * 58

    status_map = {
        "full":    "[+] Full CFI",
        "partial": "[~] Partial CFI",
        "absent":  "[-] Not detected",
    }
    overall = status_map[analysis["cfi_status"]]

    filp_icon = "[+]" if analysis["zicfilp_active"] else "[-]"
    fiss_icon = "[+]" if analysis["zicfiss_active"] else "[-]"

    lines = [
        sep,
        "  Security Extension Analysis",
        sep,
        f"  CFI (Control Flow Integrity): {overall}",
        "",
        f"  Zicfilp  Forward-edge CFI (landing pads)   {filp_icon}",
        f"  Zicfiss  Return CFI (shadow stack)          {fiss_icon}",
        "",
        "  Impact by market:",
    ]

    icons = {"FAIL": "[!]", "WARN": "[~]", "OK": "[ ]"}
    for market, info in analysis["market_impact"].items():
        icon = icons[info["status"]]
        lines.append(
            f"  {icon}  {market.capitalize():<12} {info['standard']}"
        )
        if info["status"] in ("FAIL", "WARN"):
            lines.append(f"              {info['note']}")

    if analysis["cfi_status"] != "full":
        lines += [
            "",
            "  To enable CFI:",
            f"    Compile with: {analysis['compile_flag']}",
            "    Requires:     GCC 14+ or LLVM 18+ with RISC-V CFI support",
            "    Hardware:     RVA23-compliant silicon",
            "",
            "  Note: CFI instructions are injected by the compiler,",
            "  not written manually. Check your compiler version first.",
        ]

    lines.append(sep)
    return "\n".join(lines)
