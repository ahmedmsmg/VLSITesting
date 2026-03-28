#!/usr/bin/env python3
"""Demo: Full regression flow with fault coverage analysis and provable completeness.

Demonstrates the cross-cutting regression infrastructure:
  - Automated circuit discovery
  - All three ATPG algorithms run on all faults
  - Fault coverage analysis with per-algorithm breakdown
  - SAT-based proof that uncovered faults are truly redundant
  - Text, HTML, and JSON report generation

Run from the project root::

    python examples/demo_regression.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from regression.runner import RegressionRunner
from regression.coverage import FaultCoverageAnalyzer
from regression.report import ReportGenerator


print("=" * 60)
print("ATPG REGRESSION FLOW")
print("=" * 60)

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Discover and run all circuits
# ─────────────────────────────────────────────────────────────────────────────

runner = RegressionRunner("examples/")
circuits = runner.discover_circuits()
print(f"\nDiscovered {len(circuits)} circuit(s):")
for c in circuits:
    print(f"  {os.path.basename(c)}")

print("\nRunning D-Algorithm and SAT on all faults...")
results = runner.run_all(algorithms=["D", "SAT"], verbose=False)
print(f"Generated {len(results)} test results.")

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Analyze fault coverage
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "─" * 60)
print("FAULT COVERAGE ANALYSIS")
print("─" * 60)

analyzer = FaultCoverageAnalyzer()
reports = analyzer.analyze_all(results)

for name, report in sorted(reports.items()):
    print(f"\n{report}")

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Prove completeness on t4_3
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "─" * 60)
print("PROVABLE COMPLETENESS CHECK (t4_3)")
print("─" * 60)

if "t4_3" in reports:
    t4_3_report = reports["t4_3"]
    if t4_3_report.unknown_faults > 0:
        print(f"\nProving {t4_3_report.unknown_faults} uncovered fault(s) are redundant...")
        proved = analyzer.prove_completeness("examples/t4_3.ckt", t4_3_report)
        print(f"  Proven undetectable : {proved.undetectable_faults}")
        print(f"  Remaining unknown   : {proved.unknown_faults}")
        print(f"  Adjusted coverage   : {proved.coverage_pct:.1f}%")
        if proved.unknown_faults == 0:
            print("  RESULT: Provably complete fault coverage on t4_3!")
    else:
        print("All faults covered — t4_3 is already at 100% coverage.")

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Generate reports
# ─────────────────────────────────────────────────────────────────────────────

gen = ReportGenerator()

print("\n" + "=" * 60)
print("SUMMARY REPORT")
print("=" * 60)
print(gen.text_report(reports))

# Write HTML and JSON to a temporary reports/ directory
os.makedirs("reports", exist_ok=True)
with open("reports/coverage.html", "w") as f:
    f.write(gen.html_report(reports))
print("HTML report  → reports/coverage.html")

with open("reports/coverage.json", "w") as f:
    f.write(gen.json_report_str(reports))
print("JSON report  → reports/coverage.json")

print("\nRegression demo complete.")
