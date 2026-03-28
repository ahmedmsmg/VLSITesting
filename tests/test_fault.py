"""Unit tests for the Fault model and collapse_faults utility."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fault import Fault, collapse_faults


def test_fault_label_sa0():
    f = Fault("nodeA", 0)
    assert f.label() == "nodeA-sa0"


def test_fault_label_sa1():
    f = Fault("nodeB", 1)
    assert f.label() == "nodeB-sa1"


def test_fault_frozen():
    f = Fault("n", 0)
    with pytest.raises(Exception):
        f.node = "other"  # type: ignore


def test_fault_hashable():
    f1 = Fault("n", 0)
    f2 = Fault("n", 0)
    assert f1 == f2
    assert hash(f1) == hash(f2)
    assert len({f1, f2}) == 1


def test_collapse_faults_two_per_node():
    classes = collapse_faults(["a", "b", "c"])
    # each node → sa0 class + sa1 class
    assert len(classes) == 6
    labels = {cls[0].label() for cls in classes}
    assert "a-sa0" in labels
    assert "a-sa1" in labels
    assert "b-sa0" in labels
    assert "b-sa1" in labels
    assert "c-sa0" in labels
    assert "c-sa1" in labels


def test_collapse_faults_empty():
    assert collapse_faults([]) == []


def test_collapse_faults_single_node():
    classes = collapse_faults(["x"])
    assert len(classes) == 2
    stuck_values = {cls[0].stuck_at for cls in classes}
    assert stuck_values == {0, 1}
