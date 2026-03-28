"""Combinational Equivalence Checking (CEC) using Z3.

Encodes two circuits with identical PI/PO sets and checks whether they
produce identical outputs for every possible input combination.  If the
circuits differ, a concrete counterexample (input assignment) is returned.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from z3 import And, Or, Solver, Xor, sat

from circuit import Circuit
from formal.encoder import CircuitEncoder


@dataclass
class EquivalenceResult:
    """Result of a combinational equivalence check."""

    equivalent: bool
    counterexample: Optional[Dict[str, str]] = None
    differing_outputs: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        if self.equivalent:
            return "EQUIVALENT: circuits produce identical outputs for all inputs."
        lines = ["NOT EQUIVALENT"]
        if self.counterexample:
            ce_str = ", ".join(f"{k}={v}" for k, v in self.counterexample.items())
            lines.append(f"  Counterexample inputs : {ce_str}")
        if self.differing_outputs:
            lines.append(f"  Differing outputs     : {', '.join(self.differing_outputs)}")
        return "\n".join(lines)


class EquivalenceChecker:
    """Check whether two combinational circuits are functionally equivalent.

    Both circuits must share the same primary input names and the same
    primary output names (though internal net names may differ freely).

    Usage::

        checker = EquivalenceChecker(circuit_a, circuit_b)
        result  = checker.check()
        if not result.equivalent:
            print("Counterexample:", result.counterexample)
    """

    def __init__(self, circuit_a: Circuit, circuit_b: Circuit) -> None:
        a_pis = set(circuit_a.primary_inputs)
        b_pis = set(circuit_b.primary_inputs)
        a_pos = set(circuit_a.primary_outputs)
        b_pos = set(circuit_b.primary_outputs)
        if a_pis != b_pis:
            raise ValueError(
                f"PI mismatch: circuit_a has {a_pis}, circuit_b has {b_pis}"
            )
        if a_pos != b_pos:
            raise ValueError(
                f"PO mismatch: circuit_a has {a_pos}, circuit_b has {b_pos}"
            )
        self.circuit_a = circuit_a
        self.circuit_b = circuit_b

    def check(self) -> EquivalenceResult:
        """Run the CEC query and return an :class:`EquivalenceResult`."""
        enc_a = CircuitEncoder(self.circuit_a, suffix="A")
        enc_b = CircuitEncoder(self.circuit_b, suffix="B")

        constraints: list = []
        constraints.extend(enc_a.encode())
        constraints.extend(enc_b.encode())

        # Tie PI pairs: same input drives both circuits.
        for pi in self.circuit_a.primary_inputs:
            constraints.append(enc_a.var(pi) == enc_b.var(pi))

        # Miter: assert that at least one output differs.
        diff_terms = [
            Xor(enc_a.var(po), enc_b.var(po))
            for po in self.circuit_a.primary_outputs
        ]
        if not diff_terms:
            # No primary outputs → trivially equivalent.
            return EquivalenceResult(equivalent=True)
        constraints.append(Or(diff_terms))

        solver = Solver()
        solver.add(constraints)

        if solver.check() != sat:
            # UNSAT → no input makes them differ → equivalent.
            return EquivalenceResult(equivalent=True)

        # SAT → extract the counterexample.
        model = solver.model()
        counterexample: Dict[str, str] = {}
        for pi in self.circuit_a.primary_inputs:
            interp = model.eval(enc_a.var(pi), model_completion=True)
            counterexample[pi] = "1" if bool(interp) else "0"

        differing = [
            po for po in self.circuit_a.primary_outputs
            if bool(model.eval(enc_a.var(po), model_completion=True))
            != bool(model.eval(enc_b.var(po), model_completion=True))
        ]

        return EquivalenceResult(
            equivalent=False,
            counterexample=counterexample,
            differing_outputs=differing,
        )
