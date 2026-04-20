#!/usr/bin/env python3
"""Validate repo-relative paths referenced from Docify hub skills markdown.

Scans ``'fy'-suites/docify/superpowers/**/*.md`` for:

  - Markdown link targets ``](path)`` (skips http(s), mailto, bare fragments)
  - Inline repo paths in backticks: ``'fy'-suites/docify/...`` (optional legacy ``docify/...``) with a file suffix

Run from repository root:

  python "./'fy'-suites/docify/tools/validate_docify_skill_paths.py"

Exit 1 if any path is missing.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from fy_platform.core.project_resolver import resolve_project_root

DOCIFY_ROOT = Path(__file__).resolve().parents[1]
ROOT = resolve_project_root(start=Path(__file__), marker_text=None)
SCAN_ROOT = DOCIFY_ROOT / "superpowers"

LINK_RE = re.compile(r"\]\(([^)]+)\)")
BACKTICK_REPO_RE = re.compile(
    r"`(('fy'-suites/)?docify(?:/tools)?/[a-zA-Z0-9_./'-]+(?:\.(?:md|py|yaml|yml)|/))`"
)


def _should_skip_target(raw: str) -> bool:
    t = raw.strip()
    if not t or t.startswith("#"):
        return True
    if t.startswith(("http://", "https://", "mailto:", "vscode:", "data:")):
        return True
    return False


def _resolve(base_file: Path, target: str) -> Path:
    t = target.strip().split("#", 1)[0].strip()
    p = Path(t)
    if p.is_absolute():
        return p
    return (base_file.parent / t).resolve()


def _under_repo(path: Path) -> bool:
    try:
        path.relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def collect_paths(md_path: Path, text: str) -> list[tuple[str, str]]:
    """Return list of (kind, path_str_for_display) needing validation."""
    out: list[tuple[str, str]] = []
    for m in LINK_RE.finditer(text):
        raw = m.group(1)
        if _should_skip_target(raw):
            continue
        resolved = _resolve(md_path, raw)
        if not _under_repo(resolved):
            out.append(("link_escape", f"{md_path.relative_to(ROOT)}: {raw!r} -> {resolved}"))
            continue
        out.append(("link", str(resolved)))
    for m in BACKTICK_REPO_RE.finditer(text):
        raw = m.group(1).rstrip("/")
        if not raw:
            continue
        resolved = (ROOT / raw).resolve()
        if not _under_repo(resolved):
            out.append(("backtick_escape", f"{md_path.relative_to(ROOT)}: {raw!r}"))
            continue
        out.append(("backtick", str(resolved)))
    return out


def main() -> int:
    """Validate repo-relative targets referenced from Docify router skills."""
    if not SCAN_ROOT.is_dir():
        print(f"Missing {SCAN_ROOT}", file=sys.stderr)
        return 2

    errors: list[str] = []
    scanned = 0
    for md_path in sorted(SCAN_ROOT.rglob("*.md")):
        scanned += 1
        text = md_path.read_text(encoding="utf-8", errors="replace")
        for kind, ref in collect_paths(md_path, text):
            if kind.endswith("_escape"):
                errors.append(ref)
                continue
            p = Path(ref)
            if not p.exists():
                rel = md_path.relative_to(ROOT)
                errors.append(f"{rel}: missing {kind} target {p.relative_to(ROOT)}")

    if errors:
        print("Docify skill path validation failed:\n", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    print(f"OK: validated paths in {scanned} markdown file(s) under {SCAN_ROOT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
