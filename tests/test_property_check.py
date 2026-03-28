"""Unit tests for PropertyChecker (formal/property_check.py)."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuit import Circuit
from formal.property_check import Property, PropertyChecker, PropertyResult
from z3 import And, Implies, Not, Or


def make_and_circuit():
    c = Circuit("and")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "AND", ["A", "B"])
    c.build_topological()
    return c


def make_or_circuit():
    c = Circuit("or")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "OR", ["A", "B"])
    c.build_topological()
    return c


# ── Properties that HOLD ──────────────────────────────────────────────────────

def test_and_zero_when_a_zero():
    """AND(A,B) == 0 whenever A == 0."""
    prop = Property(
        name="and_zero_when_a_zero",
        formula=lambda enc: Implies(enc.var("A") == False, enc.var("Z") == False),
    )
    result = PropertyChecker(make_and_circuit()).check(prop)
    assert result.holds is True
    assert result.counterexample is None


def test_and_one_iff_both_one():
    """AND(A,B)==1  ↔  A==1 AND B==1."""
    prop = Property(
        name="and_iff",
        formula=lambda enc: enc.var("Z") == And(enc.var("A"), enc.var("B")),
    )
    result = PropertyChecker(make_and_circuit()).check(prop)
    assert result.holds is True


def test_or_zero_only_when_both_zero():
    """OR(A,B)==0  → A==0 AND B==0."""
    prop = Property(
        name="or_zero_implies_both_zero",
        formula=lambda enc: Implies(
            enc.var("Z") == False,
            And(enc.var("A") == False, enc.var("B") == False),
        ),
    )
    result = PropertyChecker(make_or_circuit()).check(prop)
    assert result.holds is True


# ── Properties that are VIOLATED ─────────────────────────────────────────────

def test_false_property_produces_counterexample():
    """AND output is always 1 — obviously false."""
    prop = Property(
        name="always_one",
        formula=lambda enc: enc.var("Z") == True,
    )
    result = PropertyChecker(make_and_circuit()).check(prop)
    assert result.holds is False
    assert result.counterexample is not None
    # Verify the counterexample actually violates the property
    ce = result.counterexample
    a, b = int(ce["A"]), int(ce["B"])
    assert (a & b) == 0  # AND should be 0 for this input


def test_or_always_zero_violated():
    prop = Property(
        name="or_always_zero",
        formula=lambda enc: enc.var("Z") == False,
    )
    result = PropertyChecker(make_or_circuit()).check(prop)
    assert result.holds is False
    assert result.counterexample is not None


def test_counterexample_values_are_binary():
    prop = Property("always_one", lambda enc: enc.var("Z") == True)
    result = PropertyChecker(make_and_circuit()).check(prop)
    ce = result.counterexample
    assert all(v in {"0", "1"} for v in ce.values())


# ── check_all ─────────────────────────────────────────────────────────────────

def test_check_all_returns_list():
    checker = PropertyChecker(make_and_circuit())
    props = [
        Property("p1", lambda enc: enc.var("Z") == And(enc.var("A"), enc.var("B"))),
        Property("p2", lambda enc: enc.var("Z") == True),  # false
    ]
    results = checker.check_all(props)
    assert len(results) == 2
    assert results[0].holds is True
    assert results[1].holds is False


# ── String representation ─────────────────────────────────────────────────────

def test_result_str_holds():
    r = PropertyResult(property_name="p", holds=True)
    assert "HOLDS" in str(r)


def test_result_str_violated():
    r = PropertyResult(property_name="p", holds=False, counterexample={"A": "0"})
    s = str(r)
    assert "VIOLATED" in s
    assert "A=0" in s
