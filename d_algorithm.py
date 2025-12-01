"""Implementation of the D-Algorithm for SSF ATPG."""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import logic5 as l5
from circuit import Circuit, Gate
from fault import Fault


class DAlgorithm:
    def __init__(self, circuit: Circuit, fault: Fault):
        self.circuit = circuit
        self.fault = fault
        self.assignments: Dict[str, str] = {sig: l5.LX for sig in circuit.all_signals}
        self.assignments.update({pi: l5.LX for pi in circuit.primary_inputs})

    def run(self) -> Optional[str]:
        if not self._search(depth=0, limit=len(self.circuit.all_signals) * 4):
            return None
        return self.circuit.assignments_to_vector(self.assignments)

    def _activate_fault(self) -> Tuple[str, str]:
        need = l5.L1 if self.fault.stuck_at == 0 else l5.L0
        return self.fault.net, need

    def _choose_from_d_frontier(self, values: Dict[str, str]) -> Optional[Gate]:
        frontier = self.circuit.d_frontier(values)
        if not frontier:
            return None
        return frontier[0]

    def _backtrace(self, target: str, desired: str, values: Dict[str, str]) -> Tuple[str, str]:
        node = target
        need = desired
        while node not in self.circuit.primary_inputs:
            gate = self.circuit.gates[node]
            if gate.gate_type in {"NOT", "INV", "NAND", "NOR", "XNOR"}:
                need = l5.logic_not(need)
            candidate = None
            for inp in gate.inputs:
                if l5.is_unknown(values.get(inp, l5.LX)):
                    candidate = inp
                    break
            if candidate is None:
                candidate = gate.inputs[0]
            node = candidate
        return node, need

    def _imply_and_check(self) -> Optional[Dict[str, str]]:
        values = self.circuit.imply(self.assignments, self.fault)
        for sig, val in values.items():
            if sig in self.assignments and not l5.is_unknown(self.assignments[sig]):
                if val != self.assignments[sig]:
                    return None
            self.assignments[sig] = val
        return values

    def _objective(self, values: Dict[str, str]) -> Optional[Tuple[str, str]]:
        fault_val = values.get(self.fault.net, l5.LX)
        activate_needed = l5.L1 if self.fault.stuck_at == 0 else l5.L0
        if fault_val == l5.LX:
            return self.fault.net, activate_needed
        if fault_val not in {l5.LD, l5.LD_BAR}:
            return self.fault.net, activate_needed
        gate = self._choose_from_d_frontier(values)
        if gate is None:
            return None
        non_controlling = l5.L1 if gate.gate_type in {"AND", "NAND"} else l5.L0
        for inp in gate.inputs:
            if l5.is_unknown(values.get(inp, l5.LX)):
                return inp, non_controlling
        return None

    def _search(self, depth: int, limit: int) -> bool:
        if depth > limit:
            return False
        values = self._imply_and_check()
        if values is None:
            return False
        if any(l5.is_d_like(values.get(po, l5.LX)) for po in self.circuit.primary_outputs):
            return True
        obj = self._objective(values)
        if obj is None:
            return False
        line, val = obj
        pi, pi_val = self._backtrace(line, val, values)
        for trial in [pi_val, l5.logic_not(pi_val)]:
            prev = self.assignments.get(pi, l5.LX)
            if not l5.is_unknown(prev) and prev != trial:
                continue
            self.assignments[pi] = trial
            if self._search(depth + 1, limit):
                return True
            self.assignments[pi] = prev
        return False


def generate_test(circuit: Circuit, fault: Fault) -> Optional[str]:
    algo = DAlgorithm(circuit, fault)
    return algo.run()

