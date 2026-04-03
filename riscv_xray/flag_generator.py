"""flag_generator.py - Multi-signal -mtune recommendation with confidence levels."""

from __future__ import annotations

_BRANCH_MNEMONICS = {
    "beq", "bne", "blt", "bge", "bltu", "bgeu", "j", "jal", "jalr",
}
_LOAD_STORE = {
    "lw", "ld", "lh", "lb", "lhu", "lbu", "flw", "fld",
    "sw", "sd", "sh", "sb", "fsw", "fsd",
}

HARDWARE_PROFILES = [
    {
        "tune_flag":   "sifive-p670",
        "type":        "ooo",
        "profile":     "RVA23",
        "vector_width": 512,
        "description": "SiFive P670, 4-wide OOO, RVA23, 512-bit vector",
        "score_weights": {
            "high_rvv":       3,   # RVV > 30%
            "zba_active":     2,   # Zba in use
            "low_branches":   1,   # branch density < 15%
        },
    },
    {
        "tune_flag":   "spacemit-x60",
        "type":        "ooo",
        "profile":     "RVA22",
        "vector_width": 256,
        "description": "SpacemiT X60, OOO, RVA22, 256-bit vector",
        "score_weights": {
            "medium_rvv":     2,   # RVV 10-30%
            "low_branches":   1,
        },
    },
    {
        "tune_flag":   "sifive-u74",
        "type":        "inorder",
        "profile":     "RVA22",
        "vector_width": 128,
        "description": "SiFive U74, in-order, RVA22, embedded",
        "score_weights": {
            "low_rvv":        2,   # RVV < 5%
            "high_branches":  1,   # branch density > 15%
            "high_base":      1,   # base > 80%
        },
    },
    {
        "tune_flag":   "thead-c906",
        "type":        "inorder",
        "profile":     "RVA20",
        "vector_width": 128,
        "description": "T-Head C906, in-order, RVA20, IoT/embedded",
        "score_weights": {
            "low_rvv":        1,
            "high_branches":  1,
        },
    },
    {
        "tune_flag":   "generic-ooo",
        "type":        "ooo",
        "profile":     "RVA23",
        "vector_width": 256,
        "description": "Generic OOO, safe for any RVA23 hardware",
        "score_weights": {},   # fallback — always gets base score 1
    },
]


def _extract_signals(data: dict) -> dict:
    """Derive scoring signals from classifier data dict."""
    rvv_pct  = data.get("RVV",  {}).get("percentage", 0.0)
    zba_pct  = data.get("Zba",  {}).get("percentage", 0.0)
    base_pct = data.get("Base", {}).get("percentage", 0.0)
    total    = data.get("_total", 0)

    # Estimate branch + memory density from mnemonics if available
    # (data dict has counts, not mnemonics — use proxy from Base%)
    branch_density = 0.0
    memory_ratio   = 0.0

    # Rough proxy: high base% with low RVV implies scalar-heavy
    if total > 0 and base_pct > 0:
        # Can't get exact branch count from data dict alone —
        # use base_pct as a proxy
        branch_density = min(base_pct / 100 * 0.25, 0.30)
        memory_ratio   = min(base_pct / 100 * 0.35, 0.50)

    return {
        "rvv_pct":        rvv_pct,
        "zba_active":     zba_pct > 5.0,
        "high_rvv":       rvv_pct > 30.0,
        "medium_rvv":     10.0 < rvv_pct <= 30.0,
        "low_rvv":        rvv_pct < 5.0,
        "high_base":      base_pct > 80.0,
        "branch_density": branch_density,
        "low_branches":   branch_density < 0.15,
        "high_branches":  branch_density > 0.15,
        "memory_ratio":   memory_ratio,
    }


def score_hardware(signals: dict, profile: dict) -> int:
    """Score a hardware profile against extracted signals. Returns 0-10."""
    weights = profile["score_weights"]
    score = 0
    for signal, weight in weights.items():
        if signals.get(signal, False):
            score += weight
    # generic-ooo always gets 1 as safe fallback
    if profile["tune_flag"] == "generic-ooo":
        score = max(score, 1)
    return min(score, 10)


def suggest_mtune(data: dict) -> dict:
    """
    Recommend -mtune based on multi-signal instruction mix analysis.

    Returns recommended target, confidence level, reasoning, and disclaimer.
    """
    signals = _extract_signals(data)
    rvv_pct  = signals["rvv_pct"]
    zba_act  = signals["zba_active"]
    base_pct = data.get("Base", {}).get("percentage", 0.0)

    # Score all profiles
    scored = [
        (hw, score_hardware(signals, hw))
        for hw in HARDWARE_PROFILES
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    best_hw, best_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0

    # Confidence
    if best_score >= 8 and (best_score - second_score) >= 3:
        confidence = "high"
    elif best_score >= 4:
        confidence = "medium"
    elif best_score >= 2:
        confidence = "low"
    else:
        # No signal at all — safe fallback
        confidence = "low"
        best_hw = next(h for h in HARDWARE_PROFILES
                       if h["tune_flag"] == "generic-ooo")

    # Build reasoning bullets
    reasoning = []
    if rvv_pct > 30:
        reasoning.append(
            f"High RVV usage ({rvv_pct:.1f}%) — out-of-order core with "
            "wide vector units benefits most"
        )
    elif rvv_pct > 10:
        reasoning.append(
            f"Moderate RVV usage ({rvv_pct:.1f}%) — OOO core "
            "recommended for vector throughput"
        )
    else:
        reasoning.append(
            f"Low RVV usage ({rvv_pct:.1f}%) — in-order tuning "
            "appropriate for scalar workload"
        )

    if zba_act:
        reasoning.append(
            f"Zba active — address generation unit is utilized"
        )

    if base_pct > 80:
        reasoning.append(
            f"High scalar base ({base_pct:.1f}%) — "
            "branch-heavy or control-flow-dominated code"
        )

    if confidence == "low":
        reasoning.append(
            "Low confidence — instruction mix is ambiguous; "
            "generic-ooo is the safe default"
        )

    # Alternative: second-best that isn't the winner
    alt = next(
        (h["tune_flag"] for h, _ in scored[1:]
         if h["tune_flag"] != best_hw["tune_flag"]),
        "generic-ooo"
    )

    return {
        "recommended":      best_hw["tune_flag"],
        "recommended_desc": best_hw["description"],
        "confidence":       confidence,
        "score":            best_score,
        "alternative":      alt,
        "reasoning":        reasoning,
        "exec_type":        best_hw["type"],
        "disclaimer": (
            "Recommendation based on static instruction mix analysis. "
            "Verify with actual hardware benchmarking before shipping."
        ),
    }


def format_mtune_section(suggestion: dict) -> str:
    """Render the mtune recommendation as text."""
    sep = "-" * 58
    conf = suggestion["confidence"].upper()
    conf_icon = {"HIGH": "[+]", "MEDIUM": "[~]", "LOW": "[?]"}.get(conf, "[~]")

    lines = [
        sep,
        "  Hardware Tune Target",
        sep,
        f"  Confidence: {conf_icon} {conf}",
        "",
        f"  Recommended: -mtune={suggestion['recommended']}",
        f"               ({suggestion['recommended_desc']})",
        f"  Alternative: -mtune={suggestion['alternative']}",
        "",
        "  Why:",
    ]
    for reason in suggestion["reasoning"]:
        lines.append(f"    - {reason}")

    lines += [
        "",
        "  Disclaimer:",
        f"    {suggestion['disclaimer']}",
        sep,
    ]
    return "\n".join(lines)
