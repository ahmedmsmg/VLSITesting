#!/usr/bin/env python3
"""Demo: Formal verification — equivalence checking and property verification.

Demonstrates Track 3 of the framework:
  - Combinational Equivalence Checking (CEC) between two circuit implementations
  - Property checking: proving Boolean invariants hold for all inputs
  - Bounded Model Checking basics

Run from the project root::

    python examples/demo_formal.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuit import Circuit
from ckt_parser import parse_file
from formal.equivalence import EquivalenceChecker
from formal.property_check import Property, PropertyChecker
from formal.bmc import BadStateProperty, BoundedModelChecker
from z3 import And, Implies, Not


# ─────────────────────────────────────────────────────────────────────────────
# Helper: build circuits
# ─────────────────────────────────────────────────────────────────────────────

def make_and():
    c = Circuit("and_impl")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "AND", ["A", "B"])
    c.build_topological()
    return c


def make_nand_not():
    """NAND(A,B) → NOT  ≡  AND(A,B) — alternate implementation."""
    c = Circuit("nand_not_impl")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("tmp", "NAND", ["A", "B"])
    c.add_gate("Z", "NOT", ["tmp"])
    c.build_topological()
    return c


def make_or():
    c = Circuit("or_impl")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "OR", ["A", "B"])
    c.build_topological()
    return c


# ─────────────────────────────────────────────────────────────────────────────
# Demo 1: Combinational Equivalence Checking
# ─────────────────────────────────────────────────────────────────────────────

print("=" * 60)
print("DEMO 1: Combinational Equivalence Checking (CEC)")
print("=" * 60)

and_circ   = make_and()
nand_not   = make_nand_not()
or_circ    = make_or()

# Case 1: AND ≡ NAND→NOT (should be equivalent)
result = EquivalenceChecker(and_circ, nand_not).check()
print(f"\nAND  vs  NAND→NOT:")
print(f"  {result}")

# Case 2: AND vs OR (should NOT be equivalent)
result2 = EquivalenceChecker(and_circ, or_circ).check()
print(f"\nAND  vs  OR:")
print(f"  {result2}")

# Case 3: Real benchmark — t4_3 against itself
t4_3_a = parse_file("examples/t4_3.ckt")
t4_3_b = parse_file("examples/t4_3.ckt")
result3 = EquivalenceChecker(t4_3_a, t4_3_b).check()
print(f"\nt4_3  vs  t4_3 (same circuit):")
print(f"  {result3}")

# ─────────────────────────────────────────────────────────────────────────────
# Demo 2: Property Checking
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("DEMO 2: Property Checking")
print("=" * 60)

checker = PropertyChecker(and_circ)

# Property 1: AND(A,B)=0 whenever A=0 (must hold)
p1 = Property(
    name="and_zero_when_a_zero",
    formula=lambda enc: Implies(enc.var("A") == False, enc.var("Z") == False),
    description="Output is 0 whenever input A is 0",
)

# Property 2: AND(A,B) == 1 always (false property — should be violated)
p2 = Property(
    name="output_always_one",
    formula=lambda enc: enc.var("Z") == True,
    description="Output is always 1 (false property)",
)

# Property 3: AND(A,B) ↔ A∧B (definitional equivalence — must hold)
p3 = Property(
    name="and_definition",
    formula=lambda enc: enc.var("Z") == And(enc.var("A"), enc.var("B")),
    description="Output equals AND of inputs",
)

for p in [p1, p2, p3]:
    r = checker.check(p)
    print(f"\n  [{p.name}]  ({p.description})")
    print(f"  {r}")

# ─────────────────────────────────────────────────────────────────────────────
# Demo 3: Bounded Model Checking on t4_3
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("DEMO 3: Bounded Model Checking")
print("=" * 60)

t4_3 = parse_file("examples/t4_3.ckt")

# Bad state: output 9gat = 1 (should be reachable with appropriate inputs)
bad_output_1 = BadStateProperty(
    name="output_can_be_1",
    formula=lambda enc, k: enc.var("9gat") == True,
    description="Output 9gat = 1 is reachable",
)

# Truly impossible bad state
impossible = BadStateProperty(
    name="output_and_not_output",
    formula=lambda enc, k: __import__("z3").And(
        enc.var("9gat") == True, enc.var("9gat") == False
    ),
    description="Output simultaneously 0 and 1 (impossible)",
)

bmc = BoundedModelChecker(t4_3)

r1 = bmc.check(bad_output_1, bound=1)
print(f"\n[{bad_output_1.name}] {bad_output_1.description}:")
print(f"  {r1}")

r2 = bmc.check(impossible, bound=3)
print(f"\n[{impossible.name}] {impossible.description}:")
print(f"  {r2}")

print("\nFormal verification demo complete.")
