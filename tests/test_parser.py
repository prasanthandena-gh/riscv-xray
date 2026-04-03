"""Tests for parser.py"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.parser import parse_xray_output, parse_log_file


def test_parse_basic():
    raw = "XRAY_INSN:add\nXRAY_INSN:addi\nXRAY_DONE\n"
    result = parse_xray_output(raw)
    assert result == ["add", "addi"]


def test_parse_stops_at_done():
    raw = "XRAY_INSN:add\nXRAY_DONE\nXRAY_INSN:sub\n"
    result = parse_xray_output(raw)
    assert result == ["add"]
    assert "sub" not in result


def test_parse_empty():
    result = parse_xray_output("")
    assert result == []


def test_parse_ignores_non_xray_lines():
    raw = "some noise\nXRAY_INSN:add\nmore noise\nXRAY_INSN:mul\n"
    result = parse_xray_output(raw)
    assert result == ["add", "mul"]


def test_parse_log_file():
    fixtures = os.path.join(os.path.dirname(__file__), "fixtures", "sample_log.txt")
    result = parse_log_file(fixtures)
    assert "vadd.vv" in result
    assert "add" in result


def test_parse_log_file_not_found():
    import pytest
    with pytest.raises(FileNotFoundError):
        parse_log_file("/nonexistent/path/log.txt")
