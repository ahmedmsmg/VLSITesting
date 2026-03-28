"""Unit tests for the D-Algorithm ATPG engine."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from d_algorithm import d_algorithm
from fault import Fault


def _verify_detection(circuit, fault, vector):
    """Confirm a vector actually detects *fault* by simulation."""
    good = circuit.evaluate_vector(vector)
    faulty = circuit.evaluate_vector(vector, fault=fault)
    return any(good[po] != faulty[po] for po in circuit.primary_outputs)


# ── t4_3 circuit ──────────────────────────────────────────────────────────────

def test_detects_output_sa0(t4_3):
    fault = Fault("9gat", 0)
    vec = d_algorithm(t4_3, fault)
    assert vec is not None
    assert _verify_detection(t4_3, fault, vec)


def test_detects_output_sa1(t4_3):
    fault = Fault("9gat", 1)
    vec = d_algorithm(t4_3, fault)
    assert vec is not None
    assert _verify_detection(t4_3, fault, vec)


def test_detects_internal_gate_sa0(t4_3):
    """Internal gate 5gat (OR 2gat 3gat) stuck-at-0."""
    fault = Fault("5gat", 0)
    vec = d_algorithm(t4_3, fault)
    assert vec is not None
    assert _verify_detection(t4_3, fault, vec)


def test_detects_pi_sa0(t4_3):
    fault = Fault("1gat", 0)
    vec = d_algorithm(t4_3, fault)
    assert vec is not None
    assert _verify_detection(t4_3, fault, vec)


def test_all_faults_on_t4_3(t4_3):
    """All faults on t4_3 should be either detected or confirmed untestable."""
    faults = t4_3.fault_list()
    detected = 0
    for fault in faults:
        vec = d_algorithm(t4_3, fault)
        if vec is not None:
            assert _verify_detection(t4_3, fault, vec), \
                f"D-Alg returned invalid vector for {fault.label()}"
            detected += 1
    # t4_3 should have a high detection rate; at least 60% detectable
    assert detected / len(faults) >= 0.6


# ── full adder (t5_26a) ───────────────────────────────────────────────────────

def test_full_adder_faults(t5_26a):
    """D-Algorithm should detect the majority of full-adder faults."""
    faults = t5_26a.fault_list()
    detected = 0
    for fault in faults:
        vec = d_algorithm(t5_26a, fault)
        if vec is not None:
            assert _verify_detection(t5_26a, fault, vec), \
                f"Invalid vector for {fault.label()}"
            detected += 1
    assert detected / len(faults) >= 0.5


# ── vector format ─────────────────────────────────────────────────────────────

def test_vector_keys_are_pis(t4_3):
    """The returned dict must only contain primary input keys."""
    fault = Fault("9gat", 0)
    vec = d_algorithm(t4_3, fault)
    assert vec is not None
    assert set(vec.keys()) == set(t4_3.primary_inputs)
