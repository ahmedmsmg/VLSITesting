"""Bounded Model Checking (BMC) for sequential circuits.

Extends the combinational :class:`CircuitEncoder` by unrolling a circuit with
flip-flops for *k* time steps and checking whether a bad-state property is
reachable within those steps.

Sequential support requires the :class:`~circuit.Circuit` to have
``flip_flops`` populated (a list of :class:`~circuit.FlipFlop` objects added
in Phase 2 of the project).  Purely combinational circuits (no flip-flops) are
also supported: BMC on them reduces to a single-step property check.

Usage::

    from formal.bmc import BoundedModelChecker, BadStateProperty

    bad = BadStateProperty(
        name="output_never_1",
        formula=lambda enc, step: enc.var("Z") == True,
    )
    result = BoundedModelChecker(circuit).check(bad, bound=5)
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from z3 import And, Bool, BoolRef, Not, Or, Solver, sat

from circuit import Circuit, Gate
from formal.encoder import CircuitEncoder


# ---------------------------------------------------------------------------
# Bad-state property for BMC
# ---------------------------------------------------------------------------

@dataclass
class BadStateProperty:
    """A condition that, if reachable, constitutes a violation.

    ``formula`` receives the :class:`_StepEncoder` for a given time step and
    must return a Z3 :class:`BoolRef` that is ``True`` when the bad state is
    entered at that step.
    """

    name: str
    formula: Callable[["_StepEncoder", int], BoolRef]
    description: str = ""


@dataclass
class BMCResult:
    """Result of a bounded model check."""

    property_name: str
    reachable: bool
    step: Optional[int] = None
    witness: Optional[List[Dict[str, str]]] = None  # input sequence per step

    def __str__(self) -> str:
        if not self.reachable:
            return (
                f"Property '{self.property_name}': "
                f"bad state NOT reachable within bound."
            )
        lines = [
            f"Property '{self.property_name}': bad state REACHABLE at step {self.step}."
        ]
        if self.witness:
            for i, inputs in enumerate(self.witness):
                inp_str = ", ".join(f"{k}={v}" for k, v in inputs.items())
                lines.append(f"  Step {i}: {inp_str}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal per-step encoder (wraps CircuitEncoder with time-step suffix)
# ---------------------------------------------------------------------------

class _StepEncoder:
    """Wraps a :class:`CircuitEncoder` for a specific time step *k*."""

    def __init__(self, circuit: Circuit, step: int) -> None:
        self._enc = CircuitEncoder(circuit, suffix=f"t{step}")
        self.step = step

    def var(self, net: str) -> BoolRef:
        return self._enc.var(net)

    def state_var(self, net: str) -> BoolRef:
        """Return the state variable for *net* at this step."""
        return Bool(f"state_{net}_t{self.step}")

    def encode(self) -> List[BoolRef]:
        return self._enc.encode()


# ---------------------------------------------------------------------------
# Bounded Model Checker
# ---------------------------------------------------------------------------

class BoundedModelChecker:
    """Unroll a (possibly sequential) circuit for up to *bound* steps.

    For each step from 0 to *bound − 1*:
      1. Encode the combinational cone.
      2. If the circuit has flip-flops, constrain FF inputs/outputs across steps.
      3. Assert the bad-state property; if SAT, we found a witness.

    If no violation is found within *bound* steps, the result reports
    ``reachable=False`` (inconclusive — the property *may* still be violated
    beyond the bound).
    """

    def __init__(self, circuit: Circuit) -> None:
        self.circuit = circuit
        self._has_ffs = hasattr(circuit, "flip_flops") and bool(circuit.flip_flops)

    def check(self, bad: BadStateProperty, bound: int = 10) -> BMCResult:
        """Search for the bad state within *bound* time steps (incremental)."""
        solver = Solver()
        step_encoders: List[_StepEncoder] = []

        for k in range(bound):
            enc = _StepEncoder(self.circuit, k)
            step_encoders.append(enc)

            # Combinational constraints for this step.
            solver.add(enc.encode())

            # Sequential: tie FF output at step k to FF input at step k-1.
            if self._has_ffs:
                for ff in self.circuit.flip_flops:  # type: ignore[attr-defined]
                    q_k = enc.state_var(ff.output)
                    if k == 0:
                        # Initial state
                        init_val = ff.initial
                        if init_val == "0":
                            solver.add(q_k == False)
                        elif init_val == "1":
                            solver.add(q_k == True)
                        # "X" → unconstrained (leave free)
                    else:
                        # Q at step k = D input at step k-1
                        prev_enc = step_encoders[k - 1]
                        d_prev = prev_enc.var(ff.input)
                        solver.add(q_k == d_prev)

                    # Tie FF output net in the combinational cone to state var.
                    solver.add(enc.var(ff.output) == q_k)

            # Check bad-state property at this step.
            bad_at_k = bad.formula(enc, k)
            solver.push()
            solver.add(bad_at_k)

            if solver.check() == sat:
                model = solver.model()
                witness: List[Dict[str, str]] = []
                for step_enc in step_encoders[: k + 1]:
                    step_inputs: Dict[str, str] = {}
                    for pi in self.circuit.primary_inputs:
                        interp = model.eval(step_enc.var(pi), model_completion=True)
                        step_inputs[pi] = "1" if bool(interp) else "0"
                    witness.append(step_inputs)
                return BMCResult(
                    property_name=bad.name,
                    reachable=True,
                    step=k,
                    witness=witness,
                )

            solver.pop()

        return BMCResult(property_name=bad.name, reachable=False)
