"""UVM-aligned top-level verification environment.

UVMEnv wires together an agent, scoreboard, coverage group, and assertion
list into a single component that can be driven with a sequence.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import List, Optional

from circuit import Circuit
from uvm.base import UVMComponent
from uvm.agent import UVMAgent, Transaction
from uvm.scoreboard import UVMScoreboard
from uvm.coverage import CoverGroup
from uvm.assertions import Assertion, ImmediateAssertion, ConcurrentAssertion
from uvm.sequence import UVMSequence


class UVMEnv(UVMComponent):
    """Top-level verification environment.

    Instantiates and wires:
    - One :class:`~uvm.agent.UVMAgent` (driver + monitor)
    - One :class:`~uvm.scoreboard.UVMScoreboard`
    - One :class:`~uvm.coverage.CoverGroup` (``"functional_coverage"``)
    - A list of :class:`~uvm.assertions.Assertion` objects

    Usage::

        env = UVMEnv("env", circuit=dut, reference=golden_model)
        env.add_assertion(my_assertion)
        env.build_phase()
        env.run_sequence(sequence)
        env.report_phase()
    """

    def __init__(
        self,
        name: str,
        circuit: Circuit,
        reference: Optional[Circuit] = None,
    ) -> None:
        super().__init__(name)
        self.circuit = circuit
        self._reference = reference
        # Sub-components (wired in build_phase)
        self.agent      = UVMAgent("agent", self)
        self.scoreboard = UVMScoreboard("scoreboard", self, reference)
        self.coverage   = CoverGroup("functional_coverage")
        self._assertions: List[Assertion] = []

    # ── Phase hooks ───────────────────────────────────────────────────────────

    def build_phase(self) -> None:
        """Wire driver circuit and connect monitor callbacks."""
        self.agent.driver.circuit = self.circuit
        self.agent.monitor.add_callback(self.scoreboard.compare)
        self.agent.monitor.add_callback(self._sample_coverage)
        self.agent.monitor.add_callback(self._check_assertions)

    def report_phase(self) -> None:
        """Print scoreboard and coverage summaries."""
        print(self.scoreboard.report())
        print(self.coverage.report())
        for a in self._assertions:
            print(a.report())

    # ── Public API ────────────────────────────────────────────────────────────

    def add_assertion(self, assertion: Assertion) -> None:
        self._assertions.append(assertion)

    def run_sequence(self, sequence: UVMSequence) -> None:
        """Drive a sequence through the agent (shortcut for single-sequence runs)."""
        self.agent.run_sequence(sequence)

    # ── Internal callbacks ────────────────────────────────────────────────────

    def _sample_coverage(self, txn: Transaction) -> None:
        self.coverage.sample(txn)

    def _check_assertions(self, txn: Transaction) -> None:
        for assertion in self._assertions:
            if isinstance(assertion, ImmediateAssertion):
                assertion.check(txn)
            elif isinstance(assertion, ConcurrentAssertion):
                assertion.check(txn)
