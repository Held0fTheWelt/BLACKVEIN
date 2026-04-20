#!/usr/bin/env python3
"""Copy Postmanify hub skills into `.cursor/skills/` for Cursor project skill discovery."""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

_tools = Path(__file__).resolve().parent
_hub = _tools.parent
_grand = _hub.parent
_ins = str(_grand if _grand.name == "'fy'-suites" else _hub.parent)
if _ins not in sys.path:
    sys.path.insert(0, _ins)

from postmanify.tools.repo_paths import postmanify_hub_dir, repo_root

ROOT = repo_root()
SRC_ROOT = postmanify_hub_dir(ROOT) / "superpowers"
DST_ROOT = ROOT / ".cursor" / "skills"


def sync(*, check_only: bool) -> int:
    """
    Implement ``sync`` for the surrounding module workflow.

    Module context: ``'fy'-suites/postmanify/tools/sync_postmanify_skills.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Args:
        check_only: Check Only for this call. Declared type: ``bool``. (keyword-only)

    Returns:
        Value typed as ``int`` for downstream use.

    """
    if not SRC_ROOT.is_dir():
        print(f"Missing source: {SRC_ROOT}", file=sys.stderr)
        return 2
    skill_dirs = [p for p in SRC_ROOT.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()]
    if not skill_dirs:
        print(f"No */SKILL.md under {SRC_ROOT}", file=sys.stderr)
        return 2

    mismatches: list[str] = []
    for src_dir in sorted(skill_dirs, key=lambda p: p.name):
        name = src_dir.name
        src = src_dir / "SKILL.md"
        dst = DST_ROOT / name / "SKILL.md"
        if check_only:
            if not dst.is_file():
                mismatches.append(f"missing {dst.relative_to(ROOT)}")
            elif not filecmp.cmp(src, dst, shallow=False):
                mismatches.append(f"differ {dst.relative_to(ROOT)}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"synced {name} -> {dst.relative_to(ROOT)}")

    if check_only:
        if mismatches:
            print("Skill sync drift:\n" + "\n".join(mismatches), file=sys.stderr)
            return 1
        print("OK: .cursor/skills matches postmanify hub superpowers/")
        return 0
    return 0


def main() -> int:
    """
    Implement ``main`` for the surrounding module workflow.

    Module context: ``'fy'-suites/postmanify/tools/sync_postmanify_skills.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Returns:
        Value typed as ``int`` for downstream use.

    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if copies are missing or differ from canonical SKILL.md files.",
    )
    args = ap.parse_args()
    return sync(check_only=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
