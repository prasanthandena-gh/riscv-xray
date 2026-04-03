"""Tests for classifier.py - updated for Phase 2 extensions."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.classifier import classify, top_extension


def test_vector_instructions():
    mnemonics = ["vadd.vv", "vsub.vv", "vmul.vv", "add", "add", "add"]
    data = classify(mnemonics)
    assert data["RVV"]["count"] == 3
    assert data["Base"]["count"] == 3


def test_empty_input():
    data = classify([])
    for ext in data:
        if ext == "_total":
            assert data[ext] == 0
        else:
            assert data[ext]["count"] == 0
    assert data["_total"] == 0


def test_base_catches_unknown():
    mnemonics = ["unknowninstr", "anotherfake"]
    data = classify(mnemonics)
    assert data["Base"]["count"] == 2
    for ext in ["RVV", "Zba", "Zbb", "Zbc", "Zicntr"]:
        assert data[ext]["count"] == 0


def test_percentage_sums_to_100():
    mnemonics = ["vadd.vv", "add", "clz", "sh1add"]
    data = classify(mnemonics)
    total_pct = sum(
        info["percentage"] for key, info in data.items()
        if not key.startswith("_")
    )
    assert abs(total_pct - 100.0) < 0.2


def test_status_thresholds():
    mnemonics = ["vadd.vv", "vsub.vv", "vmul.vv", "add"]
    data = classify(mnemonics)
    assert data["RVV"]["status"] == "heavy_use"


def test_zba_classification():
    mnemonics = ["sh1add", "sh2add", "sh3add", "add"]
    data = classify(mnemonics)
    assert data["Zba"]["count"] == 3
    assert data["Base"]["count"] == 1


def test_zbb_classification():
    mnemonics = ["clz", "ctz", "cpop", "andn", "add"]
    data = classify(mnemonics)
    assert data["Zbb"]["count"] == 4
    assert data["Base"]["count"] == 1


def test_top_extension():
    mnemonics = ["vadd.vv", "vsub.vv", "vmul.vv", "sh1add"]
    data = classify(mnemonics)
    assert top_extension(data) == "RVV"


def test_top_extension_empty():
    data = classify([])
    from riscv_xray.extensions import EXTENSION_ORDER
    result = top_extension(data)
    assert result is None or result in EXTENSION_ORDER


def test_fixture_log():
    from riscv_xray.parser import parse_log_file
    fixtures = os.path.join(os.path.dirname(__file__), "fixtures", "sample_log.txt")
    mnemonics = parse_log_file(fixtures)
    assert len(mnemonics) > 0
    data = classify(mnemonics)
    assert data["_total"] == len(mnemonics)
    assert data["RVV"]["count"] >= 3


# Phase 2 new extension tests

def test_zicond_classification():
    mnemonics = ["czero.eqz", "czero.nez", "add"]
    data = classify(mnemonics)
    assert data["Zicond"]["count"] == 2
    assert data["Base"]["count"] == 1


def test_zcb_classification():
    mnemonics = ["c.lbu", "c.not", "c.mul", "add"]
    data = classify(mnemonics)
    assert data["Zcb"]["count"] == 3
    assert data["Base"]["count"] == 1


def test_zfa_classification():
    mnemonics = ["fli.s", "fminm.s", "fmaxm.s", "fadd.s"]
    data = classify(mnemonics)
    assert data["Zfa"]["count"] == 3
    # fadd goes to Base (not in Zfa prefixes)
    assert data["Base"]["count"] == 1


def test_zvbb_classification():
    mnemonics = ["vbrev8", "vrev8", "vandn.vv", "add"]
    data = classify(mnemonics)
    assert data["Zvbb"]["count"] == 3
    assert data["Base"]["count"] == 1


def test_zvkng_classification():
    mnemonics = ["vghsh.vv", "vaesdf.vv", "vaeskf1.vi", "add"]
    data = classify(mnemonics)
    assert data["Zvkng"]["count"] == 3
    assert data["Base"]["count"] == 1


def test_zvfhmin_classification():
    mnemonics = ["vfncvt.f.f.w", "vfwcvt.f.f.v", "add"]
    data = classify(mnemonics)
    assert data["Zvfhmin"]["count"] == 2
    assert data["Base"]["count"] == 1


def test_zvfbfwma_classification():
    mnemonics = ["vfwmaccbf16.vv", "vfwmaccbf16.vf", "add"]
    data = classify(mnemonics)
    assert data["Zvfbfwma"]["count"] == 2


def test_security_extension_classification():
    mnemonics = ["lpad", "sspush", "sspopchk", "add"]
    data = classify(mnemonics)
    assert data["Zicfilp"]["count"] == 1
    assert data["Zicfiss"]["count"] == 2
    assert data["Base"]["count"] == 1


def test_zbkx_removed():
    """Zbkx must not be in extensions — it was removed in Phase 2."""
    from riscv_xray.extensions import EXTENSIONS
    assert "Zbkx" not in EXTENSIONS
