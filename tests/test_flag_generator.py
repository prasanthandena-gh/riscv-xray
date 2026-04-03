"""Tests for flag_generator.py (multi-signal mtune with confidence)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.flag_generator import suggest_mtune, format_mtune_section, HARDWARE_PROFILES


def _make_data(rvv_pct=0.0, zba_pct=0.0, base_pct=100.0):
    return {
        "RVV":  {"count": 0, "percentage": rvv_pct,  "status": "unused"},
        "Zba":  {"count": 0, "percentage": zba_pct,  "status": "unused"},
        "Base": {"count": 0, "percentage": base_pct, "status": "info"},
        "_total": 100,
    }


def test_high_rvv_scores_p670_higher_than_u74():
    data = _make_data(rvv_pct=50.0, zba_pct=10.0, base_pct=40.0)
    result = suggest_mtune(data)
    assert result["recommended"] == "sifive-p670"
    assert result["exec_type"] == "ooo"


def test_branch_heavy_scalar_recommends_inorder():
    data = _make_data(rvv_pct=1.0, base_pct=95.0)
    result = suggest_mtune(data)
    assert result["exec_type"] == "inorder"
    assert result["recommended"] in ("sifive-u74", "thead-c906")


def test_low_confidence_still_recommends_best_match():
    """Low confidence still picks the best-scoring hardware, not forced generic."""
    data = _make_data(rvv_pct=5.0, base_pct=90.0)
    result = suggest_mtune(data)
    # Low RVV + high base => in-order is the best match
    assert result["exec_type"] == "inorder"
    assert result["confidence"] in ("low", "medium")


def test_reasoning_not_empty():
    data = _make_data(rvv_pct=50.0, zba_pct=10.0)
    result = suggest_mtune(data)
    assert len(result["reasoning"]) > 0


def test_disclaimer_always_present():
    for rvv in (0, 15, 50):
        data = _make_data(rvv_pct=rvv)
        result = suggest_mtune(data)
        assert "disclaimer" in result
        assert len(result["disclaimer"]) > 10


def test_format_shows_confidence():
    data = _make_data(rvv_pct=50.0, zba_pct=10.0)
    suggestion = suggest_mtune(data)
    text = format_mtune_section(suggestion)
    assert "Confidence" in text or "confidence" in text.lower()


def test_format_shows_disclaimer():
    data = _make_data(rvv_pct=5.0)
    suggestion = suggest_mtune(data)
    text = format_mtune_section(suggestion)
    assert "Disclaimer" in text or "disclaimer" in text.lower()


def test_format_shows_reasoning_bullets():
    data = _make_data(rvv_pct=50.0)
    suggestion = suggest_mtune(data)
    text = format_mtune_section(suggestion)
    assert " - " in text or "•" in text or "Why" in text


def test_hardware_profiles_have_required_keys():
    for hw in HARDWARE_PROFILES:
        assert "tune_flag" in hw
        assert "type" in hw
        assert "description" in hw
        assert "score_weights" in hw


def test_result_has_all_keys():
    data = _make_data(rvv_pct=30.0)
    result = suggest_mtune(data)
    for key in ("recommended", "confidence", "score", "alternative",
                "reasoning", "exec_type", "disclaimer"):
        assert key in result
