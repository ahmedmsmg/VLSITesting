"""Tests for SVA-like assertion primitives."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from uvm.assertions import (
    AssertionResult,
    ConcurrentAssertion,
    ImmediateAssertion,
    PropertySequence,
)


# ── AssertionResult ───────────────────────────────────────────────────────────

def test_assertion_result_pass_str():
    r = AssertionResult(name="p", passed=True)
    assert "PASS" in str(r)
    assert "p" in str(r)


def test_assertion_result_fail_str():
    r = AssertionResult(name="p", passed=False, message="wrong value")
    s = str(r)
    assert "FAIL" in s
    assert "wrong value" in s


# ── ImmediateAssertion ────────────────────────────────────────────────────────

def test_immediate_assertion_passes():
    ia = ImmediateAssertion("z_is_1", lambda txn: txn["outputs"]["Z"] == "1")
    result = ia.check({"inputs": {}, "outputs": {"Z": "1"}})
    assert result.passed is True


def test_immediate_assertion_fails():
    ia = ImmediateAssertion("z_is_1", lambda txn: txn["outputs"]["Z"] == "1")
    result = ia.check({"inputs": {}, "outputs": {"Z": "0"}})
    assert result.passed is False


def test_immediate_assertion_accumulates_results():
    ia = ImmediateAssertion("a", lambda t: t["v"] == "1")
    ia.check({"v": "1"})
    ia.check({"v": "0"})
    ia.check({"v": "1"})
    assert ia.pass_count == 2
    assert ia.fail_count == 1


def test_immediate_assertion_exception_is_fail():
    ia = ImmediateAssertion("bad", lambda t: t["missing_key"])
    result = ia.check({})
    assert result.passed is False
    assert "Exception" in result.message


def test_immediate_assertion_report():
    ia = ImmediateAssertion("p", lambda t: t.get("v") == "1")
    ia.check({"v": "1"})
    ia.check({"v": "0"})
    report = ia.report()
    assert "1/2 passed" in report


# ── ConcurrentAssertion ───────────────────────────────────────────────────────

def test_concurrent_assertion_same_cycle():
    """antecedent and consequent check the same transaction (depth=1)."""
    ca = ConcurrentAssertion(
        name="a_implies_z",
        antecedent=lambda t: t["inputs"].get("A") == "1",
        consequent=lambda t: t["outputs"].get("Z") == "1",
        history_depth=1,
    )
    # A=1, Z=1 → should pass
    result = ca.check({"inputs": {"A": "1"}, "outputs": {"Z": "1"}})
    assert result is not None
    assert result.passed is True


def test_concurrent_assertion_same_cycle_fails():
    ca = ConcurrentAssertion(
        name="a_implies_z",
        antecedent=lambda t: t["inputs"].get("A") == "1",
        consequent=lambda t: t["outputs"].get("Z") == "1",
        history_depth=1,
    )
    result = ca.check({"inputs": {"A": "1"}, "outputs": {"Z": "0"}})
    assert result is not None
    assert result.passed is False


def test_concurrent_assertion_antecedent_not_fired():
    ca = ConcurrentAssertion(
        name="a_implies_z",
        antecedent=lambda t: t["inputs"].get("A") == "1",
        consequent=lambda t: t["outputs"].get("Z") == "1",
        history_depth=1,
    )
    # A=0 → antecedent does not fire → no assertion to check
    result = ca.check({"inputs": {"A": "0"}, "outputs": {"Z": "0"}})
    assert result is None


def test_concurrent_assertion_multi_cycle():
    """Antecedent fires at step 0, consequent checked at step 1."""
    ca = ConcurrentAssertion(
        name="delayed",
        antecedent=lambda t: t.get("trigger") is True,
        consequent=lambda t: t.get("response") is True,
        history_depth=2,
    )
    # Step 0: trigger=True
    r0 = ca.check({"trigger": True, "response": False})
    assert r0 is None  # window not yet full (need 2 txns)

    # Step 1: response=True
    r1 = ca.check({"trigger": False, "response": True})
    assert r1 is not None
    assert r1.passed is True


def test_concurrent_assertion_window_not_full():
    """No result returned until history window is full."""
    ca = ConcurrentAssertion(
        name="check",
        antecedent=lambda t: True,
        consequent=lambda t: True,
        history_depth=3,
    )
    assert ca.check({"v": "0"}) is None
    assert ca.check({"v": "1"}) is None
    result = ca.check({"v": "0"})
    assert result is not None


# ── PropertySequence ──────────────────────────────────────────────────────────

def test_property_sequence_runs_all_assertions():
    ia1 = ImmediateAssertion("a1", lambda t: t.get("A") == "1")
    ia2 = ImmediateAssertion("a2", lambda t: t.get("B") == "1")
    ps = PropertySequence("suite")
    ps.add(ia1).add(ia2)

    results = ps.check({"A": "1", "B": "0"})
    assert len(results) == 2
    assert results[0].passed is True
    assert results[1].passed is False


def test_property_sequence_report():
    ia = ImmediateAssertion("p", lambda t: True)
    ia.check({})
    ps = PropertySequence("my_suite")
    ps.add(ia)
    assert "my_suite" in ps.report()
    assert "p" in ps.report()
