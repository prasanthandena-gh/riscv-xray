"""Tests for recommender.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.classifier import classify
from riscv_xray.recommender import recommend


def _make_data(ext_pcts, total=1000):
    """Build a minimal data dict with given extension percentages."""
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


def test_no_rvv_recommendation():
    """Binary with no RVV gets a 'no vector' recommendation."""
    data = _make_data({"Base": 100.0})
    recs = recommend(data, "mybinary")
    titles = [r["title"] for r in recs]
    assert any("No vector" in t for t in titles)


def test_heavy_rvv_recommendation():
    """High RVV usage gets a positive recommendation."""
    data = _make_data({"RVV": 60.0, "Base": 40.0})
    recs = recommend(data, "mybinary")
    titles = [r["title"] for r in recs]
    assert any("strong" in t.lower() or "Vector usage" in t for t in titles)


def test_moderate_rvv_recommendation():
    """Moderate RVV (20%) gets a 'moderate vector usage' recommendation."""
    data = _make_data({"RVV": 20.0, "Base": 80.0})
    recs = recommend(data, "mybinary")
    titles = [r["title"] for r in recs]
    assert any("Moderate" in t for t in titles)


def test_scalar_heavy_recommendation():
    """base_pct > 80 triggers a scalar-heavy warning."""
    data = _make_data({"Base": 95.0, "RVV": 5.0})
    recs = recommend(data, "mybinary")
    titles = [r["title"] for r in recs]
    assert any("scalar" in t.lower() for t in titles)


def test_rva23_action_always_present():
    """Every profiling result ends with RVA23 compile flag recommendation."""
    data = _make_data({"Base": 100.0})
    recs = recommend(data, "mybinary")
    actions = [r.get("action", "") or "" for r in recs]
    assert any("march" in a for a in actions)


def test_mandatory_unused_recommendation():
    """Unused mandatory extensions produce a recommendation."""
    # All mandatory extensions absent except Base
    data = _make_data({"Base": 100.0})
    recs = recommend(data, "mybinary")
    titles = [r["title"] for r in recs]
    assert any("unused" in t.lower() or "Mandatory" in t for t in titles)


def test_recommend_returns_list():
    mnemonics = ["vadd.vv", "add", "sh1add"]
    data = classify(mnemonics)
    recs = recommend(data, "testbin")
    assert isinstance(recs, list)
    assert len(recs) > 0
    for rec in recs:
        assert "icon" in rec
        assert "title" in rec
        assert "detail" in rec


def test_recommend_no_zbkx():
    """Zbkx must not appear in any recommendation (removed in Phase 2)."""
    data = _make_data({"Base": 100.0})
    recs = recommend(data, "mybinary")
    for rec in recs:
        assert "Zbkx" not in rec["title"]
        assert "Zbkx" not in (rec.get("detail") or "")
        assert "Zbkx" not in (rec.get("action") or "")
