"""Fault representation and simple collapsing utilities."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Fault:
    """Single stuck-at fault on a circuit node."""

    node: str
    stuck_at: int  # 0 or 1

    def label(self) -> str:
        return f"{self.node}-sa{self.stuck_at}"


def collapse_faults(nodes: List[str]) -> List[List[Fault]]:
    """Return fault classes after structural collapsing.

    The implementation keeps the interface simple and deterministic: every node
    produces two possible single stuck-at faults, and each fault occupies its own
    equivalence class. This provides a hook for more aggressive collapsing while
    preserving a stable data structure for the menu workflow.
    """

    classes: List[List[Fault]] = []
    for n in nodes:
        classes.append([Fault(n, 0)])
        classes.append([Fault(n, 1)])
    return classes
