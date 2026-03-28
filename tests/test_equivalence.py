"""Unit tests for CombinationalEquivalenceChecker."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuit import Circuit
from formal.equivalence import EquivalenceChecker, EquivalenceResult


def make_and():
    c = Circuit("and")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "AND", ["A", "B"])
    c.build_topological()
    return c


def make_nand_not():
    """NAND(A,B) → NOT → same function as AND."""
    c = Circuit("nand_not")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("tmp", "NAND", ["A", "B"])
    c.add_gate("Z", "NOT", ["tmp"])
    c.build_topological()
    return c


def make_or():
    c = Circuit("or")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "OR", ["A", "B"])
    c.build_topological()
    return c


# ── Equivalent circuits ────────────────────────────────────────────────────────

def test_circuit_equivalent_to_itself(t4_3):
    from ckt_parser import parse_file
    c2 = parse_file("examples/t4_3.ckt")
    result = EquivalenceChecker(t4_3, c2).check()
    assert result.equivalent is True
    assert result.counterexample is None


def test_and_equivalent_to_nand_not():
    result = EquivalenceChecker(make_and(), make_nand_not()).check()
    assert result.equivalent is True


# ── Non-equivalent circuits ───────────────────────────────────────────────────

def test_and_not_equivalent_to_or():
    result = EquivalenceChecker(make_and(), make_or()).check()
    assert result.equivalent is False
    assert result.counterexample is not None
    # Counterexample: A=1,B=0 or A=0,B=1 (AND=0, OR=1)
    ce = result.counterexample
    a, b = int(ce["A"]), int(ce["B"])
    assert (a & b) != (a | b), "Counterexample should actually differ"


def test_counterexample_is_concrete():
    result = EquivalenceChecker(make_and(), make_or()).check()
    ce = result.counterexample
    assert all(v in {"0", "1"} for v in ce.values())


def test_differing_outputs_listed():
    result = EquivalenceChecker(make_and(), make_or()).check()
    assert len(result.differing_outputs) > 0


# ── Error handling ────────────────────────────────────────────────────────────

def test_pi_mismatch_raises():
    c1 = Circuit()
    c1.add_pi("A"); c1.add_po("Z"); c1.add_gate("Z", "BUF", ["A"]); c1.build_topological()
    c2 = Circuit()
    c2.add_pi("B"); c2.add_po("Z"); c2.add_gate("Z", "BUF", ["B"]); c2.build_topological()
    with pytest.raises(ValueError, match="PI mismatch"):
        EquivalenceChecker(c1, c2)


def test_po_mismatch_raises():
    c1 = Circuit()
    c1.add_pi("A"); c1.add_po("Z"); c1.add_gate("Z", "BUF", ["A"]); c1.build_topological()
    c2 = Circuit()
    c2.add_pi("A"); c2.add_po("W"); c2.add_gate("W", "BUF", ["A"]); c2.build_topological()
    with pytest.raises(ValueError, match="PO mismatch"):
        EquivalenceChecker(c1, c2)


# ── String representation ─────────────────────────────────────────────────────

def test_result_str_equivalent():
    r = EquivalenceResult(equivalent=True)
    assert "EQUIVALENT" in str(r)


def test_result_str_not_equivalent():
    r = EquivalenceResult(equivalent=False, counterexample={"A": "1"}, differing_outputs=["Z"])
    s = str(r)
    assert "NOT EQUIVALENT" in s
    assert "A=1" in s
