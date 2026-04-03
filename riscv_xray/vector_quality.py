"""vector_quality.py - Analyze vector instruction quality metrics."""

from __future__ import annotations

VECTOR_CATEGORIES = {
    "vsetvl": ["vsetvli", "vsetvl", "vsetivli"],
    "vload":  ["vle8", "vle16", "vle32", "vle64",
               "vlse8", "vlse16", "vlse32", "vlse64",
               "vluxei8", "vluxei16", "vluxei32", "vluxei64",
               "vloxei8", "vloxei16", "vloxei32", "vloxei64"],
    "vstore": ["vse8", "vse16", "vse32", "vse64",
               "vsse8", "vsse16", "vsse32", "vsse64",
               "vsuxei8", "vsuxei16", "vsuxei32", "vsuxei64",
               "vsoxei8", "vsoxei16", "vsoxei32", "vsoxei64"],
    "vcompute": [
        "vadd", "vsub", "vmul", "vdiv", "vrem",
        "vfadd", "vfsub", "vfmul", "vfdiv",
        "vfmacc", "vfmadd", "vfmsac", "vfmsub",
        "vfnmacc", "vfnmadd", "vfnmsac", "vfnmsub",
        "vfwmacc", "vfwmsac", "vfwnmacc", "vfwnmsac",
        "vsadd", "vssub", "vsmul",
        "vand", "vor", "vxor", "vsll", "vsrl", "vsra",
        "vmin", "vmax", "vminu", "vmaxu",
    ],
    "vmove":  ["vmv", "vmerge"],
    "vmask":  ["vmseq", "vmsne", "vmsltu", "vmslt",
               "vmsleu", "vmsle", "vmsgtu", "vmsgt",
               "vmand", "vmnand", "vmandnot",
               "vmor",  "vmnor",  "vmornot", "vmxor", "vmxnor"],
}


def _categorize(mnemonic: str) -> str:
    """Return the vector category for a mnemonic, or None."""
    for cat, prefixes in VECTOR_CATEGORIES.items():
        if any(mnemonic.startswith(p) for p in prefixes):
            return cat
    return None


def analyze_vector_quality(mnemonics: list) -> dict:
    """
    Analyze vector instruction quality from a mnemonic list.

    Returns metrics including vsetvl ratio, memory ratio, VLEN utilization,
    quality score, and a list of issues.
    """
    rvv_mnemonics = [m for m in mnemonics if _categorize(m) is not None]
    total_rvv = len(rvv_mnemonics)

    if total_rvv == 0:
        return {
            "total_rvv": 0,
            "vsetvl_count": 0, "vsetvl_ratio": 0.0,
            "vload_count": 0,  "vstore_count": 0, "memory_ratio": 0.0,
            "compute_count": 0, "compute_ratio": 0.0,
            "estimated_vlen_bits": 0, "vlen_utilization": 0.0,
            "quality_score": 0,
            "issues": [],
        }

    cats = {"vsetvl": 0, "vload": 0, "vstore": 0, "vcompute": 0,
            "vmove": 0, "vmask": 0}
    elem_widths = {"8": 0, "16": 0, "32": 0, "64": 0}

    for m in rvv_mnemonics:
        cat = _categorize(m)
        if cat in cats:
            cats[cat] += 1
        # Estimate element width from vle/vse suffix
        for w in ["64", "32", "16", "8"]:
            if w in m:
                elem_widths[w] += 1
                break

    vsetvl_count  = cats["vsetvl"]
    vload_count   = cats["vload"]
    vstore_count  = cats["vstore"]
    compute_count = cats["vcompute"]

    vsetvl_ratio  = round(vsetvl_count  / total_rvv * 100, 1)
    memory_ratio  = round((vload_count + vstore_count) / total_rvv * 100, 1)
    compute_ratio = round(compute_count / total_rvv * 100, 1)

    # VLEN estimation: assume VLEN=128 bits (QEMU default), estimate utilization
    dominant_width = max(elem_widths, key=elem_widths.get)
    width_to_bits = {"8": 8, "16": 16, "32": 32, "64": 64}
    elem_bits = width_to_bits.get(dominant_width, 32)
    vlen_bits = 128  # QEMU default
    # Elements per register = VLEN / elem_bits
    # Utilization = how much of vector register width is filled
    vlen_utilization = round(min(100.0, (elem_bits / 64) * 100), 1)
    estimated_vlen = elem_bits * 2  # rough estimate of effective usage

    # Build issues
    issues = []

    if vsetvl_ratio > 15:
        issues.append({
            "type": "high_vsetvl",
            "severity": "warning",
            "message": (
                f"vsetvli ratio is {vsetvl_ratio:.1f}% — high overhead. "
                "Ideal < 5%. Frequent vector length resets indicate short, "
                "non-amortized loops."
            ),
            "action": "Use longer loop bodies or strip-mine. Try: -mrvv-max-lmul=dynamic",
        })
    elif vsetvl_ratio > 5:
        issues.append({
            "type": "moderate_vsetvl",
            "severity": "info",
            "message": (
                f"vsetvli ratio is {vsetvl_ratio:.1f}% — moderate overhead."
            ),
            "action": None,
        })

    if memory_ratio > 40:
        issues.append({
            "type": "memory_bound",
            "severity": "info",
            "message": (
                f"{memory_ratio:.1f}% of vector instructions are memory ops. "
                "Workload appears memory-bandwidth bound."
            ),
            "action": "Consider data layout optimization or prefetching.",
        })

    if vlen_utilization < 50 and total_rvv > 10:
        issues.append({
            "type": "low_vlen",
            "severity": "info",
            "message": (
                f"Estimated VLEN utilization ~{vlen_utilization:.0f}%. "
                "Wider element types or data packing could improve throughput."
            ),
            "action": "Consider using 32-bit or 64-bit element types.",
        })

    # Quality score
    score = 100
    if vsetvl_ratio > 15:
        score -= 20
    elif vsetvl_ratio > 5:
        score -= 10
    if memory_ratio > 40:
        score -= 15
    if vlen_utilization < 50:
        score -= 5
    score = max(0, score)

    return {
        "total_rvv":          total_rvv,
        "vsetvl_count":       vsetvl_count,
        "vsetvl_ratio":       vsetvl_ratio,
        "vload_count":        vload_count,
        "vstore_count":       vstore_count,
        "memory_ratio":       memory_ratio,
        "compute_count":      compute_count,
        "compute_ratio":      compute_ratio,
        "estimated_vlen_bits": estimated_vlen,
        "vlen_utilization":   vlen_utilization,
        "quality_score":      score,
        "issues":             issues,
    }


def format_vector_quality_report(analysis: dict) -> str:
    """Render vector quality analysis as text."""
    if analysis["total_rvv"] == 0:
        return ""

    lines = []
    sep = "-" * 58

    lines += [
        sep,
        "  Vector Quality Metrics",
        sep,
        f"  Total RVV instructions: {analysis['total_rvv']:,}",
        f"  Quality score:          {analysis['quality_score']}/100",
        "",
    ]

    # vsetvl
    vr = analysis["vsetvl_ratio"]
    vr_icon = "[!]" if vr > 15 else ("[~]" if vr > 5 else "[+]")
    lines.append(f"  vsetvli ratio:     {vr:>5.1f}%  {vr_icon}")
    if vr > 5:
        lines.append(f"    {analysis['issues'][0]['message']}")
        if analysis["issues"][0].get("action"):
            lines.append(f"    => {analysis['issues'][0]['action']}")
    lines.append("")

    # memory ratio
    mr = analysis["memory_ratio"]
    mr_icon = "[~]" if mr > 40 else "[+]"
    lines.append(f"  Vector mem ratio:  {mr:>5.1f}%  {mr_icon}")
    if mr > 40:
        lines.append("    Workload is memory-bandwidth bound.")
        lines.append("    => Consider data layout optimization or prefetching.")
    lines.append("")

    # compute ratio
    cr = analysis["compute_ratio"]
    lines.append(f"  Compute ratio:     {cr:>5.1f}%")
    lines.append("")

    # VLEN utilization
    vu = analysis["vlen_utilization"]
    vu_icon = "[~]" if vu < 50 else "[+]"
    lines.append(
        f"  Est. VLEN util:    {vu:>5.1f}%  {vu_icon}  "
        f"(~{analysis['estimated_vlen_bits']} / 128 bits)"
    )
    if vu < 50:
        lines.append("    => Consider wider element types to improve throughput.")

    lines.append(sep)
    return "\n".join(lines)
