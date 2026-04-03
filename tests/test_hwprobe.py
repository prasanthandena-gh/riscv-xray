"""Tests for hwprobe.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.hwprobe import (
    generate_hwprobe_snippet,
    generate_snippets_for_missing,
    format_hwprobe_section,
    HWPROBE_CONSTANTS,
)


def test_snippet_rvv():
    """RVV has a known hwprobe constant."""
    snippet = generate_hwprobe_snippet("RVV")
    assert snippet is not None
    assert "RISCV_HWPROBE_EXT_ZVE64X" in snippet
    assert "has_rvv" in snippet


def test_snippet_zvfbfmin():
    """Zvfbfmin has a known hwprobe constant."""
    snippet = generate_hwprobe_snippet("Zvfbfmin")
    assert snippet is not None
    assert "RISCV_HWPROBE_EXT_ZVFBFMIN" in snippet


def test_snippet_unknown():
    """Zcb has no hwprobe constant => returns None."""
    snippet = generate_hwprobe_snippet("Zcb")
    assert snippet is None


def test_snippet_zicntr_none():
    """Zicntr is mapped to None => no snippet."""
    snippet = generate_hwprobe_snippet("Zicntr")
    assert snippet is None


def test_snippets_for_missing():
    """generate_snippets_for_missing returns content for known extensions."""
    missing = ["RVV", "Zba", "Zcb"]  # Zcb has no constant, others do
    result = generate_snippets_for_missing(missing)
    assert result != ""
    assert "RISCV_HWPROBE_EXT_ZVE64X" in result
    assert "RISCV_HWPROBE_EXT_ZBA" in result


def test_snippets_for_all_unknown():
    """All extensions without constants => empty string."""
    result = generate_snippets_for_missing(["Zcb", "Zfa", "Zicntr"])
    assert result == ""


def test_format_returns_none_for_no_hwprobe():
    """format_hwprobe_section returns None when nothing to show."""
    result = format_hwprobe_section(["Zcb", "Zfa"])
    assert result is None


def test_format_returns_section():
    """format_hwprobe_section returns a section string for known extensions."""
    result = format_hwprobe_section(["RVV", "Zba"])
    assert result is not None
    assert "Runtime Detection" in result
    assert "has_rvv" in result
