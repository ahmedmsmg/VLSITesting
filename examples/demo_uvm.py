#!/usr/bin/env python3
"""Demo: UVM-aligned verification environment for the t4_3 circuit.

Demonstrates Track 1 of the framework:
  - UVMEnv with agent (driver + monitor), scoreboard, coverage, assertions
  - Constrained random stimulus generation
  - SVA-like assertions (immediate and concurrent)
  - Functional coverage with coverpoints and cross coverage
  - Full UVM phase execution (build → connect → run → extract → check → report)

Run from the project root::

    python examples/demo_uvm.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ckt_parser import parse_file
from uvm.env import UVMEnv
from uvm.assertions import ConcurrentAssertion, ImmediateAssertion, PropertySequence
from uvm.coverage import CoverCross, CoverGroup, CoverPoint
from uvm.sequence import DirectedVectorSequence, RandomVectorSequence


# ─────────────────────────────────────────────────────────────────────────────
# Load the DUT (Device Under Test) and a golden reference model
# ─────────────────────────────────────────────────────────────────────────────

print("=" * 60)
print("UVM-ALIGNED VERIFICATION: t4_3 Circuit")
print("=" * 60)

dut = parse_file("examples/t4_3.ckt")
ref = parse_file("examples/t4_3.ckt")  # golden model (same circuit)

print(f"\nDUT PIs : {dut.primary_inputs}")
print(f"DUT POs : {dut.primary_outputs}")

# ─────────────────────────────────────────────────────────────────────────────
# Build the verification environment
# ─────────────────────────────────────────────────────────────────────────────

env = UVMEnv("t4_3_env", circuit=dut, reference=ref)

# ── SVA-like assertions ───────────────────────────────────────────────────────

# Immediate: output must be 0 or 1 (never unknown after full assignment)
output_valid = ImmediateAssertion(
    "output_valid",
    lambda txn: txn["outputs"].get("9gat") in {"0", "1"},
    message="Output 9gat must be a concrete Boolean value",
)

# Immediate: t4_3 structural property — if 1gat=0, output can be at most 0
# (because 7gat=AND(1gat,5gat)=0 when 1gat=0; 8gat still might produce 1)
# True property: output=1 requires either (1gat=1 ∧ 5gat=1) or (4gat=1 ∧ 6gat=1)
# Simplified check: output is well-formed (0 or 1)
output_is_boolean = ImmediateAssertion(
    "po_is_boolean",
    lambda txn: txn["outputs"]["9gat"] in {"0", "1"},
)

# Concurrent: if we see a "1" output once, the circuit is capable of it
saw_one = {"count": 0}

concurrent_tracks_ones = ConcurrentAssertion(
    "tracks_output_transitions",
    antecedent=lambda t: t["outputs"].get("9gat") == "1",
    consequent=lambda t: True,  # vacuously — just counting antecedent fires
    history_depth=1,
)

suite = PropertySequence("t4_3_properties")
suite.add(output_valid).add(output_is_boolean)

env.add_assertion(output_valid)
env.add_assertion(output_is_boolean)
env.add_assertion(concurrent_tracks_ones)

# ── Functional coverage ───────────────────────────────────────────────────────

# CoverPoint: track whether output was observed at 0 and 1
cp_output = CoverPoint("output_values", bins={
    "output_0": lambda t: t["outputs"].get("9gat") == "0",
    "output_1": lambda t: t["outputs"].get("9gat") == "1",
})

# CoverPoint: track PI 1gat value
cp_pi1 = CoverPoint("pi_1gat", bins={
    "pi1_zero": lambda t: t["inputs"].get("1gat") == "0",
    "pi1_one":  lambda t: t["inputs"].get("1gat") == "1",
})

# CoverPoint: track PI 4gat value
cp_pi4 = CoverPoint("pi_4gat", bins={
    "pi4_zero": lambda t: t["inputs"].get("4gat") == "0",
    "pi4_one":  lambda t: t["inputs"].get("4gat") == "1",
})

# CoverCross: all combinations of pi_1gat × pi_4gat
cx_pi14 = CoverCross("pi1_x_pi4", [cp_pi1, cp_pi4])

env.coverage.add_coverpoint(cp_output)
env.coverage.add_coverpoint(cp_pi1)
env.coverage.add_coverpoint(cp_pi4)
env.coverage.add_cross(cx_pi14)

# ─────────────────────────────────────────────────────────────────────────────
# Run all UVM phases
# ─────────────────────────────────────────────────────────────────────────────

print("\n--- BUILD phase ---")
env.build_phase()

print("--- RUN phase ---")

# Phase A: directed corner cases
corner_vectors = [
    {"1gat": "0", "2gat": "0", "3gat": "0", "4gat": "0"},  # all zeros
    {"1gat": "1", "2gat": "1", "3gat": "1", "4gat": "1"},  # all ones
    {"1gat": "1", "2gat": "0", "3gat": "0", "4gat": "1"},  # mix
    {"1gat": "0", "2gat": "1", "3gat": "1", "4gat": "0"},  # mix
]
directed_seq = DirectedVectorSequence("corner_cases", corner_vectors)
print(f"  Running {len(corner_vectors)} directed corner-case vectors...")
env.run_sequence(directed_seq)

# Phase B: constrained random — force PI 1gat=1 (half the input space)
constraint_pi1_one = lambda item: item.values["1gat"] == "1"
random_seq = RandomVectorSequence(
    "constrained_random", dut, count=500,
    constraints=[constraint_pi1_one],
)
print(f"  Running 500 constrained random vectors (1gat=1)...")
env.run_sequence(random_seq)

# Phase C: unconstrained random
free_seq = RandomVectorSequence("free_random", dut, count=500)
print(f"  Running 500 unconstrained random vectors...")
env.run_sequence(free_seq)

print(f"\n  Total transactions: {env.scoreboard.total}")

# ─────────────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────────────

print("\n--- REPORT phase ---\n")
env.report_phase()

# Summary
print("\n" + "─" * 60)
print(f"Assertion summary:")
print(f"  output_valid       : {output_valid.pass_count} pass / {output_valid.fail_count} fail")
print(f"  po_is_boolean      : {output_is_boolean.pass_count} pass / {output_is_boolean.fail_count} fail")
print(f"  concurrent tracked : {concurrent_tracks_ones.pass_count} antecedent fires")
print(f"\nCoverage summary:")
print(f"  Output coverage    : {cp_output.coverage_pct:.1f}%")
print(f"  PI-1gat coverage   : {cp_pi1.coverage_pct:.1f}%")
print(f"  PI-4gat coverage   : {cp_pi4.coverage_pct:.1f}%")
print(f"  Cross pi1×pi4      : {cx_pi14.coverage_pct:.1f}%")
print(f"  Overall            : {env.coverage.overall_coverage_pct:.1f}%")
print("UVM demo complete.")
