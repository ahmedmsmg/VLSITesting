"""Unit tests for the PODEM ATPG engine."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from podem import podem
from fault import Fault


def _verify_detection(circuit, fault, vector):
    good = circuit.evaluate_vector(vector)
    faulty = circuit.evaluate_vector(vector, fault=fault)
    return any(good[po] != faulty[po] for po in circuit.primary_outputs)


# ── t4_3 circuit ──────────────────────────────────────────────────────────────

def test_detects_output_sa0(t4_3):
    fault = Fault("9gat", 0)
    vec = podem(t4_3, fault)
    assert vec is not None
    assert _verify_detection(t4_3, fault, vec)


def test_detects_output_sa1(t4_3):
    fault = Fault("9gat", 1)
    vec = podem(t4_3, fault)
    assert vec is not None
    assert _verify_detection(t4_3, fault, vec)


def test_detects_internal_gate(t4_3):
    fault = Fault("5gat", 0)
    vec = podem(t4_3, fault)
    assert vec is not None
    assert _verify_detection(t4_3, fault, vec)


def test_all_faults_on_t4_3(t4_3):
    faults = t4_3.fault_list()
    detected = 0
    for fault in faults:
        vec = podem(t4_3, fault)
        if vec is not None:
            assert _verify_detection(t4_3, fault, vec), \
                f"PODEM returned invalid vector for {fault.label()}"
            detected += 1
    assert detected / len(faults) >= 0.6


# ── full adder ────────────────────────────────────────────────────────────────

def test_full_adder_faults(t5_26a):
    faults = t5_26a.fault_list()
    detected = 0
    for fault in faults:
        vec = podem(t5_26a, fault)
        if vec is not None:
            assert _verify_detection(t5_26a, fault, vec), \
                f"Invalid vector for {fault.label()}"
            detected += 1
    assert detected / len(faults) >= 0.5


# ── result format ─────────────────────────────────────────────────────────────

def test_vector_keys_are_pis(t4_3):
    fault = Fault("9gat", 0)
    vec = podem(t4_3, fault)
    assert vec is not None
    assert set(vec.keys()) == set(t4_3.primary_inputs)
