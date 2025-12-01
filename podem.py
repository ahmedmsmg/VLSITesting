"""PODEM algorithm implementation."""
from __future__ import annotations
from typing import Dict, Optional, Tuple, List

import logic5 as L
from circuit import Circuit, Gate
from fault import Fault


def _is_inverting(gate_type: str) -> bool:
    return gate_type in {"NAND", "NOR", "NOT", "INV"}


def _controlling_value(gate_type: str) -> str:
    if gate_type in {"AND", "NAND"}:
        return L.L0
    if gate_type in {"OR", "NOR"}:
        return L.L1
    return L.LX


def _non_controlling_value(gate_type: str) -> str:
    if gate_type in {"AND", "NAND"}:
        return L.L1
    if gate_type in {"OR", "NOR"}:
        return L.L0
    return L.LX


def _d_frontier(circ: Circuit, values: Dict[str, str]) -> List[Gate]:
    frontier: List[Gate] = []
    for g in circ.topo:
        if values[g.output] == L.LX and any(v in {L.LD, L.LD_BAR} for v in (values.get(i, L.LX) for i in g.inputs)):
            frontier.append(g)
    return frontier


def x_path_exists(circ: Circuit, values: Dict[str, str], start: str) -> bool:
    visited = set()

    def dfs(node: str) -> bool:
        if node in visited:
            return False
        visited.add(node)
        if node in circ.primary_outputs:
            return True
        for g in circ.topo:
            if node in g.inputs:
                if values[g.output] == L.LX:
                    if dfs(g.output):
                        return True
        return False

    return dfs(start)


def backtrace(circ: Circuit, node: str, desired: str, values: Dict[str, str]) -> Tuple[str, str]:
    current = node
    val = desired
    while current not in circ.primary_inputs:
        driving = next((g for g in circ.topo if g.output == current), None)
        if driving is None:
            break
        if _is_inverting(driving.type):
            val = L.logic_not(val)
        # pick an unassigned input if available else first
        candidate = None
        for i in driving.inputs:
            if values.get(i, L.LX) == L.LX:
                candidate = i
                break
        if candidate is None:
            candidate = driving.inputs[0]
        current = candidate
    return current, val


def imply(circ: Circuit, assignments: Dict[str, str], fault: Fault) -> Dict[str, str]:
    return circ.imply(assignments, fault=fault)


def objective(circ: Circuit, values: Dict[str, str], fault: Fault) -> Optional[Tuple[str, str]]:
    # fault activation
    fault_val = values.get(fault.node, L.LX)
    desired = L.L1 if fault.stuck_at == 0 else L.L0
    if fault_val == L.LX:
        return fault.node, desired
    # need propagation
    frontier = _d_frontier(circ, values)
    if not frontier:
        return None
    gate = frontier[0]
    non_ctrl = _non_controlling_value(gate.type)
    for i in gate.inputs:
        if values.get(i, L.LX) == L.LX:
            return i, non_ctrl
    return None


def podem(circ: Circuit, fault: Fault) -> Optional[Dict[str, str]]:
    circ.build_topological()
    assignments: Dict[str, str] = {}

    def rec(assignments: Dict[str, str]) -> Optional[Dict[str, str]]:
        values = imply(circ, assignments, fault)
        if any(values[po] in {L.LD, L.LD_BAR} for po in circ.primary_outputs):
            return {pi: values.get(pi, L.LX) for pi in circ.primary_inputs}
        obj = objective(circ, values, fault)
        if obj is None:
            return None
        line, val = obj
        pi, pi_val = backtrace(circ, line, val, values)
        if pi_val not in {L.L0, L.L1}:
            pi_val = L.L1 if pi_val == L.LX else pi_val
        for trial in [pi_val, L.logic_not(pi_val)]:
            if assignments.get(pi, L.LX) not in {L.LX, trial}:
                continue
            new_assign = dict(assignments)
            new_assign[pi] = trial
            result = rec(new_assign)
            if result:
                return result
            assignments[pi] = L.LX
        return None

    return rec(assignments)
