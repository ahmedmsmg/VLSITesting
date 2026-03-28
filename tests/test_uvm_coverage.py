"""Tests for CoverPoint, CoverCross, and CoverGroup."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from uvm.coverage import CoverCross, CoverGroup, CoverPoint


# ── CoverPoint ────────────────────────────────────────────────────────────────

def test_coverpoint_initial_all_zero():
    cp = CoverPoint("test", bins={
        "bin_a": lambda txn: txn.get("val") == "0",
        "bin_b": lambda txn: txn.get("val") == "1",
    })
    assert cp.bins_hit == 0
    assert cp.coverage_pct == 0.0


def test_coverpoint_sample_hits_bin():
    cp = CoverPoint("pi_val", bins={
        "zero": lambda txn: txn.get("inputs", {}).get("A") == "0",
        "one":  lambda txn: txn.get("inputs", {}).get("A") == "1",
    })
    cp.sample({"inputs": {"A": "0"}})
    assert cp.hit_count["zero"] == 1
    assert cp.hit_count["one"] == 0
    assert cp.bins_hit == 1


def test_coverpoint_full_coverage():
    cp = CoverPoint("pi_val", bins={
        "zero": lambda txn: txn.get("inputs", {}).get("A") == "0",
        "one":  lambda txn: txn.get("inputs", {}).get("A") == "1",
    })
    cp.sample({"inputs": {"A": "0"}})
    cp.sample({"inputs": {"A": "1"}})
    assert cp.bins_hit == 2
    assert cp.coverage_pct == 100.0


def test_coverpoint_report_contains_name():
    cp = CoverPoint("my_cp", bins={"a": lambda t: True})
    cp.sample({})
    assert "my_cp" in cp.report()


def test_coverpoint_empty_bins():
    cp = CoverPoint("empty", bins={})
    assert cp.coverage_pct == 100.0  # vacuously complete


def test_coverpoint_bad_predicate_does_not_raise():
    cp = CoverPoint("safe", bins={
        "bad": lambda txn: txn["nonexistent"],
    })
    cp.sample({})  # should not raise
    assert cp.hit_count["bad"] == 0


# ── CoverCross ────────────────────────────────────────────────────────────────

def test_cover_cross_requires_two_points():
    cp = CoverPoint("cp", bins={"a": lambda t: True})
    with pytest.raises(ValueError):
        CoverCross("cx", [cp])


def test_cover_cross_hit():
    cp_a = CoverPoint("a_val", bins={
        "a0": lambda t: t.get("inputs", {}).get("A") == "0",
        "a1": lambda t: t.get("inputs", {}).get("A") == "1",
    })
    cp_b = CoverPoint("b_val", bins={
        "b0": lambda t: t.get("inputs", {}).get("B") == "0",
        "b1": lambda t: t.get("inputs", {}).get("B") == "1",
    })
    cx = CoverCross("ab_cross", [cp_a, cp_b])
    cx.sample({"inputs": {"A": "0", "B": "0"}})
    assert cx.cross_hit[("a0", "b0")] == 1
    assert cx.cross_bins_hit == 1
    assert cx.total_cross_bins == 4


def test_cover_cross_full_coverage():
    cp_a = CoverPoint("a", bins={"a0": lambda t: t["A"] == "0", "a1": lambda t: t["A"] == "1"})
    cp_b = CoverPoint("b", bins={"b0": lambda t: t["B"] == "0", "b1": lambda t: t["B"] == "1"})
    cx = CoverCross("cross", [cp_a, cp_b])
    for a in ["0", "1"]:
        for b in ["0", "1"]:
            cx.sample({"A": a, "B": b})
    assert cx.coverage_pct == 100.0


# ── CoverGroup ────────────────────────────────────────────────────────────────

def test_covergroup_sample_count():
    cg = CoverGroup("g")
    cg.sample({"x": 1})
    cg.sample({"x": 2})
    assert cg._sample_count == 2


def test_covergroup_overall_coverage():
    cg = CoverGroup("g")
    cp = cg.add_coverpoint(CoverPoint("cp", bins={
        "a": lambda t: t.get("v") == "0",
        "b": lambda t: t.get("v") == "1",
    }))
    cg.sample({"v": "0"})
    # 1 of 2 bins hit → 50%
    assert cg.overall_coverage_pct == pytest.approx(50.0)


def test_covergroup_empty():
    cg = CoverGroup("empty")
    assert cg.overall_coverage_pct == 100.0


def test_covergroup_report():
    cg = CoverGroup("test_group")
    cg.sample({})
    report = cg.report()
    assert "test_group" in report
    assert "Samples" in report
