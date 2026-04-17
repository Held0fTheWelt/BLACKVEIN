#!/usr/bin/env python3
"""
Docify Gate Check Script
Compares PR docstring audit against baseline and generates gate result.
"""

import json
import sys


def main():
    try:
        with open("'fy'-suites/docify/baseline_docstring_coverage.json") as f:
            baseline = json.load(f)
    except FileNotFoundError:
        print("WARNING: Baseline not found, skipping comparison")
        baseline = None

    try:
        with open("'fy'-suites/docify/reports/pr_docstring_audit.json") as f:
            pr_audit = json.load(f)
    except FileNotFoundError:
        print("ERROR: PR audit not generated")
        sys.exit(1)

    failures = []

    # Check for parse errors (must be zero or same as baseline)
    pr_parse_errors = len(pr_audit.get("parse_errors", []))
    baseline_parse_errors = 0
    if baseline:
        baseline_parse_errors = len(baseline.get("parse_errors", []))

    if pr_parse_errors > baseline_parse_errors:
        new_errors = pr_parse_errors - baseline_parse_errors
        failures.append(
            f"New parse errors introduced: {new_errors} "
            f"(baseline: {baseline_parse_errors}, PR: {pr_parse_errors})"
        )

    # Check for docstring coverage degradation
    pr_findings = len(pr_audit.get("findings", []))
    baseline_findings = 0
    if baseline:
        baseline_findings = len(baseline.get("findings", []))

    if pr_findings > baseline_findings:
        new_findings = pr_findings - baseline_findings
        failures.append(
            f"Docstring coverage degraded: {new_findings} new findings "
            f"(baseline: {baseline_findings}, PR: {pr_findings})"
        )

    # Check for files with findings increase
    pr_files_with_findings = len(pr_audit.get("files_with_findings", []))
    baseline_files_with_findings = 0
    if baseline:
        baseline_files_with_findings = len(baseline.get("files_with_findings", []))

    if pr_files_with_findings > baseline_files_with_findings:
        new_files = pr_files_with_findings - baseline_files_with_findings
        failures.append(
            f"New files with missing docstrings: {new_files} "
            f"(baseline: {baseline_files_with_findings}, PR: {pr_files_with_findings})"
        )

    with open("docify_gate_result.json", "w") as f:
        json.dump(
            {
                "passed": len(failures) == 0,
                "failures": failures,
                "summary": {
                    "pr_findings": pr_findings,
                    "baseline_findings": baseline_findings,
                    "pr_parse_errors": pr_parse_errors,
                    "baseline_parse_errors": baseline_parse_errors,
                    "pr_files_with_findings": pr_files_with_findings,
                    "baseline_files_with_findings": baseline_files_with_findings,
                },
            },
            f,
            indent=2,
        )

    if failures:
        print("GATE_RESULT: FAIL")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print("GATE_RESULT: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
