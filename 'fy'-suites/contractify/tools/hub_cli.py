"""Contractify hub CLI — discover, audit (discovery + drift), JSON reports."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from contractify.tools.audit_pipeline import run_audit
from contractify.tools.discovery import discover_contracts_and_projections
from contractify.tools.models import automation_tier, serialise
from contractify.tools.repo_paths import repo_root


def _print_global_help() -> None:
    print(
        "Contractify hub CLI\n\n"
        "Commands:\n"
        "  discover   Emit discovered contracts/projections/relations (JSON).\n"
        "  audit      Full audit: discovery + drift + conflicts + actionable units (JSON).\n"
        "  self-check Run audit scoped to fy-suite integration sanity (same as audit for now).\n\n"
        "Examples:\n"
        "  python -m contractify.tools discover --json --out \"'fy'-suites/contractify/reports/contract_discovery.json\"\n"
        "  python -m contractify.tools audit --json --out \"'fy'-suites/contractify/reports/contract_audit.json\"\n"
    )


def cmd_discover(args: argparse.Namespace) -> int:
    root = repo_root()
    contracts, projections, relations = discover_contracts_and_projections(
        root,
        max_contracts=args.max_contracts,
    )
    payload = {
        "contracts": [serialise(c) for c in contracts],
        "projections": [serialise(p) for p in projections],
        "relations": [serialise(r) for r in relations],
        "automation_tiers_sample": {
            "0.95": automation_tier(0.95),
            "0.75": automation_tier(0.75),
            "0.4": automation_tier(0.4),
        },
    }
    text = json.dumps(payload, indent=2)
    if args.out:
        out = (root / args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    if not args.quiet:
        print(text)
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    root = repo_root()
    payload = run_audit(root, max_contracts=args.max_contracts)
    text = json.dumps(payload, indent=2)
    if args.out:
        out = (root / args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    if not args.quiet or not args.out:
        print(text)
    return 0


def cmd_self_check(args: argparse.Namespace) -> int:
    """Narrow pass: reuse full audit (suite is small); consumers grep actionable_units."""
    return cmd_audit(args)


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        _print_global_help()
        return 0

    parser = argparse.ArgumentParser(description="Contractify repository contract governance CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_disc = sub.add_parser("discover", help="Discovery-only JSON")
    p_disc.add_argument("--json", action="store_true", help="Emit JSON (always on for discover)")
    p_disc.add_argument("--out", default="", help="Repo-relative JSON output path")
    p_disc.add_argument("--max-contracts", type=int, default=30, help="Phase-1 discovery ceiling")
    p_disc.add_argument("--quiet", action="store_true", help="When --out set, skip stdout")
    p_disc.set_defaults(func=cmd_discover)

    p_audit = sub.add_parser("audit", help="Discovery + drift + conflicts")
    p_audit.add_argument("--json", action="store_true", help="Emit JSON")
    p_audit.add_argument("--out", default="", help="Repo-relative JSON output path")
    p_audit.add_argument("--max-contracts", type=int, default=30)
    p_audit.add_argument("--quiet", action="store_true", help="When --out set, skip stdout")
    p_audit.set_defaults(func=cmd_audit)

    p_self = sub.add_parser("self-check", help="Integration sanity audit")
    p_self.add_argument("--json", action="store_true", help="Emit JSON")
    p_self.add_argument("--out", default="")
    p_self.add_argument("--max-contracts", type=int, default=30)
    p_self.add_argument("--quiet", action="store_true")
    p_self.set_defaults(func=cmd_self_check)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
