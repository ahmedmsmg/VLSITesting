"""SAT-based ATPG using CNF construction and an internal DPLL solver."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ckt_parser import GateDef
from circuit import Circuit
from fault import Fault


class CnfBuilder:
    def __init__(self) -> None:
        self.clauses: List[List[int]] = []
        self.var_for: Dict[Tuple[str, str], int] = {}
        self.var_count = 0

    def new_var(self, name: Tuple[str, str]) -> int:
        if name in self.var_for:
            return self.var_for[name]
        self.var_count += 1
        self.var_for[name] = self.var_count
        return self.var_count

    def gate_encode(self, out_var: int, gate: GateDef, input_vars: List[int]) -> None:
        if gate.gate_type in {"AND", "NAND"}:
            for inp in input_vars:
                self.clauses.append([-out_var, inp])
            self.clauses.append([out_var] + [-i for i in input_vars])
            if gate.gate_type == "NAND":
                self._invert(out_var)
        elif gate.gate_type in {"OR", "NOR"}:
            for inp in input_vars:
                self.clauses.append([out_var, -inp])
            self.clauses.append([-out_var] + input_vars)
            if gate.gate_type == "NOR":
                self._invert(out_var)
        elif gate.gate_type in {"XOR", "XNOR"}:
            assert len(input_vars) == 2, "Only 2-input XOR/XNOR supported"
            a, b = input_vars
            self.clauses.extend([
                [-out_var, -a, -b],
                [-out_var, a, b],
                [out_var, -a, b],
                [out_var, a, -b],
            ])
            if gate.gate_type == "XNOR":
                self._invert(out_var)
        elif gate.gate_type in {"NOT", "INV"}:
            inp = input_vars[0]
            self.clauses.append([-out_var, -inp])
            self.clauses.append([out_var, inp])
        elif gate.gate_type == "BUF":
            inp = input_vars[0]
            self.clauses.append([-out_var, inp])
            self.clauses.append([out_var, -inp])
        else:
            raise ValueError(f"Unsupported gate type {gate.gate_type}")

    def _invert(self, var: int) -> None:
        self.clauses.append([-var, -var])

    def add_clause(self, clause: List[int]) -> None:
        self.clauses.append(clause)


class DPLLSolver:
    def __init__(self, clauses: List[List[int]], num_vars: int):
        self.clauses = clauses
        self.num_vars = num_vars

    def solve(self) -> Optional[List[bool]]:
        assignment = [False] * (self.num_vars + 1)
        unassigned = set(range(1, self.num_vars + 1))
        if self._search(self.clauses, assignment, unassigned):
            return assignment[1:]
        return None

    def _search(self, clauses: List[List[int]], assignment: List[bool], unassigned: set[int]) -> bool:
        result = self._unit_propagate(clauses, assignment, unassigned)
        if result is None:
            return False
        clauses, assignment = result
        if not clauses:
            return True
        if not unassigned:
            return False
        var = next(iter(unassigned))
        unassigned.remove(var)
        for value in [True, False]:
            new_assign = assignment.copy()
            new_assign[var] = value
            new_clauses = self._simplify(clauses, var, value)
            if self._search(new_clauses, new_assign, set(unassigned)):
                assignment[:] = new_assign
                return True
        return False

    def _unit_propagate(self, clauses: List[List[int]], assignment: List[bool], unassigned: set[int]):
        changed = True
        while changed:
            changed = False
            for clause in list(clauses):
                if len(clause) == 1:
                    lit = clause[0]
                    var = abs(lit)
                    val = lit > 0
                    if var not in unassigned and assignment[var] != val:
                        return None
                    if var in unassigned:
                        unassigned.remove(var)
                        assignment[var] = val
                        clauses = self._simplify(clauses, var, val)
                        changed = True
                        break
                if clause == [0]:
                    return None
        return clauses, assignment

    def _simplify(self, clauses: List[List[int]], var: int, val: bool) -> List[List[int]]:
        new_clauses: List[List[int]] = []
        for clause in clauses:
            if (val and var in clause) or (not val and -var in clause):
                continue
            if (val and -var in clause) or (not val and var in clause):
                new_clause = [lit for lit in clause if lit not in {var, -var}]
                if not new_clause:
                    new_clause = [0]
                new_clauses.append(new_clause)
            else:
                new_clauses.append(clause)
        return new_clauses


def build_cnf(circuit: Circuit, fault: Fault) -> Tuple[CnfBuilder, Dict[str, int]]:
    builder = CnfBuilder()
    mapping: Dict[str, int] = {}
    for signal in circuit.all_signals:
        mapping[signal + "_g"] = builder.new_var((signal, "g"))
        mapping[signal + "_f"] = builder.new_var((signal, "f"))
    for pi in circuit.primary_inputs:
        g = mapping[pi + "_g"]
        f = mapping[pi + "_f"]
        builder.add_clause([g, -f])
        builder.add_clause([-g, f])
    for name in circuit.topo_order:
        gate = circuit.gates[name]
        out_g = mapping[name + "_g"]
        out_f = mapping[name + "_f"]
        ins_g = [mapping[inp + "_g"] for inp in gate.inputs]
        ins_f = [mapping[inp + "_f"] for inp in gate.inputs]
        builder.gate_encode(out_g, GateDef(gate.name, gate.gate_type, gate.inputs), ins_g)
        builder.gate_encode(out_f, GateDef(gate.name, gate.gate_type, gate.inputs), ins_f)
    fault_var = mapping[fault.net + "_f"]
    builder.add_clause([fault_var if fault.stuck_at == 1 else -fault_var])
    diff_vars = []
    for po in circuit.primary_outputs:
        g = mapping[po + "_g"]
        f = mapping[po + "_f"]
        diff = builder.new_var((po, "diff"))
        builder.add_clause([-diff, g, f])
        builder.add_clause([-diff, -g, -f])
        builder.add_clause([diff, -g, f])
        builder.add_clause([diff, g, -f])
        diff_vars.append(diff)
    builder.add_clause(diff_vars)
    return builder, mapping


def solve_with_sat(circuit: Circuit, fault: Fault) -> Optional[str]:
    builder, mapping = build_cnf(circuit, fault)
    solver = DPLLSolver(builder.clauses, builder.var_count)
    model = solver.solve()
    if model is None:
        return None
    pi_bits = []
    for pi in circuit.primary_inputs:
        var = mapping[pi + "_g"]
        val = model[var - 1]
        pi_bits.append("1" if val else "0")
    return "".join(pi_bits)

