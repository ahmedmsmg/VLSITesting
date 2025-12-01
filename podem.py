"""PODEM ATPG implementation."""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import logic5 as l5
from circuit import Circuit
from fault import Fault


class Podem:
    def __init__(self, circuit: Circuit, fault: Fault):
        self.circuit = circuit
        self.fault = fault
        self.assignments: Dict[str, str] = {sig: l5.LX for sig in circuit.all_signals}

    def run(self) -> Optional[str]:
        if self._podem(depth=0, limit=len(self.circuit.all_signals) * 4):
            return self.circuit.assignments_to_vector(self.assignments)
        return None

    def _podem(self, depth: int, limit: int) -> bool:
        if depth > limit:
            return False
        values = self.circuit.imply(self.assignments, self.fault)
        if any(l5.is_d_like(values.get(po, l5.LX)) for po in self.circuit.primary_outputs):
            self.assignments.update(values)
            return True
        if all(not l5.is_unknown(values.get(pi, l5.LX)) for pi in self.circuit.primary_inputs):
            return False
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
            if self._podem(depth + 1, limit):
                return True
            self.assignments[pi] = prev
        return False

    def _objective(self, values: Dict[str, str]) -> Optional[Tuple[str, str]]:
        fault_val = values.get(self.fault.net, l5.LX)
        activate = l5.L1 if self.fault.stuck_at == 0 else l5.L0
        if fault_val == l5.LX:
            return self.fault.net, activate
        if fault_val not in {l5.LD, l5.LD_BAR}:
            return self.fault.net, activate
        frontier = self.circuit.d_frontier(values)
        if not frontier:
            return None
        gate = frontier[0]
        # ensure path exists to output
        if not self.circuit.x_path_exists(gate, values):
            return None
        desired = l5.L1 if gate.gate_type in {"AND", "NAND"} else l5.L0
        for inp in gate.inputs:
            if l5.is_unknown(values.get(inp, l5.LX)):
                return inp, desired
        return None

    def _backtrace(self, node: str, desired: str, values: Dict[str, str]) -> Tuple[str, str]:
        current = node
        need = desired
        while current not in self.circuit.primary_inputs:
            gate = self.circuit.gates[current]
            inv = gate.gate_type in {"NOT", "INV", "NAND", "NOR", "XNOR"}
            if inv:
                need = l5.logic_not(need)
            candidate = None
            for inp in gate.inputs:
                if l5.is_unknown(values.get(inp, l5.LX)):
                    candidate = inp
                    break
            if candidate is None:
                candidate = gate.inputs[0]
            current = candidate
        return current, need


def generate_test(circuit: Circuit, fault: Fault) -> Optional[str]:
    solver = Podem(circuit, fault)
    return solver.run()

