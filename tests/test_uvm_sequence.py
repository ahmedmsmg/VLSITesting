"""Tests for UVM sequence and sequence-item classes."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuit import Circuit
from uvm.sequence import (
    CircuitVector,
    DirectedVectorSequence,
    RandomVectorSequence,
    UVMSequence,
)


def make_circuit():
    c = Circuit("test")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "AND", ["A", "B"])
    c.build_topological()
    return c


# ── CircuitVector ─────────────────────────────────────────────────────────────

def test_circuit_vector_initial_values(t4_3):
    v = CircuitVector(t4_3)
    assert all(val == "X" for val in v.values.values())


def test_circuit_vector_randomize_returns_binary():
    c = make_circuit()
    v = CircuitVector(c)
    ok = v.randomize()
    assert ok is True
    assert all(val in {"0", "1"} for val in v.values.values())


def test_circuit_vector_keys_are_pis():
    c = make_circuit()
    v = CircuitVector(c)
    v.randomize()
    assert set(v.values.keys()) == set(c.primary_inputs)


def test_circuit_vector_constraint_satisfied():
    c = make_circuit()
    v = CircuitVector(c)
    # Constraint: A must be 1
    constraint = lambda item: item.values["A"] == "1"
    ok = v.randomize(constraints=[constraint])
    assert ok is True
    assert v.values["A"] == "1"


def test_circuit_vector_impossible_constraint_returns_false():
    c = make_circuit()
    v = CircuitVector(c)
    # Impossible constraint
    ok = v.randomize(constraints=[lambda _: False], max_tries=10)
    assert ok is False


def test_circuit_vector_repr():
    c = make_circuit()
    v = CircuitVector(c)
    v.values = {"A": "1", "B": "0"}
    r = repr(v)
    assert "CircuitVector" in r
    assert "10" in r


def test_circuit_vector_as_dict():
    c = make_circuit()
    v = CircuitVector(c)
    v.values = {"A": "0", "B": "1"}
    d = v.as_dict()
    assert d == {"A": "0", "B": "1"}


# ── RandomVectorSequence ──────────────────────────────────────────────────────

def test_random_sequence_yields_count_items():
    c = make_circuit()
    seq = RandomVectorSequence("test_seq", c, count=10)
    items = list(seq.body())
    assert len(items) == 10


def test_random_sequence_items_are_circuit_vectors():
    c = make_circuit()
    seq = RandomVectorSequence("test_seq", c, count=5)
    for item in seq.body():
        assert isinstance(item, CircuitVector)
        assert all(v in {"0", "1"} for v in item.values.values())


def test_random_sequence_with_constraint():
    c = make_circuit()
    constraint = lambda item: item.values["A"] == "1"
    seq = RandomVectorSequence("constrained", c, count=20, constraints=[constraint])
    for item in seq.body():
        assert item.values["A"] == "1"


# ── DirectedVectorSequence ────────────────────────────────────────────────────

def test_directed_sequence_replays_vectors():
    vectors = [
        {"A": "0", "B": "0"},
        {"A": "1", "B": "1"},
        {"A": "1", "B": "0"},
    ]
    seq = DirectedVectorSequence("directed", vectors)
    items = list(seq.body())
    assert len(items) == 3
    assert items[0].values == {"A": "0", "B": "0"}
    assert items[1].values == {"A": "1", "B": "1"}


# ── Base UVMSequence ──────────────────────────────────────────────────────────

def test_base_sequence_empty_body():
    seq = UVMSequence("empty")
    assert list(seq.body()) == []
