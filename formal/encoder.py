"""Shared Z3 circuit encoder for formal verification.

Extracted and generalized from SatATPG.encode_gate() so that equivalence
checking, property checking, and BMC can all share the same Boolean encoding
without coupling to the ATPG fault-injection logic.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Dict, List, Tuple

try:
    from z3 import And, Bool, Not, Or, Solver, Xor, BoolRef
except ImportError as exc:
    raise RuntimeError(
        "Formal verification requires the 'z3-solver' package. "
        "Install it via `pip install z3-solver`."
    ) from exc

from circuit import Circuit, Gate


class CircuitEncoder:
    """Encode a combinational Circuit into Z3 Boolean constraints.

    Each net in the circuit is represented as a Z3 Bool variable named
    ``<net>_<suffix>``. A unique suffix lets you embed multiple copies of
    the same circuit (e.g., good/faulty, or unrolled time steps) into a
    single Z3 solver context without variable name collisions.
    """

    def __init__(self, circuit: Circuit, suffix: str = "") -> None:
        self.circuit = circuit
        self.suffix = suffix
        self._vars: Dict[str, BoolRef] = {}

    def var(self, net: str) -> BoolRef:
        """Return (creating if needed) the Z3 Bool for *net* in this copy."""
        key = f"{net}_{self.suffix}" if self.suffix else net
        if key not in self._vars:
            self._vars[key] = Bool(key)
        return self._vars[key]

    def encode_gate(self, gate: Gate) -> BoolRef:
        """Return a single Z3 equality constraint for *gate*."""
        out = self.var(gate.output)
        ins = [self.var(i) for i in gate.inputs]
        typ = gate.type  # always uppercase (Circuit.add_gate normalizes it)

        if typ == "BUF":
            return out == ins[0]
        if typ in {"NOT", "INV"}:
            return out == Not(ins[0])
        if typ == "AND":
            return out == And(*ins)
        if typ == "OR":
            return out == Or(*ins)
        if typ == "NAND":
            return out == Not(And(*ins))
        if typ == "NOR":
            return out == Not(Or(*ins))
        if typ == "XOR":
            expr = ins[0]
            for v in ins[1:]:
                expr = Xor(expr, v)
            return out == expr
        if typ == "XNOR":
            expr = ins[0]
            for v in ins[1:]:
                expr = Xor(expr, v)
            return out == Not(expr)

        raise ValueError(f"Unsupported gate type '{typ}' in Z3 encoding")

    def encode(self) -> List[BoolRef]:
        """Return Z3 constraints for the full circuit (all gates in topo order)."""
        self.circuit.build_topological()
        # Pre-create PI variables so they are always accessible even when
        # the encoder is used to build partial constraint sets.
        for pi in self.circuit.primary_inputs:
            self.var(pi)
        constraints = [self.encode_gate(g) for g in self.circuit.topo]
        return constraints
