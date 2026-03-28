"""Unit tests for the ISCAS-style .ckt parser."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ckt_parser import parse_ckt, parse_file, ParseError


# ── parse_ckt (string-based) ─────────────────────────────────────────────────

def test_parse_parenthesized_syntax():
    text = "INPUT(A)\nINPUT(B)\nOUTPUT(Z)\nZ = AND(A, B)\n"
    c = parse_ckt(text, "test")
    assert c.primary_inputs == ["A", "B"]
    assert c.primary_outputs == ["Z"]
    assert len(c.gates) == 1
    assert c.gates[0].type == "AND"


def test_parse_tabular_syntax():
    text = "A  $ ... primary input\nB  $ ... primary input\nZ  $ ... primary output\nZ AND A B\n"
    c = parse_ckt(text, "test")
    assert "A" in c.primary_inputs
    assert "B" in c.primary_inputs
    assert "Z" in c.primary_outputs
    assert c.gates[0].type == "AND"


def test_parse_error_on_invalid_line():
    with pytest.raises(ParseError):
        parse_ckt("NOT A VALID LINE AT ALL !@#$%^", "bad")


def test_gate_type_case_insensitive():
    text = "INPUT(A)\nINPUT(B)\nOUTPUT(Z)\nZ = nand(A, B)\n"
    c = parse_ckt(text)
    assert c.gates[0].type == "NAND"


# ── parse_file — example circuits ─────────────────────────────────────────────

def test_t4_3_structure():
    c = parse_file("examples/t4_3.ckt")
    assert len(c.primary_inputs) == 4
    assert len(c.primary_outputs) == 1
    assert len(c.gates) == 5
    assert "9gat" in c.primary_outputs


def test_t4_21_structure():
    c = parse_file("examples/t4_21.ckt")
    assert len(c.primary_inputs) == 5
    assert len(c.primary_outputs) == 1


def test_t5_10_structure():
    c = parse_file("examples/t5_10.ckt")
    assert len(c.primary_inputs) == 5
    assert len(c.primary_outputs) == 1


def test_t5_26a_full_adder():
    c = parse_file("examples/t5_26a.ckt")
    assert len(c.primary_inputs) == 3
    assert len(c.primary_outputs) == 2
    assert "X" in c.primary_inputs
    assert "Y" in c.primary_inputs
    assert "CI" in c.primary_inputs
    assert "S" in c.primary_outputs
    assert "CO" in c.primary_outputs
    assert len(c.gates) == 9


def test_t6_24_v1_structure():
    c = parse_file("examples/t6_24_v1.ckt")
    assert len(c.primary_inputs) == 6
    assert len(c.primary_outputs) == 1
    assert len(c.gates) == 16


def test_all_circuits_have_topological_order(all_example_circuits):
    """Every loaded circuit must have a populated topo list."""
    for name, circuit in all_example_circuits.items():
        assert len(circuit.topo) > 0, f"{name} topo is empty"


def test_all_circuits_simulate_all_zeros(all_example_circuits):
    """Every circuit must evaluate without error when all PIs are 0."""
    for name, circuit in all_example_circuits.items():
        vec = {pi: "0" for pi in circuit.primary_inputs}
        result = circuit.evaluate_vector(vec)
        assert all(v in {"0", "1"} for v in result.values() if v is not None), \
            f"{name}: unexpected values in simulation"
