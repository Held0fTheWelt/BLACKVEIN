#!/usr/bin/env python3
"""Fail if legacy hardcoded locale strings reappear in runtime shell paths (ADR-0037 guard)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "world-engine" / "app" / "story_runtime" / "manager.py",
    ROOT / "ai_stack" / "langgraph" / "langgraph_runtime_executor.py",
]
# Phrases that previously lived inline and must now come only from content/modules/.../locale/
BANNED = [
    re.compile(r"NPC am Zug"),
    re.compile(r"Du spielst:"),
    re.compile(r"Alle für die Spielerin"),
    re.compile(r"SICHTBARER DIALOG \(spoken_lines"),
]


def main() -> int:
    bad: list[str] = []
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        for pat in BANNED:
            if pat.search(text):
                bad.append(f"{path.relative_to(ROOT)}: matched {pat.pattern!r}")
    if bad:
        print("Locale drift check failed:\n" + "\n".join(bad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
