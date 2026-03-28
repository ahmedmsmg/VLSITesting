"""Unit tests for the SAT-based ATPG engine."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sat_atpg import sat_atpg, SatATPG
from fault import Fault


def _verify_detection(circuit, fault, vector):
    good = circuit.evaluate_vector(vector)
    faulty = circuit.evaluate_vector(vector, fault=fault)
    return any(good[po] != faulty[po] for po in circuit.primary_outputs)


# ── SatATPG class ─────────────────────────────────────────────────────────────

def test_sat_atpg_engine_init(t4_3):
    engine = SatATPG(t4_3)
    assert engine.circuit is t4_3


# ── t4_3 circuit ──────────────────────────────────────────────────────────────

def test_detects_output_sa0(t4_3):
    fault = Fault("9gat", 0)
    vec = sat_atpg(t4_3, fault)
    assert vec is not None
    assert _verify_detection(t4_3, fault, vec)


def test_detects_output_sa1(t4_3):
    fault = Fault("9gat", 1)
    vec = sat_atpg(t4_3, fault)
    assert vec is not None
    assert _verify_detection(t4_3, fault, vec)


def test_detects_internal_gate_sa0(t4_3):
    fault = Fault("5gat", 0)
    vec = sat_atpg(t4_3, fault)
    assert vec is not None
    assert _verify_detection(t4_3, fault, vec)


def test_all_faults_on_t4_3(t4_3):
    faults = t4_3.fault_list()
    detected = 0
    for fault in faults:
        vec = sat_atpg(t4_3, fault)
        if vec is not None:
            assert _verify_detection(t4_3, fault, vec), \
                f"SAT returned invalid vector for {fault.label()}"
            detected += 1
    assert detected / len(faults) >= 0.6


# ── full adder ────────────────────────────────────────────────────────────────

def test_full_adder_sa0_output(t5_26a):
    fault = Fault("S", 0)
    vec = sat_atpg(t5_26a, fault)
    assert vec is not None
    assert _verify_detection(t5_26a, fault, vec)


def test_full_adder_sa1_carry(t5_26a):
    fault = Fault("CO", 1)
    vec = sat_atpg(t5_26a, fault)
    assert vec is not None
    assert _verify_detection(t5_26a, fault, vec)


# ── result format ─────────────────────────────────────────────────────────────

def test_vector_values_are_binary_or_x(t4_3):
    """SAT engine should only return 0/1/X in the test vector."""
    fault = Fault("9gat", 0)
    vec = sat_atpg(t4_3, fault)
    assert vec is not None
    assert all(v in {"0", "1", "X"} for v in vec.values())


def test_vector_keys_are_pis(t4_3):
    fault = Fault("9gat", 0)
    vec = sat_atpg(t4_3, fault)
    assert vec is not None
    assert set(vec.keys()) == set(t4_3.primary_inputs)
