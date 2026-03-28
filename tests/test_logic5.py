"""Unit tests for the five-valued logic layer (logic5.py)."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import logic5 as L


# ── normalize ──────────────────────────────────────────────────────────────────

def test_normalize_valid_values():
    for v in ("0", "1", "X", "D", "D'"):
        assert L.normalize(v) == v


def test_normalize_invalid_raises():
    with pytest.raises(ValueError):
        L.normalize("Z")


# ── logic_not ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("inp,expected", [
    (L.L0, L.L1),
    (L.L1, L.L0),
    (L.LD, L.LD_BAR),
    (L.LD_BAR, L.LD),
    (L.LX, L.LX),
])
def test_logic_not(inp, expected):
    assert L.logic_not(inp) == expected


# ── logic_and ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("a,b,expected", [
    (L.L0, L.L0, L.L0),
    (L.L0, L.L1, L.L0),
    (L.L1, L.L0, L.L0),
    (L.L1, L.L1, L.L1),
    (L.LX, L.L1, L.LX),
    (L.L1, L.LX, L.LX),
    (L.L0, L.LX, L.L0),   # 0 is controlling
    (L.LX, L.L0, L.L0),
    (L.LD, L.L1, L.LD),
    (L.LD_BAR, L.L1, L.LD_BAR),
    (L.LD, L.LD, L.LD),
    (L.LD_BAR, L.LD_BAR, L.LD_BAR),
    (L.LD, L.LD_BAR, L.L0),  # D and D' conflict → 0
    (L.LD_BAR, L.LD, L.L0),
])
def test_logic_and(a, b, expected):
    assert L.logic_and(a, b) == expected


# ── logic_or ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("a,b,expected", [
    (L.L0, L.L0, L.L0),
    (L.L0, L.L1, L.L1),
    (L.L1, L.L0, L.L1),
    (L.L1, L.L1, L.L1),
    (L.LX, L.L0, L.LX),
    (L.L0, L.LX, L.LX),
    (L.L1, L.LX, L.L1),   # 1 is controlling
    (L.LX, L.L1, L.L1),
    (L.LD, L.L0, L.LD),
    (L.LD_BAR, L.L0, L.LD_BAR),
    (L.LD, L.LD, L.LD),
    (L.LD_BAR, L.LD_BAR, L.LD_BAR),
    (L.LD, L.LD_BAR, L.L1),  # D or D' → 1
    (L.LD_BAR, L.LD, L.L1),
])
def test_logic_or(a, b, expected):
    assert L.logic_or(a, b) == expected


# ── logic_xor ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("a,b,expected", [
    (L.L0, L.L0, L.L0),
    (L.L0, L.L1, L.L1),
    (L.L1, L.L0, L.L1),
    (L.L1, L.L1, L.L0),
    (L.LX, L.L0, L.LX),
    (L.L0, L.LX, L.LX),
    (L.LD, L.L0, L.LD),
    (L.LD_BAR, L.L0, L.LD_BAR),
    (L.LD, L.L1, L.LD_BAR),
    (L.LD_BAR, L.L1, L.LD),
    (L.L0, L.LD, L.LD),
    (L.L0, L.LD_BAR, L.LD_BAR),
    (L.L1, L.LD, L.LD_BAR),
    (L.L1, L.LD_BAR, L.LD),
    (L.LD, L.LD, L.L0),
    (L.LD_BAR, L.LD_BAR, L.L0),
    (L.LD, L.LD_BAR, L.L1),
    (L.LD_BAR, L.LD, L.L1),
])
def test_logic_xor(a, b, expected):
    assert L.logic_xor(a, b) == expected


# ── reduce helpers ────────────────────────────────────────────────────────────

def test_reduce_and_all_ones():
    assert L.reduce_and(["1", "1", "1"]) == L.L1


def test_reduce_and_with_zero():
    assert L.reduce_and(["1", "0", "1"]) == L.L0


def test_reduce_or_all_zeros():
    assert L.reduce_or(["0", "0", "0"]) == L.L0


def test_reduce_or_with_one():
    assert L.reduce_or(["0", "0", "1"]) == L.L1


def test_reduce_xor_parity():
    assert L.reduce_xor(["1", "1", "0"]) == L.L0
    assert L.reduce_xor(["1", "0", "0"]) == L.L1


# ── predicates ────────────────────────────────────────────────────────────────

def test_is_unknown():
    assert L.is_unknown(L.LX)
    assert not L.is_unknown(L.L0)
    assert not L.is_unknown(L.L1)
    assert not L.is_unknown(L.LD)
    assert not L.is_unknown(L.LD_BAR)


def test_is_fault_symbol():
    assert L.is_fault_symbol(L.LD)
    assert L.is_fault_symbol(L.LD_BAR)
    assert not L.is_fault_symbol(L.L0)
    assert not L.is_fault_symbol(L.L1)
    assert not L.is_fault_symbol(L.LX)
