"""Tests for profile_checker.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.profile_checker import check_profile, get_profile_names, PROFILES


def _make_data(ext_pcts):
    """Build a minimal data dict with given extension percentages."""
    data = {"_total": 1000}
    all_exts = [
        "RVV", "Zba", "Zbb", "Zicond", "Zcb", "Zfa",
        "Zvbb", "Zvkng", "Zvfhmin", "Zicntr",
        "Zbc", "Zvfh", "Zvfbfmin", "Zvfbfwma", "Zvksg",
        "Zicfilp", "Zicfiss", "Base",
    ]
    for ext in all_exts:
        pct = ext_pcts.get(ext, 0.0)
        data[ext] = {"count": int(1000 * pct / 100), "percentage": pct, "status": "unused"}
    return data


def test_rva23_perfect_score():
    """All mandatory RVA23 extensions active => score == 10/10."""
    pcts = {ext: 10.0 for ext in PROFILES["rva23"]["mandatory"]}
    data = _make_data(pcts)
    result = check_profile(data, "rva23")
    assert result["score"] == result["total_mandatory"]
    assert result["percentage"] == 100.0
    assert result["missing"] == []
    assert result["minimal"] == []


def test_rva23_zero_score():
    """No extensions active => score 0, all mandatory missing."""
    data = _make_data({})
    result = check_profile(data, "rva23")
    assert result["score"] == 0
    assert len(result["missing"]) == result["total_mandatory"]


def test_profile_suggested_march():
    """Missing RVV and Zicond => suggested march includes 'v' and 'zicond'."""
    pcts = {ext: 10.0 for ext in PROFILES["rva23"]["mandatory"] if ext not in ("RVV", "Zicond")}
    data = _make_data(pcts)
    result = check_profile(data, "rva23")
    march = result["suggested_march"]
    assert "zicond" in march
    # RVV maps to 'v' suffix on rv64gcv
    assert "v" in march


def test_rva23_ai_profile():
    """rva23+ai profile includes Zvfbfmin and Zvfbfwma as mandatory."""
    mandatory = PROFILES["rva23+ai"]["mandatory"]
    assert "Zvfbfmin" in mandatory
    assert "Zvfbfwma" in mandatory
    # Score 0 on all-zero data
    data = _make_data({})
    result = check_profile(data, "rva23+ai")
    assert result["score"] == 0
    assert "Zvfbfmin" in result["missing"]


def test_minimal_threshold():
    """Extension at 2% is 'minimal', not active or missing."""
    pcts = {ext: 10.0 for ext in PROFILES["rva23"]["mandatory"]}
    pcts["Zicond"] = 2.0  # below MINIMAL_THRESHOLD (5%)
    data = _make_data(pcts)
    result = check_profile(data, "rva23")
    assert "Zicond" in result["minimal"]
    assert "Zicond" not in result["active"]
    assert "Zicond" not in result["missing"]
    # Score counts only fully active
    assert result["score"] == result["total_mandatory"] - 1


def test_get_profile_names():
    names = get_profile_names()
    assert "rva23" in names
    assert "rva22" in names
    assert "rva23+ai" in names
