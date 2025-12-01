"""Interactive ATPG driver supporting menu-based workflow."""
from __future__ import annotations
import argparse
from typing import Dict, List, Optional

import logic5 as L
from ckt_parser import parse_file, ParseError
from circuit import Circuit
from fault import Fault, collapse_faults
from d_algorithm import d_algorithm
from podem import podem
from sat_atpg import sat_atpg


ALGORITHMS = {
    "D": d_algorithm,
    "PODEM": podem,
    "SAT": sat_atpg,
}


def run_for_fault(circuit: Circuit, fault: Fault, algo: str) -> Optional[Dict[str, str]]:
    return ALGORITHMS[algo](circuit, fault)


def format_vector(circ: Circuit, vec: Dict[str, str]) -> str:
    return "".join(vec.get(pi, L.LX) for pi in circ.primary_inputs)


def parse_vector(circuit: Circuit, raw: str) -> Dict[str, str]:
    raw = raw.strip().upper()
    if len(raw) != len(circuit.primary_inputs):
        raise ValueError("Vector length does not match number of primary inputs")
    mapping = {"0": L.L0, "1": L.L1, "X": L.LX}
    vec: Dict[str, str] = {}
    for pi, ch in zip(circuit.primary_inputs, raw):
        if ch not in mapping:
            raise ValueError("Vector must contain only 0, 1, or X")
        vec[pi] = mapping[ch]
    return vec


def list_fault_classes(classes: List[List[Fault]]) -> None:
    if not classes:
        print("No fault classes. Perform collapsing first.")
        return
    for idx, group in enumerate(classes):
        joined = ", ".join(f.label() for f in group)
        print(f"Class {idx}: {joined}")


def simulate_vector(circuit: Circuit, vector: Dict[str, str], faults: List[Fault]) -> None:
    if not faults:
        values = circuit.evaluate_vector(vector)
        out = {po: values[po] for po in circuit.primary_outputs}
        print(f"Outputs: {out}")
        return
    for f in faults:
        values = circuit.evaluate_vector(vector, fault=f)
        out = {po: values[po] for po in circuit.primary_outputs}
        flagged = [po for po, v in out.items() if L.is_fault_symbol(v)]
        label = f.label()
        if flagged:
            print(f"Fault {label} detected at outputs {flagged}: {out}")
        else:
            print(f"Fault {label} not observable at outputs: {out}")


def generate_tests(circuit: Circuit, algos: List[str], fault_classes: List[List[Fault]]) -> None:
    targets = [cls[0] for cls in fault_classes] if fault_classes else circuit.fault_list()
    for algo in algos:
        print(f"\nAlgorithm {algo} results:")
        detected = 0
        for fault in targets:
            vec = run_for_fault(circuit, fault, algo)
            if vec is None:
                print(f"Fault {fault.label()}: no test found")
            else:
                detected += 1
                print(f"Fault {fault.label()}: test = {format_vector(circuit, vec)}")
        print(f"Detected {detected}/{len(targets)} faults")


def interactive_menu(initial_path: Optional[str] = None) -> None:
    circuit: Optional[Circuit] = None
    fault_classes: List[List[Fault]] = []

    def ensure_circuit() -> Circuit:
        if circuit is None:
            raise RuntimeError("Load a netlist first (option 0)")
        return circuit

    while True:
        print("""
[0] Read the input net-list
[1] Perform fault collapsing
[2] List fault classes
[3] Simulate
[4] Generate tests (D-Algorithm)
[5] Generate tests (PODEM)
[6] Generate tests (Boolean Satisfaibility)
[7] Exit
""")

        choice = input("Select an option: ").strip()

        if choice == "0":
            path = initial_path or input("Enter path to .ckt file: ").strip()
            initial_path = None
            try:
                circuit = parse_file(path)
                fault_classes.clear()
                print(f"Loaded circuit with {len(circuit.nodes)} nodes, {len(circuit.primary_inputs)} PIs, {len(circuit.primary_outputs)} POs.")
            except FileNotFoundError:
                print(f"File not found: {path}")
            except ParseError as exc:
                print(f"Parse error: {exc}")
        elif choice == "1":
            try:
                circ = ensure_circuit()
            except RuntimeError as exc:
                print(exc)
                continue
            fault_classes = collapse_faults(circ.nodes)
            print(f"Created {len(fault_classes)} fault classes")
        elif choice == "2":
            list_fault_classes(fault_classes)
        elif choice == "3":
            try:
                circ = ensure_circuit()
            except RuntimeError as exc:
                print(exc)
                continue
            vec_raw = input(f"Enter test vector for PIs {circ.primary_inputs}: ")
            try:
                vec = parse_vector(circ, vec_raw)
            except ValueError as exc:
                print(f"Invalid vector: {exc}")
                continue
            faults_raw = input("Enter faults (e.g., a-sa0,b-sa1) or leave blank: ").strip()
            faults: List[Fault] = []
            if faults_raw:
                for token in faults_raw.split(','):
                    name = token.strip()
                    if not name:
                        continue
                    if "-sa" not in name:
                        print(f"Unrecognized fault token: {name}")
                        faults = []
                        break
                    node, sa = name.split("-sa", 1)
                    if node not in circ.nodes:
                        print(f"Unknown node {node}")
                        faults = []
                        break
                    if sa not in {"0", "1"}:
                        print(f"Invalid stuck-at value for {name}")
                        faults = []
                        break
                    faults.append(Fault(node, int(sa)))
            if faults or faults_raw == "":
                simulate_vector(circ, vec, faults)
        elif choice == "4":
            try:
                circ = ensure_circuit()
            except RuntimeError as exc:
                print(exc)
                continue
            generate_tests(circ, ["D"], fault_classes)
        elif choice == "5":
            try:
                circ = ensure_circuit()
            except RuntimeError as exc:
                print(exc)
                continue
            generate_tests(circ, ["PODEM"], fault_classes)
        elif choice == "6":
            try:
                circ = ensure_circuit()
            except RuntimeError as exc:
                print(exc)
                continue
            generate_tests(circ, ["SAT"], fault_classes)
        elif choice == "7":
            print("Exiting.")
            break
        else:
            print("Invalid option. Please select 0-7.")


def main() -> None:
    parser = argparse.ArgumentParser(description="ATPG for single stuck-at faults")
    parser.add_argument("ckt", nargs="?", help="Path to .ckt netlist")
    parser.add_argument("--algo", choices=["D", "PODEM", "SAT", "ALL"], help="Run in batch mode with the selected algorithm")
    args = parser.parse_args()

    if args.algo:
        if not args.ckt:
            raise SystemExit("Batch mode requires a .ckt file path")
        try:
            circuit = parse_file(args.ckt)
        except FileNotFoundError:
            raise SystemExit(f"File not found: {args.ckt}")
        except ParseError as exc:
            raise SystemExit(f"Parse error: {exc}")
        algos = [args.algo] if args.algo != "ALL" else list(ALGORITHMS.keys())
        generate_tests(circuit, algos, fault_classes=[])
    else:
        interactive_menu(initial_path=args.ckt)


if __name__ == "__main__":
    main()
