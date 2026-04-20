"""Operational versioning helpers — parse declared versions from anchors, never from guessed behaviour."""
from __future__ import annotations

import re
from pathlib import Path

def openapi_declared_version(text: str) -> str:
    """Return ``info.version`` from an OpenAPI YAML head slice (line-scoped, deterministic)."""
    lines = text[:12_000].splitlines()
    in_info = False
    for line in lines:
        stripped = line.strip()
        if stripped == "info:" or stripped.startswith("info:") and stripped.endswith(":"):
            in_info = True
            continue
        if in_info:
            if stripped and not line.startswith(" ") and stripped.endswith(":") and not stripped.startswith("version"):
                # Next top-level YAML key at column 0 — end of info block.
                break
            m = re.match(r"\s+version:\s*(.+)$", line)
            if m:
                v = m.group(1).strip().strip("'\"")
                return v or "unversioned"
    return "unversioned"

# ADR / Markdown status line (explicit marker only — no semantic inference).
_ADR_STATUS_LINE = re.compile(
    r"(?im)^\s*\*{0,2}status\*{0,2}\s*:\s*([A-Za-z][A-Za-z\s-]{0,40})$",
)

# Front-matter style contractify projection block (optional machine anchor).
_PROJECTION_REF = re.compile(
    r"contractify-projection:\s*\n(?:[^\n]*\n)*?\s*(?:source_contract_id|anchor)\s*:\s*([^\n#]+)",
    re.IGNORECASE,
)


def adr_declared_status(adr_head: str) -> str:
    """Return first explicit ``Status:`` value from an ADR header slice, lowercased, or ``unknown``."""
    m = _ADR_STATUS_LINE.search(adr_head[:6000])
    if not m:
        return "unknown"
    return m.group(1).strip().lower().replace(" ", "_")


def openapi_sha256_prefix(sha256_full: str, *, n: int = 16) -> str:
    """Stable short fingerprint for projection cross-checks (matches manifest convention)."""
    s = sha256_full.strip().lower()
    if len(s) < n:
        return s
    return s[:n]


def parse_projection_marker_head(md_text_head: str) -> dict[str, str]:
    """Extract minimal fields from an optional ``contractify-projection`` YAML-ish block."""
    out: dict[str, str] = {}
    if "contractify-projection:" not in md_text_head:
        return out
    m = _PROJECTION_REF.search(md_text_head[:16000])
    if m:
        out["anchor_or_source"] = m.group(1).strip()
    vm = re.search(
        r"(?im)contractify-projection:[^\n]*(?:\n[^\n]*)*?\n\s*contract_version_ref\s*:\s*([^\n#]+)",
        md_text_head[:16000],
    )
    if vm:
        out["contract_version_ref"] = vm.group(1).strip().strip("'\"")
    return out


def read_openapi_version_from_file(path: Path) -> str:
    if not path.is_file():
        return "unversioned"
    return openapi_declared_version(path.read_text(encoding="utf-8", errors="replace"))


_SUPERSEDES_LINE = re.compile(r"(?im)^\s*\*{0,2}supersedes\*{0,2}\s*:\s*(.+)$")


def adr_supersedes_line(head: str) -> str:
    """Return raw ``Supersedes:`` line body from an ADR header slice, or empty string."""
    m = _SUPERSEDES_LINE.search(head[:12_000])
    return m.group(1).strip() if m else ""


def resolve_supersedes_markdown_target(line_body: str, *, adr_file: Path, repo: Path) -> str:
    """Resolve ``[label](path.md)`` or bare ``adr-*.md`` next to ``adr_file`` to a repo-relative posix path."""
    line_body = line_body.strip()
    if not line_body:
        return ""
    mlink = re.search(r"\(([^)]+\.md)\)", line_body)
    raw = mlink.group(1).strip() if mlink else ""
    if not raw:
        mfile = re.search(r"(adr-[\w-]+\.md)", line_body, re.IGNORECASE)
        raw = mfile.group(1) if mfile else ""
    if not raw:
        return ""
    base = adr_file.parent / raw
    try:
        return base.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return ""
