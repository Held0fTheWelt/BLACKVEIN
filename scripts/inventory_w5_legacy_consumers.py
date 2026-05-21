"""W5 Phase 6A — non-failing inventory reporter for legacy localization consumers.

Scans the working tree for the legacy localization / current-room surfaces
listed in ``docs/MVPs/w5_legacy_consumer_removal_inventory.md`` and prints a
summary by surface. **Always exits 0** — this is a planning aid, not a gate.

Usage:

    python scripts/inventory_w5_legacy_consumers.py
    python scripts/inventory_w5_legacy_consumers.py --json
    python scripts/inventory_w5_legacy_consumers.py --root D:/WorldOfShadows

The script is intentionally minimal: it greps the working tree for known
substrings, deduplicates by ``(path, line_number)``, and groups by surface.
It deliberately does not classify findings — classification belongs in the
inventory doc, which is the authoritative artifact.

Excluded directories: ``.git``, ``__pycache__``, ``node_modules``,
``'fy'-suites/delagecy``, ``'fy'-suites/docify``, and every ``audit_*.json``
or ``*.log`` artifact at the repository root.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# Each entry: (key, regex pattern). Regexes use word boundaries where useful.
LEGACY_SURFACES: list[tuple[str, str]] = [
    ("current_room", r"\bcurrent_room\b"),
    ("current_room_id", r"\bcurrent_room_id\b"),
    ("current_area", r"\bcurrent_area\b"),
    ("previous_room_id", r"\bprevious_room_id\b"),
    ("actor_locations", r"\bactor_locations\b"),
    ("visible_room_ids", r"\bvisible_room_ids\b"),
    ("visible_occupants", r"\bvisible_occupants\b"),
    ("RuntimeVisibilityPolicy", r"\bRuntimeVisibilityPolicy\b"),
    ("complete_actor_locations_for_gathering", r"complete_actor_locations_for_gathering"),
    ("gathering_scene_id", r"\bgathering_scene_id\b"),
    ("derived_gathering_room_id", r"derived_gathering_room_id"),
    ("transition_from_previous", r"\btransition_from_previous\b"),
    ("location_changed", r"\blocation_changed\b"),
    ("forbidden_ai_stack_actor_situation", r"ai_stack[\\/]actor_situation\b"),
    ("forbidden_ai_stack_w5_actor_situation", r"ai_stack[\\/]w5_actor_situation\b"),
    ("w5_actor_situation_term", r"w5_actor_situation"),
    # Phase 6B-0 rename items. These should now be present (R1/R2) — they are
    # the new names — and the old names (validate_w5_actor_situation,
    # "w5_actor_situation_validation") should only appear in inventory/audit
    # artifacts after the rename lands. The scanner reports both so future
    # audits can confirm the rename did not regress.
    ("validate_w5_actor_situation_old", r"\bvalidate_w5_actor_situation\b"),
    ("validate_w5_actor_tracking_new", r"\bvalidate_w5_actor_tracking\b"),
    ("w5_actor_situation_validation_old", r"\bw5_actor_situation_validation\b"),
    ("w5_actor_tracking_validation_new", r"\bw5_actor_tracking_validation\b"),
]


# Phase 6B-2 classification labels per surface. Informational only — the
# authoritative classification lives in the inventory doc's per-branch table.
# This map exists so the human-readable scan output can hint which surfaces
# fire under explicit opt-out (`O`), missing/malformed W5 (`M`), substrate
# reads (`S`), compatibility aliases for legacy clients (`L`), or are pure
# documentation/comment mentions (`D`).
PHASE_6B2_CLASSIFICATION: dict[str, str] = {
    "current_room": "L/S — compatibility alias on player-shell + WS payloads; also substrate read in runtime_world/environment_state",
    "current_room_id": "L/S — compatibility alias + Participant dataclass substrate field",
    "current_area": "S/L — substrate field; read by C5/C8 affordance + sensory engines (migrate_to_w5_first_before_removal)",
    "previous_room_id": "S — substrate field on environment_state",
    "actor_locations": "S — substrate field on environment_state; read by W5 extractor + Director baseline completion",
    "visible_room_ids": "S — substrate field on environment_state.visible_room_ids",
    "visible_occupants": "S — RuntimeVisibilityPolicy substrate field",
    "RuntimeVisibilityPolicy": "S — engine-level visibility substrate",
    "complete_actor_locations_for_gathering": "S — Director baseline completion algorithm; called by F1/F4/F5",
    "gathering_scene_id": "S — derived from actor_locations by F5; consumed by ADR-0061 pause predicate",
    "derived_gathering_room_id": "S — Director alias (also produced by F5)",
    "transition_from_previous": "migrate_to_w5_first_before_removal (F8) — narrator legacy fallback; prompt + parity tests still read it",
    "location_changed": "S — W5 mirror of `transition_from_previous.location_changed`",
    "forbidden_ai_stack_actor_situation": "FORBIDDEN — must be zero outside inventory docs/scripts",
    "forbidden_ai_stack_w5_actor_situation": "FORBIDDEN — must be zero outside inventory docs/scripts",
    "w5_actor_situation_term": "D/historical — only inventory/audit artifacts may mention this term",
    "validate_w5_actor_situation_old": "D/historical — old function name; only inventory/audit artifacts may reference it (R1 in 6B-0)",
    "validate_w5_actor_tracking_new": "current — Phase 6B-0 R1 rename target",
    "w5_actor_situation_validation_old": "D/historical — old failure_class string (R2 in 6B-0)",
    "w5_actor_tracking_validation_new": "current — Phase 6B-0 R2 rename target",
}


EXCLUDED_DIR_NAMES: set[str] = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
}

# Directory path fragments to exclude (matched against POSIX-style path)
EXCLUDED_PATH_FRAGMENTS: tuple[str, ...] = (
    "'fy'-suites/delagecy/",
    "'fy'-suites/docify/",
    "'fy'-suites/observifyfy/",
    "'fy'-suites/despaghettify/",
    "tests/reports/",
    "world-engine/app/story_runtime/manager/_legacy_sources/",
)

# Filename patterns to exclude
EXCLUDED_FILENAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^audit_.*\.json$"),
    re.compile(r"^.*\.log$"),
    re.compile(r"^engine_run_last\.txt$"),
    re.compile(r"^failing-tests\.txt$"),
)

INCLUDED_EXTENSIONS: set[str] = {
    ".py",
    ".md",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".yaml",
    ".yml",
    ".json",
    ".txt",
    ".bak",
}


@dataclass(frozen=True)
class Finding:
    surface: str
    path: str
    line: int
    text: str

    def to_dict(self) -> dict[str, object]:
        return {
            "surface": self.surface,
            "path": self.path,
            "line": self.line,
            "text": self.text[:240],
        }


@dataclass
class ScanReport:
    root: str
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0

    def by_surface(self) -> dict[str, int]:
        counts: dict[str, int] = {key: 0 for key, _ in LEGACY_SURFACES}
        for f in self.findings:
            counts[f.surface] = counts.get(f.surface, 0) + 1
        return counts

    def files_with_findings(self) -> int:
        return len({f.path for f in self.findings})


def _is_excluded_path(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return True
    for fragment in EXCLUDED_PATH_FRAGMENTS:
        if fragment in rel:
            return True
    for pat in EXCLUDED_FILENAME_PATTERNS:
        if pat.match(path.name):
            return True
    return False


def _iter_candidate_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for current_dir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIR_NAMES]
        for name in files:
            p = Path(current_dir) / name
            if p.suffix.lower() not in INCLUDED_EXTENSIONS:
                continue
            if _is_excluded_path(p, root):
                continue
            out.append(p)
    return out


def scan(root: Path) -> ScanReport:
    report = ScanReport(root=str(root))
    compiled = [(key, re.compile(pattern)) for key, pattern in LEGACY_SURFACES]
    for path in _iter_candidate_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            report.files_skipped += 1
            continue
        report.files_scanned += 1
        for line_no, line in enumerate(text.splitlines(), start=1):
            for key, regex in compiled:
                if regex.search(line):
                    rel_path = path.relative_to(root).as_posix()
                    report.findings.append(
                        Finding(surface=key, path=rel_path, line=line_no, text=line.strip())
                    )
    return report


def _format_human(report: ScanReport) -> str:
    out: list[str] = []
    out.append("W5 Phase 6A — legacy localization surface scan")
    out.append("=" * 50)
    out.append(f"root: {report.root}")
    out.append(f"files scanned: {report.files_scanned}")
    out.append(f"files skipped: {report.files_skipped}")
    out.append(f"files with findings: {report.files_with_findings()}")
    out.append(f"total findings: {len(report.findings)}")
    out.append("")
    out.append("Count by surface:")
    for key, count in report.by_surface().items():
        out.append(f"  {key:48s} {count:5d}")
    out.append("")
    out.append("Phase 6B-2 classification (informational; authoritative table in")
    out.append("docs/MVPs/w5_legacy_consumer_removal_inventory.md §'Phase 6B-2'):")
    out.append("  S = substrate_keep  O = opt-out fallback  M = malformed-W5 safety")
    out.append("  L = compatibility alias  D = doc/comment only")
    for key, _ in LEGACY_SURFACES:
        label = PHASE_6B2_CLASSIFICATION.get(key, "—")
        out.append(f"  {key:48s} {label}")
    out.append("")
    forbidden_keys = (
        "forbidden_ai_stack_actor_situation",
        "forbidden_ai_stack_w5_actor_situation",
    )
    forbidden = [f for f in report.findings if f.surface in forbidden_keys]
    if forbidden:
        out.append("WARNING — forbidden package references detected:")
        for f in forbidden:
            out.append(f"  {f.path}:{f.line}: {f.text[:200]}")
    else:
        out.append("OK — no forbidden package references detected.")
    out.append("")
    out.append("This report is informational; the authoritative inventory and")
    out.append("classification live in docs/MVPs/w5_legacy_consumer_removal_inventory.md.")
    return "\n".join(out)


def _reconfigure_stdout_utf8() -> None:
    """Best-effort: force stdout to UTF-8 so non-ASCII findings can be printed
    on Windows consoles whose default code page is cp1252."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _reconfigure_stdout_utf8()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root to scan (default: repository root inferred from this script).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON report instead of a human-readable summary.",
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    report = scan(root)
    if args.json:
        payload = {
            "root": report.root,
            "files_scanned": report.files_scanned,
            "files_skipped": report.files_skipped,
            "files_with_findings": report.files_with_findings(),
            "total_findings": len(report.findings),
            "counts_by_surface": report.by_surface(),
            "findings": [f.to_dict() for f in report.findings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_format_human(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
