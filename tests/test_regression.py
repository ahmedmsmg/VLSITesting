"""Tests for the regression runner and fault coverage analyzer."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from regression.runner import RegressionRunner, FaultTestResult
from regression.coverage import CoverageReport, FaultCoverageAnalyzer
from regression.report import ReportGenerator
from fault import Fault


# ── RegressionRunner ──────────────────────────────────────────────────────────

def test_discover_circuits():
    runner = RegressionRunner("examples/")
    circuits = runner.discover_circuits()
    assert len(circuits) >= 5
    assert all(p.endswith(".ckt") for p in circuits)


def test_discover_circuits_empty_dir(tmp_path):
    runner = RegressionRunner(str(tmp_path))
    assert runner.discover_circuits() == []


def test_run_circuit_returns_results():
    runner = RegressionRunner("examples/")
    results = runner.run_circuit("examples/t4_3.ckt", algorithms=["SAT"])
    assert len(results) > 0
    assert all(isinstance(r, FaultTestResult) for r in results)


def test_run_circuit_result_fields():
    runner = RegressionRunner("examples/")
    results = runner.run_circuit("examples/t4_3.ckt", algorithms=["D"])
    for r in results:
        assert r.circuit_name == "t4_3"
        assert r.algorithm == "D"
        assert isinstance(r.fault, Fault)
        assert isinstance(r.runtime_sec, float)
        assert r.runtime_sec >= 0.0


def test_run_all_covers_all_circuits():
    runner = RegressionRunner("examples/")
    results = runner.run_all(algorithms=["SAT"])
    circuit_names = {r.circuit_name for r in results}
    assert len(circuit_names) >= 5


def test_detected_vectors_are_valid():
    """Any test vector returned should actually detect the fault."""
    runner = RegressionRunner("examples/")
    results = runner.run_circuit("examples/t4_3.ckt", algorithms=["SAT"])
    from ckt_parser import parse_file
    circuit = parse_file("examples/t4_3.ckt")
    for r in results:
        if r.detected and r.test_vector is not None:
            good = circuit.evaluate_vector(r.test_vector)
            faulty = circuit.evaluate_vector(r.test_vector, fault=r.fault)
            assert any(
                good[po] != faulty[po] for po in circuit.primary_outputs
            ), f"Invalid vector for {r.fault.label()}"


# ── FaultCoverageAnalyzer ─────────────────────────────────────────────────────

def test_analyze_empty_results():
    report = FaultCoverageAnalyzer().analyze([])
    assert report.total_faults == 0
    assert report.coverage_pct == 100.0


def test_analyze_all_detected():
    results = [
        FaultTestResult("c1", Fault("n", 0), "SAT", {"A": "1"}, True, 0.001),
        FaultTestResult("c1", Fault("n", 1), "SAT", {"A": "0"}, True, 0.001),
    ]
    report = FaultCoverageAnalyzer().analyze(results)
    assert report.detected_faults == 2
    assert report.coverage_pct == pytest.approx(100.0)


def test_analyze_partial_coverage():
    results = [
        FaultTestResult("c1", Fault("a", 0), "SAT", {"X": "1"}, True, 0.001),
        FaultTestResult("c1", Fault("b", 0), "SAT", None, False, 0.001),
    ]
    report = FaultCoverageAnalyzer().analyze(results)
    assert report.detected_faults == 1
    assert report.coverage_pct == pytest.approx(50.0)
    assert "b-sa0" in report.uncovered_fault_labels


def test_analyze_per_algorithm_coverage():
    results = [
        FaultTestResult("c1", Fault("a", 0), "D",   {"X": "1"}, True, 0.001),
        FaultTestResult("c1", Fault("a", 0), "SAT", {"X": "1"}, True, 0.001),
        FaultTestResult("c1", Fault("b", 0), "D",   None, False, 0.001),
        FaultTestResult("c1", Fault("b", 0), "SAT", {"X": "0"}, True, 0.001),
    ]
    report = FaultCoverageAnalyzer().analyze(results)
    assert "D" in report.per_algorithm
    assert "SAT" in report.per_algorithm
    assert report.per_algorithm["SAT"] == pytest.approx(100.0)


def test_analyze_all_groups_by_circuit():
    results = [
        FaultTestResult("c1", Fault("a", 0), "SAT", {"X": "1"}, True, 0.001),
        FaultTestResult("c2", Fault("b", 0), "SAT", None, False, 0.001),
    ]
    reports = FaultCoverageAnalyzer().analyze_all(results)
    assert "c1" in reports
    assert "c2" in reports
    assert reports["c1"].detected_faults == 1
    assert reports["c2"].detected_faults == 0


def test_prove_completeness_t4_3():
    """All undetected faults on t4_3 should be confirmed redundant by SAT."""
    runner = RegressionRunner("examples/")
    results = runner.run_circuit("examples/t4_3.ckt", algorithms=["D"])
    report = FaultCoverageAnalyzer().analyze(results)
    proved = FaultCoverageAnalyzer().prove_completeness("examples/t4_3.ckt", report)
    # After proving, coverage_pct should be >= report coverage_pct
    assert proved.coverage_pct >= report.coverage_pct


# ── ReportGenerator ───────────────────────────────────────────────────────────

def test_text_report_contains_circuit_name():
    report = CoverageReport(
        circuit_name="test_ckt",
        total_faults=10, detected_faults=9,
        undetectable_faults=1, unknown_faults=0,
        coverage_pct=100.0,
    )
    gen = ReportGenerator()
    text = gen.text_report({"test_ckt": report})
    assert "test_ckt" in text
    assert "OVERALL" in text


def test_html_report_contains_circuit_name():
    report = CoverageReport(
        circuit_name="html_test",
        total_faults=5, detected_faults=5,
        undetectable_faults=0, unknown_faults=0,
        coverage_pct=100.0,
    )
    gen = ReportGenerator()
    html = gen.html_report({"html_test": report})
    assert "html_test" in html
    assert "<table>" in html


def test_json_report_structure():
    import json
    report = CoverageReport(
        circuit_name="j",
        total_faults=4, detected_faults=4,
        undetectable_faults=0, unknown_faults=0,
        coverage_pct=100.0,
    )
    gen = ReportGenerator()
    data = gen.json_report({"j": report})
    assert "j" in data
    assert data["j"]["total_faults"] == 4
    assert data["j"]["coverage_pct"] == 100.0


def test_full_regression_on_t4_3():
    """End-to-end: run, analyze, prove, report."""
    runner = RegressionRunner("examples/")
    results = runner.run_circuit("examples/t4_3.ckt", algorithms=["D", "SAT"])
    reports = FaultCoverageAnalyzer().analyze_all(results)
    assert "t4_3" in reports
    proved = FaultCoverageAnalyzer().prove_completeness(
        "examples/t4_3.ckt", reports["t4_3"]
    )
    # Provably complete: all detectable faults should be covered
    assert proved.unknown_faults == 0
    assert proved.coverage_pct == pytest.approx(100.0, abs=0.1)
    text = ReportGenerator().text_report({"t4_3": proved})
    assert "t4_3" in text
