"""Unit tests for CircuitEncoder (formal/encoder.py)."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuit import Circuit
from formal.encoder import CircuitEncoder
from z3 import Solver, sat, unsat


def make_and_circuit():
    c = Circuit("and")
    c.add_pi("A")
    c.add_pi("B")
    c.add_po("Z")
    c.add_gate("Z", "AND", ["A", "B"])
    c.build_topological()
    return c


def make_or_circuit():
    c = Circuit("or")
    c.add_pi("A")
    c.add_pi("B")
    c.add_po("Z")
    c.add_gate("OR_out", "OR", ["A", "B"])
    c.add_gate("Z", "BUF", ["OR_out"])
    c.build_topological()
    return c


# ── Variable management ───────────────────────────────────────────────────────

def test_var_returns_bool():
    from z3 import BoolRef
    enc = CircuitEncoder(make_and_circuit(), suffix="x")
    v = enc.var("A")
    assert isinstance(v, BoolRef)


def test_var_same_name_returns_same_object():
    enc = CircuitEncoder(make_and_circuit(), suffix="x")
    v1 = enc.var("A")
    v2 = enc.var("A")
    assert v1 is v2


def test_var_different_suffix_different_names():
    c = make_and_circuit()
    enc1 = CircuitEncoder(c, suffix="s1")
    enc2 = CircuitEncoder(c, suffix="s2")
    assert str(enc1.var("A")) != str(enc2.var("A"))


# ── Gate encoding correctness ─────────────────────────────────────────────────

def _model_for(constraints, extra=None):
    s = Solver()
    s.add(constraints)
    if extra:
        s.add(extra)
    return s


def test_encode_and_gate_sat():
    c = make_and_circuit()
    enc = CircuitEncoder(c, suffix="")
    constraints = enc.encode()
    # Z=1 requires A=1, B=1
    s = _model_for(constraints, [enc.var("Z") == True])
    assert s.check() == sat
    m = s.model()
    assert bool(m.eval(enc.var("A"))) is True
    assert bool(m.eval(enc.var("B"))) is True


def test_encode_and_gate_unsat():
    c = make_and_circuit()
    enc = CircuitEncoder(c, suffix="")
    constraints = enc.encode()
    # Z=1 AND (A=0 OR B=0) should be UNSAT
    from z3 import Or
    s = _model_for(constraints, [enc.var("Z") == True, Or(enc.var("A") == False, enc.var("B") == False)])
    assert s.check() == unsat


def test_encode_nand_gate():
    c = Circuit("nand")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "NAND", ["A", "B"])
    c.build_topological()
    enc = CircuitEncoder(c, suffix="")
    constraints = enc.encode()
    # NAND(1,1) = 0
    s = _model_for(constraints, [enc.var("A") == True, enc.var("B") == True, enc.var("Z") == True])
    assert s.check() == unsat


def test_encode_or_gate():
    c = Circuit("or")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "OR", ["A", "B"])
    c.build_topological()
    enc = CircuitEncoder(c, suffix="")
    constraints = enc.encode()
    # OR(0,0) must be 0
    s = _model_for(constraints, [enc.var("A") == False, enc.var("B") == False, enc.var("Z") == True])
    assert s.check() == unsat


def test_encode_xor_gate():
    c = Circuit("xor")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "XOR", ["A", "B"])
    c.build_topological()
    enc = CircuitEncoder(c, suffix="")
    constraints = enc.encode()
    # XOR(1,1) = 0
    s = _model_for(constraints, [enc.var("A") == True, enc.var("B") == True, enc.var("Z") == True])
    assert s.check() == unsat
    # XOR(1,0) = 1
    s2 = _model_for(constraints, [enc.var("A") == True, enc.var("B") == False, enc.var("Z") == True])
    assert s2.check() == sat


def test_encode_multi_gate_circuit(t4_3):
    enc = CircuitEncoder(t4_3, suffix="g")
    constraints = enc.encode()
    # With all-zero inputs, output 9gat must be 0
    pis = {pi: False for pi in t4_3.primary_inputs}
    s = Solver()
    s.add(constraints)
    for pi, val in pis.items():
        s.add(enc.var(pi) == val)
    assert s.check() == sat
    m = s.model()
    assert bool(m.eval(enc.var("9gat"))) is False
