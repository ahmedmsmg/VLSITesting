"""Unit tests for the Circuit data structure and simulation."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuit import Circuit, Gate
from fault import Fault
import logic5 as L


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_simple_and():
    """Build a 2-input AND circuit: A AND B = Z."""
    c = Circuit("and_test")
    c.add_pi("A")
    c.add_pi("B")
    c.add_po("Z")
    c.add_gate("Z", "AND", ["A", "B"])
    c.build_topological()
    return c


def make_simple_or():
    """Build a 2-input OR circuit: A OR B = Z."""
    c = Circuit("or_test")
    c.add_pi("A")
    c.add_pi("B")
    c.add_po("Z")
    c.add_gate("Z", "OR", ["A", "B"])
    c.build_topological()
    return c


def make_inverter():
    """Build a single inverter: NOT A = Z."""
    c = Circuit("inv_test")
    c.add_pi("A")
    c.add_po("Z")
    c.add_gate("Z", "NOT", ["A"])
    c.build_topological()
    return c


# ── Circuit construction ───────────────────────────────────────────────────────

def test_add_pi_deduplication():
    c = Circuit()
    c.add_pi("A")
    c.add_pi("A")
    assert c.primary_inputs.count("A") == 1


def test_add_po_deduplication():
    c = Circuit()
    c.add_po("Z")
    c.add_po("Z")
    assert c.primary_outputs.count("Z") == 1


def test_nodes_populated():
    c = make_simple_and()
    assert "A" in c.nodes
    assert "B" in c.nodes
    assert "Z" in c.nodes


def test_gate_type_normalized_to_uppercase():
    c = Circuit()
    c.add_pi("A")
    c.add_pi("B")
    c.add_gate("Z", "and", ["A", "B"])
    assert c.gates[0].type == "AND"


def test_build_topological_order():
    """A 3-gate chain should be ordered source → middle → sink."""
    c = Circuit()
    c.add_pi("A")
    c.add_gate("M", "NOT", ["A"])
    c.add_gate("Z", "BUF", ["M"])
    c.build_topological()
    outputs = [g.output for g in c.topo]
    assert outputs.index("M") < outputs.index("Z")


def test_build_topological_cycle_raises():
    c = Circuit()
    c.add_pi("A")
    c.add_gate("X", "BUF", ["Y"])
    c.add_gate("Y", "BUF", ["X"])
    with pytest.raises(ValueError):
        c.build_topological()


def test_fault_list_count():
    c = make_simple_and()
    faults = c.fault_list()
    # 3 nodes (A, B, Z) → 6 faults
    assert len(faults) == 6
    assert all(isinstance(f, Fault) for f in faults)


# ── imply (five-valued simulation) ────────────────────────────────────────────

def test_imply_and_gate_basic():
    c = make_simple_and()
    vals = c.imply({"A": "1", "B": "1"})
    assert vals["Z"] == "1"

    vals = c.imply({"A": "0", "B": "1"})
    assert vals["Z"] == "0"


def test_imply_or_gate_basic():
    c = make_simple_or()
    vals = c.imply({"A": "0", "B": "0"})
    assert vals["Z"] == "0"

    vals = c.imply({"A": "1", "B": "0"})
    assert vals["Z"] == "1"


def test_imply_unknown_propagation():
    c = make_simple_and()
    vals = c.imply({"A": "X"})
    assert vals["Z"] == "X"


def test_imply_fault_activation_sa0():
    """sa0 on Z with A=1, B=1 → Z should show D (good=1, faulty=0)."""
    c = make_simple_and()
    fault = Fault("Z", 0)
    vals = c.imply({"A": "1", "B": "1"}, fault=fault)
    assert vals["Z"] == L.LD


def test_imply_fault_activation_sa1():
    """sa1 on Z with A=0, B=0 → Z should show D' (good=0, faulty=1)."""
    c = make_simple_and()
    fault = Fault("Z", 1)
    vals = c.imply({"A": "0", "B": "0"}, fault=fault)
    assert vals["Z"] == L.LD_BAR


def test_imply_fault_not_activated():
    """sa0 on Z with A=0 (Z=0 anyway) → fault not activated, Z stays 0."""
    c = make_simple_and()
    fault = Fault("Z", 0)
    vals = c.imply({"A": "0", "B": "1"}, fault=fault)
    assert vals["Z"] == "0"


def test_imply_pi_fault():
    """sa0 on PI A with A=1 → A shows D."""
    c = make_simple_and()
    fault = Fault("A", 0)
    vals = c.imply({"A": "1", "B": "1"}, fault=fault)
    assert vals["A"] == L.LD


# ── evaluate_vector ───────────────────────────────────────────────────────────

def test_evaluate_vector_t4_3(t4_3):
    """Spot-check simulation on the t4_3 circuit."""
    # With all PIs=0, the OR and AND gates should propagate correctly.
    vec = {pi: "0" for pi in t4_3.primary_inputs}
    result = t4_3.evaluate_vector(vec)
    # 5gat = OR(2gat=0, 3gat=0) = 0
    # 6gat = NOT(1gat=0) = 1
    # 7gat = AND(1gat=0, 5gat=0) = 0
    # 8gat = AND(6gat=1, 4gat=0) = 0
    # 9gat = OR(7gat=0, 8gat=0) = 0
    assert result["9gat"] == "0"


def test_evaluate_vector_detects_fault(t4_3):
    """Verify that a test vector for 9gat-sa0 actually detects the fault."""
    from d_algorithm import d_algorithm
    fault = Fault("9gat", 0)
    vec = d_algorithm(t4_3, fault)
    assert vec is not None
    good = t4_3.evaluate_vector(vec)
    faulty = t4_3.evaluate_vector(vec, fault=fault)
    assert any(good[po] != faulty[po] for po in t4_3.primary_outputs)


# ── format_vector ─────────────────────────────────────────────────────────────

def test_format_vector(t4_3):
    vec = {"1gat": "0", "2gat": "1", "3gat": "X", "4gat": "1"}
    result = t4_3.format_vector(vec)
    assert result == "01X1"


def test_format_vector_missing_pi_defaults_to_x(t4_3):
    """Missing PIs should default to X."""
    result = t4_3.format_vector({})
    assert result == "XXXX"
