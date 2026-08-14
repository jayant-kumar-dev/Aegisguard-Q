"""
aegisguard_q.report
===================

Serialize a LeakageReport to JSON or a human-readable markdown risk report.
"""

from __future__ import annotations

import json

from .core import LeakageReport, LeakageClass


_RISK_LEVEL = {
    LeakageClass.AFFINE: "CRITICAL",
    LeakageClass.GENERIC: "HIGH",
    LeakageClass.PARTIAL: "MEDIUM",
    LeakageClass.BENT: "LOW",
}


def to_json(report: LeakageReport, indent: int = 2) -> str:
    return json.dumps(report.to_dict(), indent=indent)


def to_markdown(report: LeakageReport) -> str:
    risk = _RISK_LEVEL[report.leakage_class]
    lines = [
        "# AegisGuard-Q Leakage Report",
        "",
        f"- **Register size (n):** {report.n}",
        f"- **Leakage class:** {report.leakage_class.value}",
        f"- **Risk level:** {risk}",
        "",
        "## Spectral metrics",
        "",
        f"- Spectral Ambiguity Index (SAI): {report.sai}",
        f"- Residual ambiguity: {report.residual_ambiguity:.4f} bits",
        f"- Probability gap (Delta_prob): {report.delta_prob:.6f}",
        f"- Single-query exact-recovery probability: "
        f"{report.single_query_recovery_probability:.6f}",
        f"- Leakage entropy: {report.leakage_entropy:.4f} bits",
        f"- Nonlinearity Nl(g): {report.nonlinearity:.1f}",
        "",
        "## Classical usability",
        "",
        f"- Noise density (tau): {report.tau:.6f}",
        f"- Completeness bound |0.5 - tau| <= {report.completeness_bound:.6f} "
        f"(Theorem 3)",
        "",
        "## Attack cost",
        "",
    ]
    if report.query_complexity is not None:
        lines.append(
            f"- Estimated queries to recover secret: {report.query_complexity} "
            f"(Theorem 2)"
        )
    else:
        lines.append("- No unique-mode recovery (SAI > 1 or bent); see notes.")
    lines += ["", "## Notes", ""]
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)
