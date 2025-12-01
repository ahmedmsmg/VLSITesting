"""Parser for ISCAS-style .ckt netlists.

The parser is intentionally tolerant to accommodate both the classic
``OUTPUT = TYPE(IN1, IN2)`` style as well as the tabular/column-oriented
lists used in the AM book examples (e.g., lines such as ``5gat or 2gat 3gat``
and primary input/output declarations like ``1gat    $... primary input``).
"""
from __future__ import annotations
import re
from typing import Iterable

from circuit import Circuit

INPUT_RE = re.compile(r"INPUT\((?P<name>[^)]+)\)", re.IGNORECASE)
OUTPUT_RE = re.compile(r"OUTPUT\((?P<name>[^)]+)\)", re.IGNORECASE)
GATE_RE = re.compile(r"(?P<out>\w+)\s*=\s*(?P<type>\w+)\((?P<inputs>[^)]*)\)")
ALT_GATE_RE = re.compile(r"(?P<out>\w+)\s+(?P<type>\w+)\s+(?P<inputs>\w+(?:\s+\w+)*)", re.IGNORECASE)


class ParseError(RuntimeError):
    pass


def parse_ckt(text: str, name: str = "") -> Circuit:
    circuit = Circuit(name=name)
    gates_started = False
    for raw_line in text.splitlines():
        dollar_split = raw_line.split("$", 1)
        comment = dollar_split[1].lower() if len(dollar_split) > 1 else ""
        line = dollar_split[0].split("#", 1)[0].strip()
        if not line:
            continue
        # Explicit INPUT/OUTPUT keywords
        if m := INPUT_RE.fullmatch(line):
            circuit.add_pi(m.group("name"))
            continue
        if m := OUTPUT_RE.fullmatch(line):
            circuit.add_po(m.group("name"))
            continue
        # Parenthesized gate form (out = TYPE(in1, in2, ...))
        if m := GATE_RE.fullmatch(line):
            out = m.group("out")
            gtype = m.group("type")
            inputs = [p.strip() for p in m.group("inputs").split(",") if p.strip()]
            circuit.add_gate(out, gtype, inputs)
            gates_started = True
            continue
        # Whitespace-delimited gate table (out TYPE in1 in2 ...)
        if m := ALT_GATE_RE.fullmatch(line):
            out = m.group("out")
            gtype = m.group("type")
            inputs = m.group("inputs").split()
            if len(inputs) == 0:
                raise ParseError(f"Gate declaration missing inputs: {raw_line}")
            circuit.add_gate(out, gtype, inputs)
            gates_started = True
            continue
        # Bare node names (with or without helpful comments)
        if re.fullmatch(r"\w+", line):
            name = line
            if "primary input" in comment:
                circuit.add_pi(name)
                continue
            if "primary output" in comment:
                circuit.add_po(name)
                continue
            if not gates_started:
                if not circuit.primary_outputs:
                    circuit.add_pi(name)
                else:
                    circuit.add_po(name)
                continue
        raise ParseError(f"Cannot parse line: {raw_line}")
    circuit.build_topological()
    return circuit


def parse_file(path: str) -> Circuit:
    with open(path, "r", encoding="utf-8") as f:
        return parse_ckt(f.read(), name=path)
