"""Playability helpers: quality vs hard-boundary failures, degraded commit, rewrite hints.

Used by the LangGraph runtime turn executor for bounded self-correction. Lives in ``ai_stack``
so the executor does not depend on world-engine application packages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

REWRITEABLE_VALIDATION_REASONS = frozenset(
    {
        "dramatic_alignment_narrative_too_short",
        "dramatic_alignment_insufficient_mass",
        "dramatic_alignment_insufficient_mass_thin_or_silence",
        "dramatic_alignment_withhold_requires_min_beat",
        "opening_leniency_approved",
        "empty_visible_output",
        "meta_output_detected",
        "insufficient_scene_grounding",
        "insufficient_character_reaction",
        "parser_error",
        "model_generation_failed",
        "actor_lane_illegal_actor",
        "actor_lane_invalid_initiative_type",
        "actor_lane_scene_function_mismatch",
    }
)

HARD_BOUNDARY_REASON_PREFIXES = (
    "scene_",
    "character_",
    "trigger_",
    "boundary_",
    "illegal_",
    "canonical_",
)

# Explicit degraded-commit policy table:
# - Allowed: legal-but-weak prose outcomes after retries (tagged degraded_commit).
# - Blocked: structural / legality / parser / empty-structure failures.
DEGRADED_COMMIT_ALLOWED_REASONS = frozenset(
    {
        "dramatic_alignment_narrative_too_short",
        "dramatic_alignment_insufficient_mass",
        "dramatic_alignment_insufficient_mass_thin_or_silence",
        "dramatic_alignment_withhold_requires_min_beat",
        "dramatic_effect_reject_empty_fluency",
        "empty_visible_output",
        "opening_leniency_approved",
        "insufficient_character_reaction",
    }
)

DEGRADED_COMMIT_BLOCK_REASONS = frozenset(
    {
        "actor_lane_illegal_actor",
        "actor_lane_invalid_initiative_type",
        "actor_lane_scene_function_mismatch",
        "malformed_proposed_effect",
        "incomplete_proposed_effect",
        "model_generation_failed",
    }
)

DEGRADED_COMMIT_BLOCK_FEEDBACK_CODES = frozenset(
    {
        "parser_error",
        "model_call_failed",
    }
)


@dataclass(slots=True)
class PlayabilityDecision:
    should_retry: bool
    allow_degraded_commit: bool
    feedback_codes: list[str]
    hard_boundary_failure: bool
    preserve_actor_lanes: bool = False


def _reason(outcome: dict[str, Any] | None) -> str:
    if not isinstance(outcome, dict):
        return ""
    return str(outcome.get("reason") or "").strip()


def is_hard_boundary_failure(outcome: dict[str, Any] | None) -> bool:
    reason = _reason(outcome)
    if not reason:
        return False
    if reason.startswith(HARD_BOUNDARY_REASON_PREFIXES):
        return True
    geo = outcome.get("dramatic_effect_gate_outcome") if isinstance(outcome, dict) else None
    if isinstance(geo, dict):
        codes = [str(x) for x in geo.get("effect_rationale_codes") or []]
        return any(code.startswith(HARD_BOUNDARY_REASON_PREFIXES) for code in codes)
    return False


def collect_playability_feedback_codes(
    *,
    outcome: dict[str, Any] | None,
    generation: dict[str, Any] | None,
    proposed_state_effects: list[dict[str, Any]] | None = None,
) -> list[str]:
    feedback: list[str] = []
    reason = _reason(outcome)
    if reason:
        feedback.append(reason)
    gen = generation if isinstance(generation, dict) else {}
    meta = gen.get("metadata") if isinstance(gen.get("metadata"), dict) else {}
    if gen.get("success") is False:
        feedback.append("model_call_failed")
    if meta.get("langchain_parser_error"):
        feedback.append("parser_error")
    raw = str(gen.get("model_raw_text") or gen.get("content") or "")
    if raw.strip().startswith("[mock]"):
        feedback.append("mock_fallback_output")
    if len(raw.strip()) < 80:
        feedback.append("narration_too_short")
    proposed = proposed_state_effects if isinstance(proposed_state_effects, list) else []
    if not proposed:
        feedback.append("no_structured_effects")
    deduped: list[str] = []
    for code in feedback:
        c = str(code or "").strip()
        if c and c not in deduped:
            deduped.append(c)
    return deduped


def _degraded_commit_allowed(
    *,
    reason: str,
    feedback: list[str],
    actor_lane_validation: dict[str, Any] | None,
    generation: dict[str, Any] | None = None,
) -> bool:
    """Determine whether degraded commit is legal under explicit policy."""
    if reason in DEGRADED_COMMIT_BLOCK_REASONS:
        return False
    gen = generation if isinstance(generation, dict) else {}
    for code in feedback:
        if code not in DEGRADED_COMMIT_BLOCK_FEEDBACK_CODES:
            continue
        if code == "parser_error" and bool(gen.get("fallback_used")):
            # Graph-managed fallback prose often carries parser errors by
            # construction; allow bounded degraded commit for prose-only
            # outcomes when fallback already succeeded.
            continue
        return False
    if isinstance(actor_lane_validation, dict) and actor_lane_validation.get("status") == "rejected":
        return False
    if reason in DEGRADED_COMMIT_ALLOWED_REASONS:
        return True
    return False


def decide_playability_recovery(
    *,
    turn_number: int,
    attempt_index: int,
    max_attempts: int,
    outcome: dict[str, Any] | None,
    generation: dict[str, Any] | None,
    proposed_state_effects: list[dict[str, Any]] | None = None,
    allow_degraded_commit_after_retries: bool = True,
    actor_lane_validation: dict[str, Any] | None = None,
) -> PlayabilityDecision:
    hard_boundary = is_hard_boundary_failure(outcome)
    feedback = collect_playability_feedback_codes(
        outcome=outcome,
        generation=generation,
        proposed_state_effects=proposed_state_effects,
    )
    status = str((outcome or {}).get("status") or "")
    reason = _reason(outcome)
    rewriteable = False
    if status == "rejected" and not hard_boundary:
        rewriteable = (
            reason in REWRITEABLE_VALIDATION_REASONS
            or "parser_error" in feedback
            or "mock_fallback_output" in feedback
            or "narration_too_short" in feedback
            or "no_structured_effects" in feedback
        )
    should_retry = rewriteable and attempt_index < max_attempts
    allow_degraded = (
        allow_degraded_commit_after_retries
        and rewriteable
        and not should_retry
        and not hard_boundary
        and turn_number <= 12
        and _degraded_commit_allowed(
            reason=reason,
            feedback=feedback,
            actor_lane_validation=actor_lane_validation,
            generation=generation,
        )
    )
    actor_lane_healthy = (
        isinstance(actor_lane_validation, dict)
        and actor_lane_validation.get("status") == "approved"
        and actor_lane_validation.get("reason") == "actor_lane_legal"
    )
    prose_only_reject = reason in {
        "dramatic_alignment_narrative_too_short",
        "dramatic_alignment_insufficient_mass",
        "dramatic_alignment_insufficient_mass_thin_or_silence",
        "dramatic_alignment_withhold_requires_min_beat",
        "dramatic_effect_reject_empty_fluency",
        "empty_visible_output",
    }
    preserve_actor_lanes = actor_lane_healthy and prose_only_reject
    return PlayabilityDecision(
        should_retry=should_retry,
        allow_degraded_commit=allow_degraded,
        feedback_codes=feedback,
        hard_boundary_failure=hard_boundary,
        preserve_actor_lanes=preserve_actor_lanes,
    )


def build_rewrite_instruction(feedback_codes: list[str], allowed_actor_ids: list[str] | None = None, preserve_actor_lanes: bool = False) -> str:
    if preserve_actor_lanes:
        preserve_prefix = (
            "Your actor lanes (primary_responder_id, spoken_lines, action_lines, initiative_events) are structurally valid — "
            "do NOT change them. Only improve narration_summary. Do not invent new actors, new dialogue, or new actions. "
        )
    else:
        preserve_prefix = ""

    issues = ", ".join(str(x) for x in feedback_codes[:8]) or "quality_improvement_needed"
    base_instruction = (
        "Rewrite the previous runtime turn so it is commit-worthy. "
        "Stay strictly inside canonical module boundaries, remain in-scene, avoid meta commentary, "
        "produce concrete narrative progression with visible character reaction, and fix these issues: "
        f"{issues}."
    )

    actor_lane_issues = [
        code
        for code in feedback_codes
        if code.startswith("actor_lane_")
        or code in {"human_actor_selected_as_responder", "ai_controlled_human_actor"}
    ]
    if actor_lane_issues:
        allowed_str = ", ".join(sorted(allowed_actor_ids or [])) or "the approved responder set"
        actor_feedback = (
            " When populating actor lanes: "
            f"use only these approved actor IDs: {allowed_str}. "
            "Populate spoken_lines with speaker_id, action_lines with actor_id, and initiative_events with valid types. "
            "Do not invent new actor IDs. Do not include the human/player actor in primary_responder_id, "
            "secondary_responder_ids, responder_actor_ids, spoken_lines, action_lines, initiative_events, or narration-as-action."
        )
        return preserve_prefix + base_instruction + actor_feedback

    return preserve_prefix + base_instruction


def degrade_validation_outcome(
    outcome: dict[str, Any] | None,
    *,
    reason: str = "degraded_commit_after_retries",
) -> dict[str, Any]:
    base = dict(outcome or {})
    base["status"] = "approved"
    base["reason"] = reason
    geo = base.get("dramatic_effect_gate_outcome") if isinstance(base.get("dramatic_effect_gate_outcome"), dict) else {}
    geo = dict(geo)
    geo["gate_result"] = reason
    geo["rejection_reasons"] = []
    geo["legacy_fallback_used"] = bool(geo.get("legacy_fallback_used"))
    geo["empty_fluency_risk"] = "managed"
    base["dramatic_effect_gate_outcome"] = geo
    return base
