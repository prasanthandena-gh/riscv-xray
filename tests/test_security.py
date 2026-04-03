"""Tests for security.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.security import analyze_security, format_security_report, MARKET_CFI_REQUIREMENTS


def _make_data(filp_pct=0.0, fiss_pct=0.0):
    return {
        "Zicfilp": {"count": 0, "percentage": filp_pct, "status": "unused"},
        "Zicfiss": {"count": 0, "percentage": fiss_pct, "status": "unused"},
        "_total": 100,
    }


def test_cfi_absent():
    data = _make_data(filp_pct=0.0, fiss_pct=0.0)
    result = analyze_security(data)
    assert result["cfi_status"] == "absent"
    assert not result["zicfilp_active"]
    assert not result["zicfiss_active"]


def test_cfi_partial():
    data = _make_data(filp_pct=5.0, fiss_pct=0.0)
    result = analyze_security(data)
    assert result["cfi_status"] == "partial"
    assert result["zicfilp_active"]
    assert not result["zicfiss_active"]


def test_cfi_full():
    data = _make_data(filp_pct=3.0, fiss_pct=4.0)
    result = analyze_security(data)
    assert result["cfi_status"] == "full"
    assert result["zicfilp_active"]
    assert result["zicfiss_active"]


def test_automotive_fail():
    """Automotive requires CFI; absent => FAIL."""
    data = _make_data(filp_pct=0.0, fiss_pct=0.0)
    result = analyze_security(data)
    assert result["market_impact"]["automotive"]["status"] == "FAIL"


def test_embedded_ok():
    """Embedded does not require CFI; absent => OK."""
    data = _make_data(filp_pct=0.0, fiss_pct=0.0)
    result = analyze_security(data)
    assert result["market_impact"]["embedded"]["status"] == "OK"


def test_server_warn_on_partial():
    """Server requires CFI; partial => WARN."""
    data = _make_data(filp_pct=5.0, fiss_pct=0.0)
    result = analyze_security(data)
    assert result["market_impact"]["server"]["status"] == "WARN"


def test_format_security_report_absent():
    data = _make_data()
    result = analyze_security(data)
    text = format_security_report(result)
    assert "Not detected" in text or "absent" in text.lower()
    assert "Zicfilp" in text
    assert "Zicfiss" in text


def test_format_security_report_full():
    data = _make_data(filp_pct=5.0, fiss_pct=5.0)
    result = analyze_security(data)
    text = format_security_report(result)
    assert "Full CFI" in text
