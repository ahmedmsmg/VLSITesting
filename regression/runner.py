"""Regression runner: exercises all ATPG algorithms on all example circuits.

Discovers .ckt files, enumerates faults, runs each algorithm, and collects
:class:`TestResult` objects for downstream coverage analysis.
"""
from __future__ import annotations

import glob
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from circuit import Circuit
from ckt_parser import parse_file
from fault import Fault
from d_algorithm import d_algorithm
from podem import podem
from sat_atpg import sat_atpg


_ALGO_MAP = {
    "D":    d_algorithm,
    "PODEM": podem,
    "SAT":  sat_atpg,
}


@dataclass
class FaultTestResult:
    """The outcome of running one ATPG algorithm on one fault."""
    circuit_name: str
    fault: Fault
    algorithm: str
    test_vector: Optional[Dict[str, str]]
    detected: bool
    runtime_sec: float


class RegressionRunner:
    """Discovers .ckt files and runs ATPG algorithms against all faults.

    Args:
        circuit_dir: Directory path to search for ``.ckt`` files.
    """

    def __init__(self, circuit_dir: str = "examples/") -> None:
        self.circuit_dir = circuit_dir
        self.results: List[FaultTestResult] = []

    def discover_circuits(self) -> List[str]:
        """Return sorted list of .ckt file paths found in *circuit_dir*."""
        pattern = os.path.join(self.circuit_dir, "*.ckt")
        return sorted(glob.glob(pattern))

    def run_all(
        self,
        algorithms: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> List[FaultTestResult]:
        """Run all algorithms on every fault in every discovered circuit.

        Args:
            algorithms: Subset of ``["D", "PODEM", "SAT"]`` to run.
                        Defaults to all three.
            verbose:    Print per-fault progress when True.

        Returns:
            Flat list of :class:`TestResult` objects.
        """
        if algorithms is None:
            algorithms = ["D", "PODEM", "SAT"]
        self.results = []
        for path in self.discover_circuits():
            self.results.extend(
                self.run_circuit(path, algorithms, verbose=verbose)
            )
        return self.results

    def run_circuit(
        self,
        circuit_path: str,
        algorithms: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> List[FaultTestResult]:
        """Run ATPG on all faults for a single circuit.

        Args:
            circuit_path: Absolute or relative path to a .ckt file.
            algorithms:   Algorithms to run (default all three).
            verbose:      Print progress when True.

        Returns:
            List of :class:`TestResult` for this circuit.
        """
        if algorithms is None:
            algorithms = ["D", "PODEM", "SAT"]

        circuit = parse_file(circuit_path)
        circuit_name = os.path.splitext(os.path.basename(circuit_path))[0]
        faults = circuit.fault_list()
        results: List[FaultTestResult] = []

        for fault in faults:
            for algo_name in algorithms:
                algo_fn = _ALGO_MAP.get(algo_name.upper())
                if algo_fn is None:
                    continue
                t0 = time.perf_counter()
                try:
                    vec = algo_fn(circuit, fault)
                except Exception:
                    vec = None
                elapsed = time.perf_counter() - t0

                detected = vec is not None
                results.append(
                    FaultTestResult(
                        circuit_name=circuit_name,
                        fault=fault,
                        algorithm=algo_name.upper(),
                        test_vector=vec,
                        detected=detected,
                        runtime_sec=elapsed,
                    )
                )
                if verbose:
                    status = "DETECTED" if detected else "no test"
                    print(
                        f"  [{algo_name:5s}] {fault.label():20s}  {status}"
                        f"  ({elapsed*1000:.1f} ms)"
                    )

        return results
