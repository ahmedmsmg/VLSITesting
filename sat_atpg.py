"""SAT-based ATPG using the Z3 SMT solver.

This module encodes two copies of the circuit (good and faulty), injects the
stuck-at condition into the faulty copy, enforces activation in the good copy,
ties primary inputs (except at the fault site), and requires a primary-output
mismatch. A satisfying model corresponds to a PI test cube consisting solely of
0/1/X assignments.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

try:
    from z3 import And, Bool, Not, Or, Solver, Xor, sat
except ImportError as exc:  # pragma: no cover - dependency guard
    raise RuntimeError(
        "SAT-based ATPG requires the 'z3-solver' package. Install it via "
        "`pip install z3-solver` or select another algorithm."
    ) from exc

from circuit import Circuit, Gate
from fault import Fault


class SatATPG:
    """SAT-based ATPG engine built on top of a Z3 Boolean model."""

    def __init__(self, circuit: Circuit) -> None:
        self.circuit = circuit
        # ensure we have a topological ordering of gates
        self.circuit.build_topological()
        # map (net_name, suffix) -> Bool variable
        self.vars: Dict[Tuple[str, str], Bool] = {}

    # ---------- variable helper ----------

    def var(self, net: str, suffix: str) -> Bool:
        """Return (and create if needed) a Bool for `net` in copy `suffix`."""
        key = (net, suffix)
        if key not in self.vars:
            # Z3 identifiers just need to be unique and readable
            self.vars[key] = Bool(f"{net}_{suffix}")
        return self.vars[key]

    # ---------- gate encoding ----------

    def encode_gate(self, constraints: List, gate: Gate, suffix: str) -> None:
        """Encode a single gate as a Boolean equality in the given copy."""
        out = self.var(gate.output, suffix)
        ins = [self.var(i, suffix) for i in gate.inputs]
        typ = gate.type  # assumed to be normalized (e.g., "AND", "OR", ...)

        if typ == "BUF":
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

    # ---------- full SAT encoding ----------

    def build_constraints(self, fault: Fault) -> List:
        """
        Build the Z3 constraints for a single stuck-at fault.

        We create:
          - a 'good' copy (suffix 'g') with normal logic
          - a 'faulty' copy (suffix 'f') where `fault.node` is stuck-at 0/1
          - activation: good(fault.node) is opposite of stuck value
          - PI tying: PI_g == PI_f for all PIs EXCEPT the fault site if it is a PI
          - at least one PO differs: Or(Xor(PO_g, PO_f) for all POs)
        """
        constraints: List = []

        # Encode gates for good copy completely.
        for pi in self.circuit.primary_inputs:
            self.var(pi, "g")
        for gate in self.circuit.topo:
            self.encode_gate(constraints, gate, "g")

        # Encode gates for faulty copy, BUT skip the gate that drives the fault
        # node (for internal/PO faults) so that the stuck-at constraint is the
        # only driver for that net.
        for pi in self.circuit.primary_inputs:
            self.var(pi, "f")
        for gate in self.circuit.topo:
            if gate.output == fault.node:
                # In the faulty copy, the fault node is driven only by the
                # stuck-at constraint, not by its gate equation.
                continue
            self.encode_gate(constraints, gate, "f")

        # Fault injection (faulty copy) and activation (good copy)
        good_var = self.var(fault.node, "g")
        faulty_var = self.var(fault.node, "f")
        if fault.stuck_at == 0:
            # faulty node forced to 0; good node must be 1 to excite the fault
            constraints.append(faulty_var == False)
            constraints.append(good_var == True)
        else:
            # faulty node forced to 1; good node must be 0
            constraints.append(faulty_var == True)
            constraints.append(good_var == False)

        # Tie primary inputs between copies, except when the fault site itself
        # is a primary input. For a PI fault, the good and faulty copies must
        # be allowed to differ at that PI.
        for pi in self.circuit.primary_inputs:
            if pi == fault.node:
                continue
            constraints.append(self.var(pi, "g") == self.var(pi, "f"))

        # Primary-output difference: at least one PO differs between good/faulty
        diff_terms = [
            Xor(self.var(po, "g"), self.var(po, "f"))
            for po in self.circuit.primary_outputs
        ]
        if diff_terms:
            constraints.append(Or(diff_terms))

        return constraints

    # ---------- solving & extracting test cube ----------

    def solve(self, fault: Fault) -> Optional[Dict[str, str]]:
        """Run Z3 and, if satisfiable, return a PI test cube (0/1/X)."""
        # Reset variable map per fault to avoid leakage of old Bool symbols
        self.vars.clear()
        constraints = self.build_constraints(fault)

        solver = Solver()
        solver.add(constraints)
        if solver.check() != sat:
            return None

        model = solver.model()
        assignment: Dict[str, str] = {}

        # We read the PI assignments from the GOOD copy (suffix 'g'). The
        # faulty copy is purely for modeling the fault effect.
        for pi in self.circuit.primary_inputs:
            var = self.var(pi, "g")
            interp = model.eval(var, model_completion=False)
            if interp is None:
                assignment[pi] = "X"
            elif bool(interp):
                assignment[pi] = "1"
            else:
                assignment[pi] = "0"

        return assignment


def sat_atpg(circ: Circuit, fault: Fault) -> Optional[Dict[str, str]]:
    """Convenience wrapper used by the main ATPG tool."""
    engine = SatATPG(circ)
    return engine.solve(fault)
