"""patterns.py - Known instruction sequence patterns for custom opcode candidates."""

from __future__ import annotations

KNOWN_PATTERNS = [
    {
        "name": "rvv_fma_kernel",
        "display_name": "RVV FMA kernel (load-multiply-accumulate-store)",
        "sequence": ["vle32", "vle32", "vfmacc", "vse32"],
        "min_repeats": 2,
        "domain": "ML inference",
        "description": "Inner loop of a fused multiply-accumulate over float32 vectors.",
        "reduction_estimate": 75,
        "custom_opcode_hint": "XFMAK",
    },
    {
        "name": "rvv_scale_store",
        "display_name": "RVV scale-store (array scaling)",
        "sequence": ["vle32", "vfmul", "vse32"],
        "min_repeats": 2,
        "domain": "signal processing",
        "description": "Scales a float32 array by a scalar and stores the result.",
        "reduction_estimate": 67,
        "custom_opcode_hint": "XSCALE",
    },
    {
        "name": "rvv_add_store",
        "display_name": "RVV vector addition (load-add-store)",
        "sequence": ["vle32", "vle32", "vfadd", "vse32"],
        "min_repeats": 2,
        "domain": "signal processing",
        "description": "Element-wise addition of two float32 vectors.",
        "reduction_estimate": 75,
        "custom_opcode_hint": "XVADD",
    },
    {
        "name": "rvv_threshold",
        "display_name": "RVV threshold (conditional select)",
        "sequence": ["vle8", "vmsgtu", "vmerge", "vse8"],
        "min_repeats": 2,
        "domain": "image processing",
        "description": "Applies a threshold to a uint8 image: pixels above threshold set to max.",
        "reduction_estimate": 75,
        "custom_opcode_hint": "XTHRESH",
    },
    {
        "name": "rvv_dot_reduce",
        "display_name": "RVV dot product (load-FMA-reduce)",
        "sequence": ["vle32", "vle32", "vfmacc", "vfredusum"],
        "min_repeats": 2,
        "domain": "ML inference",
        "description": "Dot product of two float32 vectors using FMA and horizontal reduction.",
        "reduction_estimate": 75,
        "custom_opcode_hint": "XDOTP",
    },
    {
        "name": "rvv_abs_diff",
        "display_name": "RVV absolute difference (load-sub-abs-store)",
        "sequence": ["vle32", "vle32", "vfsub", "vfabs", "vse32"],
        "min_repeats": 2,
        "domain": "image processing",
        "description": "Computes element-wise absolute difference of two float32 vectors.",
        "reduction_estimate": 80,
        "custom_opcode_hint": "XABSD",
    },
    {
        "name": "scalar_mac",
        "display_name": "Scalar float MAC (load-load-fmadd-store)",
        "sequence": ["flw", "flw", "fmadd", "fsw"],
        "min_repeats": 2,
        "domain": "signal processing",
        "description": "Scalar float multiply-accumulate without RVV — candidate for vectorisation.",
        "reduction_estimate": 75,
        "custom_opcode_hint": "XSMAC",
    },
    {
        "name": "scalar_branch_load",
        "display_name": "Conditional load pattern (load-branch-load-add)",
        "sequence": ["lw", "beq", "lw", "add"],
        "min_repeats": 2,
        "domain": "embedded",
        "description": "Conditional pointer-chasing pattern common in linked-list traversal.",
        "reduction_estimate": 50,
        "custom_opcode_hint": "XCLOAD",
    },
    {
        "name": "bitmanip_crc",
        "display_name": "CRC-style bit manipulation (xor-shift-and-xor)",
        "sequence": ["xor", "srli", "andi", "xor"],
        "min_repeats": 2,
        "domain": "cryptography",
        "description": "XOR-shift-mask pattern found in CRC and lightweight hash functions.",
        "reduction_estimate": 75,
        "custom_opcode_hint": "XCRC",
    },
    {
        "name": "crypto_aes_round",
        "display_name": "AES-like round function (xor-load-shift-xor)",
        "sequence": ["xor", "lbu", "sll", "xor"],
        "min_repeats": 2,
        "domain": "cryptography",
        "description": "SubBytes-MixColumns-like round step in table-driven AES implementations.",
        "reduction_estimate": 75,
        "custom_opcode_hint": "XAESR",
    },
]

CUSTOM_OPCODE_SPACE = {
    "custom-0": "0001011 — R/I/S/U type, opcode 0x0B",
    "custom-1": "0101011 — R/I/S/U type, opcode 0x2B",
    "custom-2": "1011011 — R/I/S/U type, opcode 0x5B",
    "custom-3": "1111011 — R/I/S/U type, opcode 0x7B",
}


def _prefix_match(mnemonic: str, prefix: str) -> bool:
    """True if mnemonic starts with prefix (dot-aware)."""
    return mnemonic == prefix or mnemonic.startswith(prefix + ".") or mnemonic.startswith(prefix + "_")


def _sequence_matches(mnemonics: list, pattern_sequence: list) -> bool:
    """Check if a list of mnemonics matches a pattern sequence via prefix matching."""
    if len(mnemonics) != len(pattern_sequence):
        return False
    return all(_prefix_match(m, p) for m, p in zip(mnemonics, pattern_sequence))


def find_matching_patterns(sequence_ngrams: list) -> list:
    """
    Takes a list of instruction sequences (each a list of mnemonics).
    Returns matching patterns with a match_count field added.
    Uses prefix matching (mnemonic starts with pattern prefix).
    """
    # Count how many times each pattern appears across all ngrams
    pattern_counts: dict[str, int] = {}

    for ngram in sequence_ngrams:
        for pattern in KNOWN_PATTERNS:
            if _sequence_matches(ngram, pattern["sequence"]):
                pattern_counts[pattern["name"]] = pattern_counts.get(pattern["name"], 0) + 1

    results = []
    for pattern in KNOWN_PATTERNS:
        count = pattern_counts.get(pattern["name"], 0)
        if count >= pattern["min_repeats"]:
            results.append({**pattern, "match_count": count})

    return results


def get_pattern_by_name(name: str) -> dict | None:
    """Return a pattern dict by name, or None if not found."""
    for pattern in KNOWN_PATTERNS:
        if pattern["name"] == name:
            return pattern
    return None
