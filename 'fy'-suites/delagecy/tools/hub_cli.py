"""Hub CLI for delagecy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from delagecy.tools.registry import approve, load_registry, mark_removed, registered_fingerprints, register_hit, save_registry, tracker_markdown
from delagecy.tools.repo_paths import default_tracker_path, registry_path, repo_root
from delagecy.tools.scanner import scan


def _load_scan(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _print_help() -> None:
    print(
        "Delagecy legacy-governance CLI\n\n"
        "Commands:\n"
        "  scan            Scan for legacy surfaces.\n"
        "  new             Print unregistered scan hits.\n"
        "  register        Register one scan hit as reported.\n"
        "  approve         Mark a finding approved for removal.\n"
        "  mark-removed    Mark an approved finding removed after verification.\n"
        "  check           Gate: no unregistered hits and no removed residue.\n"
        "  export-tracker  Write legacy_removal_tracker.md.\n"
        "  policy          Print the hard removal rules.\n"
    )


def cmd_scan(args: argparse.Namespace) -> int:
    root = repo_root(start=Path.cwd())
    payload = scan(root, include=args.include, patterns=args.pattern)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(out.as_posix())
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    root = repo_root(start=Path.cwd())
    registry = load_registry(registry_path(root))
    known = registered_fingerprints(registry)
    payload = _load_scan(Path(args.scan_json))
    hits = [hit for hit in payload.get("hits", []) if hit.get("fingerprint") not in known]
    print(json.dumps({"unregistered_count": len(hits), "hits": hits}, indent=2, sort_keys=True))
    return 1 if hits and args.fail_on_new else 0


def cmd_register(args: argparse.Namespace) -> int:
    root = repo_root(start=Path.cwd())
    path = registry_path(root)
    registry = load_registry(path)
    payload = _load_scan(Path(args.scan_json))
    hit = next((row for row in payload.get("hits", []) if row.get("fingerprint") == args.fingerprint), None)
    if not isinstance(hit, dict):
        print(f"Unknown fingerprint in scan: {args.fingerprint}", file=sys.stderr)
        return 3
    row = register_hit(registry, hit, title=args.title, reported_to=args.reported_to or "")
    save_registry(path, registry)
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    root = repo_root(start=Path.cwd())
    path = registry_path(root)
    registry = load_registry(path)
    row = approve(registry, args.id, approved_by=args.approved_by, note=args.note)
    save_registry(path, registry)
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


def cmd_mark_removed(args: argparse.Namespace) -> int:
    root = repo_root(start=Path.cwd())
    path = registry_path(root)
    registry = load_registry(path)
    row = mark_removed(registry, args.id, verification=args.verification)
    save_registry(path, registry)
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    root = repo_root(start=Path.cwd())
    registry = load_registry(registry_path(root))
    payload = _load_scan(Path(args.scan_json))
    known = registered_fingerprints(registry)
    hits = payload.get("hits", [])
    unregistered = [hit for hit in hits if hit.get("fingerprint") not in known]
    active_fps = {str(hit.get("fingerprint")) for hit in hits}
    removed_residue = [
        row for row in registry.get("findings", [])
        if row.get("status") == "removed" and row.get("fingerprint") in active_fps
    ]
    approved_ui = [
        row for row in registry.get("findings", [])
        if row.get("status") == "approved_for_removal" and row.get("kind") == "ui"
    ]
    result = {
        "ok": not unregistered and not removed_residue,
        "unregistered_count": len(unregistered),
        "removed_residue_count": len(removed_residue),
        "approved_ui_pending_count": len(approved_ui),
        "discussion_required": [
            row for row in registry.get("findings", [])
            if row.get("status") == "blocked" or row.get("discussion_required")
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


def cmd_export_tracker(args: argparse.Namespace) -> int:
    root = repo_root(start=Path.cwd())
    registry = load_registry(registry_path(root))
    out = Path(args.out) if args.out else default_tracker_path(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(tracker_markdown(registry), encoding="utf-8")
    print(out.as_posix())
    return 0


def cmd_policy(_args: argparse.Namespace) -> int:
    print(
        "Delagecy policy:\n"
        "1. Register and report new legacy findings before removal.\n"
        "2. Remove only after explicit approval.\n"
        "3. Remove code, route, docs, tests, data, and UI residue together.\n"
        "4. Discuss blockers and integrity risks before continuing.\n"
        "5. Verify with scan + targeted tests before marking removed."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Delagecy legacy governance CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    p_scan = sub.add_parser("scan")
    p_scan.add_argument("--include", action="append", help="Repo-relative path to include; repeatable.")
    p_scan.add_argument("--pattern", action="append", help="Regex pattern; defaults to legacy terms.")
    p_scan.add_argument("--out")
    p_new = sub.add_parser("new")
    p_new.add_argument("--scan-json", required=True)
    p_new.add_argument("--fail-on-new", action="store_true")
    p_reg = sub.add_parser("register")
    p_reg.add_argument("--scan-json", required=True)
    p_reg.add_argument("--fingerprint", required=True)
    p_reg.add_argument("--title", required=True)
    p_reg.add_argument("--reported-to", default="")
    p_ap = sub.add_parser("approve")
    p_ap.add_argument("--id", required=True)
    p_ap.add_argument("--approved-by", required=True)
    p_ap.add_argument("--note", required=True)
    p_rm = sub.add_parser("mark-removed")
    p_rm.add_argument("--id", required=True)
    p_rm.add_argument("--verification", required=True)
    p_check = sub.add_parser("check")
    p_check.add_argument("--scan-json", required=True)
    p_export = sub.add_parser("export-tracker")
    p_export.add_argument("--out")
    sub.add_parser("policy")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help", "help"}:
        _print_help()
        return 0
    args = build_parser().parse_args(argv)
    try:
        return int(globals()[f"cmd_{args.command.replace('-', '_')}"](args))
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
