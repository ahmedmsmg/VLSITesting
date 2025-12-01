"""Simplified D-algorithm implementation with backtracking."""
from __future__ import annotations
from typing import Dict, Optional, Tuple, List

import logic5 as L
from circuit import Circuit, Gate
from fault import Fault


class DAlgoState:
    def __init__(self, circuit: Circuit, fault: Fault) -> None:
        self.circuit = circuit
        self.fault = fault
        self.assignments: Dict[str, str] = {n: L.LX for n in circuit.primary_inputs}

    def evaluate(self) -> Dict[str, str]:
        known = {k: v for k, v in self.assignments.items() if v != L.LX}
        return self.circuit.imply(known, fault=self.fault)

    def d_frontier(self, values: Dict[str, str]) -> List[Gate]:
        frontier = []
        for g in self.circuit.topo:
            if values[g.output] == L.LX and any(values.get(i, L.LX) in {L.LD, L.LD_BAR} for i in g.inputs):
                frontier.append(g)
        return frontier

    def j_frontier(self, values: Dict[str, str]) -> List[Gate]:
        frontier = []
        for g in self.circuit.topo:
            if values[g.output] != L.LX and any(values.get(i, L.LX) == L.LX for i in g.inputs):
                frontier.append(g)
        return frontier

    def is_consistent(self, values: Dict[str, str]) -> bool:
        for pi, v in self.assignments.items():
            if v != L.LX and values.get(pi, L.LX) not in {L.LX, v}:
                return False
        return True

    def select_objective(self, values: Dict[str, str]) -> Optional[Tuple[str, str]]:
        fault_line = values.get(self.fault.node, L.LX)
        activation_val = L.L1 if self.fault.stuck_at == 0 else L.L0
        if fault_line == L.LX:
            return self.fault.node, activation_val
        # propagate
        df = self.d_frontier(values)
        if not df:
            return None
        gate = df[0]
        non_ctrl = self._non_controlling(gate.type)
        for i in gate.inputs:
            if values.get(i, L.LX) == L.LX:
                return i, non_ctrl
        return None

    @staticmethod
    def _non_controlling(gate_type: str) -> str:
        if gate_type in {"AND", "NAND"}:
            return L.L1
        if gate_type in {"OR", "NOR"}:
            return L.L0
        return L.LX

    def backtrace(self, node: str, desired: str, values: Dict[str, str]) -> Tuple[str, str]:
        current, val = node, desired
        while current not in self.circuit.primary_inputs:
            driving = next((g for g in self.circuit.topo if g.output == current), None)
            if driving is None:
                break
            if driving.type in {"NAND", "NOR", "NOT", "INV"}:
                val = L.logic_not(val)
            candidate = next((i for i in driving.inputs if values.get(i, L.LX) == L.LX), driving.inputs[0])
            current = candidate
        return current, val


def d_algorithm(circ: Circuit, fault: Fault) -> Optional[Dict[str, str]]:
    circ.build_topological()
    state = DAlgoState(circ, fault)

    def search() -> Optional[Dict[str, str]]:
        values = state.evaluate()
        if any(values[po] in {L.LD, L.LD_BAR} for po in circ.primary_outputs):
            return {pi: values.get(pi, L.LX) for pi in circ.primary_inputs}
        obj = state.select_objective(values)
        if obj is None:
            return None
        line, val = obj
        pi, pi_val = state.backtrace(line, val, values)
        for trial in [pi_val, L.logic_not(pi_val)]:
            prev = state.assignments.get(pi, L.LX)
            if prev not in {L.LX, trial}:
                continue
            state.assignments[pi] = trial
            res = search()
            if res:
                return res
            state.assignments[pi] = L.LX
        return None

    return search()
