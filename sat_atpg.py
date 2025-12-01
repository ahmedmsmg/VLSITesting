"""SAT-based ATPG using the Z3 SMT solver.

This module encodes two copies of the circuit (good and faulty), injects the
stuck-at condition into the faulty copy, enforces activation in the good copy,
ties primary inputs, and requires a primary-output mismatch. A satisfying model
corresponds to a PI test cube consisting solely of 0/1/X assignments.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

try:
    from z3 import And, Bool, Not, Or, Solver, Xor, sat
except ImportError as exc:  # pragma: no cover - dependency guard
    raise RuntimeError(
        "SAT-based ATPG requires the 'z3-solver' package. Install it via `pip "
        "install z3-solver` or select another algorithm."
    ) from exc

from circuit import Circuit, Gate
from fault import Fault


class SatATPG:
    def __init__(self, circuit: Circuit) -> None:
        self.circuit = circuit
        self.circuit.build_topological()
        self.vars: Dict[Tuple[str, str], Bool] = {}

    def var(self, net: str, suffix: str) -> Bool:
        key = (net, suffix)
        if key not in self.vars:
            self.vars[key] = Bool(f"{net}_{suffix}")
        return self.vars[key]

    def encode_gate(self, constraints: List, gate: Gate, suffix: str) -> None:
        out = self.var(gate.output, suffix)
        ins = [self.var(i, suffix) for i in gate.inputs]
        typ = gate.type

        if typ in {"BUF"}:
            constraints.append(out == ins[0])
            return
        if typ in {"NOT", "INV"}:
            constraints.append(out == Not(ins[0]))
            return
        if typ == "AND":
            constraints.append(out == And(*ins))
            return
        if typ == "OR":
            constraints.append(out == Or(*ins))
            return
        if typ == "NAND":
            constraints.append(out == Not(And(*ins)))
            return
        if typ == "NOR":
            constraints.append(out == Not(Or(*ins)))
            return
        if typ == "XOR":
            expr = ins[0]
            for v in ins[1:]:
                expr = Xor(expr, v)
            constraints.append(out == expr)
            return
        if typ == "XNOR":
            expr = ins[0]
            for v in ins[1:]:
                expr = Xor(expr, v)
            constraints.append(out == Not(expr))
            return
        raise ValueError(f"Unsupported gate type {typ} in SAT encoding")

    def build_constraints(self, fault: Fault) -> List:
        constraints: List = []
        # create variables and gate encodings for good and faulty copies
        for suffix in ["g", "f"]:
            for pi in self.circuit.primary_inputs:
                self.var(pi, suffix)
            for gate in self.circuit.topo:
                self.encode_gate(constraints, gate, suffix)

        # fault injection and activation
        good_var = self.var(fault.node, "g")
        faulty_var = self.var(fault.node, "f")
        if fault.stuck_at == 0:
            constraints.append(faulty_var == False)
            constraints.append(good_var == True)
        else:
            constraints.append(faulty_var == True)
            constraints.append(good_var == False)

        # tie PIs between good and faulty copies
        for pi in self.circuit.primary_inputs:
            constraints.append(self.var(pi, "g") == self.var(pi, "f"))

        # primary output difference
        diff_terms = [Xor(self.var(po, "g"), self.var(po, "f")) for po in self.circuit.primary_outputs]
        if diff_terms:
            constraints.append(Or(diff_terms))

        return constraints

    def solve(self, fault: Fault) -> Optional[Dict[str, str]]:
        constraints = self.build_constraints(fault)
        solver = Solver()
        solver.add(constraints)
        if solver.check() != sat:
            return None
        model = solver.model()

        assignment: Dict[str, str] = {}
        for pi in self.circuit.primary_inputs:
            var = self.var(pi, "g")
            interp = model.get_interp(var)
            if interp is None:
                assignment[pi] = "X"
            elif interp.is_true():
                assignment[pi] = "1"
            elif interp.is_false():
                assignment[pi] = "0"
            else:
                assignment[pi] = "X"
        return assignment


def sat_atpg(circ: Circuit, fault: Fault) -> Optional[Dict[str, str]]:
    engine = SatATPG(circ)
    return engine.solve(fault)
