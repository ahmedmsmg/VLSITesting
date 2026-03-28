"""Pytest configuration and shared fixtures for the VLSITesting test suite."""
import sys
import os

# Ensure the project root is on sys.path so bare module imports work.
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from ckt_parser import parse_file


@pytest.fixture
def t4_3():
    """Load the t4_3 circuit (4 PIs, 1 PO, 5 gates)."""
    return parse_file("examples/t4_3.ckt")


@pytest.fixture
def t5_26a():
    """Load the full-adder circuit (3 PIs, 2 POs, 9 NAND gates)."""
    return parse_file("examples/t5_26a.ckt")


@pytest.fixture
def all_example_circuits():
    """Load all example circuits as a dict keyed by filename stem."""
    examples = [
        "examples/t4_3.ckt",
        "examples/t4_21.ckt",
        "examples/t5_10.ckt",
        "examples/t5_26a.ckt",
        "examples/t6_24_v1.ckt",
    ]
    return {os.path.basename(p): parse_file(p) for p in examples}
