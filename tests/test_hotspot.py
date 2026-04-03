"""Tests for hotspot.py, patterns.py, and gen_stub.py (Phase 4)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from riscv_xray.patterns import (
    find_matching_patterns, get_pattern_by_name, KNOWN_PATTERNS, CUSTOM_OPCODE_SPACE
)
from riscv_xray.hotspot import (
    find_ngrams, score_candidate, analyze, format_report,
    HotspotCandidate, HotspotReport
)
from riscv_xray.gen_stub import generate_stub

# ── Fixtures ──────────────────────────────────────────────────────────────────

SCALAR_MNEMONICS = [
    "addi", "sw", "lw", "lw", "fmadd.s", "flw", "flw", "fmadd.s", "fsw",
    "lw", "beq", "lw", "add", "lw", "beq", "lw", "add",
    "xor", "srli", "andi", "xor", "xor", "srli", "andi", "xor",
    "ret", "addi", "sw", "lw", "mul", "add", "sub", "beq",
    "lw", "sw", "addi", "ret", "flw", "flw", "fmadd.s", "fsw",
    "lw", "beq", "lw", "add", "addi", "ret", "nop", "nop",
]

RVV_MNEMONICS = [
    # rvv_fma_kernel x4
    "vsetvli", "vle32.v", "vle32.v", "vfmacc.vv", "vse32.v",
    "vsetvli", "vle32.v", "vle32.v", "vfmacc.vv", "vse32.v",
    "vsetvli", "vle32.v", "vle32.v", "vfmacc.vv", "vse32.v",
    "vsetvli", "vle32.v", "vle32.v", "vfmacc.vv", "vse32.v",
    # rvv_threshold x2
    "vsetvli", "vle8.v", "vmsgtu.vx", "vmerge.vxm", "vse8.v",
    "vsetvli", "vle8.v", "vmsgtu.vx", "vmerge.vxm", "vse8.v",
    # scalar glue
    "addi", "mv", "ret", "addi", "beq", "lw", "sw",
]

# ── patterns.py tests ─────────────────────────────────────────────────────────

def test_get_pattern_by_name():
    p = get_pattern_by_name("rvv_fma_kernel")
    assert p is not None
    assert p["name"] == "rvv_fma_kernel"
    assert "sequence" in p
    assert "reduction_estimate" in p


def test_get_pattern_by_name_missing():
    assert get_pattern_by_name("nonexistent_pattern") is None


def test_known_patterns_have_required_keys():
    required = {"name", "display_name", "sequence", "min_repeats", "domain",
                "description", "reduction_estimate", "custom_opcode_hint"}
    for p in KNOWN_PATTERNS:
        for key in required:
            assert key in p, f"Pattern '{p.get('name')}' missing key '{key}'"


def test_custom_opcode_space_has_four_slots():
    assert len(CUSTOM_OPCODE_SPACE) == 4
    for slot in ("custom-0", "custom-1", "custom-2", "custom-3"):
        assert slot in CUSTOM_OPCODE_SPACE


def test_pattern_matching_rvv_fma():
    # Build ngrams that contain the rvv_fma_kernel sequence
    ngrams = [
        ["vle32.v", "vle32.v", "vfmacc.vv", "vse32.v"],
        ["vle32.v", "vle32.v", "vfmacc.vv", "vse32.v"],
    ]
    results = find_matching_patterns(ngrams)
    names = [r["name"] for r in results]
    assert "rvv_fma_kernel" in names


def test_pattern_matching_scalar_no_rvv():
    # Build ngrams from scalar mnemonics — should not match RVV patterns
    ngrams = [
        ["lw", "beq", "lw", "add"],
        ["lw", "beq", "lw", "add"],
    ]
    results = find_matching_patterns(ngrams)
    names = [r["name"] for r in results]
    assert "rvv_fma_kernel" not in names
    assert "rvv_threshold" not in names


def test_pattern_matching_scalar_branch_load():
    ngrams = [["lw", "beq", "lw", "add"]] * 3
    results = find_matching_patterns(ngrams)
    names = [r["name"] for r in results]
    assert "scalar_branch_load" in names


# ── hotspot.py tests ──────────────────────────────────────────────────────────

def test_find_ngrams_basic():
    mnemonics = ["a", "b", "c", "a", "b", "c", "d"]
    result = find_ngrams(mnemonics, 3)
    assert ("a", "b", "c") in result
    assert result[("a", "b", "c")] == 2


def test_find_ngrams_no_repeats():
    mnemonics = ["a", "b", "c", "d", "e", "f"]
    result = find_ngrams(mnemonics, 3)
    assert result == {}


def test_find_ngrams_longer_window():
    seq = ["vle32.v", "vle32.v", "vfmacc.vv", "vse32.v"]
    mnemonics = seq * 3 + ["addi", "ret"]
    result = find_ngrams(mnemonics, 4)
    key = tuple(seq)
    assert key in result
    assert result[key] >= 2


def test_score_candidate_high_severity():
    p = get_pattern_by_name("rvv_fma_kernel")
    c = score_candidate("myfunc", p, match_count=4, total_instructions=30)
    assert c.severity == "HIGH"
    assert c.function_name == "myfunc"
    assert c.estimated_reduction <= p["reduction_estimate"]


def test_score_candidate_medium_severity():
    p = get_pattern_by_name("rvv_fma_kernel")
    c = score_candidate("myfunc", p, match_count=2, total_instructions=100)
    assert c.severity in ("MEDIUM", "LOW")


def test_score_candidate_coverage():
    p = get_pattern_by_name("rvv_fma_kernel")  # sequence len 4
    c = score_candidate("myfunc", p, match_count=3, total_instructions=12)
    # 3 matches * 4 seq_len / 12 total = 100%
    assert c.pattern_coverage == 1.0


def test_analyze_with_mock(monkeypatch):
    """Mock extract_functions to inject synthetic RVV function data."""
    from riscv_xray import hotspot

    synthetic = [
        ("saxpy", RVV_MNEMONICS[:]),
        ("scalar_helper", SCALAR_MNEMONICS[:]),
    ]

    monkeypatch.setattr(hotspot, "extract_functions", lambda path: synthetic)

    report = analyze("./fake_binary.elf")

    assert report.total_functions == 2
    assert report.total_instructions == len(RVV_MNEMONICS) + len(SCALAR_MNEMONICS)
    # Should find at least the FMA kernel pattern in saxpy
    names = [c.pattern["name"] for c in report.candidates]
    assert "rvv_fma_kernel" in names


def test_analyze_top_candidate_is_high(monkeypatch):
    from riscv_xray import hotspot

    # Heavy RVV function — 4 FMA repetitions
    heavy_rvv = (
        ["vle32.v", "vle32.v", "vfmacc.vv", "vse32.v"] * 5
        + ["addi", "mv", "ret", "addi", "beq"]
    )
    synthetic = [("vec_kernel", heavy_rvv)]
    monkeypatch.setattr(hotspot, "extract_functions", lambda path: synthetic)

    report = analyze("./fake.elf")
    assert len(report.candidates) > 0
    assert report.candidates[0].severity == "HIGH"


# ── format_report tests ───────────────────────────────────────────────────────

def test_format_report_contains_key_fields():
    p = get_pattern_by_name("rvv_fma_kernel")
    candidate = HotspotCandidate(
        function_name="vec_fma_rvv",
        pattern=p,
        match_count=4,
        total_instructions=23,
        pattern_coverage=0.70,
        severity="HIGH",
        estimated_reduction=60,
    )
    report = HotspotReport(
        binary_path="./bench_rvv",
        total_functions=5,
        total_instructions=200,
        candidates=[candidate],
        unknown_ngrams=[],
    )
    text = format_report(report)
    assert "[!]" in text
    assert "vec_fma_rvv" in text
    assert "RVV FMA kernel" in text
    assert "Next step:" in text


def test_format_report_no_candidates():
    report = HotspotReport(
        binary_path="./bench_scalar",
        total_functions=3,
        total_instructions=50,
        candidates=[],
        unknown_ngrams=[],
    )
    text = format_report(report)
    assert "No significant" in text


def test_format_report_verbose_shows_low():
    p = get_pattern_by_name("rvv_fma_kernel")
    candidate = HotspotCandidate(
        function_name="tiny_fn",
        pattern=p,
        match_count=1,
        total_instructions=50,
        pattern_coverage=0.08,
        severity="LOW",
        estimated_reduction=5,
    )
    report = HotspotReport(
        binary_path="./bench",
        total_functions=1,
        total_instructions=50,
        candidates=[candidate],
        unknown_ngrams=[],
    )
    text_default = format_report(report, verbose=False)
    text_verbose = format_report(report, verbose=True)
    assert "tiny_fn" not in text_default
    assert "tiny_fn" in text_verbose


# ── gen_stub.py tests ─────────────────────────────────────────────────────────

def test_generate_stub_fma():
    p = get_pattern_by_name("rvv_fma_kernel")
    candidate = HotspotCandidate(
        function_name="vec_fma_rvv",
        pattern=p,
        match_count=4,
        total_instructions=23,
        pattern_coverage=0.70,
        severity="HIGH",
        estimated_reduction=60,
    )
    stub = generate_stub(candidate, opcode_slot="custom-0")

    assert "#ifndef" in stub
    assert "__riscv_xfmak" in stub
    assert ".insn" in stub
    assert "vle32" in stub
    assert "vfmacc" in stub
    assert "vse32" in stub
    assert "0x0B" in stub


def test_generate_stub_custom1_slot():
    p = get_pattern_by_name("rvv_threshold")
    candidate = HotspotCandidate(
        function_name="threshold_fn",
        pattern=p,
        match_count=2,
        total_instructions=19,
        pattern_coverage=0.42,
        severity="MEDIUM",
        estimated_reduction=40,
    )
    stub = generate_stub(candidate, opcode_slot="custom-1")
    assert "0x2B" in stub
    assert "XTHRESH" in stub


def test_generate_stub_has_header_guard():
    p = get_pattern_by_name("bitmanip_crc")
    candidate = HotspotCandidate(
        function_name="crc_fn",
        pattern=p,
        match_count=3,
        total_instructions=40,
        pattern_coverage=0.30,
        severity="HIGH",
        estimated_reduction=50,
    )
    stub = generate_stub(candidate)
    assert "#ifndef RISCV_CUSTOM_BITMANIP_CRC_H" in stub
    assert "#endif" in stub
