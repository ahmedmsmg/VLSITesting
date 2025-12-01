"""Fault representation for single stuck-at faults."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fault:
    net: str
    stuck_at: int  # 0 or 1

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.net}-sa{self.stuck_at}"

