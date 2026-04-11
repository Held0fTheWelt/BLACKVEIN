"""Dry-run preview evaluation using canonical guard/validation semantics."""

from __future__ import annotations

import asyncio
from copy import deepcopy

from app.content.module_models import ContentModule
from app.runtime.preview_models import PreviewDeltaRequest, PreviewDeltaResult
from app.runtime.turn_executor import MockDecision, ProposedStateDelta, execute_turn
from app.runtime.runtime_models import DeltaType, SessionContextLayers, SessionState


def _coerce_delta_type(raw_delta_type: str | None) -> DeltaType | None:
    if raw_delta_type is None:
        return None
    try:
        return DeltaType(raw_delta_type)
    except ValueError:
        return None


def _build_preview_session_clone(session: SessionState) -> SessionState:
    """Create a bounded session clone for dry-run guard evaluation only."""
    return SessionState(
        session_id=session.session_id,
        module_id=session.module_id,
        module_version=session.module_version,
        current_scene_id=session.current_scene_id,
        status=session.status,
        turn_counter=session.turn_counter,
        canonical_state=deepcopy(session.canonical_state),
        execution_mode=session.execution_mode,
        adapter_name=session.adapter_name,
        seed=session.seed,
        created_at=session.created_at,
        updated_at=session.updated_at,
        metadata={},
        context_layers=SessionContextLayers(),
        degraded_state=session.degraded_state.model_copy(deep=True),
    )


def preview_delta_dry_run(
    *,
    session: SessionState,
    module: ContentModule,
    current_turn: int,
    request: PreviewDeltaRequest,
) -> PreviewDeltaResult:
    """Preview candidate deltas with canonical runtime guard in dry-run mode."""
    warnings: list[str] = []
    if request.scene_id and request.scene_id != session.current_scene_id:
        warnings.append(
            "Preview request scene_id differs from active session scene_id."
        )

    preview_decision = MockDecision(
        detected_triggers=request.detected_triggers,
        proposed_deltas=[
            ProposedStateDelta(
                target=delta.target_path,
                next_value=delta.next_value,
                delta_type=_coerce_delta_type(delta.delta_type),
                source="preview_request",
            )
            for delta in request.proposed_state_deltas
        ],
        proposed_scene_id=request.proposed_scene_id,
        narrative_text="[preview dry-run]",
        rationale=request.reasoning_summary or "",
    )

    # Guarded dry-run: evaluate on a bounded cloned session only.
    session_clone = _build_preview_session_clone(session)
    result = asyncio.run(
        execute_turn(
            session_clone,
            current_turn=current_turn,
            mock_decision=preview_decision,
            module=module,
            enforce_responder_only=False,
        )
    )

    accepted = [delta.target_path for delta in result.accepted_deltas]
    rejected = [delta.target_path for delta in result.rejected_deltas]
    rejection_reasons = list((result.validation_errors or [])[:10])
    accepted_count = len(accepted)
    rejected_count = len(rejected)
    partial = accepted_count > 0 and rejected_count > 0
    preview_allowed = result.execution_status == "success" and rejected_count == 0

    suggested_corrections: list[str] = []
    if rejection_reasons:
        suggested_corrections.append(
            "Revise rejected targets to comply with canonical guard constraints."
        )
    if rejected_count > 0:
        suggested_corrections.append(
            "Prefer existing entities/paths already present in canonical state."
        )

    summary = (
        f"Preview guard outcome={result.guard_outcome.value}; "
        f"accepted={accepted_count}, rejected={rejected_count}."
    )
    input_targets = [delta.target_path for delta in request.proposed_state_deltas][:20]
    normalized_feedback = {
        "preview_allowed": preview_allowed,
        "guard_outcome": result.guard_outcome.value,
        "accepted_delta_count": accepted_count,
        "rejected_delta_count": rejected_count,
        "partial_acceptance": partial,
        "top_rejection_reasons": rejection_reasons[:5],
        "suggested_corrections": suggested_corrections[:5],
    }

    return PreviewDeltaResult(
        preview_allowed=preview_allowed,
        accepted_deltas=accepted[:20],
        rejected_deltas=rejected[:20],
        partial_acceptance=partial,
        guard_outcome=result.guard_outcome.value,
        rejection_reasons=rejection_reasons,
        warning_reasons=warnings[:10],
        suggested_corrections=suggested_corrections[:10],
        normalized_feedback=normalized_feedback,
        summary=summary,
        preview_safe_no_write=True,
        accepted_delta_count=accepted_count,
        rejected_delta_count=rejected_count,
        input_delta_count=len(request.proposed_state_deltas),
        input_targets=input_targets,
    )
