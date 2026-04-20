"""Read-only closure cockpit normalization from canonical GoC audit artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_EXPECTED_GATE_ORDER: tuple[str, ...] = (
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

_GATE_MATRIX_PATH = _DOCS_AUDIT_ROOT / "gate_summary_matrix.md"
_CLOSURE_LEVEL_PATH = _DOCS_AUDIT_ROOT / "closure_level_classification_summary.md"
_MASTER_REPORT_PATH = _DOCS_AUDIT_ROOT / "master_goc_baseline_audit_report.md"
_G9B_BASELINE_PATH = _DOCS_AUDIT_ROOT / "gate_G9B_evaluator_independence_baseline.md"
_G9B_ATTEMPT_RECORD_PATH = _EVIDENCE_ROOT / "g9_level_a_fullsix_20260410" / "g9b_level_b_attempt_record.json"
_G9_RUN_METADATA_PATH = _EVIDENCE_ROOT / "g9_level_a_fullsix_20260410" / "run_metadata.json"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_gate_id(gate_label: str) -> str | None:
    candidate = gate_label.strip()
    if candidate.startswith("G9B"):
        return "G9B"
    match = re.match(r"^(G\d+)\b", candidate)
    if not match:
        return None
    return match.group(1)


def _parse_gate_summary_rows(gate_summary_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pattern = re.compile(
        r"^\| (?P<gate>G\d+B?[^|]*) \| `(?P<structural>[^`]+)` \| `(?P<closure>[^`]+)` \| "
        r"`(?P<quality>[^`]+)` \| \[(?P<link_text>[^\]]+)\]\((?P<link_target>[^)]+)\) \|$"
    )
    for line in gate_summary_text.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        gate_id = _extract_gate_id(match.group("gate"))
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


def _parse_closure_notes(closure_level_text: str) -> dict[str, str]:
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


def _extract_heading_statement(markdown_text: str, heading: str) -> str:
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


def _extract_level_reason(markdown_text: str, heading: str) -> str:
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


def _ordered_gate_stack(gates_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    for gate_id in _EXPECTED_GATE_ORDER:
        gate = gates_by_id.get(gate_id)
        if gate:
            ordered.append(gate)
    return ordered


def build_closure_cockpit_report(*, trace_id: str) -> dict[str, Any]:
    """Return a read-only closure cockpit model derived from canonical audit artifacts."""
    gate_summary_text = _read_text(_GATE_MATRIX_PATH)
    closure_level_text = _read_text(_CLOSURE_LEVEL_PATH)
    master_report_text = _read_text(_MASTER_REPORT_PATH)
    g9b_baseline_text = _read_text(_G9B_BASELINE_PATH)
    g9b_attempt = _read_json(_G9B_ATTEMPT_RECORD_PATH)
    g9_run_metadata = _read_json(_G9_RUN_METADATA_PATH)

    gate_rows = _parse_gate_summary_rows(gate_summary_text)
    closure_notes = _parse_closure_notes(closure_level_text)

    gates_by_id: dict[str, dict[str, Any]] = {}
    for row in gate_rows:
        gate_id = row["gate_id"]
        row["rationale"] = closure_notes.get(gate_id) or "No gate-specific rationale extracted."
        gates_by_id[gate_id] = row

    gate_stack = _ordered_gate_stack(gates_by_id)
    missing_gates = [gate_id for gate_id in _EXPECTED_GATE_ORDER if gate_id not in gates_by_id]

    level_a_status = _extract_heading_statement(closure_level_text, "Level A (program closure capability)")
    level_b_status = _extract_heading_statement(closure_level_text, "Level B (program closure capability)")
    level_a_reason = _extract_level_reason(closure_level_text, "Level A (program closure capability)")
    level_b_reason = _extract_level_reason(closure_level_text, "Level B (program closure capability)")

    g9b_attempt_status = g9b_attempt.get("level_b_attempt_status")
    g9b_primary_class = g9b_attempt.get("independence_classification_primary")
    g9b_reason_codes = g9b_attempt.get("reason_codes") if isinstance(g9b_attempt.get("reason_codes"), list) else []

    decisive_blocker = (
        f"G9B evaluator independence remains blocked ({g9b_attempt_status}, {g9b_primary_class})."
        if isinstance(g9b_attempt_status, str) and g9b_attempt_status.startswith("failed")
        else "No decisive blocker extracted from G9B attempt record."
    )

    resolved_repo_local = [
        f"{gate['gate_id']} structural_status={gate['structural_status']}"
        for gate in gate_stack
        if gate.get("structural_status") == "green"
    ]

    evidential_blockers: list[dict[str, Any]] = []
    if isinstance(g9b_attempt_status, str) and g9b_attempt_status.startswith("failed"):
        evidential_blockers.append(
            {
                "id": "g9b_independence",
                "title": "G9B evaluator independence",
                "status": g9b_attempt_status,
                "reason_codes": g9b_reason_codes,
                "primary_classification": g9b_primary_class,
                "artifact_refs": [
                    {"label": "G9B level-B attempt record", "path": str(_G9B_ATTEMPT_RECORD_PATH.resolve())},
                    {"label": "G9B baseline report", "path": str(_G9B_BASELINE_PATH.resolve())},
                ],
            }
        )

    consistency_notes: list[str] = []
    if "G10" in gates_by_id and isinstance(level_b_status, str) and "Not supported" in level_b_status:
        consistency_notes.append(
            "G10 is structural green/level_a_capable, but this does not imply program Level B."
        )
    if missing_gates:
        consistency_notes.append(f"Missing expected gates in summary matrix: {', '.join(missing_gates)}")

    g9_row = gates_by_id.get("G9", {})
    g9b_row = gates_by_id.get("G9B", {})
    g10_row = gates_by_id.get("G10", {})

    g9_acceptance_result = "unknown"
    if "pass_all: true" in closure_level_text:
        g9_acceptance_result = "pass_all_true_on_authoritative_run"
    elif g9_row.get("closure_level_status") == "level_a_capable":
        g9_acceptance_result = "level_a_capable_without_explicit_pass_flag"

    report = {
        "trace_id": trace_id,
        "canonical_model": "ai_stack_closure_cockpit_v1",
        "aggregate_summary": {
            "overall_closure_posture": "level_a_supported_level_b_blocked",
            "level_a_status": level_a_status,
            "level_b_status": level_b_status,
            "key_blocker_summary": decisive_blocker,
            "authoritative_reference": {
                "audit_run_id": g9b_attempt.get("audit_run_id") or g9_run_metadata.get("audit_run_id"),
                "timestamp_utc": g9_run_metadata.get("timestamp_utc"),
                "source": str(_G9_RUN_METADATA_PATH.resolve()),
            },
        },
        "gate_stack": gate_stack,
        "current_blockers": {
            "repo_local_resolved": resolved_repo_local,
            "evidential_or_external": evidential_blockers,
            "decisive_blocker_id": "g9b_independence" if evidential_blockers else None,
        },
        "g9_g9b_g10_focus": {
            "g9_acceptance": {
                "gate_id": "G9",
                "closure_level_status": g9_row.get("closure_level_status"),
                "result": g9_acceptance_result,
                "rationale": g9_row.get("rationale"),
                "artifact_refs": g9_row.get("artifact_refs", []),
            },
            "g9b_independence": {
                "gate_id": "G9B",
                "closure_level_status": g9b_row.get("closure_level_status"),
                "level_b_attempt_status": g9b_attempt_status,
                "independence_classification_primary": g9b_primary_class,
                "rationale": g9b_row.get("rationale"),
                "artifact_refs": [
                    *g9b_row.get("artifact_refs", []),
                    {"label": "G9B level-B attempt record", "path": str(_G9B_ATTEMPT_RECORD_PATH.resolve())},
                ],
            },
            "g10_integrative": {
                "gate_id": "G10",
                "closure_level_status": g10_row.get("closure_level_status"),
                "structural_status": g10_row.get("structural_status"),
                "rationale": g10_row.get("rationale"),
                "artifact_refs": g10_row.get("artifact_refs", []),
            },
            "why_level_a_supported": level_a_reason,
            "why_level_b_not_supported": level_b_reason,
            "anti_misread_statement": (
                "G10 green indicates integrative gate health; it is not equal to Level B closure when G9B "
                "independence remains insufficient."
            ),
        },
        "source_refs": [
            {"label": "Gate summary matrix", "path": str(_GATE_MATRIX_PATH.resolve())},
            {"label": "Closure level classification summary", "path": str(_CLOSURE_LEVEL_PATH.resolve())},
            {"label": "Master GoC baseline audit report", "path": str(_MASTER_REPORT_PATH.resolve())},
            {"label": "G9B evaluator independence baseline", "path": str(_G9B_BASELINE_PATH.resolve())},
            {"label": "G9B level-B attempt record", "path": str(_G9B_ATTEMPT_RECORD_PATH.resolve())},
        ],
        "consistency_notes": consistency_notes,
        "warnings": (
            [f"One or more canonical gate rows are missing ({', '.join(missing_gates)})."]
            if missing_gates
            else []
        ),
        "non_claims": [
            "This payload is a read-only normalized view of canonical audit artifacts.",
            "No semantic-authoring controls are exposed.",
            "No Level B claim is made when G9B independence evidence is insufficient.",
        ],
        "debug_context": {
            "g9b_reason_codes_count": len(g9b_reason_codes),
            "canonical_files_loaded": {
                "gate_summary": bool(gate_summary_text),
                "closure_level_summary": bool(closure_level_text),
                "master_report": bool(master_report_text),
                "g9b_baseline": bool(g9b_baseline_text),
                "g9b_attempt_record": bool(g9b_attempt),
                "g9_run_metadata": bool(g9_run_metadata),
            },
        },
    }
    return report
