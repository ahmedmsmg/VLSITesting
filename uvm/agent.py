"""UVM-aligned Agent, Driver, and Monitor.

- UVMDriver:  Applies stimulus (CircuitVector) to a Circuit and returns
              the output net values.
- UVMMonitor: Observes (input, output) pairs and notifies registered
              callback functions (analysis ports).
- UVMAgent:   Composes one driver and one monitor under a common parent.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Callable, Dict, List, Optional

from circuit import Circuit
from uvm.base import UVMComponent
from uvm.sequence import CircuitVector, UVMSequence


Transaction = Dict[str, Dict[str, str]]  # {"inputs": {..}, "outputs": {..}}


class UVMDriver(UVMComponent):
    """Drives stimulus items into a DUT (Circuit) and returns outputs.

    The driver is intentionally thin: it receives a :class:`CircuitVector`,
    calls ``Circuit.evaluate_vector()``, and returns the full net-value dict.
    """

    def __init__(self, name: str, parent: Optional[UVMComponent] = None) -> None:
        super().__init__(name, parent)
        self.circuit: Optional[Circuit] = None

    def drive(self, item: CircuitVector) -> Dict[str, str]:
        """Apply *item* to the DUT and return all net values."""
        if self.circuit is None:
            raise RuntimeError("UVMDriver.circuit must be set before driving.")
        return self.circuit.evaluate_vector(item.values)


class UVMMonitor(UVMComponent):
    """Observes circuit input/output pairs and broadcasts to analysis ports.

    Analysis ports are plain Python callables that receive a
    :data:`Transaction` dict.  Register them via :meth:`add_callback`.
    """

    def __init__(self, name: str, parent: Optional[UVMComponent] = None) -> None:
        super().__init__(name, parent)
        self._callbacks: List[Callable[[Transaction], None]] = []
        self.observed: List[Transaction] = []

    def add_callback(self, fn: Callable[[Transaction], None]) -> None:
        self._callbacks.append(fn)

    def observe(self, inputs: Dict[str, str], outputs: Dict[str, str]) -> None:
        """Record a transaction and notify all registered callbacks."""
        txn: Transaction = {"inputs": dict(inputs), "outputs": dict(outputs)}
        self.observed.append(txn)
        for cb in self._callbacks:
            cb(txn)


class UVMAgent(UVMComponent):
    """Composes a :class:`UVMDriver` and :class:`UVMMonitor`.

    The agent exposes a high-level :meth:`run_sequence` method that iterates
    over a sequence's body, drives each item, and publishes observations.
    """

    def __init__(self, name: str, parent: Optional[UVMComponent] = None) -> None:
        super().__init__(name, parent)
        self.driver:  UVMDriver  = UVMDriver("driver", self)
        self.monitor: UVMMonitor = UVMMonitor("monitor", self)

    def run_sequence(self, sequence: UVMSequence) -> None:
        """Drive every item in *sequence.body()* and observe outputs."""
        for item in sequence.body():
            outputs = self.driver.drive(item)
            self.monitor.observe(item.values, outputs)
