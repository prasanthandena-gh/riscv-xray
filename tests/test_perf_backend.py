"""Tests for backends/perf_backend.py"""

import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.backends.perf_backend import (
    parse_perf_annotate,
    get_hot_mnemonics,
    get_all_mnemonics,
    validate_perf_file,
    detect_risc_v,
)

_SAMPLE = """\
Percent │  Disassembly of my-service

        │ 0000000000012340 <json_parse>:
  0.00  │       addi    sp,sp,-48
  0.12  │       sd      ra,40(sp)
 15.08  │       vadd.vv v8,v8,v16
  8.34  │       vsetvli t0,a2,e32,m1,tu,mu
  0.01  │       sd      a0,32(sp)

        │ 0000000000013000 <hash_compute>:
  5.00  │       fadd.s  fa0,fa1,fa2
  2.00  │       add     a0,a1,a2
"""

_X86_SAMPLE = """\
        │ 0000000000001234 <main>:
  5.00  │       mov     eax,0x1
  3.00  │       push    rbp
  2.00  │       call    printf
"""


def test_parse_basic():
    parsed = parse_perf_annotate(_SAMPLE)
    assert parsed["backend"] == "perf-annotate"
    assert len(parsed["mnemonics"]) > 0
    assert "vadd.vv" in parsed["mnemonics"]
    assert "addi" in parsed["mnemonics"]


def test_parse_function_boundaries():
    parsed = parse_perf_annotate(_SAMPLE)
    assert "json_parse" in parsed["functions"]
    assert "hash_compute" in parsed["functions"]
    jp = parsed["functions"]["json_parse"]
    assert "vadd.vv" in jp["mnemonics"]
    # hash_compute should not contain vadd.vv
    assert "vadd.vv" not in parsed["functions"]["hash_compute"]["mnemonics"]


def test_weighted_mnemonics():
    parsed = parse_perf_annotate(_SAMPLE)
    weighted = dict(parsed["weighted_mnemonics"])
    assert weighted.get("vadd.vv", 0) == 15.08
    assert weighted.get("vsetvli", 0) == 8.34


def test_hot_mnemonics_threshold():
    parsed = parse_perf_annotate(_SAMPLE)
    hot = get_hot_mnemonics(parsed, threshold=1.0)
    assert "vadd.vv" in hot   # 15.08% > 1%
    assert "vsetvli" in hot   # 8.34% > 1%
    assert "addi" not in hot  # 0.0% < 1%


def test_all_mnemonics_weighted():
    """get_all_mnemonics returns vadd.vv ~15x more than addi."""
    parsed = parse_perf_annotate(_SAMPLE)
    all_m = get_all_mnemonics(parsed)
    vadd_count = all_m.count("vadd.vv")
    sd_count   = all_m.count("addi") or 1
    assert vadd_count > sd_count


def test_total_sample_percent():
    parsed = parse_perf_annotate(_SAMPLE)
    assert parsed["total_sample_percent"] > 0


def test_validate_valid_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(_SAMPLE)
        fname = f.name
    ok, reason = validate_perf_file(fname)
    os.unlink(fname)
    assert ok is True
    assert reason == ""


def test_validate_invalid_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("this is just random text without any perf output\n")
        fname = f.name
    ok, reason = validate_perf_file(fname)
    os.unlink(fname)
    assert ok is False
    assert reason != ""


def test_validate_missing_file():
    ok, reason = validate_perf_file("/nonexistent/path/profile.txt")
    assert ok is False
    assert "not found" in reason.lower() or "File" in reason


def test_detect_riscv_true():
    parsed = parse_perf_annotate(_SAMPLE)
    assert detect_risc_v(parsed) is True


def test_detect_riscv_false():
    parsed = parse_perf_annotate(_X86_SAMPLE)
    assert detect_risc_v(parsed) is False
