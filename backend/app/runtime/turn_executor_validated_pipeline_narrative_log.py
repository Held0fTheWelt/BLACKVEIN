"""Narrative outcome logging for the validated turn pipeline (DS-005 optional thin-slice)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.content.module_models import ContentModule
from app.runtime.event_log import RuntimeEventLog
from app.runtime.runtime_models import MockDecision, NarrativeCommitRecord, SessionState
from app.runtime.scene_legality import SceneTransitionLegality


def log_narrative_outcomes_after_commit(
    event_log: RuntimeEventLog,
    narrative_commit: NarrativeCommitRecord,
    session: SessionState,
    mock_decision: MockDecision,
    updated_state: dict[str, Any],
    prior_scene_id: str | None,
    module: ContentModule,
) -> None:
    """Log narrative commit outcomes (endings, scene transitions, blocks)."""
    if narrative_commit.situation_status == "ending_reached":
        event_log.log(
            "ending_triggered",
            f"Ending triggered: {narrative_commit.committed_ending_id}",
            payload={"ending_id": narrative_commit.committed_ending_id},
        )
    elif narrative_commit.situation_status == "transitioned":
        event_log.log(
            "scene_changed",
            f"Scene transitioned to {narrative_commit.committed_scene_id}",
            payload={
                "from_scene": prior_scene_id,
                "to_scene": narrative_commit.committed_scene_id,
            },
        )
    elif mock_decision.proposed_scene_id:
        post_delta_session = session.model_copy(deep=True)
        post_delta_session.canonical_state = deepcopy(updated_state)
        post_delta_session.current_scene_id = prior_scene_id or session.current_scene_id
        td = SceneTransitionLegality.check_transition_legal(
            prior_scene_id or session.current_scene_id,
            mock_decision.proposed_scene_id,
            module,
            session=post_delta_session,
            detected_triggers=mock_decision.detected_triggers,
        )
        if not td.allowed:
            event_log.log(
                "scene_transition_blocked",
                f"Scene transition to {mock_decision.proposed_scene_id} blocked: {td.reason}",
                payload={
                    "from_scene": prior_scene_id,
                    "proposed_scene": mock_decision.proposed_scene_id,
                    "reason": td.reason,
                },
            )
