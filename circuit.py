"""Circuit data structure and five-valued simulation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

import logic5 as L
from fault import Fault


@dataclass
class Gate:
    output: str
    type: str
    inputs: List[str]


class Circuit:
    def __init__(self, name: str = "") -> None:
        self.name = name
        self.primary_inputs: List[str] = []
        self.primary_outputs: List[str] = []
        self.gates: List[Gate] = []
        self.topo: List[Gate] = []
        self.nodes: List[str] = []

    def add_pi(self, name: str) -> None:
        if name not in self.primary_inputs:
            self.primary_inputs.append(name)
            self.nodes.append(name)

    def add_po(self, name: str) -> None:
        if name not in self.primary_outputs:
            self.primary_outputs.append(name)
            if name not in self.nodes:
                self.nodes.append(name)

    def add_gate(self, output: str, gtype: str, inputs: List[str]) -> None:
        gate = Gate(output=output, type=gtype.upper(), inputs=inputs)
        self.gates.append(gate)
        if output not in self.nodes:
            self.nodes.append(output)
        for i in inputs:
            if i not in self.nodes:
                self.nodes.append(i)

    def build_topological(self) -> None:
        deps = {g.output: set(g.inputs) for g in self.gates}
        known = set(self.primary_inputs)
        order: List[Gate] = []
        remaining = self.gates.copy()
        while remaining:
            progress = False
            for g in list(remaining):
                if set(g.inputs).issubset(known):
                    order.append(g)
                    known.add(g.output)
                    remaining.remove(g)
                    progress = True
            if not progress:
                raise ValueError("Circuit has cycles or unresolved dependencies")
        self.topo = order

    # --- Simulation helpers -------------------------------------------------
    def _eval_gate(self, g: Gate, values: Dict[str, str]) -> str:
        ins = [values.get(n, L.LX) for n in g.inputs]
        typ = g.type
        if typ == "AND":
            return L.reduce_and(ins)
        if typ == "NAND":
            return L.logic_not(L.reduce_and(ins))
        if typ == "OR":
            return L.reduce_or(ins)
        if typ == "NOR":
            return L.logic_not(L.reduce_or(ins))
        if typ == "XOR":
            return L.reduce_xor(ins)
        if typ == "XNOR":
            return L.logic_not(L.reduce_xor(ins))
        if typ in {"NOT", "INV"}:
            return L.logic_not(ins[0])
        if typ == "BUF":
            return ins[0]
        raise ValueError(f"Unknown gate type {typ}")

    def imply(self, assignment: Dict[str, str], fault: Optional[Fault] = None) -> Dict[str, str]:
        """Forward imply assigned PIs through the circuit.

        If *fault* is given, inject the fault on its site by overriding the
        value after normal evaluation.
        """
        values = {n: L.LX for n in self.nodes}
        values.update(assignment)

        # Inject PI fault before gate evaluation so D/D' can propagate
        if fault and fault.node in self.primary_inputs:
            sa_val = L.L0 if fault.stuck_at == 0 else L.L1
            injected = L.LD if fault.stuck_at == 0 else L.LD_BAR
            current = values.get(fault.node, L.LX)
            if current in {L.L0, L.L1}:
                if current != sa_val:
                    values[fault.node] = injected
                else:
                    values[fault.node] = sa_val

        for g in self.topo:
            # compute gate output
            out = self._eval_gate(g, values)
            values[g.output] = out
            # inject fault if at this node
            if fault and g.output == fault.node:
                sa = L.L0 if fault.stuck_at == 0 else L.L1
                good = out
                # Only inject the fault when the good value is resolved. If the
                # good value is still X, keep it unknown so activation has to be
                # satisfied by the search.
                if good in {L.L0, L.L1}:
                    if good == sa:
                        # fault not activated
                        values[g.output] = sa
                    else:
                        # activated -> drive D/D'
                        values[g.output] = L.LD if sa == L.L0 else L.LD_BAR
        return values

    def evaluate_vector(self, vector: Dict[str, str], fault: Optional[Fault] = None) -> Dict[str, str]:
        self.build_topological()
        return self.imply(vector, fault=fault)

    def fault_list(self) -> List[Fault]:
        return [Fault(n, 0) for n in self.nodes] + [Fault(n, 1) for n in self.nodes]

    # Utility to format PI assignment in consistent PI order
    def format_vector(self, values: Dict[str, str]) -> str:
        return "".join(values.get(pi, L.LX) for pi in self.primary_inputs)
