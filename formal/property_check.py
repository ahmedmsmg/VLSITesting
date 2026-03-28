"""Formal property checking using Z3.

A :class:`Property` is a named Boolean formula over circuit nets.
:class:`PropertyChecker` encodes the circuit and checks whether the property
holds for *all* possible input assignments (UNSAT on the negated formula) or
is violated (SAT, producing a counterexample).

Example::

    from formal.property_check import Property, PropertyChecker

    # "Output Z is always 0 when both A and B are 0"
    prop = Property(
        name="z_zero_when_ab_zero",
        formula=lambda enc: Implies(
            And(enc.var("A") == False, enc.var("B") == False),
            enc.var("Z") == False,
        ),
    )
    result = PropertyChecker(circuit).check(prop)
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from z3 import BoolRef, Not, Solver, sat

from circuit import Circuit
from formal.encoder import CircuitEncoder


@dataclass
class Property:
    """A named Boolean property over circuit nets.

    The ``formula`` callable receives a fully-built :class:`CircuitEncoder`
    (so all PI and gate-output Z3 variables are accessible via
    ``enc.var(net_name)``) and must return a Z3 :class:`BoolRef`.

    The property is considered to *hold* when the formula evaluates to ``True``
    for every possible primary-input assignment.
    """

    name: str
    formula: Callable[[CircuitEncoder], BoolRef]
    description: str = ""


@dataclass
class PropertyResult:
    """Result of checking a single property."""

    property_name: str
    holds: bool
    counterexample: Optional[Dict[str, str]] = None

    def __str__(self) -> str:
        status = "HOLDS" if self.holds else "VIOLATED"
        msg = f"Property '{self.property_name}': {status}"
        if not self.holds and self.counterexample:
            ce_str = ", ".join(f"{k}={v}" for k, v in self.counterexample.items())
            msg += f"\n  Counterexample: {ce_str}"
        return msg


class PropertyChecker:
    """Check Boolean properties against a combinational circuit.

    Usage::

        checker = PropertyChecker(circuit)
        result  = checker.check(prop)
    """

    def __init__(self, circuit: Circuit) -> None:
        self.circuit = circuit

    def check(self, prop: Property) -> PropertyResult:
        """Check whether *prop* holds for all circuit inputs.

        Internally, we negate the property and ask the SAT solver.  If the
        negation is UNSATISFIABLE, no input can violate the property → it
        holds universally.  If SAT, we have a concrete counterexample.
        """
        enc = CircuitEncoder(self.circuit, suffix="")
        constraints = enc.encode()

        prop_expr = prop.formula(enc)
        # Negate the property: if NOT(prop) is SAT, the property is violated.
        constraints.append(Not(prop_expr))

        solver = Solver()
        solver.add(constraints)

        if solver.check() != sat:
            return PropertyResult(property_name=prop.name, holds=True)

        model = solver.model()
        counterexample: Dict[str, str] = {}
        for pi in self.circuit.primary_inputs:
            interp = model.eval(enc.var(pi), model_completion=True)
            counterexample[pi] = "1" if bool(interp) else "0"

        return PropertyResult(
            property_name=prop.name,
            holds=False,
            counterexample=counterexample,
        )

    def check_all(self, properties: List[Property]) -> List[PropertyResult]:
        """Check a list of properties and return all results."""
        return [self.check(p) for p in properties]
