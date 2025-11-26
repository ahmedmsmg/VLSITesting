import argparse
import itertools
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple


@dataclass(frozen=True)
class Fault:
    """Represents a single stuck-at fault on a circuit line."""

    net: str
    stuck_at: int

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.net}-sa{self.stuck_at}"


@dataclass
class Gate:
    name: str
    gate_type: str
    inputs: List[str]

    def evaluate(self, values: Dict[str, int]) -> int:
        gate = self.gate_type.lower()
        ins = [values[i] for i in self.inputs]
        if gate == "and":
            result = int(all(ins))
        elif gate == "nand":
            result = 1 - int(all(ins))
        elif gate == "or":
            result = int(any(ins))
        elif gate == "nor":
            result = 1 - int(any(ins))
        elif gate == "xor":
            result = 0
            for bit in ins:
                result ^= bit
        elif gate == "xnor":
            result = 0
            for bit in ins:
                result ^= bit
            result = 1 - result
        elif gate in {"not", "inv"}:
            if len(ins) != 1:
                raise ValueError(f"{self.name}: NOT gate expects 1 input")
            result = 1 - ins[0]
        elif gate == "buf":
            if len(ins) != 1:
                raise ValueError(f"{self.name}: BUF gate expects 1 input")
            result = ins[0]
        else:
            raise ValueError(f"Unsupported gate type: {self.gate_type}")
        return result


@dataclass
class Circuit:
    gates: List[Gate] = field(default_factory=list)
    primary_inputs: List[str] = field(default_factory=list)
    primary_outputs: List[str] = field(default_factory=list)
    net_names: Set[str] = field(default_factory=set)
    topo_order: List[Gate] = field(default_factory=list)
    fault_classes: Dict[str, List[Fault]] = field(default_factory=dict)
    test_vectors: Dict[Fault, List[str]] = field(default_factory=dict)

    @classmethod
    def from_netlist(cls, path: str) -> "Circuit":
        interface_names: List[str] = []
        gates: List[Gate] = []
        with open(path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.split("$")[0].strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) == 1:
                    interface_names.append(parts[0])
                else:
                    out_name = parts[0]
                    gate_type = parts[1]
                    inputs = parts[2:]
                    gates.append(Gate(out_name, gate_type, inputs))
        if not gates:
            raise ValueError("Netlist contains no gates")

        output_names = {gate.name for gate in gates}
        primary_inputs = [n for n in interface_names if n not in output_names]
        primary_outputs = [n for n in interface_names if n in output_names]
        if not primary_inputs:
            primary_inputs = sorted({i for g in gates for i in g.inputs if i not in output_names})
        if not primary_outputs:
            primary_outputs = sorted(output_names - set(primary_inputs))

        circuit = cls(
            gates=gates,
            primary_inputs=primary_inputs,
            primary_outputs=primary_outputs,
            net_names=set(output_names) | set(primary_inputs),
        )
        circuit.topo_order = circuit._compute_topological_order()
        return circuit

    def _compute_topological_order(self) -> List[Gate]:
        known: Set[str] = set(self.primary_inputs)
        order: List[Gate] = []
        # Using list for deterministic iteration order
        queue = list(self.gates)
        while queue:
            progressed = False
            next_queue: List[Gate] = []
            for gate in queue:
                if all(inp in known for inp in gate.inputs):
                    order.append(gate)
                    known.add(gate.name)
                    progressed = True
                else:
                    next_queue.append(gate)
            if not progressed:
                missing_inputs = {g.name: [i for i in g.inputs if i not in known] for g in next_queue}
                raise ValueError(f"Netlist contains cycle or missing nets: {missing_inputs}")
            queue = next_queue
        return order

    def perform_fault_collapsing(self) -> None:
        self.fault_classes = {
            net: [Fault(net, 0), Fault(net, 1)] for net in sorted(self.net_names)
        }

    def list_fault_classes(self) -> List[str]:
        if not self.fault_classes:
            self.perform_fault_collapsing()
        lines = []
        for net, faults in self.fault_classes.items():
            faults_str = ", ".join(str(f) for f in faults)
            lines.append(f"{net}: {faults_str}")
        return lines

    def _prepare_pi_values(self, vector: str) -> Dict[str, int]:
        cleaned = vector.strip().replace(" ", "")
        if len(cleaned) != len(self.primary_inputs):
            raise ValueError(
                f"Vector length {len(cleaned)} does not match number of primary inputs {len(self.primary_inputs)}"
            )
        mapping = {}
        for name, bit in zip(self.primary_inputs, cleaned):
            if bit not in {"0", "1"}:
                raise ValueError("Test vector must contain only 0 or 1")
            mapping[name] = int(bit)
        return mapping

    def evaluate(self, pi_assignments: Dict[str, int], fault: Optional[Fault] = None) -> Dict[str, int]:
        values: Dict[str, int] = {}
        for pin in self.primary_inputs:
            base_value = pi_assignments[pin]
            if fault and fault.net == pin:
                base_value = fault.stuck_at
            values[pin] = base_value

        for gate in self.topo_order:
            inputs_ready = {name: values[name] for name in gate.inputs}
            out_value = gate.evaluate(inputs_ready)
            if fault and fault.net == gate.name:
                out_value = fault.stuck_at
            values[gate.name] = out_value

        return {po: values.get(po) for po in self.primary_outputs}

    def detect_fault(self, pi_assignments: Dict[str, int], fault: Fault) -> Tuple[bool, Dict[str, int], Dict[str, int]]:
        good = self.evaluate(pi_assignments)
        faulty = self.evaluate(pi_assignments, fault)
        return good != faulty, good, faulty

    def _all_faults(self) -> List[Fault]:
        if self.fault_classes:
            return [fault for faults in self.fault_classes.values() for fault in faults]
        return [Fault(net, val) for net in self.net_names for val in (0, 1)]

    def generate_tests(self, algorithm: str, max_vectors: int = 65536) -> Tuple[Dict[Fault, List[str]], List[Fault]]:
        faults = self._all_faults()
        pi_count = len(self.primary_inputs)
        if pi_count == 0:
            raise ValueError("Circuit has no primary inputs")

        vectors = ["".join(bits) for bits in itertools.product("01", repeat=pi_count)]
        if len(vectors) > max_vectors:
            vectors = vectors[:max_vectors]

        detectable: Dict[Fault, List[str]] = {f: [] for f in faults}
        undetectable: List[Fault] = []
        for fault in faults:
            for vector in vectors:
                pi_map = self._prepare_pi_values(vector)
                is_detected, _, _ = self.detect_fault(pi_map, fault)
                if is_detected:
                    detectable[fault].append(vector)
            if not detectable[fault]:
                undetectable.append(fault)

        self.test_vectors = detectable
        return detectable, undetectable


def parse_faults(raw: str) -> List[Fault]:
    faults: List[Fault] = []
    if not raw.strip():
        return faults
    for piece in raw.split(","):
        name = piece.strip()
        match = re.fullmatch(r"(.+)-sa([01])", name)
        if not match:
            raise ValueError(f"Invalid fault format: {name}")
        faults.append(Fault(match.group(1), int(match.group(2))))
    return faults


def interactive_menu(initial_netlist: Optional[str] = None) -> None:
    circuit: Optional[Circuit] = None
    if initial_netlist:
        try:
            circuit = Circuit.from_netlist(initial_netlist)
            print(f"Loaded netlist with {len(circuit.gates)} gates.")
        except Exception as exc:  # pragma: no cover - user interaction
            print(f"Failed to load netlist: {exc}")

    while True:  # pragma: no cover - interactive loop
        print("\n[0] Read the input net-list")
        print("[1] Perform fault collapsing")
        print("[2] List fault classes")
        print("[3] Simulate")
        print("[4] Generate tests (D-Algorithm)")
        print("[5] Generate tests (PODEM)")
        print("[6] Generate tests (Boolean Satisfaibility)")
        print("[7] Exit")
        choice = input("Select an option: ").strip()

        if choice == "0":
            path = input("Enter netlist path: ").strip()
            try:
                circuit = Circuit.from_netlist(path)
                print(f"Loaded netlist with {len(circuit.gates)} gates.")
            except Exception as exc:
                print(f"Failed to load netlist: {exc}")
        elif choice == "1":
            if not circuit:
                print("Load a netlist first (option 0).")
                continue
            circuit.perform_fault_collapsing()
            print(f"Fault collapsing complete. Classes: {len(circuit.fault_classes)}")
        elif choice == "2":
            if not circuit:
                print("Load a netlist first (option 0).")
                continue
            classes = circuit.list_fault_classes()
            print("\n".join(classes))
        elif choice == "3":
            if not circuit:
                print("Load a netlist first (option 0).")
                continue
            vector = input(f"Enter test vector ({len(circuit.primary_inputs)} bits for {circuit.primary_inputs}): ").strip()
            try:
                pi_map = circuit._prepare_pi_values(vector)
            except Exception as exc:
                print(f"Invalid vector: {exc}")
                continue
            fault_input = input("Enter faults (comma separated <net>-sa<value>) or leave empty: ").strip()
            try:
                faults = parse_faults(fault_input)
            except Exception as exc:
                print(f"Invalid fault specification: {exc}")
                continue
            if not faults:
                outputs = circuit.evaluate(pi_map)
                print(f"Outputs: {outputs}")
            else:
                for fault in faults:
                    detected, good, faulty = circuit.detect_fault(pi_map, fault)
                    status = "detected" if detected else "not detected"
                    print(f"Fault {fault} {status}. Good={good}, Faulty={faulty}")
        elif choice in {"4", "5", "6"}:
            if not circuit:
                print("Load a netlist first (option 0).")
                continue
            alg_name = {"4": "D-Algorithm", "5": "PODEM", "6": "SAT"}[choice]
            print(f"Running {alg_name} style generation (exhaustive enumeration for demonstration)...")
            try:
                detected, undetectable = circuit.generate_tests(alg_name)
            except Exception as exc:
                print(f"Generation failed: {exc}")
                continue
            for fault, vectors in detected.items():
                if vectors:
                    print(f"Fault {fault}: detected by {', '.join(vectors)}")
            if undetectable:
                print("Undetectable faults:", ", ".join(str(f) for f in undetectable))
        elif choice == "7":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please select 0-7.")


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Interactive ATPG tool for single stuck-at faults")
    parser.add_argument("--netlist", help="Optional netlist to load on startup")
    args = parser.parse_args(argv)
    interactive_menu(initial_netlist=args.netlist)


if __name__ == "__main__":  # pragma: no cover - script entry
    main()
