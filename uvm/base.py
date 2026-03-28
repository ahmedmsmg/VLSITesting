"""UVM-aligned base classes: component hierarchy and phase management.

Models the UVM component tree and six-phase execution lifecycle in Python.
Phases execute in a defined order; build/connect propagate top-down through
the component tree, run executes on all leaf components, and
extract/check/report propagate bottom-up.
"""
from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Dict, Iterator, List, Optional

_log = logging.getLogger(__name__)


class UVMPhase(Enum):
    """The six standard UVM execution phases (simplified)."""
    BUILD   = auto()
    CONNECT = auto()
    RUN     = auto()
    EXTRACT = auto()
    CHECK   = auto()
    REPORT  = auto()


class UVMComponent:
    """Base class for all UVM components.

    Provides:
    - Parent/child hierarchy registration
    - Override-able phase hooks
    - ``run_all_phases()`` for orchestrated execution
    """

    def __init__(self, name: str, parent: Optional["UVMComponent"] = None) -> None:
        self.name = name
        self.parent = parent
        self.children: Dict[str, "UVMComponent"] = {}
        if parent is not None:
            parent.children[name] = self

    # ── Override-able phase hooks ─────────────────────────────────────────────

    def build_phase(self) -> None:   """Instantiate sub-components."""

    def connect_phase(self) -> None: """Wire analysis ports between components."""

    def run_phase(self) -> None:     """Drive stimulus and collect responses."""

    def extract_phase(self) -> None: """Pull metrics out of sub-components."""

    def check_phase(self) -> None:   """Assert expected vs actual values."""

    def report_phase(self) -> None:  """Print/log the verification summary."""

    # ── Traversal helpers ─────────────────────────────────────────────────────

    def _walk_top_down(self) -> Iterator["UVMComponent"]:
        """Yield self then all descendants breadth-first."""
        queue = [self]
        while queue:
            node = queue.pop(0)
            yield node
            queue.extend(node.children.values())

    def _walk_bottom_up(self) -> Iterator["UVMComponent"]:
        """Yield all descendants then self (leaves first)."""
        nodes = list(self._walk_top_down())
        yield from reversed(nodes)

    # ── Orchestrated execution ────────────────────────────────────────────────

    def run_all_phases(self) -> None:
        """Execute all six UVM phases in order on the full component tree."""
        _log.debug("[%s] BUILD phase", self.name)
        for c in self._walk_top_down():
            c.build_phase()

        _log.debug("[%s] CONNECT phase", self.name)
        for c in self._walk_top_down():
            c.connect_phase()

        _log.debug("[%s] RUN phase", self.name)
        for c in self._walk_top_down():
            c.run_phase()

        _log.debug("[%s] EXTRACT phase", self.name)
        for c in self._walk_bottom_up():
            c.extract_phase()

        _log.debug("[%s] CHECK phase", self.name)
        for c in self._walk_bottom_up():
            c.check_phase()

        _log.debug("[%s] REPORT phase", self.name)
        for c in self._walk_bottom_up():
            c.report_phase()
