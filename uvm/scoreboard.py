"""UVM-aligned scoreboard: runtime equivalence checking.

Compares DUT outputs against a reference model (a second Circuit object)
transaction by transaction.  Functions as the runtime complement to the
formal :class:`~formal.equivalence.EquivalenceChecker`.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from circuit import Circuit
from uvm.base import UVMComponent
from uvm.agent import Transaction


@dataclass
class Mismatch:
    """Records one scoreboard failure."""
    inputs: Dict[str, str]
    dut_outputs: Dict[str, str]
    ref_outputs: Dict[str, str]
    differing_nets: List[str]

    def __str__(self) -> str:
        inp_str = ", ".join(f"{k}={v}" for k, v in self.inputs.items())
        return (
            f"MISMATCH @ inputs [{inp_str}]\n"
            f"  DUT: {self.dut_outputs}\n"
            f"  REF: {self.ref_outputs}\n"
            f"  Differing: {self.differing_nets}"
        )


class UVMScoreboard(UVMComponent):
    """Compares DUT outputs against a reference model per transaction.

    The reference model is a :class:`~circuit.Circuit` whose
    ``evaluate_vector()`` result is the expected output.  If no reference is
    provided, the scoreboard operates in monitoring-only mode (counts
    transactions but never flags mismatches).

    Register with a :class:`~uvm.agent.UVMMonitor` via::

        monitor.add_callback(scoreboard.compare)
    """

    def __init__(
        self,
        name: str,
        parent: Optional[UVMComponent] = None,
        reference: Optional[Circuit] = None,
    ) -> None:
        super().__init__(name, parent)
        self.reference = reference
        self.matches: int = 0
        self.mismatches: int = 0
        self._mismatch_log: List[Mismatch] = []

    # ── Analysis-port callback ────────────────────────────────────────────────

    def compare(self, txn: Transaction) -> bool:
        """Compare DUT output in *txn* against the reference model.

        Returns True if they match (or if no reference is set).
        """
        if self.reference is None:
            self.matches += 1
            return True

        inputs = txn["inputs"]
        dut_outputs = txn["outputs"]

        # Filter inputs to only the reference circuit's PIs (handles extra nets).
        ref_inputs = {
            pi: inputs.get(pi, "X")
            for pi in self.reference.primary_inputs
        }
        ref_outputs = self.reference.evaluate_vector(ref_inputs)

        # Compare only PO nets.
        differing = [
            po for po in self.reference.primary_outputs
            if dut_outputs.get(po) != ref_outputs.get(po)
        ]

        if differing:
            self.mismatches += 1
            self._mismatch_log.append(
                Mismatch(
                    inputs=inputs,
                    dut_outputs={po: dut_outputs.get(po, "?") for po in self.reference.primary_outputs},
                    ref_outputs={po: ref_outputs.get(po, "?") for po in self.reference.primary_outputs},
                    differing_nets=differing,
                )
            )
            return False

        self.matches += 1
        return True

    # ── Reporting ─────────────────────────────────────────────────────────────

    @property
    def total(self) -> int:
        return self.matches + self.mismatches

    @property
    def pass_rate(self) -> float:
        return self.matches / self.total if self.total else 1.0

    def report(self) -> str:
        lines = [
            "=== Scoreboard Report ===",
            f"  Total transactions : {self.total}",
            f"  Matches            : {self.matches}",
            f"  Mismatches         : {self.mismatches}",
            f"  Pass rate          : {self.pass_rate:.1%}",
        ]
        for m in self._mismatch_log[:5]:  # show first 5
            lines.append(str(m))
        if len(self._mismatch_log) > 5:
            lines.append(f"  ... ({len(self._mismatch_log) - 5} more mismatches)")
        return "\n".join(lines)

    def report_phase(self) -> None:
        print(self.report())
