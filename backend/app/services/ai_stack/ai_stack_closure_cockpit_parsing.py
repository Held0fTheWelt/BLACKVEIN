"""Parse canonical closure cockpit audit markdown/JSON — DS-051."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

EXPECTED_GATE_ORDER: tuple[str, ...] = (
    "G1",
    "G2",
    "G3",
    "G4",
    "G5",
    "G6",
    "G7",
    "G8",
    "G9",
    "G9B",
    "G10",
)

_SERVICE_ROOT = Path(__file__).resolve().parents[3]
_DOCS_AUDIT_ROOT = _SERVICE_ROOT / "docs" / "audit"
_EVIDENCE_ROOT = _SERVICE_ROOT / "tests" / "reports" / "evidence"

GATE_MATRIX_PATH = _DOCS_AUDIT_ROOT / "gate_summary_matrix.md"
CLOSURE_LEVEL_PATH = _DOCS_AUDIT_ROOT / "closure_level_classification_summary.md"
MASTER_REPORT_PATH = _DOCS_AUDIT_ROOT / "master_goc_baseline_audit_report.md"
G9B_BASELINE_PATH = _DOCS_AUDIT_ROOT / "gate_G9B_evaluator_independence_baseline.md"
G9B_ATTEMPT_RECORD_PATH = _EVIDENCE_ROOT / "g9_level_a_fullsix_20260410" / "g9b_level_b_attempt_record.json"
G9_RUN_METADATA_PATH = _EVIDENCE_ROOT / "g9_level_a_fullsix_20260410" / "run_metadata.json"


def read_audit_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def read_audit_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def extract_gate_id(gate_label: str) -> str | None:
    candidate = gate_label.strip()
    if candidate.startswith("G9B"):
        return "G9B"
    match = re.match(r"^(G\d+)\b", candidate)
    if not match:
        return None
    return match.group(1)


def parse_gate_summary_rows(gate_summary_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pattern = re.compile(
        r"^\| (?P<gate>G\d+B?[^|]*) \| `(?P<structural>[^`]+)` \| `(?P<closure>[^`]+)` \| "
        r"`(?P<quality>[^`]+)` \| \[(?P<link_text>[^\]]+)\]\((?P<link_target>[^)]+)\) \|$"
    )
    for line in gate_summary_text.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        gate_id = extract_gate_id(match.group("gate"))
        if not gate_id:
            continue
        link_target = match.group("link_target").strip()
        link_path = str((_DOCS_AUDIT_ROOT / link_target).resolve())
        rows.append(
            {
                "gate_id": gate_id,
                "gate_label": match.group("gate").strip(),
                "structural_status": match.group("structural").strip(),
                "closure_level_status": match.group("closure").strip(),
                "evidence_quality": match.group("quality").strip(),
                "artifact_refs": [
                    {
                        "label": match.group("link_text").strip(),
                        "path": link_path,
                    }
                ],
            }
        )
    return rows


def parse_closure_notes(closure_level_text: str) -> dict[str, str]:
    notes: dict[str, str] = {}
    pattern = re.compile(
        r"^\| (?P<gate>G\d+B?) \| `(?P<closure>[^`]+)` \| (?P<note>.*) \|$"
    )
    for line in closure_level_text.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        notes[match.group("gate")] = match.group("note").strip()
    return notes


def extract_heading_statement(markdown_text: str, heading: str) -> str:
    heading_line = f"### {heading}"
    if heading_line not in markdown_text:
        return "unknown"
    segment = markdown_text.split(heading_line, maxsplit=1)[1]
    for line in segment.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            break
        if stripped.startswith("**") and stripped.endswith("**"):
            return stripped.strip("*").strip()
    return "unknown"


def extract_level_reason(markdown_text: str, heading: str) -> str:
    heading_line = f"### {heading}"
    if heading_line not in markdown_text:
        return "No authoritative rationale found."
    segment = markdown_text.split(heading_line, maxsplit=1)[1]
    reason_lines: list[str] = []
    started = False
    for line in segment.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            break
        if stripped.startswith("Reason:"):
            started = True
        if started and stripped:
            reason_lines.append(stripped)
            if len(reason_lines) >= 2:
                break
    if reason_lines:
        return " ".join(reason_lines)
    return "No explicit reason paragraph found."


def ordered_gate_stack(gates_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    for gate_id in EXPECTED_GATE_ORDER:
        gate = gates_by_id.get(gate_id)
        if gate:
            ordered.append(gate)
    return ordered
