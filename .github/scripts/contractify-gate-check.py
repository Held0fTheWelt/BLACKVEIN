#!/usr/bin/env python3
"""
Contractify Gate Check Script
Compares PR contract audit against baseline and generates gate result.
"""

import json
import sys


def main():
    try:
        with open("'fy'-suites/contractify/reports/pr_contract_audit.json") as f:
            pr_audit = json.load(f)
    except FileNotFoundError:
        print("ERROR: PR audit not generated")
        sys.exit(1)

    failures = []

    # 1. Check for new contracts without relations
    pr_contracts = len(pr_audit.get("contracts", []))
    baseline_contracts = 60  # From CANONICAL_REPO_ROOT_AUDIT.md
    if pr_contracts > baseline_contracts:
        failures.append(
            f"New contracts added ({pr_contracts} vs {baseline_contracts} baseline). "
            "Ensure they relate to existing contracts."
        )

    # 2. Check for conflicts requiring human review
    conflicts = pr_audit.get("conflicts", [])
    unresolved_conflicts = [
        c for c in conflicts if c.get("requires_human_review")
    ]
    if unresolved_conflicts:
        failures.append(
            f"Found {len(unresolved_conflicts)} unresolved conflicts requiring human review. "
            "Must be escalated or documented."
        )

    # 3. Check confidence scores on runtime_authority contracts
    confidence_failures = []
    for contract in pr_audit.get("contracts", []):
        if contract.get("tier") == "runtime_authority":
            confidence = contract.get("confidence", 1.0)
            if confidence < 0.85:
                confidence_failures.append(
                    f"{contract.get('id')}: confidence {confidence:.2f}"
                )

    if confidence_failures:
        failures.append(
            f"Runtime authority contracts with confidence < 0.85: {', '.join(confidence_failures)}"
        )

    # Write results
    with open("contractify_gate_result.json", "w") as f:
        json.dump(
            {
                "passed": len(failures) == 0,
                "failures": failures,
                "summary": {
                    "contracts_found": pr_contracts,
                    "conflicts": len(conflicts),
                    "unresolved_conflicts": len(unresolved_conflicts),
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
