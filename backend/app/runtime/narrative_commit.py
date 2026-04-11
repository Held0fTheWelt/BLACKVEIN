"""In-process narrative commit resolution after state deltas are applied.

Evaluates endings and scene transitions against a **post-delta** session view. This deepens
the canonical in-process commit model for ``SessionState``; it does not replace World
Engine authority for live production play.

Resolution order (deterministic, documented):
1. Apply accepted deltas first (caller); this module reads ``post_delta_canonical_state``.
2. Check ending legality against the post-delta snapshot (highest priority). If legal, the
   story is terminal; no explicit proposed scene transition is committed afterward.
3. Else, if ``decision.proposed_scene_id`` is set, evaluate that transition against the same
   snapshot (proposal-driven semantics; no automatic module graph walk).
4. Else continue in the prior scene.

``derive_next_situation()`` is not invoked here to avoid silently replacing proposal-driven
behavior with auto-derived transitions.
"""

from __future__ import annotations

from copy import deepcopy

from app.content.module_models import ContentModule
from app.runtime.scene_legality import SceneTransitionLegality
from app.runtime.runtime_models import (
    GuardOutcome,
    MockDecision,
    NarrativeCommitRecord,
    SessionState,
    StateDelta,
)


def _sorted_targets(deltas: list[StateDelta]) -> list[str]:
    return sorted({d.target_path for d in deltas if d.target_path})


def narrative_commit_for_source_gate_rejection(
    *,
    turn_number: int,
    prior_scene_id: str,
    decision: MockDecision,
    guard_outcome: GuardOutcome,
    rejected_deltas: list[StateDelta],
) -> NarrativeCommitRecord:
    """Build narrative commit when the responder-only source gate rejects the proposal.

    No deltas are applied; the session remains in ``prior_scene_id``. Guard outcome is
    typically REJECTED.
    """
    committed_trigger_ids = sorted(set(decision.detected_triggers or []))
    rejected_targets = _sorted_targets(rejected_deltas)
    consequences: list[str] = [f"scene_continue:{prior_scene_id}", "source_gate_rejected"]
    return NarrativeCommitRecord(
        turn_number=turn_number,
        prior_scene_id=prior_scene_id,
        committed_scene_id=prior_scene_id,
        situation_status="continue",
        committed_ending_id=None,
        accepted_delta_targets=[],
        rejected_delta_targets=rejected_targets,
        committed_trigger_ids=committed_trigger_ids,
        guard_outcome=guard_outcome.value,
        authoritative_reason=(
            "Proposal source rejected by responder-only gate; no state deltas applied."
        ),
        canonical_consequences=consequences,
        is_terminal=False,
    )


def resolve_narrative_commit(
    *,
    turn_number: int,
    prior_scene_id: str,
    post_delta_canonical_state: dict,
    session_template: SessionState,
    decision: MockDecision,
    module: ContentModule,
    guard_outcome: GuardOutcome,
    accepted_deltas: list[StateDelta],
    rejected_deltas: list[StateDelta],
) -> NarrativeCommitRecord:
    """Resolve committed scene, ending, and bounded consequences after deltas.

    Args:
        turn_number: Turn index for this execution.
        prior_scene_id: Scene id at turn start (from ``session.current_scene_id``).
        post_delta_canonical_state: Canonical state after applying accepted deltas only.
        session_template: Session used for ``model_copy``; identity fields preserved.
        decision: Executed decision (triggers, optional proposed scene).
        module: Loaded content module.
        guard_outcome: Guard classification for this turn's delta set.
        accepted_deltas: Deltas that were applied.
        rejected_deltas: Deltas rejected by validation.
    """
    post_delta_session = session_template.model_copy(deep=True)
    post_delta_session.canonical_state = deepcopy(post_delta_canonical_state)
    post_delta_session.current_scene_id = prior_scene_id

    accepted_targets = _sorted_targets(accepted_deltas)
    rejected_targets = _sorted_targets(rejected_deltas)
    committed_trigger_ids = sorted(set(decision.detected_triggers or []))

    base_consequences = [f"state_changed:{t}" for t in accepted_targets]

    ending_id, ending_legality = SceneTransitionLegality.check_ending_legal(
        module,
        session=post_delta_session,
        detected_triggers=decision.detected_triggers,
    )
    if ending_id and ending_legality.allowed:
        consequences = list(base_consequences)
        consequences.append(f"ending_reached:{ending_id}")
        consequences.append(f"scene_continue:{prior_scene_id}")
        return NarrativeCommitRecord(
            turn_number=turn_number,
            prior_scene_id=prior_scene_id,
            committed_scene_id=prior_scene_id,
            situation_status="ending_reached",
            committed_ending_id=ending_id,
            accepted_delta_targets=accepted_targets,
            rejected_delta_targets=rejected_targets,
            committed_trigger_ids=committed_trigger_ids,
            guard_outcome=guard_outcome.value,
            authoritative_reason=ending_legality.reason
            or f"Ending '{ending_id}' legally triggered after post-delta state.",
            canonical_consequences=consequences,
            is_terminal=True,
        )

    proposed = decision.proposed_scene_id
    if proposed:
        transition_decision = SceneTransitionLegality.check_transition_legal(
            prior_scene_id,
            proposed,
            module,
            session=post_delta_session,
            detected_triggers=decision.detected_triggers,
        )
        if transition_decision.allowed:
            consequences = list(base_consequences)
            consequences.append(f"scene_transition:{prior_scene_id}->{proposed}")
            return NarrativeCommitRecord(
                turn_number=turn_number,
                prior_scene_id=prior_scene_id,
                committed_scene_id=proposed,
                situation_status="transitioned",
                committed_ending_id=None,
                accepted_delta_targets=accepted_targets,
                rejected_delta_targets=rejected_targets,
                committed_trigger_ids=committed_trigger_ids,
                guard_outcome=guard_outcome.value,
                authoritative_reason=transition_decision.reason
                or f"Legal transition from '{prior_scene_id}' to '{proposed}'.",
                canonical_consequences=consequences,
                is_terminal=False,
            )

    consequences = list(base_consequences)
    consequences.append(f"scene_continue:{prior_scene_id}")
    return NarrativeCommitRecord(
        turn_number=turn_number,
        prior_scene_id=prior_scene_id,
        committed_scene_id=prior_scene_id,
        situation_status="continue",
        committed_ending_id=None,
        accepted_delta_targets=accepted_targets,
        rejected_delta_targets=rejected_targets,
        committed_trigger_ids=committed_trigger_ids,
        guard_outcome=guard_outcome.value,
        authoritative_reason=(
            "No legal ending or legal explicit scene transition; continuing in current scene."
        ),
        canonical_consequences=consequences,
        is_terminal=False,
    )
