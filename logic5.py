"""Five-valued logic utilities for ATPG.

Values:
    0, 1, X (unknown), D (1 in good, 0 in faulty), D_BAR (0 in good, 1 in faulty)
"""
from __future__ import annotations

from typing import Optional, Tuple

# Canonical symbols
L0 = "0"
L1 = "1"
LX = "X"
LD = "D"
LD_BAR = "D'"


def to_pair(value: str) -> Tuple[Optional[int], Optional[int]]:
    """Convert a five-valued symbol to (good, faulty) bits where None denotes X."""
    if value == L0:
        return 0, 0
    if value == L1:
        return 1, 1
    if value == LX:
        return None, None
    if value == LD:
        return 1, 0
    if value == LD_BAR:
        return 0, 1
    raise ValueError(f"Invalid logic value {value}")


def from_pair(pair: Tuple[Optional[int], Optional[int]]) -> str:
    """Convert a (good, faulty) pair back to a five-valued symbol."""
    g, f = pair
    if g is None or f is None:
        return LX
    if g == 1 and f == 0:
        return LD
    if g == 0 and f == 1:
        return LD_BAR
    if g == f == 1:
        return L1
    if g == f == 0:
        return L0
    return LX


def _bool_and(a: Optional[int], b: Optional[int]) -> Optional[int]:
    if a == 0 or b == 0:
        return 0
    if a == 1 and b == 1:
        return 1
    return None


def _bool_or(a: Optional[int], b: Optional[int]) -> Optional[int]:
    if a == 1 or b == 1:
        return 1
    if a == 0 and b == 0:
        return 0
    return None


def _bool_xor(a: Optional[int], b: Optional[int]) -> Optional[int]:
    if a is None or b is None:
        return None
    return a ^ b


def _bool_not(a: Optional[int]) -> Optional[int]:
    if a is None:
        return None
    return 1 - a


def logic_and(a: str, b: str) -> str:
    g1, f1 = to_pair(a)
    g2, f2 = to_pair(b)
    g = _bool_and(g1, g2)
    f = _bool_and(f1, f2)
    return from_pair((g, f))


def logic_or(a: str, b: str) -> str:
    g1, f1 = to_pair(a)
    g2, f2 = to_pair(b)
    g = _bool_or(g1, g2)
    f = _bool_or(f1, f2)
    return from_pair((g, f))


def logic_xor(a: str, b: str) -> str:
    g1, f1 = to_pair(a)
    g2, f2 = to_pair(b)
    g = _bool_xor(g1, g2)
    f = _bool_xor(f1, f2)
    return from_pair((g, f))


def logic_not(a: str) -> str:
    g, f = to_pair(a)
    return from_pair((_bool_not(g), _bool_not(f)))


def is_unknown(value: str) -> bool:
    return value == LX


def is_one(value: str) -> bool:
    return value == L1


def is_zero(value: str) -> bool:
    return value == L0


def is_d_like(value: str) -> bool:
    return value in {LD, LD_BAR}


def inv_if_needed(value: str, inverted: bool) -> str:
    return logic_not(value) if inverted else value

