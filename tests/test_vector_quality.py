"""Tests for vector_quality.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.vector_quality import analyze_vector_quality, format_vector_quality_report


def test_vsetvl_high_ratio():
    """20 vsetvli + 80 vadd => 20% ratio triggers high_vsetvl issue."""
    mnemonics = ["vsetvli"] * 20 + ["vadd.vv"] * 80
    result = analyze_vector_quality(mnemonics)
    assert result["vsetvl_ratio"] == 20.0
    issues = [i["type"] for i in result["issues"]]
    assert "high_vsetvl" in issues
    assert result["quality_score"] <= 80


def test_vsetvl_good_ratio():
    """2 vsetvli + 98 vadd => 2% ratio, no vsetvl issue."""
    mnemonics = ["vsetvli"] * 2 + ["vadd.vv"] * 98
    result = analyze_vector_quality(mnemonics)
    assert result["vsetvl_ratio"] == 2.0
    issues = [i["type"] for i in result["issues"]]
    assert "high_vsetvl" not in issues
    assert "moderate_vsetvl" not in issues


def test_memory_bound():
    """50 vload + 50 vstore => 100% memory ratio triggers memory_bound issue."""
    mnemonics = ["vle32.v"] * 50 + ["vse32.v"] * 50
    result = analyze_vector_quality(mnemonics)
    assert result["memory_ratio"] > 40
    issues = [i["type"] for i in result["issues"]]
    assert "memory_bound" in issues


def test_quality_score_perfect():
    """Low vsetvl, low memory, normal compute => score close to 100."""
    mnemonics = ["vsetvli"] * 2 + ["vadd.vv"] * 78 + ["vle32.v"] * 10 + ["vse32.v"] * 10
    result = analyze_vector_quality(mnemonics)
    assert result["quality_score"] >= 80


def test_quality_score_degraded():
    """High vsetvl + heavy memory => score reduced significantly."""
    mnemonics = ["vsetvli"] * 20 + ["vle8.v"] * 50 + ["vse8.v"] * 30
    result = analyze_vector_quality(mnemonics)
    # high_vsetvl (-20) + memory_bound (-15) = -35
    assert result["quality_score"] <= 65


def test_empty_vector():
    """No vector instructions => zero total, empty issues."""
    mnemonics = ["add", "sub", "mul"]
    result = analyze_vector_quality(mnemonics)
    assert result["total_rvv"] == 0
    assert result["issues"] == []
    assert result["quality_score"] == 0


def test_format_returns_empty_for_no_rvv():
    mnemonics = ["add", "sub"]
    result = analyze_vector_quality(mnemonics)
    text = format_vector_quality_report(result)
    assert text == ""


def test_format_contains_score():
    mnemonics = ["vsetvli"] * 2 + ["vadd.vv"] * 48
    result = analyze_vector_quality(mnemonics)
    text = format_vector_quality_report(result)
    assert "Quality score" in text or "quality" in text.lower()
