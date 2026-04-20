"""Fy platform bootstrap CLI."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import yaml

from fy_platform.core.manifest import load_manifest, manifest_path
from fy_platform.core.project_resolver import resolve_project_root


def _detect_roots(repo: Path) -> dict[str, list[str]]:
    candidates = {
        "source": ["backend", "world-engine", "ai_stack", "story_runtime_core", "src"],
        "docs": ["docs"],
    }
    out: dict[str, list[str]] = {"source": [], "docs": []}
    for rel in candidates["source"]:
        if (repo / rel).exists():
            out["source"].append(rel)
    for rel in candidates["docs"]:
        if (repo / rel).exists():
            out["docs"].append(rel)
    return out


def _manifest_stub(repo: Path) -> dict:
    roots = _detect_roots(repo)
    return {
        "manifestVersion": 1,
        "platformVersion": "0.x",
        "compat": "transitional",
        "generatedBy": {
            "tool": "fy-platform bootstrap",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "project": {
            "id": repo.name.lower().replace(" ", "-"),
            "name": repo.name,
            "repository_type": "python-project",
        },
        "roots": roots,
        "suites": {
            "docify": {
                "roots": roots["source"] or ["src"],
            },
            "postmanify": {
                "openapi": "docs/api/openapi.yaml",
                "out_master": "postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json",
                "suites_dir": "postman/suites",
            },
            "despaghettify": {
                "scan_roots": roots["source"] or ["src"],
            },
            "contractify": {
                "openapi": "docs/api/openapi.yaml",
            },
        },
    }


def cmd_bootstrap(args: argparse.Namespace) -> int:
    if args.project_root:
        repo = Path(args.project_root).expanduser().resolve()
    else:
        repo = resolve_project_root(start=Path(__file__), env_var="FY_PLATFORM_PROJECT_ROOT", marker_text=None)
    path = manifest_path(repo)
    if path.is_file() and not args.force:
        print(json.dumps({"ok": False, "reason": "manifest_exists", "path": str(path.relative_to(repo))}, indent=2))
        return 2
    payload = _manifest_stub(repo)
    text = yaml.safe_dump(payload, sort_keys=False)
    path.write_text(text, encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(path.relative_to(repo))}, indent=2))
    return 0


def cmd_validate(_args: argparse.Namespace) -> int:
    if _args.project_root:
        repo = Path(_args.project_root).expanduser().resolve()
    else:
        repo = resolve_project_root(start=Path(__file__), env_var="FY_PLATFORM_PROJECT_ROOT", marker_text=None)
    _manifest, warnings = load_manifest(repo)
    if warnings:
        print(json.dumps({"ok": False, "warnings": warnings}, indent=2))
        return 2
    print(json.dumps({"ok": True, "manifest": "fy-manifest.yaml"}, indent=2))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fy platform utilities.")
    sub = parser.add_subparsers(dest="command", required=True)
    p_boot = sub.add_parser("bootstrap", help="Generate fy-manifest.yaml with conservative defaults.")
    p_boot.add_argument("--force", action="store_true", help="Overwrite existing manifest.")
    p_boot.add_argument("--project-root", default="", help="Optional explicit project root path.")
    p_boot.set_defaults(func=cmd_bootstrap)
    p_val = sub.add_parser("validate-manifest", help="Validate fy-manifest.yaml shape minimally.")
    p_val.add_argument("--project-root", default="", help="Optional explicit project root path.")
    p_val.set_defaults(func=cmd_validate)
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))

