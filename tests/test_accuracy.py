"""Tests for accuracy.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.accuracy import format_accuracy_warning


def test_static_mode_returns_warning():
    result = format_accuracy_warning("static")
    assert result is not None
    assert "static" in result.lower()
    assert "dead code" in result.lower() or "Dead code" in result


def test_dynamic_mode_returns_none():
    result = format_accuracy_warning("dynamic")
    assert result is None


def test_plugin_mode_returns_none():
    result = format_accuracy_warning("plugin")
    assert result is None


def test_warning_mentions_loop_counts():
    result = format_accuracy_warning("static")
    assert "loop" in result.lower() or "Loop" in result


def test_warning_suggests_dynamic():
    result = format_accuracy_warning("static")
    assert "dynamic" in result.lower() or "plugin" in result.lower()
