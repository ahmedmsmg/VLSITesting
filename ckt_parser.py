"""Parser for ISCAS-style .ckt netlists."""
from __future__ import annotations
import re
from typing import Iterable

from circuit import Circuit

INPUT_RE = re.compile(r"INPUT\((?P<name>[^)]+)\)")
OUTPUT_RE = re.compile(r"OUTPUT\((?P<name>[^)]+)\)")
GATE_RE = re.compile(r"(?P<out>\w+)\s*=\s*(?P<type>\w+)\((?P<inputs>[^)]*)\)")


class ParseError(RuntimeError):
    pass


def parse_ckt(text: str, name: str = "") -> Circuit:
    circuit = Circuit(name=name)
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].split("$", 1)[0].strip()
        if not line:
            continue
        if m := INPUT_RE.fullmatch(line):
            circuit.add_pi(m.group("name"))
            continue
        if m := OUTPUT_RE.fullmatch(line):
            circuit.add_po(m.group("name"))
            continue
        if m := GATE_RE.fullmatch(line):
            out = m.group("out")
            gtype = m.group("type")
            inputs = [p.strip() for p in m.group("inputs").split(",") if p.strip()]
            circuit.add_gate(out, gtype, inputs)
            continue
        raise ParseError(f"Cannot parse line: {raw_line}")
    circuit.build_topological()
    return circuit


def parse_file(path: str) -> Circuit:
    with open(path, "r", encoding="utf-8") as f:
        return parse_ckt(f.read(), name=path)
