"""Five-valued logic utilities for ATPG.

Implements the classic Roth five-valued algebra used by
structural ATPG algorithms:
    0, 1, X, D (1/0), D' (0/1)
where D represents a logic-1 in the good circuit and logic-0 in the
faulty circuit, and D' the opposite.
"""
from __future__ import annotations
from typing import Iterable

# Canonical symbols
L0 = "0"
L1 = "1"
LX = "X"
LD = "D"
LD_BAR = "D'"

ALL_VALUES = {L0, L1, LX, LD, LD_BAR}


def normalize(value: str) -> str:
    if value not in ALL_VALUES:
        raise ValueError(f"Unknown logic value: {value}")
    return value


def logic_not(a: str) -> str:
    a = normalize(a)
    if a == L0:
        return L1
    if a == L1:
        return L0
    if a == LD:
        return LD_BAR
    if a == LD_BAR:
        return LD
    return LX


def logic_and(a: str, b: str) -> str:
    a, b = normalize(a), normalize(b)
    if a == L0 or b == L0:
        return L0
    if a == L1:
        return b
    if b == L1:
        return a
    if a == LX or b == LX:
        return LX
    # Remaining combinations cover D/D' interactions
    if (a, b) in [(LD, LD), (LD, LD_BAR), (LD_BAR, LD), (LD_BAR, LD_BAR)]:
        if a == b:
            return a
        # D and D' -> controlling conflict => 0
        return L0
    return LX


def logic_or(a: str, b: str) -> str:
    a, b = normalize(a), normalize(b)
    if a == L1 or b == L1:
        return L1
    if a == L0:
        return b
    if b == L0:
        return a
    if a == LX or b == LX:
        return LX
    if (a, b) in [(LD, LD), (LD, LD_BAR), (LD_BAR, LD), (LD_BAR, LD_BAR)]:
        if a == b:
            return a
        return L1
    return LX


def logic_xor(a: str, b: str) -> str:
    a, b = normalize(a), normalize(b)
    if LX in (a, b):
        return LX
    if a == b:
        return L0
    if {a, b} == {L0, L1}:
        return L1
    # handle D symbols
    if a == LD and b == L1:
        return LD_BAR
    if a == LD_BAR and b == L1:
        return LD
    if a == L1 and b == LD:
        return LD_BAR
    if a == L1 and b == LD_BAR:
        return LD
    if a == LD and b == L0:
        return LD
    if a == LD_BAR and b == L0:
        return LD_BAR
    if a == L0 and b == LD:
        return LD
    if a == L0 and b == LD_BAR:
        return LD_BAR
    if a == LD and b == LD_BAR:
        return L1
    if a == LD_BAR and b == LD:
        return L1
    return LX


def reduce_and(values: Iterable[str]) -> str:
    result = L1
    for v in values:
        result = logic_and(result, v)
    return result


def reduce_or(values: Iterable[str]) -> str:
    result = L0
    for v in values:
        result = logic_or(result, v)
    return result


def reduce_xor(values: Iterable[str]) -> str:
    result = L0
    for v in values:
        result = logic_xor(result, v)
    return result


def is_unknown(v: str) -> bool:
    return normalize(v) == LX


def is_fault_symbol(v: str) -> bool:
    v = normalize(v)
    return v in {LD, LD_BAR}
