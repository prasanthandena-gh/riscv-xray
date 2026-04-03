"""Tests for function_diff.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.function_diff import diff_functions


def _fake_funcs(ext_pcts, total=200):
    """Build a {func_name: data_dict} structure for testing."""
    from riscv_xray.extensions import EXTENSION_ORDER
    data = {"_total": total}
    for ext in EXTENSION_ORDER:
        pct = ext_pcts.get(ext, 0.0)
        data[ext] = {
            "count": int(total * pct / 100),
            "percentage": pct,
            "status": "unused" if pct == 0 else "in_use",
        }
    return data


def test_diff_no_change():
    """Identical function profiles => no significant changes."""
    funcs = {"main": _fake_funcs({"RVV": 50.0, "Base": 50.0})}
    text = diff_functions(funcs, funcs, "v1", "v2")
    assert "No per-function changes" in text


def test_diff_shows_changed_function():
    """Function with large RVV delta appears in output."""
    funcs1 = {"compute": _fake_funcs({"RVV": 10.0, "Base": 90.0})}
    funcs2 = {"compute": _fake_funcs({"RVV": 60.0, "Base": 40.0})}
    text = diff_functions(funcs1, funcs2, "v1", "v2")
    assert "compute" in text
    assert "RVV" in text


def test_diff_detects_new_function():
    """Function present only in binary2 is flagged as new."""
    funcs1 = {"main": _fake_funcs({"Base": 100.0})}
    funcs2 = {
        "main":       _fake_funcs({"Base": 100.0}),
        "new_kernel": _fake_funcs({"RVV": 80.0, "Base": 20.0}),
    }
    text = diff_functions(funcs1, funcs2, "v1", "v2")
    assert "new_kernel" in text
    assert "[+]" in text


def test_diff_detects_removed_function():
    """Function present only in binary1 is flagged as removed."""
    funcs1 = {
        "main":      _fake_funcs({"Base": 100.0}),
        "old_func":  _fake_funcs({"Base": 100.0}),
    }
    funcs2 = {"main": _fake_funcs({"Base": 100.0})}
    text = diff_functions(funcs1, funcs2, "v1", "v2")
    assert "old_func" in text
    assert "[-]" in text


def test_diff_threshold_filters_small_changes():
    """Changes below threshold not shown."""
    funcs1 = {"fn": _fake_funcs({"RVV": 10.0, "Base": 90.0})}
    funcs2 = {"fn": _fake_funcs({"RVV": 12.0, "Base": 88.0})}
    # Default threshold is 5pp; 2pp change should not appear
    text = diff_functions(funcs1, funcs2, "v1", "v2", min_delta=5.0)
    assert "No per-function changes" in text


def test_diff_header_contains_names():
    funcs1 = {"main": _fake_funcs({"Base": 100.0})}
    funcs2 = {"main": _fake_funcs({"Base": 100.0})}
    text = diff_functions(funcs1, funcs2, "binary_a", "binary_b")
    assert "binary_a" in text
    assert "binary_b" in text


def test_diff_empty_functions():
    """Both binaries have no functions => graceful output."""
    text = diff_functions({}, {}, "v1", "v2")
    assert "No per-function changes" in text
