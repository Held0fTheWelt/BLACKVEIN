#!/usr/bin/env python3
"""Polish goc.txt tail: join dialogue under character cues; split action into readable lines."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from format_goc_screenplay import (
    ACTION_AFTER_DIALOGUE_RE,
    is_character_cue,
    is_scene_heading,
    join_parts,
    split_sentences,
)


def emit_after_character(merged: str) -> list[str]:
    out: list[str] = []
    m = ACTION_AFTER_DIALOGUE_RE.match(merged.strip())
    if not m:
        return [merged.strip()]
    out.append(m.group(1).strip())
    if out and out[-1] != "":
        out.append("")
    out.extend(split_sentences(m.group(2).strip()))
    return out


def polish_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            if out and out[-1] != "":
                out.append("")
            i += 1
            continue

        if is_scene_heading(stripped):
            if out and out[-1] != "":
                out.append("")
            out.append(stripped)
            i += 1
            continue

        if is_character_cue(stripped) or stripped == "(MORE)":
            if out and out[-1] != "":
                out.append("")
            out.append(stripped)
            i += 1
            parts: list[str] = []
            while i < len(lines):
                nxt = lines[i].strip()
                if not nxt:
                    break
                if is_character_cue(lines[i]) or is_scene_heading(lines[i]) or nxt == "(MORE)":
                    break
                parts.append(nxt)
                i += 1
            if parts:
                out.extend(emit_after_character(join_parts(parts)))
            continue

        # Standalone action block.
        parts = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or is_character_cue(lines[i]) or is_scene_heading(lines[i]) or nxt == "(MORE)":
                break
            parts.append(nxt)
            i += 1
        if out and out[-1] != "":
            out.append("")
        out.extend(split_sentences(join_parts(parts)))

    while out and out[-1] == "":
        out.pop()
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    src = root / "resources" / "goc.txt"
    keep_through = 286
    lines = src.read_text(encoding="utf-8").splitlines()
    head = lines[:keep_through]
    tail = polish_lines(lines[keep_through:])
    src.write_text("\n".join(head + tail) + "\n", encoding="utf-8")
    print(f"Polished {src}: head {len(head)}, tail {len(tail)} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
