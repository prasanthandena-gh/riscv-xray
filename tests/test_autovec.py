"""Tests for autovec.py (objdump-based function analysis)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.autovec import (
    analyze_function,
    analyze_binary,
    format_autovec_report,
)


def test_clean_function_no_branch():
    """Function without a branch is not flagged."""
    mnemonics = ["addi", "sd", "ld", "fadd.s"] * 5
    assert analyze_function("fn", mnemonics) is None


def test_clean_function_already_vectorized():
    """Function with RVV instructions is not flagged."""
    mnemonics = ["fadd.s"] * 10 + ["vadd.vv"] * 5 + ["beq"] * 3 + ["add"] * 5
    assert analyze_function("fn", mnemonics) is None


def test_clean_function_too_small():
    """Functions with < 10 instructions are not flagged."""
    mnemonics = ["fadd.s", "beq", "add"]
    assert analyze_function("tiny", mnemonics) is None


def test_missed_float_vectorization():
    """Loop + scalar floats + no RVV => flagged."""
    mnemonics = (["fadd.s"] * 15 + ["fmul.s"] * 10
                 + ["beq"] * 3 + ["lw"] * 5 + ["sw"] * 5)
    result = analyze_function("compute", mnemonics)
    assert result is not None
    assert result["function"] == "compute"
    assert result["has_loop"] is True
    assert result["vector_instruction_count"] == 0
    assert result["severity"] in ("high", "medium", "low")


def test_severity_high():
    """More than 20 pattern instructions => high severity."""
    mnemonics = ["fadd.s"] * 25 + ["beq"] * 3 + ["add"] * 5
    result = analyze_function("hot_fn", mnemonics)
    assert result is not None
    assert result["severity"] == "high"


def test_severity_medium():
    """9-20 pattern instructions => medium severity."""
    mnemonics = ["fadd.s"] * 10 + ["beq"] * 3 + ["add"] * 10
    result = analyze_function("med_fn", mnemonics)
    assert result is not None
    assert result["severity"] == "medium"


def test_analyze_binary():
    """analyze_binary returns opportunities for vectorizable functions."""
    functions = {
        "vectorized": {
            "mnemonics": ["vadd.vv"] * 10 + ["beq"] * 3 + ["add"] * 5,
            "instruction_count": 18,
        },
        "missed": {
            "mnemonics": ["fadd.s"] * 15 + ["beq"] * 3 + ["add"] * 5,
            "instruction_count": 23,
        },
        "tiny": {
            "mnemonics": ["fadd.s", "beq"],
            "instruction_count": 2,
        },
    }
    result = analyze_binary(functions)
    names = [o["function"] for o in result["opportunities"]]
    assert "missed" in names
    assert "vectorized" not in names
    assert "tiny" not in names
    assert result["total_functions"] == 3


def test_format_empty_when_no_opportunities():
    result = analyze_binary({})
    text = format_autovec_report(result)
    assert text == ""


def test_format_contains_function_name():
    functions = {
        "hot_loop": {
            "mnemonics": ["fadd.s"] * 25 + ["beq"] * 3 + ["add"] * 5,
            "instruction_count": 33,
        }
    }
    result = analyze_binary(functions)
    text = format_autovec_report(result)
    assert "hot_loop" in text
    assert "Autovectorization" in text or "Missed" in text


def test_format_includes_disclaimer():
    functions = {
        "fn": {
            "mnemonics": ["fadd.s"] * 25 + ["beq"] * 3 + ["add"] * 5,
            "instruction_count": 33,
        }
    }
    result = analyze_binary(functions)
    text = format_autovec_report(result)
    assert "Static analysis" in text or "static" in text.lower()
    assert "false positive" in text.lower() or "gcc" in text.lower()
