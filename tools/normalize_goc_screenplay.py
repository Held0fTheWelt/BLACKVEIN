#!/usr/bin/env python3
"""
Normalize resources/goc.txt to consistent screenplay layout.

Rules (aligned with the corrected opening):
- Scene headings on their own line; blank line before (except file start).
- Action: one sentence per line; merge broken PDF wraps; blank line before new action run after dialogue.
- Character cue on its own line; blank line before cue.
- Dialogue: one speech block per turn (joined lines); parentheticals and (MORE) stay on own lines.
- Orphan lines after a cue are merged into that speech until clear stage direction or next cue.
- Page numbers (e.g. "8.") removed.
"""

from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

PAGE_RE = re.compile(r"^\s*\d+\.\s*$")
SCENE_RE = re.compile(
    r"^\s*\d*\s*(INT\.|EXT\.|INT/EXT\.|I/E\.)\s+",
    re.IGNORECASE,
)
CHAR_RE = re.compile(r"^[A-Z][A-Z0-9\s'\"().\-–—]+$")
PAREN_RE = re.compile(r"^\([^)]+\)\s*$")
WRAP_WIDTH = 92

ACTION_START_RE = re.compile(
    r"^(?:"
    r"They |The |At the |In the |On the |From |While |After |Before |"
    r"Suddenly|Silence\.|A long |WE MOVE |CLOSE |WIDE |Everyone |Pretty soon|"
    r"[A-Z][A-Z][A-Z\s]{2,}(?:enters|leaves|walks|looks|hands|opens|tears|drinks|"
    r"stops|forces|crosses|whacks|breaks|rises|puts|starts|goes|takes|vomits|"
    r"hands|follows|crosses back)|"
    r"[A-Z][A-Z\s]+'s cell phone|"
    r"[A-Z][a-z]+ (?:walks|enters|leaves|looks|opens|hands|crosses|drifts|vomits|"
    r"suddenly|tears|puts|starts toward|breaks down)"
    r")",
    re.IGNORECASE,
)
SHE_HE_ACTION_RE = re.compile(
    r"^She (?:starts|walks|crosses|breaks|whacks|hands|prints|enters|leaves|tears|puts|goes|"
    r"takes|vomits|drinks|opens|forces|rises)\b",
    re.IGNORECASE,
)
SHE_HE_DIALOGUE_RE = re.compile(
    r"^She (?:doesn'?t|didn'?t|isn'?t|wasn'?t|wouldn'?t|couldn'?t|hasn'?t|won'?t)\b",
    re.IGNORECASE,
)
HE_ACTION_RE = re.compile(
    r"^He (?:starts|walks|crosses|breaks|whacks|hands|enters|leaves|tears|puts|goes|takes|"
    r"vomits|drinks|opens|forces|rises)\b",
    re.IGNORECASE,
)
LEADING_DIALOGUE_ACTION_RE = re.compile(
    r"^(.+?[.!?])\s+((?:Once |The |They |Pretty |Everyone |A |At the |In the |On the |"
    r"From |While |After |Before |Suddenly|Silence|A long |WE MOVE |CLOSE |WIDE |"
    r"She (?:starts|walks|crosses|breaks|whacks|hands|prints|enters|leaves|tears|puts|"
    r"vomits|drinks|opens|forces|rises|makes)|"
    r"He (?:starts|walks|crosses|breaks|whacks|hands|enters|leaves|tears|puts|vomits|"
    r"drinks|opens|forces|rises|makes)).+)$",
    re.DOTALL,
)
NAMED_ACTION_RE = re.compile(
    r"^[A-Z][A-Z\s]+\s+(?:enters|walks|reads|prints|hands|leaves|puts|takes|crosses|"
    r"opens|vomits|drinks|follows|forces|rises|starts|looks|whacks|breaks|hands|"
    r"writes|seated|standing)\b",
    re.IGNORECASE,
)
CONTINUATION_RE = re.compile(r"^['\u2019][A-Za-z]")
COMBINED_CUE_RE = re.compile(r"^([A-Z][A-Z0-9\s'\"().\-–—]+?)\s{2,}(.+)$")
CUE_THEN_DIALOGUE_RE = re.compile(
    r"^([A-Z][A-Z0-9\s'\"().\-–—]+?(?:\(CONT['\u2019]D\))?)\s+(.+)$",
)


def is_page_number(line: str) -> bool:
    return bool(PAGE_RE.match(line))


def is_scene_heading(line: str) -> bool:
    return bool(SCENE_RE.match(line.strip()))


def is_parenthetical(line: str) -> bool:
    s = line.strip()
    return bool(PAREN_RE.match(s)) or (s.startswith("(") and ")" in s and len(s) < 120)


def is_character_cue(line: str) -> bool:
    s = line.strip()
    if not s or s == "(MORE)":
        return False
    if is_parenthetical(s):
        return False
    if not CHAR_RE.match(s):
        return False
    if len(s) > 72:
        return False
    if s.endswith((".", "!", "?", ":", ";")):
        return False
    return True


def preprocess_lines(lines: list[str]) -> list[str]:
    """Join PDF-broken lines (apostrophe splits, NAME / verb action lines)."""
    out: list[str] = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        i += 1
        if not s:
            if out and out[-1] != "":
                out.append("")
            continue
        if out and out[-1] != "" and s.startswith(": "):
            out[-1] = out[-1].rstrip() + s
            continue
        # Repair broken ALL-CAPS slug lines at the very start (e.g. WIDE / ANGLE / VIEW:).
        if (
            len(out) < 12
            and out
            and out[-1] != ""
            and re.match(r"^[A-Z][A-Z\s]*$", out[-1])
            and re.match(r"^[A-Z]", s)
            and not is_scene_heading(s)
        ):
            out[-1] = f"{out[-1].rstrip()} {s}"
            continue
        if out and out[-1] != "" and CONTINUATION_RE.match(s):
            out[-1] = out[-1].rstrip() + s
            continue
        if out and out[-1].rstrip().endswith("(CONT"):
            out[-1] = out[-1].rstrip() + s
            continue
        if (
            out
            and out[-1] != ""
            and is_character_cue(out[-1])
            and re.match(r"^['\u2019\ufffd]?s\b", s)
        ):
            tail = re.sub(r"^['\u2019\ufffd]", "'", s)
            out[-1] = out[-1].rstrip() + tail
            continue
        if (
            out
            and out[-1] != ""
            and is_character_cue(out[-1])
            and s.startswith("(CONT")
        ):
            out[-1] = f"{out[-1].rstrip()} {s}"
            continue
        if (
            is_character_cue(s)
            and i < len(lines)
            and lines[i].strip()
            and re.match(r"^[a-z]", lines[i].strip())
        ):
            nxt = lines[i].strip()
            combined = f"{s} {nxt}"
            if NAMED_ACTION_RE.match(combined):
                out.append(combined)
                i += 1
                continue
        out.append(s)
    return out


def split_combined_cue(line: str) -> tuple[str | None, str | None]:
    """If line is 'MICHAEL (CONT'D)  dialogue…', return (cue, dialogue)."""
    s = line.strip()
    if NAMED_ACTION_RE.match(s):
        return None, s
    if is_character_cue(s):
        return s, None
    m = COMBINED_CUE_RE.match(s)
    if m and is_character_cue(m.group(1).strip()):
        return m.group(1).strip(), m.group(2).strip()
    m = CUE_THEN_DIALOGUE_RE.match(s)
    if m and is_character_cue(m.group(1).strip()):
        return m.group(1).strip(), m.group(2).strip()
    return None, s


def split_leading_dialogue(line: str) -> tuple[str | None, str]:
    s = line.strip()
    m = LEADING_DIALOGUE_ACTION_RE.match(s)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m2 = re.match(
        r"^(.+?[.!?])\s+((?:She|He) (?:makes|prints|hands|starts|walks|crosses|breaks|"
        r"whacks|enters|leaves|tears|puts|vomits|drinks|opens|forces|rises).+)$",
        s,
        re.IGNORECASE,
    )
    if m2:
        return m2.group(1).strip(), m2.group(2).strip()
    return None, s


def split_dialogue_then_action(line: str) -> tuple[str | None, str | None]:
    lead, rest = split_leading_dialogue(line)
    if lead:
        return lead, rest
    return None, None


def is_action_line(line: str, *, in_speech: bool) -> bool:
    s = line.strip()
    if not s:
        return False
    if is_scene_heading(s) or is_character_cue(s) or s == "(MORE)":
        return False
    if SHE_HE_DIALOGUE_RE.match(s):
        return False
    if SHE_HE_ACTION_RE.match(s) or HE_ACTION_RE.match(s):
        return True
    if ACTION_START_RE.match(s):
        return True
    if not in_speech:
        if re.match(r"^[A-Z][a-z]", s) and not s.startswith(('"', "'")):
            if re.search(r"\b(walks|enters|leaves|looks|hands|opens|crosses|drifts)\b", s):
                return True
    return False


def join_parts(parts: list[str]) -> str:
    if not parts:
        return ""
    out = parts[0]
    for part in parts[1:]:
        if out.endswith("-"):
            out = out[:-1] + part
        else:
            out = f"{out} {part}"
    return re.sub(r"\s+", " ", out).strip()


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    merged: list[str] = []
    for part in parts:
        if merged and merged[-1].rstrip().endswith(("WE MOVE UP", "CLOSE ON", "CLOSE", "WIDE")):
            merged[-1] = f"{merged[-1]} {part}"
        elif merged and merged[-1] == "WE MOVE":
            merged[-1] = f"{merged[-1]} {part}"
        else:
            merged.append(part)
    return merged


def wrap_dialogue(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= WRAP_WIDTH:
        return [text]
    return textwrap.wrap(
        text,
        width=WRAP_WIDTH,
        break_long_words=False,
        break_on_hyphens=False,
    )


def emit_blank_before(output: list[str]) -> None:
    if output and output[-1] != "":
        output.append("")


def normalize(lines: list[str]) -> list[str]:
    output: list[str] = []
    mode = "action"  # action | speech
    action_buf: list[str] = []
    speech: list[tuple[str, str]] = []  # (kind, text) kind: text|paren|more

    def flush_action() -> None:
        nonlocal action_buf
        if not action_buf:
            return
        merged = join_parts(action_buf)
        action_buf = []
        sentences = split_sentences(merged)
        if not sentences:
            return
        emit_blank_before(output)
        output.extend(sentences)

    def flush_speech() -> None:
        nonlocal speech, mode
        if not speech:
            mode = "action"
            return
        text_run: list[str] = []
        for kind, payload in speech:
            if kind == "more":
                if text_run:
                    output.extend(wrap_dialogue(join_parts(text_run)))
                    text_run = []
                output.append("(MORE)")
                continue
            if kind == "paren":
                if text_run:
                    output.extend(wrap_dialogue(join_parts(text_run)))
                    text_run = []
                output.append(payload)
                continue
            if payload.strip():
                text_run.append(payload)
        if text_run:
            joined = join_parts(text_run)
            lead, rest = split_dialogue_then_action(joined)
            if lead and rest:
                output.extend(wrap_dialogue(lead))
                emit_blank_before(output)
                output.extend(split_sentences(rest))
            else:
                output.extend(wrap_dialogue(joined))
        speech = []
        mode = "action"

    def ingest_content(stripped: str) -> None:
        nonlocal mode, action_buf, speech
        if mode == "speech":
            lead, rest = split_dialogue_then_action(stripped)
            if lead and rest:
                speech.append(("text", lead))
                flush_speech()
                action_buf = [rest]
                mode = "action"
                return
            if is_action_line(stripped, in_speech=True):
                flush_speech()
                action_buf = [stripped]
                mode = "action"
                return
            speech.append(("text", stripped))
            return
        action_buf.append(stripped)

    for raw in lines:
        stripped = raw.strip()
        if is_page_number(stripped):
            continue
        if not stripped:
            continue

        cue, tail = split_combined_cue(stripped)
        if cue:
            flush_speech()
            flush_action()
            emit_blank_before(output)
            output.append(cue)
            speech = []
            mode = "speech"
            if tail:
                ingest_content(tail)
            continue

        if is_scene_heading(stripped):
            flush_speech()
            flush_action()
            emit_blank_before(output)
            output.append(stripped)
            mode = "action"
            continue

        if is_character_cue(stripped):
            flush_speech()
            flush_action()
            emit_blank_before(output)
            output.append(stripped)
            speech = []
            mode = "speech"
            continue

        if stripped == "(MORE)":
            if mode != "speech":
                flush_action()
                mode = "speech"
            speech.append(("more", stripped))
            continue

        if is_parenthetical(stripped):
            if mode != "speech":
                flush_action()
                mode = "speech"
            speech.append(("paren", stripped))
            continue

        ingest_content(stripped)

    flush_speech()
    flush_action()

    cleaned: list[str] = []
    i = 0
    while i < len(output):
        line = output[i]
        if (
            is_character_cue(line)
            and i + 1 < len(output)
            and output[i + 1] == ""
            and i + 2 < len(output)
            and output[i + 2].strip()
            and not is_character_cue(output[i + 2])
            and not is_scene_heading(output[i + 2])
        ):
            cleaned.append(line)
            i += 2
            continue
        cleaned.append(line)
        i += 1

    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return cleaned


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    src = root / "resources" / "goc.txt"
    lines = preprocess_lines(src.read_text(encoding="utf-8").splitlines())
    out = normalize(lines)
    src.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Normalized {src}: {len(lines)} -> {len(out)} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
