"""Circuit representation and five-valued simulation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ckt_parser import GateDef, Netlist, fanout_map
from fault import Fault
import logic5 as l5


@dataclass
class Gate:
    name: str
    gate_type: str
    inputs: List[str]

    def eval_output(self, values: Dict[str, str]) -> str:
        """Evaluate gate output using five-valued algebra."""
        ins = [values.get(i, l5.LX) for i in self.inputs]
        if self.gate_type in {"NOT", "INV"}:
            out = l5.logic_not(ins[0])
        elif self.gate_type == "BUF":
            out = ins[0]
        elif self.gate_type in {"AND", "NAND"}:
            out = ins[0]
            for val in ins[1:]:
                out = l5.logic_and(out, val)
            if self.gate_type == "NAND":
                out = l5.logic_not(out)
        elif self.gate_type in {"OR", "NOR"}:
            out = ins[0]
            for val in ins[1:]:
                out = l5.logic_or(out, val)
            if self.gate_type == "NOR":
                out = l5.logic_not(out)
        elif self.gate_type in {"XOR", "XNOR"}:
            out = ins[0]
            for val in ins[1:]:
                out = l5.logic_xor(out, val)
            if self.gate_type == "XNOR":
                out = l5.logic_not(out)
        else:
            raise ValueError(f"Unsupported gate type {self.gate_type}")
        return out


@dataclass
class Circuit:
    primary_inputs: List[str]
    primary_outputs: List[str]
    gates: Dict[str, Gate]
    fanouts: Dict[str, List[str]]
    topo_order: List[str]
    all_signals: List[str]

    @classmethod
    def from_netlist(cls, netlist: Netlist) -> "Circuit":
        gates = {g.output: Gate(g.output, g.gate_type, g.inputs) for g in netlist.gates}
        fanouts = fanout_map(netlist.gates)
        order = cls._topological_order(netlist.primary_inputs, gates)
        all_signals = list({*netlist.primary_inputs, *gates.keys(), *(i for g in gates.values() for i in g.inputs)})
        return cls(
            primary_inputs=list(netlist.primary_inputs),
            primary_outputs=list(netlist.primary_outputs),
            gates=gates,
            fanouts=fanouts,
            topo_order=order,
            all_signals=all_signals,
        )

    @staticmethod
    def _topological_order(pis: List[str], gates: Dict[str, Gate]) -> List[str]:
        known = set(pis)
        order: List[str] = []
        remaining = set(gates.keys())
        while remaining:
            progressed = False
            for name in list(remaining):
                if all(inp in known for inp in gates[name].inputs):
                    order.append(name)
                    known.add(name)
                    remaining.remove(name)
                    progressed = True
            if not progressed:
                raise ValueError("Netlist contains combinational loop or missing signal")
        return order

    def initialize_state(self) -> Dict[str, str]:
        return {sig: l5.LX for sig in self.all_signals}

    def imply(self, assignments: Dict[str, str], fault: Optional[Fault] = None) -> Dict[str, str]:
        """Forward imply known assignments through the circuit using five-valued logic."""
        values = {sig: assignments.get(sig, l5.LX) for sig in self.all_signals}

        # Load primary inputs first
        for pi in self.primary_inputs:
            val = values.get(pi, l5.LX)
            if fault and fault.net == pi and not l5.is_unknown(val):
                good = 1 if val in {l5.L1, l5.LD} else 0 if val in {l5.L0, l5.LD_BAR} else None
                faulty_val = fault.stuck_at
                values[pi] = l5.from_pair((good, faulty_val))
            elif val not in {l5.L0, l5.L1, l5.LD, l5.LD_BAR, l5.LX}:
                values[pi] = l5.LX

        # Propagate through gates
        for gate_name in self.topo_order:
            gate = self.gates[gate_name]
            if all(not l5.is_unknown(values.get(inp, l5.LX)) for inp in gate.inputs):
                out = gate.eval_output(values)
            else:
                out = values.get(gate.name, l5.LX)
            if fault and gate.name == fault.net and not l5.is_unknown(out):
                good, _ = l5.to_pair(out)
                out = l5.from_pair((good, fault.stuck_at))
            values[gate.name] = out
        return values

    def evaluate_good_faulty(self, pi_assignment: Dict[str, int], fault: Optional[Fault] = None) -> Tuple[Dict[str, int], Dict[str, int]]:
        """Classic binary simulation for reporting."""
        values: Dict[str, int] = {}
        for pi, bit in pi_assignment.items():
            values[pi] = bit
        for gate_name in self.topo_order:
            gate = self.gates[gate_name]
            ins = [values[i] for i in gate.inputs]
            if gate.gate_type in {"NOT", "INV"}:
                out = 1 - ins[0]
            elif gate.gate_type == "BUF":
                out = ins[0]
            elif gate.gate_type in {"AND", "NAND"}:
                out = int(all(ins))
                if gate.gate_type == "NAND":
                    out = 1 - out
            elif gate.gate_type in {"OR", "NOR"}:
                out = int(any(ins))
                if gate.gate_type == "NOR":
                    out = 1 - out
            elif gate.gate_type in {"XOR", "XNOR"}:
                out = 0
                for bit in ins:
                    out ^= bit
                if gate.gate_type == "XNOR":
                    out = 1 - out
            else:
                raise ValueError(f"Unsupported gate type {gate.gate_type}")
            if fault and gate.name == fault.net:
                faulty_out = fault.stuck_at
            else:
                faulty_out = out
            values[gate.name] = out
            values[("faulty", gate.name)] = faulty_out
        if fault and fault.net in self.primary_inputs:
            values[("faulty", fault.net)] = fault.stuck_at
        good = {po: values[po] for po in self.primary_outputs}
        faulty_outputs: Dict[str, int] = {}
        for po in self.primary_outputs:
            val = values.get(("faulty", po), values[po])
            faulty_outputs[po] = val
        return good, faulty_outputs

    def d_frontier(self, values: Dict[str, str]) -> List[Gate]:
        frontier = []
        for name in self.topo_order:
            gate = self.gates[name]
            out_val = values.get(gate.name, l5.LX)
            if not l5.is_unknown(out_val):
                continue
            if any(l5.is_d_like(values.get(inp, l5.LX)) for inp in gate.inputs):
                frontier.append(gate)
        return frontier

    def x_path_exists(self, start_gate: Gate, values: Dict[str, str]) -> bool:
        """DFS to see if an X path exists from gate output to any PO."""
        stack = [start_gate.name]
        visited = set()
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            if node in self.primary_outputs and l5.is_unknown(values.get(node, l5.LX)):
                return True
            for fo in self.fanouts.get(node, []):
                if l5.is_unknown(values.get(fo, l5.LX)):
                    stack.append(fo)
        return False

    def assignments_to_vector(self, assigns: Dict[str, str]) -> Optional[str]:
        bits = []
        for pi in self.primary_inputs:
            val = assigns.get(pi, l5.LX)
            if l5.is_unknown(val):
                return None
            bits.append("1" if val in {l5.L1, l5.LD} else "0")
        return "".join(bits)

