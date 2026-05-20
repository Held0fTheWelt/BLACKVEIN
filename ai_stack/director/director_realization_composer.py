"""Director realization composer.

The Director composes the realization plan for a player turn. Given the
resolver's semantic output, it decides:

- which realization owner narrates the turn (narrator, actor_line, or both)
- which capabilities are invoked
- the outcome disposition (success / partial / fail) and reason
- the language target for visible realization

This is the only place that decides what gets realized for a player turn.
It replaces the old binary router `_route_after_resolve_player_action` and the
synthetic short-path `_authoritative_action_resolution_turn`.

In PR-A the composer is deterministic for movement turns. Later phases add
semantic LLM-driven decisions for object interaction, questions, and richer
Glueck outcomes.
"""

from __future__ import annotations

from typing import Any


REALIZATION_PLAN_SCHEMA_VERSION = "realization_plan.v1"


REALIZATION_OWNER_NARRATOR = "narrator"
REALIZATION_OWNER_ACTOR_LINE = "actor_line"
REALIZATION_OWNER_NARRATOR_AND_ACTOR = "narrator+actor_line"


OUTCOME_SUCCESS = "success"
OUTCOME_PARTIAL = "partial"
OUTCOME_FAIL = "fail"


CAPABILITY_NARRATOR_LOCATION_TRANSITION = "narrator.location_transition.describe"
CAPABILITY_NARRATOR_PERCEPTION = "narrator.perception.describe"
CAPABILITY_NARRATOR_CLARIFICATION = "narrator.clarification.describe"
CAPABILITY_NARRATOR_KANON_REFUSAL = "narrator.kanon_break_refusal.describe"
CAPABILITY_NARRATOR_DEFERRED = "narrator.deferred_capability.placeholder"
CAPABILITY_ACTOR_SPEECH = "actor_line.speech"


def compose_realization_plan(
    *,
    player_action_frame: dict[str, Any],
    affordance_resolution: dict[str, Any],
    kanon_break: bool,
    kanon_break_reason: str | None,
    session_output_language: str,
    scene_affordance_model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose a realization_plan.v1 for the current player turn.

    The Director is consulted on every player turn (no bypass). For PR-A the
    decision is deterministic over movement; richer Glueck decisions and
    semantic LLM-driven choices come in PR-A.2 / PR-A.3.
    """

    pik = str(player_action_frame.get("player_input_kind") or "").strip().lower()
    action_kind = str(player_action_frame.get("action_kind") or "").strip().lower()
    aff_status = str(affordance_resolution.get("affordance_status") or "").strip().lower()
    commit_policy = str(affordance_resolution.get("action_commit_policy") or "").strip().lower()
    target_type = str(player_action_frame.get("resolved_target_type") or "").strip().lower()
    target_id = str(player_action_frame.get("resolved_target_id") or "").strip() or None
    lang = str(session_output_language or "de").strip().lower()[:2] or "de"

    if kanon_break:
        return _plan(
            owner=REALIZATION_OWNER_NARRATOR,
            capabilities=[CAPABILITY_NARRATOR_KANON_REFUSAL],
            outcome=OUTCOME_FAIL,
            outcome_reason=kanon_break_reason or "kanon_break",
            decision_reason="kanon_break_refused",
            language=lang,
        )

    if commit_policy in {"needs_clarification", "recover_or_reject"} or aff_status in {
        "unknown_target",
        "ambiguous",
    }:
        return _plan(
            owner=REALIZATION_OWNER_NARRATOR,
            capabilities=[CAPABILITY_NARRATOR_CLARIFICATION],
            outcome=OUTCOME_PARTIAL,
            outcome_reason=str(affordance_resolution.get("reason") or "needs_clarification"),
            decision_reason="resolver_uncertain",
            language=lang,
        )

    # A perception query addresses the world, not an NPC: the player asks
    # what they find / see / hear at a known location or object. The narrator
    # answers in-world; this is NOT actor_line speech. We only route to
    # speech when the player input is a true speech act (addressing someone,
    # exclamation, statement) without a perception target.
    is_perception_query = (
        pik in {"question", "perception", "perception_action"}
        and target_type in {"location", "object"}
        and aff_status in {"allowed", "allowed_offscreen", "partial"}
    )
    if is_perception_query:
        return _plan(
            owner=REALIZATION_OWNER_NARRATOR,
            capabilities=[CAPABILITY_NARRATOR_PERCEPTION],
            outcome=OUTCOME_SUCCESS,
            outcome_reason="perception_of_known_target",
            decision_reason="perception_realization",
            language=lang,
            extras={"target_location_id": target_id} if target_type == "location" else None,
        )

    if commit_policy == "commit_speech" or pik == "speech":
        return _plan(
            owner=REALIZATION_OWNER_ACTOR_LINE,
            capabilities=[CAPABILITY_ACTOR_SPEECH],
            outcome=OUTCOME_SUCCESS,
            outcome_reason="player_speaks",
            decision_reason="speech_realization",
            language=lang,
        )

    if (
        action_kind == "movement"
        and target_type == "location"
        and aff_status in {"allowed", "allowed_offscreen", "partial"}
        and commit_policy == "commit_action"
    ):
        return _plan(
            owner=REALIZATION_OWNER_NARRATOR,
            capabilities=[CAPABILITY_NARRATOR_LOCATION_TRANSITION],
            outcome=OUTCOME_SUCCESS,
            outcome_reason="movement_to_known_location",
            decision_reason="movement_realization",
            language=lang,
            extras={"target_location_id": target_id},
        )

    return _plan(
        owner=REALIZATION_OWNER_NARRATOR,
        capabilities=[CAPABILITY_NARRATOR_DEFERRED],
        outcome=OUTCOME_PARTIAL,
        outcome_reason="deferred_to_later_phase",
        decision_reason="out_of_pr_a_scope",
        language=lang,
    )


def _plan(
    *,
    owner: str,
    capabilities: list[str],
    outcome: str,
    outcome_reason: str,
    decision_reason: str,
    language: str,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "schema_version": REALIZATION_PLAN_SCHEMA_VERSION,
        "realization_owner": owner,
        "capabilities_selected": list(capabilities),
        "outcome_disposition": {
            "outcome": outcome,
            "reason": outcome_reason,
        },
        "language_target": language,
        "visibility_constraints": [],
        "decision_reason": decision_reason,
    }
    if extras:
        plan.update(extras)
    return plan
