"""Unit tests for BoundedModelChecker (formal/bmc.py)."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuit import Circuit, FlipFlop
from formal.bmc import BadStateProperty, BMCResult, BoundedModelChecker


# ── Combinational circuits (no flip-flops) ────────────────────────────────────

def make_and_circuit():
    c = Circuit("and")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "AND", ["A", "B"])
    c.build_topological()
    return c


def test_bmc_combinational_bad_state_reachable():
    """AND(A,B)==1 is reachable at step 0 (just set A=B=1)."""
    c = make_and_circuit()
    bad = BadStateProperty("z_is_1", lambda enc, k: enc.var("Z") == True)
    result = BoundedModelChecker(c).check(bad, bound=1)
    assert result.reachable is True
    assert result.step == 0
    assert result.witness is not None
    assert result.witness[0]["A"] == "1"
    assert result.witness[0]["B"] == "1"


def test_bmc_combinational_bad_state_not_reachable():
    """AND(A,B)==1 when A=0 is always unreachable (we fix A=0 via a property)."""
    c = make_and_circuit()
    # Bad state: Z=1 AND A=0 — impossible for AND gate
    from z3 import And
    bad = BadStateProperty(
        "z_one_a_zero",
        lambda enc, k: And(enc.var("Z") == True, enc.var("A") == False),
    )
    result = BoundedModelChecker(c).check(bad, bound=3)
    assert result.reachable is False


# ── Sequential circuits (with flip-flops) ─────────────────────────────────────

def make_toggle_circuit():
    """A single toggle flip-flop: Q = NOT(Q_prev).
    Initial state Q=0. The circuit has no combinational gates besides BUF.

    Structure:
      - PI: tick (unused combinational input, needed to satisfy circuit rules)
      - FF: output=Q, input=Q_d, initial="0"
      - Gate: Q_d = NOT(Q)  (next state is complement of current state)
      - PO: Q
    """
    c = Circuit("toggle")
    c.add_pi("tick")
    c.add_po("Q")
    # Q is initially driven as a flip-flop state output
    c.add_gate("Q_d", "NOT", ["Q"])  # next state = NOT(current Q)
    c.add_gate("Q", "BUF", ["Q"])    # Q passes through (BMC ties state var)
    c.flip_flops.append(FlipFlop(output="Q", input="Q_d", initial="0"))
    # Note: build_topological will fail on cycle Q->Q_d->Q.
    # For BMC we skip build_topological for the sequential part and use
    # the state variable tie mechanism instead.
    return c


def make_simple_counter():
    """Simple 1-bit counter: Q_next = NOT(Q), starting at Q=0.

    We represent it as a circuit where the flip-flop output Q is a PI-like
    variable that the BMC constrains directly via state variables.
    """
    c = Circuit("counter")
    c.add_pi("enable")
    c.add_po("Q")
    # Mux: if enable=1, toggle Q; else hold Q.
    # Simplified: always toggle (just NOT Q as next state).
    c.add_gate("Q_not", "NOT", ["Q"])
    # We need Q as both an input to Q_not and a PO.
    # For BMC, we register Q as a state variable via FlipFlop.
    c.flip_flops.append(FlipFlop(output="Q", input="Q_not", initial="0"))
    return c


def test_bmc_result_dataclass():
    r = BMCResult(property_name="test", reachable=True, step=2, witness=[{"A": "1"}])
    assert r.reachable is True
    assert r.step == 2
    assert "step 2" in str(r).lower()


def test_bmc_result_str_not_reachable():
    r = BMCResult(property_name="p", reachable=False)
    assert "NOT reachable" in str(r)


def test_bmc_witness_format(t4_3):
    """Witness should have one dict of PI assignments per step."""
    bad = BadStateProperty("output_1", lambda enc, k: enc.var("9gat") == True)
    result = BoundedModelChecker(t4_3).check(bad, bound=1)
    if result.reachable:
        assert isinstance(result.witness, list)
        assert len(result.witness) == result.step + 1
        for step_inputs in result.witness:
            assert set(step_inputs.keys()) == set(t4_3.primary_inputs)
            assert all(v in {"0", "1"} for v in step_inputs.values())


def test_bmc_flipflop_dataclass():
    ff = FlipFlop(output="Q", input="D", initial="0")
    assert ff.output == "Q"
    assert ff.input == "D"
    assert ff.initial == "0"


def test_bmc_flipflop_default_initial():
    ff = FlipFlop(output="Q", input="D")
    assert ff.initial == "X"


def test_bmc_circuit_has_flipflops_list():
    c = Circuit()
    assert hasattr(c, "flip_flops")
    assert c.flip_flops == []


def test_bmc_no_bad_state_within_small_bound(t4_3):
    """A property that no input can satisfy is never reachable."""
    from z3 import And
    # Require 9gat=1 AND 9gat=0 simultaneously — impossible.
    bad = BadStateProperty(
        "impossible",
        lambda enc, k: And(enc.var("9gat") == True, enc.var("9gat") == False),
    )
    result = BoundedModelChecker(t4_3).check(bad, bound=3)
    assert result.reachable is False
