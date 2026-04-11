"""Section builders for closure cockpit report assembly (DS-004).

Each function returns one payload slice; ``assemble_closure_cockpit_report`` composes them
unchanged for callers (read-only normalized view contract).
"""

from __future__ import annotations

from typing import Any

from app.services.ai_stack_closure_cockpit_parsing import (
    EXPECTED_GATE_ORDER,
    CLOSURE_LEVEL_PATH,
    G9B_ATTEMPT_RECORD_PATH,
    G9B_BASELINE_PATH,
    GATE_MATRIX_PATH,
    G9_RUN_METADATA_PATH,
    MASTER_REPORT_PATH,
    extract_heading_statement,
    extract_level_reason,
    ordered_gate_stack,
    parse_closure_notes,
    parse_gate_summary_rows,
)


def compute_gates_by_id_and_stack(
    gate_summary_text: str,
    closure_level_text: str,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[str]]:
    gate_rows = parse_gate_summary_rows(gate_summary_text)
    closure_notes = parse_closure_notes(closure_level_text)
    gates_by_id: dict[str, dict[str, Any]] = {}
    for row in gate_rows:
        gate_id = row["gate_id"]
        row["rationale"] = closure_notes.get(gate_id) or "No gate-specific rationale extracted."
        gates_by_id[gate_id] = row
    gate_stack = ordered_gate_stack(gates_by_id)
    missing_gates = [gate_id for gate_id in EXPECTED_GATE_ORDER if gate_id not in gates_by_id]
    return gates_by_id, gate_stack, missing_gates


def closure_level_heading_fields(closure_level_text: str) -> dict[str, Any]:
    return {
        "level_a_status": extract_heading_statement(
            closure_level_text, "Level A (program closure capability)"
        ),
        "level_b_status": extract_heading_statement(
            closure_level_text, "Level B (program closure capability)"
        ),
        "level_a_reason": extract_level_reason(closure_level_text, "Level A (program closure capability)"),
        "level_b_reason": extract_level_reason(closure_level_text, "Level B (program closure capability)"),
    }


def g9b_attempt_derivatives(g9b_attempt: dict[str, Any]) -> dict[str, Any]:
    g9b_attempt_status = g9b_attempt.get("level_b_attempt_status")
    g9b_primary_class = g9b_attempt.get("independence_classification_primary")
    g9b_reason_codes = (
        g9b_attempt.get("reason_codes") if isinstance(g9b_attempt.get("reason_codes"), list) else []
    )
    decisive_blocker = (
        f"G9B evaluator independence remains blocked ({g9b_attempt_status}, {g9b_primary_class})."
        if isinstance(g9b_attempt_status, str) and g9b_attempt_status.startswith("failed")
        else "No decisive blocker extracted from G9B attempt record."
    )
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
                    {"label": "G9B level-B attempt record", "path": str(G9B_ATTEMPT_RECORD_PATH.resolve())},
                    {"label": "G9B baseline report", "path": str(G9B_BASELINE_PATH.resolve())},
                ],
            }
        )
    return {
        "g9b_attempt_status": g9b_attempt_status,
        "g9b_primary_class": g9b_primary_class,
        "g9b_reason_codes": g9b_reason_codes,
        "decisive_blocker": decisive_blocker,
        "evidential_blockers": evidential_blockers,
    }


def resolved_repo_local_from_gate_stack(gate_stack: list[dict[str, Any]]) -> list[str]:
    return [
        f"{gate['gate_id']} structural_status={gate['structural_status']}"
        for gate in gate_stack
        if gate.get("structural_status") == "green"
    ]


def build_consistency_notes(
    gates_by_id: dict[str, dict[str, Any]],
    level_b_status: Any,
    missing_gates: list[str],
) -> list[str]:
    consistency_notes: list[str] = []
    if "G10" in gates_by_id and isinstance(level_b_status, str) and "Not supported" in level_b_status:
        consistency_notes.append(
            "G10 is structural green/level_a_capable, but this does not imply program Level B."
        )
    if missing_gates:
        consistency_notes.append(f"Missing expected gates in summary matrix: {', '.join(missing_gates)}")
    return consistency_notes


def infer_g9_acceptance_result(closure_level_text: str, g9_row: dict[str, Any]) -> str:
    g9_acceptance_result = "unknown"
    if "pass_all: true" in closure_level_text:
        g9_acceptance_result = "pass_all_true_on_authoritative_run"
    elif g9_row.get("closure_level_status") == "level_a_capable":
        g9_acceptance_result = "level_a_capable_without_explicit_pass_flag"
    return g9_acceptance_result


def aggregate_summary_section(
    *,
    level_a_status: Any,
    level_b_status: Any,
    decisive_blocker: str,
    g9b_attempt: dict[str, Any],
    g9_run_metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "overall_closure_posture": "level_a_supported_level_b_blocked",
        "level_a_status": level_a_status,
        "level_b_status": level_b_status,
        "key_blocker_summary": decisive_blocker,
        "authoritative_reference": {
            "audit_run_id": g9b_attempt.get("audit_run_id") or g9_run_metadata.get("audit_run_id"),
            "timestamp_utc": g9_run_metadata.get("timestamp_utc"),
            "source": str(G9_RUN_METADATA_PATH.resolve()),
        },
    }


def current_blockers_section(
    *,
    resolved_repo_local: list[str],
    evidential_blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "repo_local_resolved": resolved_repo_local,
        "evidential_or_external": evidential_blockers,
        "decisive_blocker_id": "g9b_independence" if evidential_blockers else None,
    }


def g9_g9b_g10_focus_section(
    *,
    g9_row: dict[str, Any],
    g9b_row: dict[str, Any],
    g10_row: dict[str, Any],
    g9_acceptance_result: str,
    g9b_attempt_status: Any,
    g9b_primary_class: Any,
    level_a_reason: Any,
    level_b_reason: Any,
) -> dict[str, Any]:
    return {
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
                {"label": "G9B level-B attempt record", "path": str(G9B_ATTEMPT_RECORD_PATH.resolve())},
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
    }


def source_refs_section() -> list[dict[str, Any]]:
    return [
        {"label": "Gate summary matrix", "path": str(GATE_MATRIX_PATH.resolve())},
        {"label": "Closure level classification summary", "path": str(CLOSURE_LEVEL_PATH.resolve())},
        {"label": "Master GoC baseline audit report", "path": str(MASTER_REPORT_PATH.resolve())},
        {"label": "G9B evaluator independence baseline", "path": str(G9B_BASELINE_PATH.resolve())},
        {"label": "G9B level-B attempt record", "path": str(G9B_ATTEMPT_RECORD_PATH.resolve())},
    ]


def warnings_and_non_claims(*, missing_gates: list[str]) -> tuple[list[str], list[str]]:
    warnings = (
        [f"One or more canonical gate rows are missing ({', '.join(missing_gates)})."] if missing_gates else []
    )
    non_claims = [
        "This payload is a read-only normalized view of canonical audit artifacts.",
        "No semantic-authoring controls are exposed.",
        "No Level B claim is made when G9B independence evidence is insufficient.",
    ]
    return warnings, non_claims


def debug_context_section(
    *,
    g9b_reason_codes: list[Any],
    gate_summary_text: str,
    closure_level_text: str,
    master_report_text: str,
    g9b_baseline_text: str,
    g9b_attempt: dict[str, Any],
    g9_run_metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "g9b_reason_codes_count": len(g9b_reason_codes),
        "canonical_files_loaded": {
            "gate_summary": bool(gate_summary_text),
            "closure_level_summary": bool(closure_level_text),
            "master_report": bool(master_report_text),
            "g9b_baseline": bool(g9b_baseline_text),
            "g9b_attempt_record": bool(g9b_attempt),
            "g9_run_metadata": bool(g9_run_metadata),
        },
    }
