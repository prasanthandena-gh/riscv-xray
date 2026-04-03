"""profile_checker.py - RVA23 profile compliance gap analysis."""

from __future__ import annotations

PROFILES = {
    "rva22": {
        "name": "RVA22",
        "description": "2022 application processor profile",
        "mandatory": ["RVV", "Zba", "Zbb"],
        "optional": ["Zbc"],
    },
    "rva23": {
        "name": "RVA23",
        "description": "2023 application processor profile (current standard)",
        "mandatory": [
            "RVV", "Zba", "Zbb", "Zicond", "Zcb", "Zfa",
            "Zvbb", "Zvkng", "Zvfhmin", "Zicntr",
        ],
        "optional": ["Zbc", "Zvfh", "Zvksg"],
    },
    "rva23+ai": {
        "name": "RVA23+AI",
        "description": "RVA23 plus AI/ML acceleration extensions",
        "mandatory": [
            "RVV", "Zba", "Zbb", "Zicond", "Zcb", "Zfa",
            "Zvbb", "Zvkng", "Zvfhmin", "Zicntr",
            "Zvfh", "Zvfbfmin", "Zvfbfwma",
        ],
        "optional": ["Zbc", "Zvksg"],
    },
}

# Threshold: < this % is "minimal" not "active"
MINIMAL_THRESHOLD = 5.0


def _march_flag_for_missing(missing: list) -> str:
    """Build a -march flag covering all missing extensions."""
    ext_map = {
        "RVV":      "v",
        "Zba":      "zba",
        "Zbb":      "zbb",
        "Zicond":   "zicond",
        "Zcb":      "zcb",
        "Zfa":      "zfa",
        "Zvbb":     "zvbb",
        "Zvkng":    "zvkng",
        "Zvfhmin":  "zvfhmin",
        "Zicntr":   "zicntr",
        "Zbc":      "zbc",
        "Zvfh":     "zvfh",
        "Zvfbfmin": "zvfbfmin",
        "Zvfbfwma": "zvfbfwma",
        "Zvksg":    "zvksg",
    }
    parts = ["rv64gc"]
    # Always include v if RVV is in missing or not
    has_v = False
    for m in missing:
        flag = ext_map.get(m, "")
        if flag == "v":
            has_v = True
        elif flag:
            parts.append(flag)
    base = "rv64gcv" if has_v else "rv64gc"
    parts[0] = base
    return "-march=" + "_".join(parts)


def check_profile(data: dict, profile_name: str) -> dict:
    """
    Check how well a binary's extension usage matches a target profile.

    Returns a dict with score, active/missing/minimal lists, and suggested march.
    """
    profile = PROFILES.get(profile_name)
    if profile is None:
        raise ValueError(f"Unknown profile: {profile_name}. "
                         f"Choose from: {list(PROFILES)}")

    mandatory = profile["mandatory"]
    active = []
    missing = []
    minimal = []

    for ext in mandatory:
        pct = data.get(ext, {}).get("percentage", 0.0)
        if pct >= MINIMAL_THRESHOLD:
            active.append(ext)
        elif pct > 0:
            minimal.append(ext)
        else:
            missing.append(ext)

    score = len(active)
    total = len(mandatory)
    pct_score = round(score / total * 100, 1) if total > 0 else 0.0

    # Suggest march for truly missing extensions
    suggested = _march_flag_for_missing(missing)

    return {
        "profile":         profile_name,
        "profile_name":    profile["name"],
        "description":     profile["description"],
        "score":           score,
        "total_mandatory": total,
        "percentage":      pct_score,
        "active":          active,
        "missing":         missing,
        "minimal":         minimal,
        "suggested_march": suggested,
    }


def format_profile_report(result: dict, data: dict) -> str:
    """Render the profile gap report as text."""
    lines = []
    sep = "-" * 58

    lines += [
        sep,
        "  RVA23 Compliance Gap Report",
        sep,
        f"  Binary:   (see above)",
        f"  Profile:  {result['profile_name']} — {result['description']}",
        "",
        "  Mandatory Extension Coverage",
        "  " + "-" * 54,
    ]

    from .extensions import EXTENSIONS
    all_mandatory = result["active"] + result["minimal"] + result["missing"]
    for ext in all_mandatory:
        pct = data.get(ext, {}).get("percentage", 0.0)
        meta = EXTENSIONS.get(ext, {})
        name = meta.get("name", ext)

        if ext in result["active"]:
            icon = "[+] Active"
        elif ext in result["minimal"]:
            icon = "[~] Minimal (<5%)"
        else:
            icon = "[-] Missing"

        lines.append(f"  {ext:<10} {name:<20} {pct:>5.1f}%   {icon}")

    score = result["score"]
    total = result["total_mandatory"]
    pct = result["percentage"]
    lines += [
        "",
        f"  Score: {score}/{total} mandatory extensions active  ({pct:.0f}%)",
        "",
    ]

    if result["missing"]:
        lines += [
            f"  Missing extensions fix:",
            f"    {result['suggested_march']}",
            "",
            "  Note: Missing does not mean broken — your binary may not",
            "  need these extensions. But if your workload involves",
            "  branching (Zicond), crypto (Zvkng), or AI (Zvfhmin),",
            "  you are leaving performance on the table.",
        ]
    else:
        lines.append("  All mandatory extensions active. Excellent RVA23 coverage.")

    lines.append(sep)
    return "\n".join(lines)


def get_profile_names() -> list:
    """Return available profile names."""
    return list(PROFILES.keys())
