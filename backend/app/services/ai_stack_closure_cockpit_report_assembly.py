"""Assemble closure cockpit report dict from parsed audit inputs — DS-051.

DS-004: Section composition delegated to ``ai_stack_closure_cockpit_report_sections``.
"""

from __future__ import annotations

from typing import Any

from app.services.ai_stack_closure_cockpit_report_sections import (
    aggregate_summary_section,
    build_consistency_notes,
    closure_level_heading_fields,
    compute_gates_by_id_and_stack,
    current_blockers_section,
    debug_context_section,
    g9_g9b_g10_focus_section,
    g9b_attempt_derivatives,
    infer_g9_acceptance_result,
    resolved_repo_local_from_gate_stack,
    source_refs_section,
    warnings_and_non_claims,
)


def assemble_closure_cockpit_report(
    *,
    trace_id: str,
    gate_summary_text: str,
    closure_level_text: str,
    master_report_text: str,
    g9b_baseline_text: str,
    g9b_attempt: dict[str, Any],
    g9_run_metadata: dict[str, Any],
) -> dict[str, Any]:
    gates_by_id, gate_stack, missing_gates = compute_gates_by_id_and_stack(
        gate_summary_text, closure_level_text
    )
    headings = closure_level_heading_fields(closure_level_text)
    g9b = g9b_attempt_derivatives(g9b_attempt)
    resolved_repo_local = resolved_repo_local_from_gate_stack(gate_stack)
    consistency_notes = build_consistency_notes(
        gates_by_id, headings["level_b_status"], missing_gates
    )
    g9_row = gates_by_id.get("G9", {})
    g9b_row = gates_by_id.get("G9B", {})
    g10_row = gates_by_id.get("G10", {})
    g9_acceptance_result = infer_g9_acceptance_result(closure_level_text, g9_row)
    warnings, non_claims = warnings_and_non_claims(missing_gates=missing_gates)

    return {
        "trace_id": trace_id,
        "canonical_model": "ai_stack_closure_cockpit_v1",
        "aggregate_summary": aggregate_summary_section(
            level_a_status=headings["level_a_status"],
            level_b_status=headings["level_b_status"],
            decisive_blocker=g9b["decisive_blocker"],
            g9b_attempt=g9b_attempt,
            g9_run_metadata=g9_run_metadata,
        ),
        "gate_stack": gate_stack,
        "current_blockers": current_blockers_section(
            resolved_repo_local=resolved_repo_local,
            evidential_blockers=g9b["evidential_blockers"],
        ),
        "g9_g9b_g10_focus": g9_g9b_g10_focus_section(
            g9_row=g9_row,
            g9b_row=g9b_row,
            g10_row=g10_row,
            g9_acceptance_result=g9_acceptance_result,
            g9b_attempt_status=g9b["g9b_attempt_status"],
            g9b_primary_class=g9b["g9b_primary_class"],
            level_a_reason=headings["level_a_reason"],
            level_b_reason=headings["level_b_reason"],
        ),
        "source_refs": source_refs_section(),
        "consistency_notes": consistency_notes,
        "warnings": warnings,
        "non_claims": non_claims,
        "debug_context": debug_context_section(
            g9b_reason_codes=g9b["g9b_reason_codes"],
            gate_summary_text=gate_summary_text,
            closure_level_text=closure_level_text,
            master_report_text=master_report_text,
            g9b_baseline_text=g9b_baseline_text,
            g9b_attempt=g9b_attempt,
            g9_run_metadata=g9_run_metadata,
        ),
    }
