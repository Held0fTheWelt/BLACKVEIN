"""Read-only closure cockpit normalization from canonical GoC audit artifacts."""

from __future__ import annotations

from typing import Any

from app.services.ai_stack_closure_cockpit_parsing import (
    CLOSURE_LEVEL_PATH,
    G9B_ATTEMPT_RECORD_PATH,
    G9B_BASELINE_PATH,
    GATE_MATRIX_PATH,
    G9_RUN_METADATA_PATH,
    MASTER_REPORT_PATH,
    read_audit_json,
    read_audit_text,
)
from app.services.ai_stack_closure_cockpit_report_assembly import assemble_closure_cockpit_report


def build_closure_cockpit_report(*, trace_id: str) -> dict[str, Any]:
    """Return a read-only closure cockpit model derived from canonical audit artifacts."""
    gate_summary_text = read_audit_text(GATE_MATRIX_PATH)
    closure_level_text = read_audit_text(CLOSURE_LEVEL_PATH)
    master_report_text = read_audit_text(MASTER_REPORT_PATH)
    g9b_baseline_text = read_audit_text(G9B_BASELINE_PATH)
    g9b_attempt = read_audit_json(G9B_ATTEMPT_RECORD_PATH)
    g9_run_metadata = read_audit_json(G9_RUN_METADATA_PATH)

    return assemble_closure_cockpit_report(
        trace_id=trace_id,
        gate_summary_text=gate_summary_text,
        closure_level_text=closure_level_text,
        master_report_text=master_report_text,
        g9b_baseline_text=g9b_baseline_text,
        g9b_attempt=g9b_attempt,
        g9_run_metadata=g9_run_metadata,
    )
