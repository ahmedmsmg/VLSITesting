"""Tests for UVMScoreboard."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuit import Circuit
from uvm.scoreboard import UVMScoreboard, Mismatch


def make_and():
    c = Circuit("and")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "AND", ["A", "B"])
    c.build_topological()
    return c


def make_or():
    c = Circuit("or")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "OR", ["A", "B"])
    c.build_topological()
    return c


# ── Basic matching ────────────────────────────────────────────────────────────

def test_scoreboard_match_incremented():
    ref = make_and()
    sb = UVMScoreboard("sb", reference=ref)
    txn = {"inputs": {"A": "1", "B": "1"}, "outputs": {"Z": "1"}}
    result = sb.compare(txn)
    assert result is True
    assert sb.matches == 1
    assert sb.mismatches == 0


def test_scoreboard_mismatch_incremented():
    ref = make_and()
    sb = UVMScoreboard("sb", reference=ref)
    # DUT says Z=1 for AND(0,1) which should be Z=0
    txn = {"inputs": {"A": "0", "B": "1"}, "outputs": {"Z": "1"}}
    result = sb.compare(txn)
    assert result is False
    assert sb.mismatches == 1
    assert sb.matches == 0


def test_scoreboard_no_reference_always_matches():
    sb = UVMScoreboard("sb")
    txn = {"inputs": {"A": "X"}, "outputs": {"Z": "?"}}
    result = sb.compare(txn)
    assert result is True
    assert sb.matches == 1


# ── Statistics ────────────────────────────────────────────────────────────────

def test_scoreboard_total():
    ref = make_and()
    sb = UVMScoreboard("sb", reference=ref)
    sb.compare({"inputs": {"A": "1", "B": "1"}, "outputs": {"Z": "1"}})
    sb.compare({"inputs": {"A": "0", "B": "1"}, "outputs": {"Z": "1"}})
    assert sb.total == 2


def test_scoreboard_pass_rate_all_pass():
    ref = make_and()
    sb = UVMScoreboard("sb", reference=ref)
    sb.compare({"inputs": {"A": "1", "B": "1"}, "outputs": {"Z": "1"}})
    assert sb.pass_rate == 1.0


def test_scoreboard_pass_rate_partial():
    ref = make_and()
    sb = UVMScoreboard("sb", reference=ref)
    sb.compare({"inputs": {"A": "1", "B": "1"}, "outputs": {"Z": "1"}})  # match
    sb.compare({"inputs": {"A": "0", "B": "1"}, "outputs": {"Z": "1"}})  # mismatch
    assert sb.pass_rate == pytest.approx(0.5)


def test_scoreboard_pass_rate_empty():
    sb = UVMScoreboard("sb")
    assert sb.pass_rate == 1.0  # no transactions → 100%


# ── Reference mismatch scenario ───────────────────────────────────────────────

def test_and_vs_or_mismatches():
    """AND circuit used as DUT, OR as reference → mismatches for A=1,B=0."""
    ref = make_or()
    sb = UVMScoreboard("sb", reference=ref)
    # AND(1,0)=0, OR(1,0)=1 → mismatch
    txn = {"inputs": {"A": "1", "B": "0"}, "outputs": {"Z": "0"}}
    assert sb.compare(txn) is False


# ── Report ────────────────────────────────────────────────────────────────────

def test_report_contains_summary(t4_3):
    sb = UVMScoreboard("sb", reference=t4_3)
    for pi_vals in [{"1gat": "1", "2gat": "1", "3gat": "0", "4gat": "0"}]:
        outputs = t4_3.evaluate_vector(pi_vals)
        sb.compare({"inputs": pi_vals, "outputs": outputs})
    report = sb.report()
    assert "Scoreboard" in report
    assert "Matches" in report


# ── Mismatch dataclass ────────────────────────────────────────────────────────

def test_mismatch_str():
    m = Mismatch(
        inputs={"A": "1"},
        dut_outputs={"Z": "0"},
        ref_outputs={"Z": "1"},
        differing_nets=["Z"],
    )
    s = str(m)
    assert "MISMATCH" in s
    assert "Z" in s
