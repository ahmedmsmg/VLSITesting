"""Command-line ATPG driver supporting D-Algorithm, PODEM, and SAT."""
from __future__ import annotations

import argparse
from typing import Dict, List, Optional, Tuple

from ckt_parser import parse_ckt
from circuit import Circuit
from fault import Fault
import d_algorithm
import podem
import sat_atpg


def enumerate_faults(circuit: Circuit) -> List[Fault]:
    faults = []
    for sig in circuit.all_signals:
        faults.append(Fault(sig, 0))
        faults.append(Fault(sig, 1))
    return faults


def run_algorithm(circuit: Circuit, fault: Fault, algo: str) -> Optional[str]:
    if algo == "D":
        return d_algorithm.generate_test(circuit, fault)
    if algo == "PODEM":
        return podem.generate_test(circuit, fault)
    if algo == "SAT":
        return sat_atpg.solve_with_sat(circuit, fault)
    raise ValueError(f"Unknown algorithm {algo}")


def report_results(circuit: Circuit, algo: str, faults: List[Fault]) -> Tuple[Dict[Fault, str], List[Fault]]:
    detected: Dict[Fault, str] = {}
    untestable: List[Fault] = []
    for fault in faults:
        vector = run_algorithm(circuit, fault, algo)
        if vector is None:
            untestable.append(fault)
        else:
            detected[fault] = vector
    return detected, untestable


def format_results(detected: Dict[Fault, str], untestable: List[Fault]) -> str:
    lines = []
    for fault, vec in detected.items():
        lines.append(f"Fault {fault}:    test = {vec}")
    for fault in untestable:
        lines.append(f"Fault {fault}:    no test found")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="ATPG tool for single stuck-at faults")
    parser.add_argument("ckt", help="Path to .ckt netlist")
    parser.add_argument("--algo", choices=["D", "PODEM", "SAT", "ALL"], default="ALL", help="Algorithm to run")
    args = parser.parse_args(argv)

    netlist = parse_ckt(args.ckt)
    circuit = Circuit.from_netlist(netlist)
    faults = enumerate_faults(circuit)

    algos = [args.algo] if args.algo != "ALL" else ["D", "PODEM", "SAT"]
    for algo in algos:
        print(f"\n=== Running {algo} ===")
        detected, untestable = report_results(circuit, algo, faults)
        print(format_results(detected, untestable))


if __name__ == "__main__":
    main()

