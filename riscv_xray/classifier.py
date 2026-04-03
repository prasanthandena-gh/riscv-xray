"""classifier.py - Map instruction mnemonics to RVA23 extensions."""

from __future__ import annotations
from .extensions import EXTENSIONS, THRESHOLDS, EXTENSION_ORDER


def classify(mnemonics: list) -> dict:
    """
    Classify a list of instruction mnemonics by RVA23 extension.

    Returns a dict with per-extension counts, percentages, and status.
    """
    total = len(mnemonics)

    # Initialize counts for all extensions
    counts = {ext: 0 for ext in EXTENSION_ORDER}

    for mnemonic in mnemonics:
        matched = False
        # Check specific extensions before Base
        for ext_name in EXTENSION_ORDER:
            if ext_name == "Base":
                continue
            prefixes = EXTENSIONS[ext_name]["prefixes"]
            if any(mnemonic.startswith(p) for p in prefixes):
                counts[ext_name] += 1
                matched = True
                break
        if not matched:
            counts["Base"] += 1

    result = {}
    for ext_name in EXTENSION_ORDER:
        count = counts[ext_name]
        pct = (count / total * 100) if total > 0 else 0.0

        if ext_name == "Base":
            status = "info"
        elif pct > THRESHOLDS["heavy_use"]:
            status = "heavy_use"
        elif pct > THRESHOLDS["light_use"]:
            status = "in_use"
        elif pct >= THRESHOLDS["minimal_use"]:
            status = "light_use"
        else:
            status = "unused"

        result[ext_name] = {
            "count": count,
            "percentage": round(pct, 1),
            "status": status,
        }

    result["_total"] = total
    return result


def top_extension(data: dict) -> str:
    """Return the non-Base extension with the highest usage percentage."""
    best = None
    best_pct = -1.0
    for ext_name, info in data.items():
        if ext_name.startswith("_") or ext_name == "Base":
            continue
        if info["percentage"] > best_pct:
            best_pct = info["percentage"]
            best = ext_name
    return best
