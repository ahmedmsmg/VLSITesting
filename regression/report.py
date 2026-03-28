"""Report generation: text, HTML, and JSON formats.

Converts :class:`~regression.coverage.CoverageReport` objects into
human-readable and machine-parseable output.
"""
from __future__ import annotations

import json
from typing import Dict, List

from regression.coverage import CoverageReport


class ReportGenerator:
    """Serialize :class:`CoverageReport` objects into different formats."""

    def text_report(self, reports: Dict[str, CoverageReport]) -> str:
        """Generate a plain-text summary table."""
        lines = [
            "=" * 70,
            " ATPG Regression Report — Fault Coverage Summary",
            "=" * 70,
        ]
        total_faults = sum(r.total_faults for r in reports.values())
        total_detected = sum(r.detected_faults for r in reports.values())
        total_undetectable = sum(r.undetectable_faults for r in reports.values())

        for name, report in sorted(reports.items()):
            lines.append(str(report))
            lines.append("")

        # Overall summary
        detectable = total_faults - total_undetectable
        overall_pct = total_detected / detectable * 100.0 if detectable else 100.0
        lines += [
            "─" * 70,
            f"OVERALL  {total_detected}/{detectable} detectable faults covered"
            f"  ({overall_pct:.1f}%)",
            "=" * 70,
        ]
        return "\n".join(lines)

    def html_report(self, reports: Dict[str, CoverageReport]) -> str:
        """Generate a minimal HTML coverage report."""
        rows = ""
        for name, r in sorted(reports.items()):
            bar_pct = min(r.coverage_pct, 100.0)
            color = "#4caf50" if bar_pct >= 90 else "#ff9800" if bar_pct >= 70 else "#f44336"
            rows += (
                f"<tr>"
                f"<td>{name}</td>"
                f"<td>{r.total_faults}</td>"
                f"<td>{r.detected_faults}</td>"
                f"<td>{r.undetectable_faults}</td>"
                f"<td>"
                f"<div style='background:#eee;width:200px;display:inline-block'>"
                f"<div style='background:{color};width:{bar_pct*2:.0f}px;height:14px'></div>"
                f"</div> {bar_pct:.1f}%"
                f"</td>"
                f"</tr>\n"
            )

        return f"""<!DOCTYPE html>
<html>
<head><meta charset='utf-8'><title>ATPG Regression Report</title>
<style>
  body {{ font-family: monospace; padding: 20px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 12px; text-align: left; }}
  th {{ background: #333; color: #fff; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
</style>
</head>
<body>
<h2>ATPG Regression Report — Fault Coverage</h2>
<table>
<tr>
  <th>Circuit</th><th>Total Faults</th><th>Detected</th>
  <th>Undetectable</th><th>Coverage</th>
</tr>
{rows}
</table>
</body>
</html>"""

    def json_report(self, reports: Dict[str, CoverageReport]) -> Dict:
        """Serialize reports to a JSON-compatible dict."""
        out = {}
        for name, r in reports.items():
            out[name] = {
                "total_faults": r.total_faults,
                "detected_faults": r.detected_faults,
                "undetectable_faults": r.undetectable_faults,
                "unknown_faults": r.unknown_faults,
                "coverage_pct": round(r.coverage_pct, 2),
                "per_algorithm": {k: round(v, 2) for k, v in r.per_algorithm.items()},
                "uncovered_faults": r.uncovered_fault_labels,
                "undetectable_faults_list": r.undetectable_fault_labels,
            }
        return out

    def json_report_str(self, reports: Dict[str, CoverageReport]) -> str:
        """Return JSON-serialized report as a string."""
        return json.dumps(self.json_report(reports), indent=2)
