"""Tests for UVMDriver, UVMMonitor, and UVMAgent."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuit import Circuit
from uvm.agent import UVMAgent, UVMDriver, UVMMonitor
from uvm.sequence import CircuitVector, DirectedVectorSequence, RandomVectorSequence


def make_circuit():
    c = Circuit("test")
    c.add_pi("A"); c.add_pi("B"); c.add_po("Z")
    c.add_gate("Z", "AND", ["A", "B"])
    c.build_topological()
    return c


# ── UVMDriver ─────────────────────────────────────────────────────────────────

def test_driver_drive_basic():
    c = make_circuit()
    driver = UVMDriver("drv")
    driver.circuit = c
    item = CircuitVector(c)
    item.values = {"A": "1", "B": "1"}
    outputs = driver.drive(item)
    assert outputs["Z"] == "1"


def test_driver_drive_zero():
    c = make_circuit()
    driver = UVMDriver("drv")
    driver.circuit = c
    item = CircuitVector(c)
    item.values = {"A": "0", "B": "1"}
    outputs = driver.drive(item)
    assert outputs["Z"] == "0"


def test_driver_no_circuit_raises():
    driver = UVMDriver("drv")
    c = make_circuit()
    item = CircuitVector(c)
    item.values = {"A": "1", "B": "1"}
    with pytest.raises(RuntimeError, match="circuit must be set"):
        driver.drive(item)


# ── UVMMonitor ────────────────────────────────────────────────────────────────

def test_monitor_observe_records_transaction():
    monitor = UVMMonitor("mon")
    monitor.observe({"A": "1"}, {"Z": "1"})
    assert len(monitor.observed) == 1
    txn = monitor.observed[0]
    assert txn["inputs"]["A"] == "1"
    assert txn["outputs"]["Z"] == "1"


def test_monitor_callback_called():
    received = []
    monitor = UVMMonitor("mon")
    monitor.add_callback(received.append)
    monitor.observe({"A": "0"}, {"Z": "0"})
    assert len(received) == 1
    assert received[0]["inputs"]["A"] == "0"


def test_monitor_multiple_callbacks():
    log1, log2 = [], []
    monitor = UVMMonitor("mon")
    monitor.add_callback(log1.append)
    monitor.add_callback(log2.append)
    monitor.observe({"A": "1"}, {"Z": "1"})
    assert len(log1) == 1
    assert len(log2) == 1


# ── UVMAgent ──────────────────────────────────────────────────────────────────

def test_agent_has_driver_and_monitor():
    agent = UVMAgent("agent")
    assert isinstance(agent.driver, UVMDriver)
    assert isinstance(agent.monitor, UVMMonitor)


def test_agent_children_registered():
    agent = UVMAgent("agent")
    assert "driver" in agent.children
    assert "monitor" in agent.children


def test_agent_run_sequence_drives_all_items(t4_3):
    agent = UVMAgent("agent")
    agent.driver.circuit = t4_3
    vectors = [
        {pi: "0" for pi in t4_3.primary_inputs},
        {pi: "1" for pi in t4_3.primary_inputs},
    ]
    seq = DirectedVectorSequence("test", vectors)
    agent.run_sequence(seq)
    assert len(agent.monitor.observed) == 2


def test_agent_run_sequence_random(t4_3):
    agent = UVMAgent("agent")
    agent.driver.circuit = t4_3
    seq = RandomVectorSequence("rand", t4_3, count=50)
    agent.run_sequence(seq)
    assert len(agent.monitor.observed) == 50
    # All outputs should be 0 or 1 (no X since all PIs are assigned)
    for txn in agent.monitor.observed:
        for po in t4_3.primary_outputs:
            assert txn["outputs"][po] in {"0", "1"}
