"""Session evidence bundle assembly — DS-051 (delegates helpers to ``ai_stack_evidence_service``).

DS-004: Section assembly lives in ``ai_stack_evidence_session_bundle_sections``.
"""

from __future__ import annotations

from typing import Any

from app.services.ai_stack_evidence_session_bundle_sections import (
    apply_diagnostics_execution_truth_and_retrieval,
    apply_world_engine_bridge,
    apply_writers_room_and_improvement_signals,
    session_bundle_base_scaffold,
    session_bundle_not_found,
)


def assemble_session_evidence_bundle(*, session_id: str, trace_id: str) -> dict[str, Any]:
    """Build governance session evidence bundle (same contract as ``build_session_evidence_bundle``)."""
    import app.services.ai_stack_evidence_service as ev

    runtime_session = ev.get_runtime_session(session_id)
    if not runtime_session:
        return session_bundle_not_found(trace_id=trace_id, session_id=session_id)

    state = runtime_session.current_runtime_state
    metadata = state.metadata if isinstance(state.metadata, dict) else {}
    engine_id = metadata.get("world_engine_story_session_id")

    bundle = session_bundle_base_scaffold(
        trace_id=trace_id,
        session_id=session_id,
        state=state,
        engine_id=engine_id,
    )

    apply_world_engine_bridge(bundle, engine_id=engine_id, trace_id=trace_id)
    apply_diagnostics_execution_truth_and_retrieval(bundle, ev)
    apply_writers_room_and_improvement_signals(bundle, ev)

    return bundle
