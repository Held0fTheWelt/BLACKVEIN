#!/usr/bin/env python3
"""Fail if scene_id→guidance mapping is duplicated outside the canonical module (ADR-0003).

Run from repo root: python tools/verify_goc_scene_identity_single_source.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Unique sentinel substring of the canonical dict (must only appear in goc_scene_identity.py)
_SENTINEL = '"courtesy": "phase_1_polite_opening"'


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    hits: list[str] = []
    for path in root.rglob("*.py"):
        if "venv" in path.parts or ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        if ".cursor" in path.parts or "node_modules" in path.parts:
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if rel.parts[:1] == (".git",):
            continue
        if path.name == "goc_scene_identity.py" and rel.parts[0] == "ai_stack":
            continue
        if rel.parts == ("tools", "verify_goc_scene_identity_single_source.py"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if _SENTINEL in text:
            hits.append(str(rel))
    if hits:
        print("Forbidden duplicate GoC scene→guidance mapping literal in:", file=sys.stderr)
        for h in hits:
            print(f"  {h}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
