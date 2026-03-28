#!/usr/bin/env python3
"""Entry point for the automated regression flow.

Usage::

    python run_regression.py [--algo D PODEM SAT] [--dir examples/]
                             [--prove] [--html PATH] [--json PATH]

Options:
    --algo          Algorithms to run (default: D PODEM SAT)
    --dir           Directory containing .ckt circuit files (default: examples/)
    --prove         Use SAT to prove undetected faults are truly redundant
    --html PATH     Write HTML report to PATH
    --json PATH     Write JSON report to PATH
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from regression.runner import RegressionRunner
from regression.coverage import FaultCoverageAnalyzer
from regression.report import ReportGenerator


def main() -> None:
    parser = argparse.ArgumentParser(description="ATPG Regression Flow")
    parser.add_argument(
        "--algo", nargs="+", default=["D", "PODEM", "SAT"],
        choices=["D", "PODEM", "SAT"],
        help="Algorithms to run (default: D PODEM SAT)",
    )
    parser.add_argument(
        "--dir", default="examples/",
        help="Directory containing .ckt circuit files (default: examples/)",
    )
    parser.add_argument(
        "--prove", action="store_true",
        help="Use SAT to prove undetected faults are truly redundant",
    )
    parser.add_argument("--html", metavar="PATH", help="Write HTML report to PATH")
    parser.add_argument("--json", metavar="PATH", help="Write JSON report to PATH")
    args = parser.parse_args()

    print(f"Running regression in '{args.dir}' with algorithms: {args.algo}")

    runner = RegressionRunner(args.dir)
    circuits = runner.discover_circuits()
    if not circuits:
        print(f"No .ckt files found in '{args.dir}'. Exiting.")
        sys.exit(1)

    print(f"Discovered {len(circuits)} circuit(s).")
    results = runner.run_all(algorithms=args.algo, verbose=True)

    analyzer = FaultCoverageAnalyzer()
    reports = analyzer.analyze_all(results)

    if args.prove:
        print("\nProving completeness with SAT engine...")
        for name, report in reports.items():
            ckt_path = os.path.join(args.dir, name + ".ckt")
            if os.path.exists(ckt_path):
                reports[name] = analyzer.prove_completeness(ckt_path, report)

    gen = ReportGenerator()
    print()
    print(gen.text_report(reports))

    if args.html:
        html = gen.html_report(reports)
        with open(args.html, "w") as f:
            f.write(html)
        print(f"HTML report written to {args.html}")

    if args.json:
        json_str = gen.json_report_str(reports)
        with open(args.json, "w") as f:
            f.write(json_str)
        print(f"JSON report written to {args.json}")


if __name__ == "__main__":
    main()
