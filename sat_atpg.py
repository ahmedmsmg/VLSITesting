"""SAT-based ATPG using PySAT.

The solver dependency is optional at import time so the rest of the tool can
still run in environments where ``python-sat`` is not installed. Attempting to
invoke the SAT algorithm without the dependency will raise a clear, actionable
error.
"""
from __future__ import annotations
from typing import Dict, Tuple, List, Optional
import importlib.util

HAS_PYSAT = importlib.util.find_spec("pysat") is not None
if HAS_PYSAT:
    from pysat.formula import CNF
    from pysat.solvers import Solver

from circuit import Circuit, Gate
from fault import Fault


class VarMap:
    def __init__(self) -> None:
        self._map: Dict[Tuple[str, str], int] = {}
        self._counter = 1

    def var(self, net: str, suffix: str) -> int:
        key = (net, suffix)
        if key not in self._map:
            self._map[key] = self._counter
            self._counter += 1
        return self._map[key]


class SatATPG:
    def __init__(self, circuit: Circuit) -> None:
        if not HAS_PYSAT:
            raise RuntimeError(
                "SAT-based ATPG requires the 'python-sat' package. Install it via "
                "`pip install python-sat[pblib,aiger]` or select another algorithm."
            )
        self.circuit = circuit
        self.circuit.build_topological()

    def encode_gate(self, cnf: CNF, gate: Gate, suffix: str, vmap: VarMap) -> None:
        out = vmap.var(gate.output, suffix)
        ins = [vmap.var(i, suffix) for i in gate.inputs]
        typ = gate.type
        if typ in {"BUF", "NOT", "INV"}:
            a = ins[0]
            if typ == "BUF":
                cnf.extend([[ -a, out], [a, -out]])
            else:
                cnf.extend([[a, out], [-a, -out]])
            return
        if typ in {"AND", "NAND", "OR", "NOR"}:
            if typ in {"NAND", "NOR"}:
                base_out = vmap.var(f"tmp_{gate.output}_{suffix}", suffix)
                base_typ = "AND" if typ == "NAND" else "OR"
                base_gate = Gate(output=f"tmp_{gate.output}_{suffix}", type=base_typ, inputs=gate.inputs)
                self.encode_gate(cnf, base_gate, suffix, vmap)
                cnf.extend([[base_out, out], [-base_out, -out]])
                return
            if typ == "AND":
                for a in ins:
                    cnf.append([-a, out])
                cnf.append([ -out] + ins)
                return
            if typ == "OR":
                for a in ins:
                    cnf.append([a, -out])
                cnf.append([out] + [-a for a in ins])
                return
        if typ in {"XOR", "XNOR"}:
            if typ == "XNOR":
                aux_out = vmap.var(f"tmp_{gate.output}_{suffix}", suffix)
                self.encode_gate(
                    cnf,
                    Gate(output=f"tmp_{gate.output}_{suffix}", type="XOR", inputs=gate.inputs),
                    suffix,
                    vmap,
                )
                cnf.extend([[aux_out, out], [-aux_out, -out]])
                return
            # XOR two-input encoding
            a, b = ins
            cnf.extend([[ -a, -b, -out], [ -a, b, out], [a, -b, out], [a, b, -out]])
            return
        raise ValueError(f"Unsupported gate type {typ} in SAT encoding")

    def build_cnf(self, fault: Fault) -> Tuple[CNF, VarMap]:
        cnf = CNF()
        vmap = VarMap()
        # encode both good and faulty circuits
        for suffix in ["g", "f"]:
            for pi in self.circuit.primary_inputs:
                vmap.var(pi, suffix)
            for g in self.circuit.topo:
                self.encode_gate(cnf, g, suffix, vmap)
        # fault injection on faulty copy
        stuck_var = vmap.var(fault.node, "f")
        if fault.stuck_at == 0:
            cnf.append([-stuck_var])
        else:
            cnf.append([stuck_var])
        # output difference constraint
        diff_vars: List[int] = []
        for po in self.circuit.primary_outputs:
            gvar = vmap.var(po, "g")
            fvar = vmap.var(po, "f")
            diff = vmap.var(f"diff_{po}", "aux")
            # diff <-> gvar xor fvar
            cnf.extend([[ -gvar, -fvar, -diff], [ -gvar, fvar, diff], [gvar, -fvar, diff], [gvar, fvar, -diff]])
            diff_vars.append(diff)
        cnf.append(diff_vars)  # at least one differs
        # tie PIs equal between good and faulty
        for pi in self.circuit.primary_inputs:
            g = vmap.var(pi, "g")
            f = vmap.var(pi, "f")
            cnf.extend([[ -g, f], [g, -f]])
        return cnf, vmap

    def solve(self, fault: Fault) -> Optional[Dict[str, str]]:
        cnf, vmap = self.build_cnf(fault)
        with Solver(name="glucose3", bootstrap_with=cnf) as solver:
            if not solver.solve():
                return None
            model = solver.get_model()
        assignment: Dict[str, str] = {}
        for pi in self.circuit.primary_inputs:
            var = vmap.var(pi, "g")
            assignment[pi] = "1" if var in model else "0" if -var in model else "X"
        return assignment


def sat_atpg(circ: Circuit, fault: Fault) -> Optional[Dict[str, str]]:
    engine = SatATPG(circ)
    return engine.solve(fault)
