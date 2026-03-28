"""Functional coverage: CoverPoint, CoverCross, CoverGroup.

Models UVM/SystemVerilog coverage constructs in Python.  Coverage bins are
predicate functions; a bin is "hit" when its predicate returns True for a
given transaction.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


Transaction = Dict[str, Any]
BinPredicate = Callable[[Transaction], bool]


# ── CoverPoint ────────────────────────────────────────────────────────────────

class CoverPoint:
    """A set of named bins, each associated with a predicate.

    A bin is *hit* when its predicate returns True for the sampled transaction.
    Multiple hits of the same bin are accumulated.

    Args:
        name: Human-readable identifier.
        bins: Mapping of bin_name → predicate(txn) → bool.
    """

    def __init__(self, name: str, bins: Dict[str, BinPredicate]) -> None:
        self.name = name
        self.bins: Dict[str, BinPredicate] = bins
        self.hit_count: Dict[str, int] = {b: 0 for b in bins}

    def sample(self, txn: Transaction) -> None:
        """Check *txn* against every bin predicate."""
        for bin_name, predicate in self.bins.items():
            try:
                if predicate(txn):
                    self.hit_count[bin_name] += 1
            except Exception:
                pass  # skip bins whose predicate raises

    @property
    def bins_hit(self) -> int:
        return sum(1 for c in self.hit_count.values() if c > 0)

    @property
    def total_bins(self) -> int:
        return len(self.bins)

    @property
    def coverage_pct(self) -> float:
        return self.bins_hit / self.total_bins * 100.0 if self.total_bins else 100.0

    def report(self) -> str:
        lines = [f"CoverPoint '{self.name}': {self.coverage_pct:.1f}%"]
        for b, cnt in self.hit_count.items():
            status = "HIT" if cnt > 0 else "miss"
            lines.append(f"  [{status:4s}] {b}: {cnt} hits")
        return "\n".join(lines)


# ── CoverCross ────────────────────────────────────────────────────────────────

class CoverCross:
    """Cross coverage of two or more :class:`CoverPoint` objects.

    A cross-bin is the Cartesian product of individual bin names.  It is hit
    when all constituent points have their respective bins hit in the same
    transaction.

    Args:
        name:   Human-readable identifier.
        points: List of :class:`CoverPoint` objects to cross.
    """

    def __init__(self, name: str, points: List[CoverPoint]) -> None:
        if len(points) < 2:
            raise ValueError("CoverCross requires at least two CoverPoints.")
        self.name = name
        self.points = points
        # Pre-build the cross-bin hit counts
        bin_lists = [list(p.bins.keys()) for p in points]
        self.cross_hit: Dict[Tuple[str, ...], int] = {
            combo: 0 for combo in itertools.product(*bin_lists)
        }

    def sample(self, txn: Transaction) -> None:
        """Record which cross-bin (if any) is hit by *txn*."""
        active_bins: List[List[str]] = []
        for pt in self.points:
            hit = [b for b, pred in pt.bins.items() if pred(txn)]
            active_bins.append(hit)
        for combo in itertools.product(*active_bins):
            if combo in self.cross_hit:
                self.cross_hit[combo] += 1

    @property
    def cross_bins_hit(self) -> int:
        return sum(1 for c in self.cross_hit.values() if c > 0)

    @property
    def total_cross_bins(self) -> int:
        return len(self.cross_hit)

    @property
    def coverage_pct(self) -> float:
        return (
            self.cross_bins_hit / self.total_cross_bins * 100.0
            if self.total_cross_bins else 100.0
        )

    def report(self) -> str:
        lines = [f"CoverCross '{self.name}': {self.coverage_pct:.1f}%"]
        for combo, cnt in list(self.cross_hit.items())[:20]:
            status = "HIT" if cnt > 0 else "miss"
            key = " × ".join(combo)
            lines.append(f"  [{status:4s}] {key}: {cnt}")
        if len(self.cross_hit) > 20:
            lines.append(f"  ... ({len(self.cross_hit) - 20} more cross-bins)")
        return "\n".join(lines)


# ── CoverGroup ────────────────────────────────────────────────────────────────

class CoverGroup:
    """Top-level coverage container grouping points and crosses.

    Call :meth:`sample` with every observed transaction to accumulate coverage.
    Call :meth:`report` at the end of the run for a summary.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.coverpoints: List[CoverPoint] = []
        self.crosses: List[CoverCross] = []
        self._sample_count: int = 0

    def add_coverpoint(self, cp: CoverPoint) -> CoverPoint:
        self.coverpoints.append(cp)
        return cp

    def add_cross(self, cx: CoverCross) -> CoverCross:
        self.crosses.append(cx)
        return cx

    def sample(self, txn: Transaction) -> None:
        """Push *txn* through all coverpoints and crosses."""
        self._sample_count += 1
        for cp in self.coverpoints:
            cp.sample(txn)
        for cx in self.crosses:
            cx.sample(txn)

    @property
    def overall_coverage_pct(self) -> float:
        all_items: List[float] = (
            [cp.coverage_pct for cp in self.coverpoints]
            + [cx.coverage_pct for cx in self.crosses]
        )
        return sum(all_items) / len(all_items) if all_items else 100.0

    def report(self) -> str:
        lines = [
            f"=== CoverGroup '{self.name}' ===",
            f"  Samples      : {self._sample_count}",
            f"  Overall      : {self.overall_coverage_pct:.1f}%",
        ]
        for cp in self.coverpoints:
            for line in cp.report().splitlines():
                lines.append("  " + line)
        for cx in self.crosses:
            for line in cx.report().splitlines():
                lines.append("  " + line)
        return "\n".join(lines)
