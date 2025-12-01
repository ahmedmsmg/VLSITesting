"""Parser for ISCAS-style .ckt netlists."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class GateDef:
    output: str
    gate_type: str
    inputs: List[str]


@dataclass
class Netlist:
    primary_inputs: List[str]
    primary_outputs: List[str]
    gates: List[GateDef]


_GATE_RE = re.compile(r"^(?P<out>\w+)\s*=\s*(?P<type>\w+)\s*\((?P<inputs>[^)]*)\)$")


def parse_ckt(path: str) -> Netlist:
    """Parse an ISCAS .ckt file."""
    pis: List[str] = []
    pos: List[str] = []
    gates: List[GateDef] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.split("$")[0].strip()
            if not stripped:
                continue
            if stripped.upper().startswith("INPUT"):
                name = stripped[stripped.find("(") + 1 : stripped.find(")")].strip()
                pis.append(name)
                continue
            if stripped.upper().startswith("OUTPUT"):
                name = stripped[stripped.find("(") + 1 : stripped.find(")")].strip()
                pos.append(name)
                continue
            match = _GATE_RE.match(stripped.replace(" ", ""))
            if not match:
                raise ValueError(f"Invalid line: {line.strip()}")
            inputs = [p.strip() for p in match.group("inputs").split(",") if p.strip()]
            gates.append(
                GateDef(
                    output=match.group("out"),
                    gate_type=match.group("type").upper(),
                    inputs=inputs,
                )
            )
    if not pis or not pos:
        raise ValueError("Netlist must declare at least one INPUT and OUTPUT")
    return Netlist(primary_inputs=pis, primary_outputs=pos, gates=gates)


def fanout_map(gates: List[GateDef]) -> Dict[str, List[str]]:
    fanouts: Dict[str, List[str]] = {}
    for gate in gates:
        for inp in gate.inputs:
            fanouts.setdefault(inp, []).append(gate.output)
    return fanouts

