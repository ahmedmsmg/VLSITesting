"""PySAT backend: CNF encoding of circuits via Tseitin transformation.

Provides an alternative to the Z3 backend for use-cases where a pure SAT
solver (e.g., for integration with other tools or for performance) is
preferred over an SMT solver.

Requires the ``python-sat`` package::

    pip install python-sat

Usage::

    from formal.pysat_backend import PySATEncoder, solve_cnf
    from ckt_parser import parse_file

    circuit = parse_file("examples/t4_3.ckt")
    enc = PySATEncoder(circuit)
    formula, var_map = enc.encode()
    # formula is a pysat.formula.CNF object
    # var_map maps net names to integer variable IDs
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Dict, List, Optional, Tuple

try:
    from pysat.formula import CNF
    from pysat.solvers import Glucose3
    _PYSAT_AVAILABLE = True
except ImportError:
    _PYSAT_AVAILABLE = False

from circuit import Circuit, Gate


def _require_pysat() -> None:
    if not _PYSAT_AVAILABLE:
        raise RuntimeError(
            "PySAT backend requires the 'python-sat' package. "
            "Install it via `pip install python-sat`."
        )


class PySATEncoder:
    """Tseitin-transform a combinational circuit into a CNF formula.

    Each net becomes an integer variable.  Gate semantics are encoded as
    short CNF clauses using standard Tseitin equivalences, preserving
    equisatisfiability with the original circuit function.

    Variable numbering starts at 1 (DIMACS convention).
    """

    def __init__(self, circuit: Circuit) -> None:
        _require_pysat()
        self.circuit = circuit
        self._counter = 0
        self._var_map: Dict[str, int] = {}

    def _new_var(self) -> int:
        self._counter += 1
        return self._counter

    def _var(self, net: str) -> int:
        if net not in self._var_map:
            self._var_map[net] = self._new_var()
        return self._var_map[net]

    @staticmethod
    def _and_clauses(out: int, ins: List[int]) -> List[List[int]]:
        """out ↔ AND(ins) in CNF."""
        clauses: List[List[int]] = []
        # out → each input
        for i in ins:
            clauses.append([-out, i])
        # AND(ins) → out
        clauses.append([out] + [-i for i in ins])
        return clauses

    @staticmethod
    def _or_clauses(out: int, ins: List[int]) -> List[List[int]]:
        """out ↔ OR(ins) in CNF."""
        clauses: List[List[int]] = []
        for i in ins:
            clauses.append([out, -i])
        clauses.append([-out] + ins)
        return clauses

    @staticmethod
    def _not_clauses(out: int, inp: int) -> List[List[int]]:
        """out ↔ NOT(inp) in CNF."""
        return [[-out, -inp], [out, inp]]

    @staticmethod
    def _buf_clauses(out: int, inp: int) -> List[List[int]]:
        """out ↔ inp in CNF."""
        return [[-out, inp], [out, -inp]]

    @staticmethod
    def _xor2_clauses(out: int, a: int, b: int) -> List[List[int]]:
        """out ↔ XOR(a, b) in CNF."""
        return [
            [-out, a, b],
            [-out, -a, -b],
            [out, -a, b],
            [out, a, -b],
        ]

    def _encode_gate(self, gate: Gate, clauses: List[List[int]]) -> None:
        out = self._var(gate.output)
        ins = [self._var(i) for i in gate.inputs]
        typ = gate.type

        if typ == "BUF":
            clauses.extend(self._buf_clauses(out, ins[0]))
        elif typ in {"NOT", "INV"}:
            clauses.extend(self._not_clauses(out, ins[0]))
        elif typ == "AND":
            clauses.extend(self._and_clauses(out, ins))
        elif typ == "OR":
            clauses.extend(self._or_clauses(out, ins))
        elif typ == "NAND":
            and_tmp = self._new_var()
            clauses.extend(self._and_clauses(and_tmp, ins))
            clauses.extend(self._not_clauses(out, and_tmp))
        elif typ == "NOR":
            or_tmp = self._new_var()
            clauses.extend(self._or_clauses(or_tmp, ins))
            clauses.extend(self._not_clauses(out, or_tmp))
        elif typ in {"XOR", "XNOR"}:
            # Build XOR tree with intermediate variables
            current = ins[0]
            for nxt in ins[1:]:
                xor_tmp = self._new_var()
                clauses.extend(self._xor2_clauses(xor_tmp, current, nxt))
                current = xor_tmp
            if typ == "XOR":
                clauses.extend(self._buf_clauses(out, current))
            else:  # XNOR
                clauses.extend(self._not_clauses(out, current))
        else:
            raise ValueError(f"Unsupported gate type '{typ}' in PySAT encoding")

    def encode(self) -> Tuple["CNF", Dict[str, int]]:
        """Encode the circuit into CNF.

        Returns:
            (cnf, var_map) where *cnf* is a :class:`pysat.formula.CNF` and
            *var_map* maps net names to their DIMACS integer IDs.
        """
        _require_pysat()
        self._counter = 0
        self._var_map = {}
        clauses: List[List[int]] = []

        self.circuit.build_topological()
        # Pre-allocate PI variables in order
        for pi in self.circuit.primary_inputs:
            self._var(pi)
        for gate in self.circuit.topo:
            self._encode_gate(gate, clauses)

        cnf = CNF(from_clauses=clauses)
        return cnf, dict(self._var_map)


def solve_cnf(
    cnf: "CNF",
    assumptions: Optional[List[int]] = None,
) -> Optional[List[int]]:
    """Solve a CNF formula and return a satisfying model or None.

    Args:
        cnf: A :class:`pysat.formula.CNF` instance.
        assumptions: Optional list of assumed literals (DIMACS signed integers).

    Returns:
        A list of model literals if SAT, or ``None`` if UNSAT.
    """
    _require_pysat()
    solver = Glucose3()
    solver.append_formula(cnf)
    if solver.solve(assumptions or []):
        model = solver.get_model()
        solver.delete()
        return model
    solver.delete()
    return None
