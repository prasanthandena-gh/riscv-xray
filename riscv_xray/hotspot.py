"""hotspot.py - Custom instruction candidate analysis for riscv-xray."""

from __future__ import annotations
import re
import subprocess
from dataclasses import dataclass, field

from .patterns import KNOWN_PATTERNS, find_matching_patterns, _sequence_matches, _prefix_match, get_pattern_by_name

_FUNC_HEADER = re.compile(r'^[0-9a-f]+ <([^>]+)>:$')
_INSN_LINE   = re.compile(r'^\s+[0-9a-f]+:\s+(\w[\w.]*)')


@dataclass
class HotspotCandidate:
    function_name: str
    pattern: dict
    match_count: int
    total_instructions: int
    pattern_coverage: float
    severity: str            # "HIGH", "MEDIUM", "LOW"
    estimated_reduction: int # % instruction reduction if fused


@dataclass
class HotspotReport:
    binary_path: str
    total_functions: int
    total_instructions: int
    candidates: list = field(default_factory=list)   # list[HotspotCandidate]
    unknown_ngrams: list = field(default_factory=list)  # top 5 unknown sequences


def extract_functions(binary_path: str) -> list:
    """
    Run objdump -d on binary_path.
    Returns list of (function_name, [mnemonic, ...]) tuples.
    Skips functions with fewer than 10 instructions.
    """
    objdump = _find_objdump()
    try:
        r = subprocess.run(
            [objdump, "-d", "--no-show-raw-insn", binary_path],
            capture_output=True, text=True, timeout=60,
        )
    except FileNotFoundError:
        raise RuntimeError(
            f"objdump not found: {objdump}\n"
            "Install with: sudo apt install binutils-riscv64-linux-gnu"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"objdump timed out on {binary_path}")

    if r.returncode != 0:
        raise RuntimeError(f"objdump failed:\n{r.stderr[:200]}")

    functions = {}
    order = []
    current = None

    for line in r.stdout.splitlines():
        m = _FUNC_HEADER.match(line.strip())
        if m:
            current = m.group(1)
            if current not in functions:
                functions[current] = []
                order.append(current)
            continue

        if current is None:
            continue

        m = _INSN_LINE.match(line)
        if m:
            functions[current].append(m.group(1))

    return [
        (name, functions[name])
        for name in order
        if len(functions[name]) >= 4
    ]


def find_ngrams(mnemonics: list, n: int) -> dict:
    """
    Sliding window over mnemonics.
    Returns dict mapping (mnemonic_tuple) -> count for n-grams appearing >= 2 times.
    """
    counts: dict[tuple, int] = {}
    for i in range(len(mnemonics) - n + 1):
        gram = tuple(mnemonics[i:i + n])
        counts[gram] = counts.get(gram, 0) + 1
    return {gram: cnt for gram, cnt in counts.items() if cnt >= 2}


def count_pattern_matches(mnemonics: list, pattern_seq: list, max_gap: int = 4) -> int:
    """
    Count non-overlapping subsequence matches of pattern_seq within mnemonics.
    Allows up to max_gap unrelated instructions between each pattern element.
    This handles compiler-interleaved glue instructions (addi, slli, mv, etc.)
    between the interesting operations.
    """
    matches = 0
    i = 0
    while i < len(mnemonics):
        # Try to match pattern starting at position i
        p_idx = 0   # position in pattern
        k = i        # position in mnemonics
        gap = 0      # consecutive non-matching instructions
        while p_idx < len(pattern_seq) and k < len(mnemonics):
            if _prefix_match(mnemonics[k], pattern_seq[p_idx]):
                p_idx += 1
                k += 1
                gap = 0
            else:
                gap += 1
                k += 1
                if gap > max_gap:
                    break
        if p_idx == len(pattern_seq):
            matches += 1
            i = k  # skip past the match to avoid overlap
        else:
            i += 1
    return matches


def score_candidate(
    function_name: str,
    pattern: dict,
    match_count: int,
    total_instructions: int,
) -> HotspotCandidate:
    """Build a HotspotCandidate with severity and estimated reduction."""
    seq_len = len(pattern["sequence"])
    pattern_coverage = (match_count * seq_len) / max(1, total_instructions)

    if match_count >= 3 or pattern_coverage >= 0.15:
        severity = "HIGH"
    elif match_count >= 2 or pattern_coverage >= 0.05:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    raw = pattern["reduction_estimate"] * match_count / max(1, total_instructions // 20)
    estimated_reduction = min(int(raw), pattern["reduction_estimate"])

    return HotspotCandidate(
        function_name=function_name,
        pattern=pattern,
        match_count=match_count,
        total_instructions=total_instructions,
        pattern_coverage=pattern_coverage,
        severity=severity,
        estimated_reduction=estimated_reduction,
    )


def analyze(binary_path: str, min_repeats: int = 2) -> HotspotReport:
    """
    Main entry point.
    Analyzes a RISC-V binary and returns a HotspotReport.

    Detection uses subsequence matching with gaps (up to 4 glue instructions
    between pattern elements), since compilers interleave scalar register
    manipulation between vector/float operations.

    Two passes:
    1. Within-function: patterns repeating inside a single function
    2. Cross-function: same pattern appearing across different functions
    """
    functions = extract_functions(binary_path)
    total_instructions = sum(len(mnemonics) for _, mnemonics in functions)

    candidates: list[HotspotCandidate] = []

    # Track which patterns appear in which functions (for cross-function detection)
    # pattern_name -> [(func_name, count_in_func, total_insns)]
    cross_func_hits: dict[str, list] = {}

    for func_name, mnemonics in functions:
        for pattern in KNOWN_PATTERNS:
            count = count_pattern_matches(mnemonics, pattern["sequence"])
            if count == 0:
                continue

            # Within-function: pattern repeats enough times in this function
            if count >= min_repeats:
                candidates.append(score_candidate(func_name, pattern, count, len(mnemonics)))

            # Track for cross-function detection (even single occurrences)
            cross_func_hits.setdefault(pattern["name"], []).append(
                (func_name, count, len(mnemonics))
            )

    # Cross-function pass: patterns appearing across multiple functions
    for pattern_name, hits in cross_func_hits.items():
        if len(hits) < min_repeats:
            continue
        pattern = get_pattern_by_name(pattern_name)
        if pattern is None:
            continue

        # Skip functions already covered by within-function detection
        existing_funcs = {c.function_name for c in candidates if c.pattern["name"] == pattern_name}

        cross_count = len(hits)
        for func_name, count_in_func, total_insns in hits:
            if func_name in existing_funcs:
                continue
            candidates.append(score_candidate(func_name, pattern, cross_count, total_insns))

    # Sort candidates: HIGH first, then by match_count desc
    _sev_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    candidates.sort(key=lambda c: (_sev_order[c.severity], -c.match_count))

    # Collect unknown repeating n-grams (strict match, for discovery)
    all_unknown: dict[tuple, int] = {}
    pattern_lengths = {len(p["sequence"]) for p in KNOWN_PATTERNS}
    for func_name, mnemonics in functions:
        for n in pattern_lengths:
            ngrams = find_ngrams(mnemonics, n)
            for gram, count in ngrams.items():
                # Skip if it matches any known pattern
                gram_list = list(gram)
                is_known = any(
                    _sequence_matches(gram_list, p["sequence"])
                    for p in KNOWN_PATTERNS if len(p["sequence"]) == n
                )
                if not is_known:
                    all_unknown[gram] = all_unknown.get(gram, 0) + count

    unknown_ngrams = sorted(all_unknown.items(), key=lambda x: -x[1])[:5]

    return HotspotReport(
        binary_path=binary_path,
        total_functions=len(functions),
        total_instructions=total_instructions,
        candidates=candidates,
        unknown_ngrams=unknown_ngrams,
    )


def format_report(report: HotspotReport, verbose: bool = False) -> str:
    """Format a HotspotReport for terminal output."""
    from pathlib import Path

    sep = "-" * 58
    name = Path(report.binary_path).name

    lines = [
        sep,
        f"  riscv-xray  Hotspot Analysis — custom instruction candidates",
        sep,
        f"  Binary:              {name}",
        f"  Functions analyzed:  {report.total_functions}",
        f"  Total instructions:  {report.total_instructions:,}",
        f"  Candidates found:    {len(report.candidates)}",
        "",
    ]

    _badge = {"HIGH": "[!]", "MEDIUM": "[~]", "LOW": "[ ]"}

    shown = report.candidates if verbose else [
        c for c in report.candidates if c.severity in ("HIGH", "MEDIUM")
    ]

    if not shown:
        lines.append("  No significant custom instruction candidates found.")
    else:
        for c in shown:
            badge = _badge[c.severity]
            seq_len = len(c.pattern["sequence"])
            covered = c.match_count * seq_len
            pct = f"{c.pattern_coverage * 100:.0f}%"
            lines += [
                f"  {badge}  {c.function_name:<42} {c.severity}",
                f"       Pattern:   {c.pattern['display_name']}",
                f"       Matches:   {c.match_count}x in this function",
                f"       Coverage:  {covered} of {c.total_instructions} function instructions ({pct})",
                f"       Est. reduction: ~{c.estimated_reduction}% if fused into {c.pattern['custom_opcode_hint']} custom opcode",
                "",
            ]

    if report.unknown_ngrams:
        lines += ["  Unknown repeating sequences (top 5):"]
        for gram, count in report.unknown_ngrams:
            seq_str = " → ".join(gram)
            lines.append(f"    {seq_str}  (appears {count}x) — potential new pattern")
        lines.append("")

    if shown:
        top = shown[0].function_name
        lines += [
            f"  Next step: riscv-xray gen-stub --function {top} {report.binary_path}",
        ]

    lines.append(sep)
    return "\n".join(lines)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _find_objdump() -> str:
    import shutil
    for candidate in [
        "riscv64-linux-gnu-objdump",
        "riscv64-unknown-linux-gnu-objdump",
        "riscv64-unknown-elf-objdump",
        "objdump",
    ]:
        path = shutil.which(candidate)
        if path:
            return path
    return "riscv64-linux-gnu-objdump"
