"""recommender.py - Generate actionable recommendations from classification data."""

from __future__ import annotations
from .extensions import EXTENSIONS, THRESHOLDS, RVA23_FLAG, EXTENSION_ORDER


def recommend(data: dict, binary_name: str) -> list:
    """
    Generate a list of recommendation dicts based on classified extension data.

    Each recommendation has: icon, title, detail, action (may be None).
    """
    recommendations = []

    rvv = data.get("RVV", {})
    rvv_pct = rvv.get("percentage", 0.0)

    base = data.get("Base", {})
    base_pct = base.get("percentage", 0.0)

    # Vector usage assessment
    if rvv_pct > THRESHOLDS["heavy_use"]:
        recommendations.append({
            "icon": "[+]",
            "title": "Vector usage is strong",
            "detail": (
                f"'{binary_name}' uses RVV at {rvv_pct:.1f}%. "
                "Your app is well-suited for RISC-V hardware with RVV support."
            ),
            "action": None,
        })
    elif rvv_pct > THRESHOLDS["light_use"]:
        recommendations.append({
            "icon": "[~]",
            "title": "Moderate vector usage detected",
            "detail": (
                f"'{binary_name}' uses RVV at {rvv_pct:.1f}%. "
                "There may be room to increase vectorization."
            ),
            "action": f"Try: {EXTENSIONS['RVV']['compile_flag']} -O3 -ftree-vectorize",
        })
    elif rvv_pct == 0.0:
        recommendations.append({
            "icon": "[!]",
            "title": "No vector instructions found",
            "detail": (
                f"'{binary_name}' has no RVV instructions. "
                "If you process arrays, images, or run ML workloads, "
                "you may be leaving performance on the table."
            ),
            "action": f"Recompile with: {EXTENSIONS['RVV']['compile_flag']} to unlock Vector.",
        })
    else:
        recommendations.append({
            "icon": "[~]",
            "title": f"Trace vector usage detected ({rvv_pct:.1f}%)",
            "detail": (
                f"'{binary_name}' has RVV instructions but they are a tiny fraction. "
                "In static mode this is expected when libc dominates — "
                "your vector code may be a larger share of actual runtime."
            ),
            "action": "For runtime frequency, use dynamic profiling (requires QEMU with plugin support).",
        })

    # Scalar-heavy warning
    if base_pct > 80:
        recommendations.append({
            "icon": "[!]",
            "title": "Most instructions are scalar",
            "detail": (
                f"{base_pct:.1f}% of instructions are base scalar. "
                "Check your compiler flags — you may not be targeting the right RISC-V profile."
            ),
            "action": "Try: -march=rv64gcv -O2 -ftree-vectorize",
        })

    # Flag unused extensions (mandatory ones only, skip security + optional)
    mandatory_unused = []
    mandatory_exts = [
        e for e in EXTENSION_ORDER
        if e not in ("Base", "RVV")
        and EXTENSIONS.get(e, {}).get("rva23_status") == "mandatory"
        and not EXTENSIONS.get(e, {}).get("security_relevant", False)
    ]
    for ext_name in mandatory_exts:
        if data.get(ext_name, {}).get("status") == "unused":
            mandatory_unused.append(ext_name)

    if mandatory_unused:
        recommendations.append({
            "icon": "[~]",
            "title": f"Mandatory RVA23 extensions unused: {', '.join(mandatory_unused)}",
            "detail": (
                f"{', '.join(mandatory_unused)} are mandatory in RVA23 "
                f"but '{binary_name}' isn't using them."
            ),
            "action": f"If relevant to your workload, recompile with: {RVA23_FLAG}",
        })

    # Always recommend full RVA23 profile
    recommendations.append({
        "icon": "[!]",
        "title": "Target RVA23 for maximum hardware compatibility",
        "detail": (
            "The RVA23 profile ensures your binary runs optimally "
            "on all conforming RISC-V hardware."
        ),
        "action": f"Compile with: {RVA23_FLAG}",
    })

    return recommendations
