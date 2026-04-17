#!/usr/bin/env python3
"""
Despaghettify Gate Check Script
Compares PR structural metrics against baseline and generates gate result.
"""

import json
import sys


def main():
    try:
        with open("'fy'-suites/despaghettify/baseline_metrics.json") as f:
            baseline = json.load(f)
    except FileNotFoundError:
        print("WARNING: Baseline not found, creating initial baseline")
        baseline = None

    try:
        with open("'fy'-suites/despaghettify/reports/pr_metrics_check.json") as f:
            pr_check = json.load(f)
    except FileNotFoundError:
        print("ERROR: PR metrics check not generated")
        sys.exit(1)

    warnings = []

    # Check for functions over 200 lines
    pr_long_functions = pr_check.get("summary", {}).get("functions_over_200_lines", 0)
    baseline_long_functions = 0
    if baseline:
        baseline_long_functions = baseline.get("summary", {}).get(
            "functions_over_200_lines", 0
        )

    if pr_long_functions > baseline_long_functions:
        new_long = pr_long_functions - baseline_long_functions
        warnings.append(
            f"New functions over 200 lines: {new_long} "
            f"(baseline: {baseline_long_functions}, PR: {pr_long_functions})"
        )

    # Check for nesting depth increase
    pr_max_nesting = pr_check.get("summary", {}).get("max_nesting_depth", 0)
    baseline_max_nesting = 0
    if baseline:
        baseline_max_nesting = baseline.get("summary", {}).get(
            "max_nesting_depth", 0
        )

    if pr_max_nesting > baseline_max_nesting:
        warnings.append(
            f"Max nesting depth increase: {pr_max_nesting} (baseline: {baseline_max_nesting})"
        )

    # Check for import cycle increase
    pr_cycles = pr_check.get("summary", {}).get("import_cycle_count", 0)
    baseline_cycles = 0
    if baseline:
        baseline_cycles = baseline.get("summary", {}).get("import_cycle_count", 0)

    if pr_cycles > baseline_cycles:
        new_cycles = pr_cycles - baseline_cycles
        warnings.append(
            f"New import cycles: {new_cycles} "
            f"(baseline: {baseline_cycles}, PR: {pr_cycles})"
        )

    with open("despaghettify_gate_result.json", "w") as f:
        json.dump(
            {
                "passed": len(warnings) == 0,
                "warnings": warnings,
                "summary": {
                    "pr_long_functions": pr_long_functions,
                    "baseline_long_functions": baseline_long_functions,
                    "pr_max_nesting": pr_max_nesting,
                    "baseline_max_nesting": baseline_max_nesting,
                    "pr_cycles": pr_cycles,
                    "baseline_cycles": baseline_cycles,
                },
            },
            f,
            indent=2,
        )

    if warnings:
        print("GATE_RESULT: ADVISORY (warnings present)")
        for warning in warnings:
            print(f"  - {warning}")
        sys.exit(0)  # Advisory gate does not block
    else:
        print("GATE_RESULT: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
