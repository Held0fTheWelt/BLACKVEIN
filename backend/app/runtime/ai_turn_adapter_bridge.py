"""Adapter request construction and Parsed→MockDecision bridging (DS-001 split).

Synchronous seams extracted from ``ai_turn_executor`` so the executor stays
focused on orchestration, tool loops, and parse/success pipelines.
"""

from __future__ import annotations

from typing import Any

from app.content.module_models import ContentModule
from app.runtime.ai_adapter import AdapterRequest
from app.runtime.input_interpreter import interpret_operator_input
from app.runtime.narrative_threads import coerce_narrative_thread_set, compact_threads_for_adapter
from app.runtime.role_structured_decision import ParsedRoleAwareDecision
from app.runtime.short_term_context import ShortTermTurnContext
from app.runtime.turn_executor import MockDecision, ProposedStateDelta
from app.runtime.runtime_models import (
    DeltaType,
    ProposalSource,
    SessionState,
)


def process_role_structured_decision(
    role_aware_decision: ParsedRoleAwareDecision,
) -> MockDecision:
    """Extract responder candidates from role-structured decision, mark as RESPONDER_DERIVED.

    This function bridges W2.4 role separation (interpreter, director, responder)
    into the canonical guarded execution path. It extracts state_change_candidates
    from the responder section and marks them with RESPONDER_DERIVED source.

    Only responder-derived proposals are authorized to enter the canonical
    execution path when enforce_responder_only=True is set.

    Args:
        role_aware_decision: ParsedRoleAwareDecision with role sections preserved

    Returns:
        MockDecision with proposal_source=ProposalSource.RESPONDER_DERIVED

    Process:
    1. Extract state_change_candidates from responder section
    2. Convert to ProposedStateDelta format (responder candidates are already in that form)
    3. Return MockDecision marked RESPONDER_DERIVED
    """
    responder_candidates = role_aware_decision.responder.state_change_candidates or []

    proposed_deltas = []
    for candidate in responder_candidates:
        proposed_deltas.append(
            ProposedStateDelta(
                target=candidate.target_path,
                next_value=candidate.proposed_value,
                delta_type=None,
                source="ai_proposal",
            )
        )

    return MockDecision(
        detected_triggers=[],
        proposed_deltas=proposed_deltas,
        proposed_scene_id=None,
        narrative_text="",
        rationale="",
        proposal_source=ProposalSource.RESPONDER_DERIVED,
    )


def _continuity_context_from_session_layers(session: SessionState) -> dict[str, Any] | None:
    """Task 1C/1D: bounded JSON snapshots from ``context_layers`` only (binding precision §1).

    Excludes diagnostic short-term blobs. Does not embed session_history, turn results,
    or raw metadata. ``active_narrative_threads`` is built only from ``context_layers.narrative_threads``.
    """
    cl = session.context_layers
    out: dict[str, Any] = {}

    st = cl.short_term_context
    if st is not None:
        if isinstance(st, ShortTermTurnContext):
            out["short_term_turn_context"] = st.model_dump(
                mode="json",
                exclude={"execution_result_full", "ai_decision_log_full"},
            )
        elif hasattr(st, "model_dump"):
            out["short_term_turn_context"] = st.model_dump(
                mode="json",
                exclude={"execution_result_full", "ai_decision_log_full"},
            )
        elif isinstance(st, dict):
            out["short_term_turn_context"] = {
                k: v for k, v in st.items() if k not in ("execution_result_full", "ai_decision_log_full")
            }

    ps = cl.progression_summary
    if ps is not None and hasattr(ps, "model_dump"):
        out["progression_summary"] = ps.model_dump(mode="json")

    rel = cl.relationship_axis_context
    if rel is not None and hasattr(rel, "model_dump"):
        out["relationship_axis_context"] = rel.model_dump(mode="json")

    lore = cl.lore_direction_context
    if lore is not None and hasattr(lore, "model_dump"):
        out["lore_direction_context"] = lore.model_dump(mode="json")

    nt = coerce_narrative_thread_set(cl.narrative_threads)
    out["active_narrative_threads"] = compact_threads_for_adapter(nt)

    return out if out else None


def build_adapter_request(
    session: SessionState,
    module: ContentModule,
    *,
    operator_input: str = "",
    recent_events: list[dict[str, Any]] | None = None,
    attempt: int = 1,
) -> AdapterRequest:
    """Build an AdapterRequest from session and module context.

    Maps canonical runtime state into the AI adapter contract.
    On retry attempts (attempt > 1), context is progressively trimmed to reduce size.

    Args:
        session: Current session state
        module: Loaded content module
        operator_input: Optional operator context
        recent_events: Optional recent event list
        attempt: Retry attempt number (1 = initial, 2+ = retries with reduced context)

    Returns:
        AdapterRequest ready for adapter.generate()
    """
    op_raw = operator_input if operator_input is not None else ""
    input_interpretation = interpret_operator_input(op_raw)
    continuity_context = _continuity_context_from_session_layers(session)
    return AdapterRequest(
        session_id=session.session_id,
        turn_number=session.turn_counter,
        current_scene_id=session.current_scene_id,
        canonical_state=session.canonical_state,
        recent_events=recent_events or [],
        operator_input=operator_input or None,
        input_interpretation=input_interpretation,
        continuity_context=continuity_context,
        request_role_structured_output=True,
        metadata={
            "module_id": module.metadata.module_id,
            "module_version": module.metadata.version,
        },
    )


def decision_from_parsed(parsed_decision: Any) -> MockDecision:
    """Bridge ParsedAIDecision to MockDecision for runtime consumption.

    This is the structural seam: ProposedDelta.target_path → ProposedStateDelta.target.

    Maps:
    - parsed_decision.proposed_deltas (ProposedDelta[]) → MockDecision.proposed_deltas (ProposedStateDelta[])
    - ProposedDelta.target_path → ProposedStateDelta.target
    - ProposedDelta.delta_type (str|None) → DeltaType(value) with try/except fallback to None
    - parsed_decision.scene_interpretation → MockDecision.narrative_text
    - parsed_decision.rationale → MockDecision.rationale

    Args:
        parsed_decision: ParsedAIDecision from process_adapter_response

    Returns:
        MockDecision ready for execute_turn
    """
    proposed_deltas: list[ProposedStateDelta] = []
    for delta in parsed_decision.proposed_deltas:
        delta_type: DeltaType | None = None
        if delta.delta_type is not None:
            try:
                delta_type = DeltaType(delta.delta_type)
            except ValueError:
                delta_type = None

        proposed_deltas.append(
            ProposedStateDelta(
                target=delta.target_path,
                next_value=delta.next_value,
                delta_type=delta_type,
            )
        )

    return MockDecision(
        detected_triggers=parsed_decision.detected_triggers,
        proposed_deltas=proposed_deltas,
        proposed_scene_id=parsed_decision.proposed_scene_id,
        narrative_text=parsed_decision.scene_interpretation,
        rationale=parsed_decision.rationale,
    )
