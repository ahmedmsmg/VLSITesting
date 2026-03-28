"""Fault coverage analysis with provable completeness.

Analyzes :class:`~regression.runner.TestResult` lists to compute fault
coverage metrics and — for any fault not covered by any algorithm — uses the
SAT engine to confirm whether it is truly undetectable (redundant).
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fault import Fault
from sat_atpg import sat_atpg
from ckt_parser import parse_file
from regression.runner import FaultTestResult


@dataclass
class CoverageReport:
    """Fault coverage metrics for one circuit."""

    circuit_name: str
    total_faults: int
    detected_faults: int
    undetectable_faults: int    # provably redundant (SAT-confirmed)
    unknown_faults: int         # not detected and not proven undetectable
    coverage_pct: float
    per_algorithm: Dict[str, float] = field(default_factory=dict)
    detected_fault_labels: List[str] = field(default_factory=list)
    undetectable_fault_labels: List[str] = field(default_factory=list)
    uncovered_fault_labels: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [
            f"Circuit: {self.circuit_name}",
            f"  Total faults      : {self.total_faults}",
            f"  Detected          : {self.detected_faults}",
            f"  Undetectable      : {self.undetectable_faults}",
            f"  Unknown           : {self.unknown_faults}",
            f"  Fault coverage    : {self.coverage_pct:.1f}%",
        ]
        for algo, pct in sorted(self.per_algorithm.items()):
            lines.append(f"  [{algo:5s}] coverage : {pct:.1f}%")
        if self.uncovered_fault_labels:
            lines.append(f"  Uncovered faults  : {', '.join(self.uncovered_fault_labels)}")
        return "\n".join(lines)


class FaultCoverageAnalyzer:
    """Compute fault coverage from a list of :class:`TestResult` objects.

    Usage::

        analyzer = FaultCoverageAnalyzer()
        report = analyzer.analyze(results)
        print(report)
    """

    def analyze(self, results: List[FaultTestResult]) -> CoverageReport:
        """Build a :class:`CoverageReport` from *results*.

        A fault is *detected* if at least one algorithm found a test vector
        for it.  Coverage percentage = detected / (total - undetectable).
        """
        if not results:
            return CoverageReport(
                circuit_name="unknown",
                total_faults=0,
                detected_faults=0,
                undetectable_faults=0,
                unknown_faults=0,
                coverage_pct=100.0,
            )

        circuit_name = results[0].circuit_name

        # Group results by fault label
        fault_detected: Dict[str, bool] = {}
        fault_obj: Dict[str, Fault] = {}
        per_algo_detected: Dict[str, set] = {}

        for r in results:
            label = r.fault.label()
            fault_obj[label] = r.fault
            if r.detected:
                fault_detected[label] = True
            elif label not in fault_detected:
                fault_detected[label] = False

            algo = r.algorithm
            if algo not in per_algo_detected:
                per_algo_detected[algo] = set()
            if r.detected:
                per_algo_detected[algo].add(label)

        total = len(fault_detected)
        detected_labels = [lbl for lbl, det in fault_detected.items() if det]
        undetected_labels = [lbl for lbl, det in fault_detected.items() if not det]

        # Per-algorithm coverage
        per_algo: Dict[str, float] = {}
        for algo, det_set in per_algo_detected.items():
            per_algo[algo] = len(det_set) / total * 100.0 if total else 100.0

        # Effective coverage: detected / (total - undetectable)
        # We don't prove completeness here by default (it's expensive);
        # use prove_completeness() for that.
        covered = len(detected_labels)
        coverage_pct = covered / total * 100.0 if total else 100.0

        return CoverageReport(
            circuit_name=circuit_name,
            total_faults=total,
            detected_faults=covered,
            undetectable_faults=0,
            unknown_faults=len(undetected_labels),
            coverage_pct=coverage_pct,
            per_algorithm=per_algo,
            detected_fault_labels=detected_labels,
            uncovered_fault_labels=undetected_labels,
        )

    def analyze_all(
        self, results: List[FaultTestResult]
    ) -> Dict[str, CoverageReport]:
        """Analyze results grouped by circuit name."""
        grouped: Dict[str, List[FaultTestResult]] = {}
        for r in results:
            grouped.setdefault(r.circuit_name, []).append(r)
        return {name: self.analyze(group) for name, group in grouped.items()}

    def prove_completeness(
        self,
        circuit_path: str,
        report: CoverageReport,
    ) -> CoverageReport:
        """Use the SAT engine to classify uncovered faults as truly undetectable.

        For each fault in ``report.uncovered_fault_labels``, runs the SAT
        ATPG engine.  If SAT also returns None, the fault is provably
        redundant (undetectable).  Updates and returns a new report.

        Args:
            circuit_path: Path to the .ckt file for the circuit.
            report:       A :class:`CoverageReport` from :meth:`analyze`.

        Returns:
            Updated :class:`CoverageReport` with ``undetectable_faults`` and
            ``coverage_pct`` recalculated.
        """
        if not report.uncovered_fault_labels:
            return report

        circuit = parse_file(circuit_path)
        proven_undetectable: List[str] = []
        still_unknown: List[str] = []

        for label in report.uncovered_fault_labels:
            # Reconstruct the Fault object from the label
            node, sa_part = label.rsplit("-sa", 1)
            fault = Fault(node, int(sa_part))
            result = sat_atpg(circuit, fault)
            if result is None:
                proven_undetectable.append(label)
            else:
                still_unknown.append(label)

        detectable = report.total_faults - len(proven_undetectable)
        coverage_pct = (
            report.detected_faults / detectable * 100.0
            if detectable > 0 else 100.0
        )

        return CoverageReport(
            circuit_name=report.circuit_name,
            total_faults=report.total_faults,
            detected_faults=report.detected_faults,
            undetectable_faults=len(proven_undetectable),
            unknown_faults=len(still_unknown),
            coverage_pct=coverage_pct,
            per_algorithm=report.per_algorithm,
            detected_fault_labels=report.detected_fault_labels,
            undetectable_fault_labels=proven_undetectable,
            uncovered_fault_labels=still_unknown,
        )
