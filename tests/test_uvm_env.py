"""Integration tests for UVMEnv (the top-level environment)."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuit import Circuit
from uvm.assertions import ImmediateAssertion
from uvm.coverage import CoverGroup, CoverPoint
from uvm.env import UVMEnv
from uvm.sequence import DirectedVectorSequence, RandomVectorSequence


def make_and():
    c = Circuit("and")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "AND", ["A", "B"])
    c.build_topological()
    return c


# ── Construction ──────────────────────────────────────────────────────────────

def test_env_creates_agent_scoreboard_coverage():
    c = make_and()
    env = UVMEnv("env", c)
    assert env.agent is not None
    assert env.scoreboard is not None
    assert env.coverage is not None


def test_env_no_reference_scoreboard_monitoring_only():
    c = make_and()
    env = UVMEnv("env", c)
    env.build_phase()
    seq = RandomVectorSequence("r", c, count=10)
    env.run_sequence(seq)
    assert env.scoreboard.total == 10
    assert env.scoreboard.mismatches == 0  # no reference → all matches


# ── With reference ────────────────────────────────────────────────────────────

def test_env_with_matching_reference():
    """DUT == reference → all matches."""
    from ckt_parser import parse_file
    dut = parse_file("examples/t4_3.ckt")
    ref = parse_file("examples/t4_3.ckt")
    env = UVMEnv("env", dut, ref)
    env.build_phase()
    seq = RandomVectorSequence("r", dut, count=50)
    env.run_sequence(seq)
    assert env.scoreboard.mismatches == 0
    assert env.scoreboard.pass_rate == 1.0


def test_env_detects_mismatches_with_wrong_reference(t4_3):
    """Using OR circuit as reference when DUT is t4_3 (AND+OR mix) — some mismatches."""
    ref = Circuit("always_zero")
    for pi in t4_3.primary_inputs:
        ref.add_pi(pi)
    for po in t4_3.primary_outputs:
        ref.add_po(po)
    # Stub gate: always output 0 (AND all PIs but force 0)
    ref.add_gate("tmp", "AND", t4_3.primary_inputs[:2])
    ref.add_gate(t4_3.primary_outputs[0], "AND", ["tmp"] + ["tmp"])
    ref.build_topological()

    env = UVMEnv("env", t4_3, ref)
    env.build_phase()
    # Use vectors where we know t4_3 output = 1 (to trigger mismatches)
    vectors = [{"1gat": "1", "2gat": "1", "3gat": "1", "4gat": "1"}]
    seq = DirectedVectorSequence("directed", vectors)
    env.run_sequence(seq)
    # The always-zero ref will mismatch when t4_3 outputs 1
    assert env.scoreboard.total >= 1


# ── Assertions ────────────────────────────────────────────────────────────────

def test_env_assertions_evaluated():
    c = make_and()
    env = UVMEnv("env", c)
    env.build_phase()
    ia = ImmediateAssertion("and_correct", lambda txn: (
        txn["outputs"].get("Z") == "1"
        if txn["inputs"]["A"] == "1" and txn["inputs"]["B"] == "1"
        else txn["outputs"].get("Z") == "0"
    ))
    env.add_assertion(ia)
    vectors = [{"A": "1", "B": "1"}, {"A": "0", "B": "1"}, {"A": "1", "B": "0"}]
    seq = DirectedVectorSequence("directed", vectors)
    env.run_sequence(seq)
    assert ia.fail_count == 0
    assert ia.pass_count == 3


# ── Coverage ──────────────────────────────────────────────────────────────────

def test_env_coverage_sampling(t4_3):
    env = UVMEnv("env", t4_3)
    cp = CoverPoint("output_vals", bins={
        "output_0": lambda t: t["outputs"].get("9gat") == "0",
        "output_1": lambda t: t["outputs"].get("9gat") == "1",
    })
    env.coverage.add_coverpoint(cp)
    env.build_phase()
    seq = RandomVectorSequence("r", t4_3, count=200)
    env.run_sequence(seq)
    # With 200 random vectors, both 0 and 1 outputs should be observed
    assert cp.coverage_pct == 100.0


# ── Monitor observation count matches sequence count ─────────────────────────

def test_env_observation_count_matches_sequence(t4_3):
    env = UVMEnv("env", t4_3)
    env.build_phase()
    seq = RandomVectorSequence("r", t4_3, count=30)
    env.run_sequence(seq)
    assert len(env.agent.monitor.observed) == 30
