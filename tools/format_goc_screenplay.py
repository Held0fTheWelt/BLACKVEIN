#!/usr/bin/env python3
"""Reformat resources/goc.txt: preserve corrected header, merge PDF line breaks, drop page numbers."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PAGE_RE = re.compile(r"^\s*\d+\.\s*$")
SCENE_RE = re.compile(
    r"^\s*\d*\s*(INT\.|EXT\.|INT/EXT\.|I/E\.)\s+",
    re.IGNORECASE,
)
CHAR_RE = re.compile(
    r"^[A-Z][A-Z0-9\s'\"().\-–—]+$",
)
ACTION_AFTER_DIALOGUE_RE = re.compile(
    r"^(.+?[.!?])\s+((?:She|He|They|The|At |In |On |From |While |After |Before |"
    r"Suddenly|Silence|A long |WE MOVE|CLOSE |WIDE |"
    r"[A-Z][A-Z]+(?:'s|'s)?\s).+)$",
    re.DOTALL,
)


def is_page_number(line: str) -> bool:
    return bool(PAGE_RE.match(line))


def is_scene_heading(line: str) -> bool:
    return bool(SCENE_RE.match(line.strip()))


def is_character_cue(line: str) -> bool:
    s = line.strip()
    if not s or s == "(MORE)":
        return False
    if s.startswith("(") and s.endswith(")"):
        return False
    if not CHAR_RE.match(s):
        return False
    if len(s) > 72:
        return False
    if s.endswith((".", "!", "?", ":", ";")):
        return False
    return True


def join_parts(parts: list[str]) -> str:
    if not parts:
        return ""
    out = parts[0]
    for part in parts[1:]:
        if out.endswith("-"):
            out = out[:-1] + part
        else:
            out = f"{out} {part}"
    return out


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def split_dialogue_action(text: str) -> list[tuple[str, str]]:
    """Return ('dialogue'|'action', text) chunks when stage direction follows speech."""
    text = text.strip()
    if not text:
        return []
    m = ACTION_AFTER_DIALOGUE_RE.match(text)
    if not m:
        return [("dialogue", text)]
    chunks: list[tuple[str, str]] = [("dialogue", m.group(1).strip())]
    rest = m.group(2).strip()
    for sentence in split_sentences(rest):
        chunks.append(("action", sentence))
    return chunks


def emit_action_lines(text: str) -> list[str]:
    return split_sentences(text)


def format_tail(lines: list[str]) -> list[str]:
    output: list[str] = []
    buffer: list[str] = []
    prev_kind: str | None = None

    def flush() -> None:
        nonlocal prev_kind
        if not buffer:
            return
        text = join_parts(buffer)
        buffer.clear()
        if prev_kind in {"character", "more"}:
            for kind, chunk in split_dialogue_action(text):
                if kind == "dialogue":
                    output.append(chunk)
                    prev_kind = "dialogue"
                else:
                    if output and output[-1] != "":
                        output.append("")
                    output.extend(emit_action_lines(chunk))
                    prev_kind = "action"
        else:
            if output and output[-1] != "":
                output.append("")
            output.extend(emit_action_lines(text))
            prev_kind = "action"

    def ensure_blank_before(kind: str) -> None:
        if not output:
            return
        if output[-1] != "" and kind in {"scene", "character"}:
            output.append("")

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if is_page_number(stripped):
            continue

        if not stripped:
            flush()
            prev_kind = "blank"
            if output and output[-1] != "":
                output.append("")
            continue

        if is_scene_heading(stripped):
            flush()
            ensure_blank_before("scene")
            output.append(stripped)
            prev_kind = "scene"
            continue

        if is_character_cue(stripped):
            flush()
            ensure_blank_before("character")
            output.append(stripped)
            prev_kind = "character"
            continue

        if stripped == "(MORE)":
            flush()
            output.append("(MORE)")
            prev_kind = "more"
            continue

        buffer.append(stripped)

    flush()
    return polish_orphan_contd(output)


def polish_orphan_contd(lines: list[str]) -> list[str]:
    """Drop CHARACTER (CONT'D) with no following dialogue before the next cue."""
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if (
            is_character_cue(line)
            and "(CONT" in line
            and i + 1 < len(lines)
            and lines[i + 1] == ""
            and i + 2 < len(lines)
            and is_character_cue(lines[i + 2])
        ):
            i += 2
            continue
        out.append(line)
        i += 1
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    src = root / "resources" / "goc.txt"
    keep_through = 286

    lines = src.read_text(encoding="utf-8").splitlines()
    head = lines[:keep_through]
    tail = lines[keep_through:]
    body = format_tail(tail)

    while body and body[-1] == "":
        body.pop()

    out_lines = head + body
    src.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    print(f"Wrote {src}")
    print(f"  Kept lines 1–{keep_through}: {len(head)}")
    print(f"  Reformatted tail: {len(tail)} -> {len(body)} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
