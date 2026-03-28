"""Tests for UVM component hierarchy and phase management."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from uvm.base import UVMComponent, UVMPhase


# ── Component hierarchy ───────────────────────────────────────────────────────

def test_component_name():
    c = UVMComponent("my_component")
    assert c.name == "my_component"


def test_parent_child_registration():
    parent = UVMComponent("parent")
    child = UVMComponent("child", parent)
    assert "child" in parent.children
    assert parent.children["child"] is child
    assert child.parent is parent


def test_orphan_component_no_parent():
    c = UVMComponent("root")
    assert c.parent is None
    assert c.children == {}


def test_multiple_children():
    root = UVMComponent("root")
    a = UVMComponent("a", root)
    b = UVMComponent("b", root)
    assert len(root.children) == 2


# ── Phase traversal ───────────────────────────────────────────────────────────

def test_walk_top_down_order():
    root = UVMComponent("root")
    child = UVMComponent("child", root)
    grandchild = UVMComponent("gc", child)
    order = list(root._walk_top_down())
    assert order.index(root) < order.index(child)
    assert order.index(child) < order.index(grandchild)


def test_walk_bottom_up_order():
    root = UVMComponent("root")
    child = UVMComponent("child", root)
    order = list(root._walk_bottom_up())
    assert order.index(child) < order.index(root)


# ── Phase execution ───────────────────────────────────────────────────────────

def test_run_all_phases_calls_all_hooks():
    log = []

    class Recorder(UVMComponent):
        def build_phase(self):   log.append(f"{self.name}:build")
        def connect_phase(self): log.append(f"{self.name}:connect")
        def run_phase(self):     log.append(f"{self.name}:run")
        def extract_phase(self): log.append(f"{self.name}:extract")
        def check_phase(self):   log.append(f"{self.name}:check")
        def report_phase(self):  log.append(f"{self.name}:report")

    root = Recorder("root")
    child = Recorder("child", root)

    root.run_all_phases()

    # Both components should have all phases recorded
    assert "root:build" in log
    assert "child:build" in log
    assert "root:run" in log
    assert "child:run" in log
    assert "root:report" in log


def test_build_before_run():
    log = []

    class TrackedComp(UVMComponent):
        def build_phase(self): log.append("build")
        def run_phase(self):   log.append("run")

    root = TrackedComp("root")
    root.run_all_phases()

    assert log.index("build") < log.index("run")


def test_extract_before_check_before_report():
    log = []

    class TrackedComp(UVMComponent):
        def extract_phase(self): log.append("extract")
        def check_phase(self):   log.append("check")
        def report_phase(self):  log.append("report")

    root = TrackedComp("root")
    root.run_all_phases()

    assert log.index("extract") < log.index("check") < log.index("report")


# ── UVMPhase enum ─────────────────────────────────────────────────────────────

def test_phase_enum_values():
    phases = list(UVMPhase)
    assert UVMPhase.BUILD in phases
    assert UVMPhase.RUN in phases
    assert UVMPhase.REPORT in phases
    assert len(phases) == 6
