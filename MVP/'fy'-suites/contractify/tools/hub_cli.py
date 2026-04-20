"""Contractify hub CLI — discover, audit (discovery + drift), JSON reports."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from fy_platform.core.artifact_envelope import build_envelope, write_envelope
from fy_platform.core.manifest import load_manifest
from contractify.tools.audit_pipeline import build_discover_payload, run_audit
from contractify.tools.repo_paths import repo_root

SUITE_VERSION = "0.1.0"


def _base_findings_from_payload(payload: dict) -> tuple[list[dict], list[dict]]:
    """Project contractify-specific payload into suite-neutral finding/evidence summaries."""
    findings: list[dict] = []
    evidence: list[dict] = []
    for d in payload.get("drift_findings", []):
        summary = str(d.get("summary", "")).strip()
        if not summary:
            continue
        findings.append(
            {
                "id": d.get("id", "unknown"),
                "suite": "contractify",
                "category": d.get("drift_class", "drift"),
                "severity": d.get("severity", "medium"),
                "confidence": float(d.get("confidence", 0.0)),
                "summary": summary,
                "scope": "repository",
                "references": d.get("evidence_sources", []),
            }
        )
        for src in d.get("evidence_sources", []):
            evidence.append({"kind": "source", "source_path": str(src), "deterministic": bool(d.get("deterministic", False))})
    for c in payload.get("conflicts", []):
        summary = str(c.get("summary", "")).strip()
        if not summary:
            continue
        findings.append(
            {
                "id": c.get("id", "unknown"),
                "suite": "contractify",
                "category": c.get("classification", "conflict"),
                "severity": c.get("severity", "medium"),
                "confidence": float(c.get("confidence", 0.0)),
                "summary": summary,
                "scope": "repository",
                "references": c.get("sources", []),
            }
        )
        for src in c.get("sources", []):
            evidence.append({"kind": "source", "source_path": str(src), "deterministic": not bool(c.get("requires_human_review", True))})
    return findings, evidence


def _write_deprecation_markdown(path: Path, deprecations: list[dict[str, str]]) -> None:
    if not deprecations:
        return
    lines = ["# Deprecations", ""]
    for item in deprecations:
        lines.append(f"- `{item.get('id', 'unknown')}`: {item.get('message', '')}")
        repl = item.get("replacement", "").strip()
        if repl:
            lines.append(f"  - replacement: `{repl}`")
        target = item.get("removal_target", "").strip()
        if target:
            lines.append(f"  - removal_target: `{target}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    manifest, _warnings = load_manifest(root)
    deprecations: list[dict[str, str]] = []
    if manifest is None:
        msg = "No fy-manifest.yaml detected; Contractify is running in legacy fallback mode."
        print(f"DEPRECATION: {msg}", file=sys.stderr)
        deprecations.append(
            {
                "id": "CONTRACTIFY-LEGACY-FALLBACK-001",
                "message": msg,
                "replacement": "Run fy-platform bootstrap and configure suites.contractify.openapi",
                "removal_target": "wave-2",
            }
        )
    payload = build_discover_payload(root, max_contracts=args.max_contracts)
    text = json.dumps(payload, indent=2)
    if args.out:
        out = (root / args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        _write_deprecation_markdown(out.with_suffix(out.suffix + ".deprecations.md"), deprecations)
    if not args.quiet:
        print(text)
    if args.envelope_out:
        findings, evidence = _base_findings_from_payload(payload)
        env = build_envelope(
            suite="contractify",
            suite_version=SUITE_VERSION,
            payload=payload,
            manifest_ref="fy-manifest.yaml",
            deprecations=deprecations,
            findings=findings,
            evidence=evidence,
            stats=payload.get("stats", {}),
        )
        env_out = Path(args.envelope_out)
        if not env_out.is_absolute():
            env_out = root / env_out
        write_envelope(env_out, env)
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    root = repo_root()
    manifest, _warnings = load_manifest(root)
    deprecations: list[dict[str, str]] = []
    if manifest is None:
        msg = "No fy-manifest.yaml detected; Contractify is running in legacy fallback mode."
        print(f"DEPRECATION: {msg}", file=sys.stderr)
        deprecations.append(
            {
                "id": "CONTRACTIFY-LEGACY-FALLBACK-001",
                "message": msg,
                "replacement": "Run fy-platform bootstrap and configure suites.contractify.openapi",
                "removal_target": "wave-2",
            }
        )
    payload = run_audit(root, max_contracts=args.max_contracts)
    text = json.dumps(payload, indent=2)
    if args.out:
        out = (root / args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        _write_deprecation_markdown(out.with_suffix(out.suffix + ".deprecations.md"), deprecations)
    if not args.quiet or not args.out:
        print(text)
    if args.envelope_out:
        findings, evidence = _base_findings_from_payload(payload)
        env = build_envelope(
            suite="contractify",
            suite_version=SUITE_VERSION,
            payload=payload,
            manifest_ref="fy-manifest.yaml",
            deprecations=deprecations,
            findings=findings,
            evidence=evidence,
            stats=payload.get("stats", {}),
        )
        env_out = Path(args.envelope_out)
        if not env_out.is_absolute():
            env_out = root / env_out
        write_envelope(env_out, env)
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
    p_disc.add_argument("--envelope-out", default="", help="Optional path for shared envelope output JSON")
    p_disc.set_defaults(func=cmd_discover)

    p_audit = sub.add_parser("audit", help="Discovery + drift + conflicts")
    p_audit.add_argument("--json", action="store_true", help="Emit JSON")
    p_audit.add_argument("--out", default="", help="Repo-relative JSON output path")
    p_audit.add_argument("--max-contracts", type=int, default=30)
    p_audit.add_argument("--quiet", action="store_true", help="When --out set, skip stdout")
    p_audit.add_argument("--envelope-out", default="", help="Optional path for shared envelope output JSON")
    p_audit.set_defaults(func=cmd_audit)

    p_self = sub.add_parser("self-check", help="Integration sanity audit")
    p_self.add_argument("--json", action="store_true", help="Emit JSON")
    p_self.add_argument("--out", default="")
    p_self.add_argument("--max-contracts", type=int, default=30)
    p_self.add_argument("--quiet", action="store_true")
    p_self.add_argument("--envelope-out", default="", help="Optional path for shared envelope output JSON")
    p_self.set_defaults(func=cmd_self_check)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
