"""Bounded narrative commit models and resolver for the story runtime (Task B).

This is not a full world-state simulation: commits record session-local, legal
scene progression and interpretation linkage only.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field
from ai_stack.social_state_contract import SocialStateRecord
from ai_stack.social_state_goc import social_state_fingerprint

logger = logging.getLogger(__name__)

from app.story_runtime.narrative_commit_resolution import (
    build_base_consequences,
    build_interpretation_summary,
    eval_core_transition_rules,
    overlay_terminal_scene,
    prepare_open_pressures,
)

SituationStatus = Literal["continue", "transitioned", "blocked", "terminal"]

# Stable codes for programmatic checks (aligned with former progression_commit.reason).
CommitReasonCode = Literal[
    "no_scene_proposal",
    "already_in_scene",
    "unknown_target_scene",
    "transition_hints_missing",
    "illegal_transition_not_allowed",
    "legal_transition_committed",
]


class ActorLineSummary(BaseModel):
	"""Typed per-actor line summary for committed planner truth."""

	model_config = {"extra": "forbid"}

	actor_id: str
	line_count: int = 0
	text_preview: str | None = None


class BeatProgression(BaseModel):
    """Committed dramatic-continuity structure carried across turns.

    The runtime uses a single beat identity per committed turn — composed from
    the committed scene and the selected scene function — so the director can
    key pacing and responder decisions off a stable continuity signal instead
    of inferring it from loose continuity impacts each turn.

    When a commit's beat identity matches the prior turn's, the record sets
    ``advanced=False`` and ``advancement_reason="continuity_carry_forward"``.
    Advancing to a new beat sets ``advanced=True`` with a reason describing
    why (scene transition, scene-function shift, blocked turn, and so on).
    """

    model_config = {"extra": "forbid"}

    beat_id: str = Field(
        ...,
        description="Stable identifier of the current beat / dramatic phase. "
        "Composed from committed_scene_id + selected_scene_function by default; "
        "may be overridden by an explicit scene-plan beat id.",
    )
    beat_slot: int = Field(
        default=0,
        description="Monotonic slot within the current beat identity. 0 for a "
        "newly advanced beat; increments when continuity carries forward.",
    )
    pressure_state: str | None = Field(
        default=None,
        description="Dominant continuity pressure label (e.g. tension_escalation, "
        "alliance_shift, repair_attempt) active on this turn.",
    )
    pacing_carry_forward: str | None = None
    responder_focus_carry_forward: list[str] = Field(default_factory=list)
    advanced: bool = Field(
        default=True,
        description="True when this turn advanced to a new beat_id; False when "
        "continuity carried forward from the prior turn.",
    )
    advancement_reason: str = Field(
        default="initial_beat",
        description="Stable code explaining why the beat advanced or carried "
        "forward (e.g. initial_beat, scene_transition, function_shift, "
        "continuity_carry_forward, blocked_turn_no_advance).",
    )
    continuity_carry_forward_reason: str | None = Field(
        default=None,
        description="Populated when the beat carried forward; explains the "
        "dominant continuity signal (dominant continuity-impact class, "
        "pacing continuity, or 'no_signal').",
    )
    prior_beat_id: str | None = None


class PlannerTruth(BaseModel):
    """Bounded snapshot of director/validator state preserved into the commit record.

    This is the dramatic-planner view the runtime used to validate and shape
    the turn. Persisting it alongside the scene-progression commit lets later
    readers explain *why* a turn was accepted, not only that it was accepted.
    All fields are optional; an absent value means the planner lane did not
    emit a value for this turn (for example under a degraded generation path).
    """

    model_config = {"extra": "forbid"}

    selected_scene_function: str | None = None
    responder_id: str | None = None
    primary_responder_id: str | None = None
    secondary_responder_ids: list[str] = Field(default_factory=list)
    responder_scope: list[str] = Field(default_factory=list)
    function_type: str | None = None
    pacing_mode: str | None = None
    silence_mode: str | None = None
    spoken_line_count: int = 0
    action_line_count: int = 0
    initiative_summary: dict[str, Any] = Field(default_factory=dict)
    last_actor_outcome_summary: str | None = None
    scene_assessment_core: dict[str, Any] = Field(default_factory=dict)
    scene_plan_ref: str | None = None
    emotional_shift: dict[str, Any] = Field(default_factory=dict)
    social_outcome: str | None = None
    dramatic_direction: str | None = None
    dramatic_effect_gate: dict[str, Any] = Field(default_factory=dict)
    social_state_summary: dict[str, Any] = Field(default_factory=dict)
    character_mind_summary: dict[str, Any] = Field(default_factory=dict)
    validation_status: str | None = None
    validation_reason: str | None = None
    validator_layers_used: list[str] = Field(default_factory=list)
    continuity_impacts: list[dict[str, Any]] = Field(default_factory=list)
    realized_secondary_responder_ids: list[str] = Field(
        default_factory=list,
        description="Secondary responders that appeared in spoken/action lines (not just director scope). Initiative-only events do NOT qualify."
    )
    interruption_actor_id: str | None = Field(
        default=None,
        description="Actor who realized an interrupt initiative event, if any. Kept separate from realized_secondary_responder_ids."
    )
    spoken_actor_summaries: list[ActorLineSummary] = Field(
        default_factory=list,
        description="Per-actor spoken-line summaries."
    )
    action_actor_summaries: list[ActorLineSummary] = Field(
        default_factory=list,
        description="Per-actor action-line summaries."
    )
    social_pressure_shift: str | None = Field(
        default=None,
        description="Pressure direction this turn: escalated/de-escalated/held/shifted. Derived from explicit state_effects first."
    )
    carry_forward_tension_notes: str | None = Field(
        default=None,
        description="Unresolved tension from pressure_shift, accusation, repair failure, or interruption residue."
    )


class StoryNarrativeCommitRecord(BaseModel):
    """Authoritative, JSON-safe summary of one story-runtime turn commit."""

    model_config = {"extra": "forbid"}

    turn_number: int
    prior_scene_id: str | None = None
    proposed_scene_id: str | None = None
    committed_scene_id: str
    situation_status: SituationStatus
    allowed: bool = False
    authoritative_reason: str = Field(
        ...,
        description="Short English explanation of the commit outcome for operators.",
    )
    commit_reason_code: str = Field(
        ...,
        description="Stable machine-readable reason code.",
    )
    selected_candidate_source: str | None = None
    candidate_sources: list[dict[str, Any]] = Field(default_factory=list)
    model_structured_proposed_scene_id: str | None = Field(
        default=None,
        description="Raw proposed_scene_id from model structured output, if any (may be unknown).",
    )
    committed_interpretation_summary: dict[str, Any] = Field(default_factory=dict)
    committed_consequences: list[str] = Field(default_factory=list)
    open_pressures: list[str] = Field(default_factory=list)
    resolved_pressures: list[str] = Field(default_factory=list)
    is_terminal: bool = False
    planner_truth: PlannerTruth = Field(
        default_factory=PlannerTruth,
        description="Bounded planner-truth snapshot preserved from the live graph state.",
    )
    beat_progression: BeatProgression | None = Field(
        default=None,
        description="Committed dramatic-continuity structure; None for commits that "
        "predate this contract version.",
    )
    commit_contract_version: str = Field(
        default="story_narrative_commit_record.v3",
        description="Stable identifier for the commit contract shape; bump when persisted shape changes.",
    )


def _scene_row_canonical_id(scene: dict[str, Any]) -> str | None:
    """Canonical scene id for runtime projection rows (compiler + hand-built payloads).

    Backend compiler historically emitted ``scene_id``; story-runtime originally read
    ``id`` only. Accept both to prevent an empty known-scene set at the commit seam (F-C1).
    """
    for key in ("id", "scene_id"):
        raw = scene.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def _scene_ids(runtime_projection: dict[str, Any]) -> set[str]:
    scenes = runtime_projection.get("scenes", [])
    scene_ids: set[str] = set()
    if isinstance(scenes, list):
        for scene in scenes:
            if isinstance(scene, dict):
                sid = _scene_row_canonical_id(scene)
                if sid:
                    scene_ids.add(sid)
    return scene_ids


def _terminal_scene_ids(runtime_projection: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    raw = runtime_projection.get("terminal_scene_ids")
    if isinstance(raw, list):
        for x in raw:
            if isinstance(x, str) and x.strip():
                ids.add(x.strip())
    scenes = runtime_projection.get("scenes", [])
    if isinstance(scenes, list):
        for scene in scenes:
            if isinstance(scene, dict) and scene.get("terminal") is True:
                sid = _scene_row_canonical_id(scene)
                if sid:
                    ids.add(sid)
    return ids


def _transition_map(runtime_projection: dict[str, Any]) -> dict[str, set[str]]:
    hints = runtime_projection.get("transition_hints", [])
    mapping: dict[str, set[str]] = {}
    if isinstance(hints, list):
        for hint in hints:
            if not isinstance(hint, dict):
                continue
            from_scene = hint.get("from")
            to_scene = hint.get("to")
            if not isinstance(from_scene, str) or not from_scene.strip():
                continue
            if not isinstance(to_scene, str) or not to_scene.strip():
                continue
            key = from_scene.strip()
            mapping.setdefault(key, set()).add(to_scene.strip())
    return mapping


def _scene_candidate_from_command(interpreted_input: dict[str, Any], known_scene_ids: set[str]) -> str | None:
    kind = str(interpreted_input.get("kind") or "").strip().lower()
    command_name = str(interpreted_input.get("command_name") or "").strip().lower()
    command_args = interpreted_input.get("command_args")
    if kind == "explicit_command" and command_name in {"move", "goto", "go", "scene", "travel"}:
        if isinstance(command_args, list):
            for raw_arg in command_args:
                arg = str(raw_arg).strip()
                if arg in known_scene_ids:
                    return arg
    return None


def _scene_candidate_from_token_scan(player_input: str, known_scene_ids: set[str]) -> str | None:
    tokens = re.split(r"[^a-zA-Z0-9_\\-]+", player_input or "")
    for token in tokens:
        candidate = token.strip()
        if candidate and candidate in known_scene_ids:
            return candidate
    return None


def _model_proposed_scene_raw(generation: dict[str, Any] | None) -> str | None:
    if not isinstance(generation, dict) or generation.get("success") is not True:
        return None
    meta = generation.get("metadata")
    if not isinstance(meta, dict):
        return None
    structured = meta.get("structured_output")
    if not isinstance(structured, dict):
        return None
    pid = structured.get("proposed_scene_id")
    if isinstance(pid, str) and pid.strip():
        return pid.strip()
    return None


def _scene_candidate_from_model(generation: dict[str, Any] | None, known_scene_ids: set[str]) -> str | None:
    raw = _model_proposed_scene_raw(generation)
    if raw is None:
        return None
    if known_scene_ids and raw not in known_scene_ids:
        return None
    return raw


def _resolve_scene_proposal(
    *,
    player_input: str,
    interpreted_input: dict[str, Any],
    known_scene_ids: set[str],
    generation: dict[str, Any] | None,
) -> tuple[str | None, str | None, list[dict[str, Any]], str | None]:
    """Deterministic priority: explicit command → model (known id) → token scan."""
    candidate_sources: list[dict[str, Any]] = []
    model_raw = _model_proposed_scene_raw(generation)

    from_command = _scene_candidate_from_command(interpreted_input, known_scene_ids)
    if from_command is not None:
        candidate_sources.append({"source": "explicit_command", "scene_id": from_command})

    if model_raw is not None:
        entry: dict[str, Any] = {"source": "model_structured_output", "scene_id": model_raw}
        if known_scene_ids and model_raw not in known_scene_ids:
            entry["rejected_unknown_scene"] = True
        candidate_sources.append(entry)

    from_tokens = _scene_candidate_from_token_scan(player_input, known_scene_ids)
    if from_tokens is not None:
        candidate_sources.append({"source": "player_input_token_scan", "scene_id": from_tokens})

    from_model = _scene_candidate_from_model(generation, known_scene_ids)

    if from_command is not None:
        return from_command, "explicit_command", candidate_sources, model_raw
    if from_model is not None:
        return from_model, "model_structured_output", candidate_sources, model_raw
    if from_tokens is not None:
        return from_tokens, "player_input_token_scan", candidate_sources, model_raw
    return None, None, candidate_sources, model_raw


def _interpretation_kind_tag(kind: Any) -> str:
    k = str(kind or "unknown").strip().lower() or "unknown"
    return k.replace(" ", "_")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, dict):
                actor_id = item.get("actor_id") or item.get("responder_id")
                if isinstance(actor_id, str) and actor_id.strip():
                    out.append(actor_id.strip())
                continue
            text = str(item).strip()
            if text:
                out.append(text)
        return out
    return []


def _resolve_validator_layers(
    validation: dict[str, Any], gate: dict[str, Any]
) -> list[str]:
    """Return the list of validator layers that actually ran on this turn.

    Prefers an explicit ``layers_used`` / ``validator_layers_used`` list
    published by the validator, and otherwise infers layers from observable
    signals (the ``validator_lane`` id and the presence of a dramatic-effect
    gate outcome). The result is the set of layers a reader can audit — not a
    wishlist of layers the live path *should* run.
    """
    explicit = _as_str_list(
        validation.get("validator_layers_used") or validation.get("layers_used")
    )
    if explicit:
        return explicit
    inferred: list[str] = []
    lane = validation.get("validator_lane")
    if isinstance(lane, str) and lane.strip():
        inferred.append(lane.strip())
    if isinstance(gate, dict) and gate:
        inferred.append("dramatic_effect_gate")
    return inferred


def _social_state_summary_from_graph_state(graph_state: dict[str, Any]) -> dict[str, Any]:
    """Preserve the bounded social-state record in committed planner truth."""
    explicit = _as_dict(graph_state.get("social_state_summary"))
    record = _as_dict(graph_state.get("social_state_record"))
    if not record:
        return explicit

    summary = dict(explicit)
    summary.setdefault("summary_source", "social_state_record")
    summary["record"] = record
    for key in (
        "scene_pressure_state",
        "guidance_phase_key",
        "responder_asymmetry_code",
        "social_risk_band",
        "active_thread_count",
        "thread_pressure_summary_present",
        "prior_continuity_classes",
        "prior_social_state_fingerprint",
        "prior_social_risk_band",
        "social_continuity_status",
    ):
        if key in record:
            summary.setdefault(key, record.get(key))

    try:
        summary.setdefault(
            "fingerprint",
            social_state_fingerprint(SocialStateRecord.model_validate(record)),
        )
        summary["validated"] = True
    except Exception:
        summary["validated"] = False
    return summary


def _planner_truth_from_graph_state(
    *,
    graph_state: dict[str, Any] | None,
    generation: dict[str, Any] | None,
) -> PlannerTruth:
    """Extract a bounded planner-truth snapshot from the live runtime state.

    Top-level ``RuntimeTurnState`` keys populated by the graph's
    ``proposal_normalize`` node are the primary source. When a key is missing
    from state, the extractor falls back to the model's structured output on
    ``generation.metadata.structured_output`` so partially-degraded turns still
    surface what they can. An absent value stays None / empty so readers can
    distinguish "planner did not emit" from "planner emitted empty".
    """
    if not isinstance(graph_state, dict):
        graph_state = {}
    gen = generation if isinstance(generation, dict) else {}
    meta = _as_dict(gen.get("metadata"))
    structured = _as_dict(meta.get("structured_output"))
    validation = _as_dict(graph_state.get("validation_outcome"))
    gate = _as_dict(graph_state.get("dramatic_effect_gate_outcome"))
    if not gate:
        gate = _as_dict(graph_state.get("dramatic_effect_gate"))
    scene_assessment = _as_dict(graph_state.get("scene_assessment"))
    if not scene_assessment:
        scene_assessment = _as_dict(graph_state.get("scene_assessment_core"))

    def _opt_str(*candidates: Any) -> str | None:
        for c in candidates:
            if isinstance(c, str) and c.strip():
                return c.strip()
        return None

    responder_scope = _as_str_list(
        graph_state.get("responder_scope")
        or graph_state.get("selected_responder_set")
        or structured.get("responder_scope")
    )

    primary_responder_id = _opt_str(
        graph_state.get("responder_id"),
        graph_state.get("primary_responder_id"),
        structured.get("primary_responder_id"),
        structured.get("responder_id"),
    )
    secondary_responder_ids = _as_str_list(
        graph_state.get("secondary_responder_ids")
        or structured.get("secondary_responder_ids")
        or structured.get("responder_actor_ids")
    )
    if primary_responder_id and primary_responder_id in secondary_responder_ids:
        secondary_responder_ids = [x for x in secondary_responder_ids if x != primary_responder_id]

    bundle = _as_dict(graph_state.get("visible_output_bundle"))

    def _lane_count(value: Any) -> int:
        if not isinstance(value, list):
            return 0
        count = 0
        for item in value:
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                if text:
                    count += 1
                continue
            if str(item).strip():
                count += 1
        return count

    spoken_line_count = _lane_count(bundle.get("spoken_lines"))
    action_line_count = _lane_count(bundle.get("action_lines"))

    initiative_events = structured.get("initiative_events")
    initiative_summary: dict[str, Any] = {}
    if isinstance(initiative_events, list):
        types: list[str] = []
        actors: list[str] = []
        for row in initiative_events:
            if not isinstance(row, dict):
                continue
            raw_type = row.get("type")
            raw_actor = row.get("actor_id")
            event_type = str(raw_type).strip() if isinstance(raw_type, str) else ""
            actor_id = str(raw_actor).strip() if isinstance(raw_actor, str) else ""
            if event_type and event_type not in types:
                types.append(event_type)
            if actor_id and actor_id not in actors:
                actors.append(actor_id)
        initiative_summary = {
            "event_count": len([x for x in initiative_events if isinstance(x, dict)]),
            "event_types": types,
            "actors": actors,
        }

    social_outcome = _opt_str(graph_state.get("social_outcome"), structured.get("social_outcome"))
    dramatic_direction = _opt_str(
        graph_state.get("dramatic_direction"),
        structured.get("dramatic_direction"),
    )
    parts: list[str] = []
    if primary_responder_id:
        parts.append(f"primary_responder={primary_responder_id}")
    parts.append(f"spoken_lines={spoken_line_count}")
    parts.append(f"action_lines={action_line_count}")
    if initiative_summary.get("event_count"):
        parts.append(f"initiative_events={initiative_summary.get('event_count')}")
    if social_outcome:
        parts.append(f"social_outcome={social_outcome}")
    if dramatic_direction:
        parts.append(f"dramatic_direction={dramatic_direction}")
    last_actor_outcome_summary = ", ".join(parts) if parts else None

    # Extract realized secondary responders from spoken/action lanes
    realized_secondary_responder_ids: list[str] = []
    spoken_lines = structured.get("spoken_lines")
    action_lines = structured.get("action_lines")
    if isinstance(spoken_lines, list):
        for item in spoken_lines:
            if isinstance(item, dict):
                speaker_id = item.get("speaker_id")
                if isinstance(speaker_id, str) and speaker_id.strip():
                    speaker_id = speaker_id.strip()
                    if speaker_id in secondary_responder_ids and speaker_id not in realized_secondary_responder_ids:
                        realized_secondary_responder_ids.append(speaker_id)
    if isinstance(action_lines, list):
        for item in action_lines:
            if isinstance(item, dict):
                actor_id = item.get("actor_id")
                if isinstance(actor_id, str) and actor_id.strip():
                    actor_id = actor_id.strip()
                    if actor_id in secondary_responder_ids and actor_id not in realized_secondary_responder_ids:
                        realized_secondary_responder_ids.append(actor_id)

    # Extract interruption actor from initiative events
    interruption_actor_id: str | None = None
    if isinstance(initiative_events, list):
        for event in initiative_events:
            if isinstance(event, dict) and event.get("type") == "interrupt":
                actor_id = event.get("actor_id")
                if isinstance(actor_id, str) and actor_id.strip():
                    interruption_actor_id = actor_id.strip()
                    break

    # Extract spoken and action summaries by actor
    spoken_actor_summaries: list[ActorLineSummary] = []
    if isinstance(spoken_lines, list):
        spoken_by_actor: dict[str, list[str]] = {}
        for item in spoken_lines:
            if isinstance(item, dict):
                speaker_id = item.get("speaker_id")
                if isinstance(speaker_id, str) and speaker_id.strip():
                    speaker_id = speaker_id.strip()
                    text = item.get("text")
                    if isinstance(text, str):
                        if speaker_id not in spoken_by_actor:
                            spoken_by_actor[speaker_id] = []
                        spoken_by_actor[speaker_id].append(text)
        for actor_id, texts in spoken_by_actor.items():
            preview = (texts[0][:120] if texts and isinstance(texts[0], str) else None)
            spoken_actor_summaries.append(
                ActorLineSummary(actor_id=actor_id, line_count=len(texts), text_preview=preview)
            )

    action_actor_summaries: list[ActorLineSummary] = []
    if isinstance(action_lines, list):
        action_by_actor: dict[str, list[str]] = {}
        for item in action_lines:
            if isinstance(item, dict):
                actor_id = item.get("actor_id")
                if isinstance(actor_id, str) and actor_id.strip():
                    actor_id = actor_id.strip()
                    text = item.get("text")
                    if isinstance(text, str):
                        if actor_id not in action_by_actor:
                            action_by_actor[actor_id] = []
                        action_by_actor[actor_id].append(text)
        for actor_id, texts in action_by_actor.items():
            preview = (texts[0][:120] if texts and isinstance(texts[0], str) else None)
            action_actor_summaries.append(
                ActorLineSummary(actor_id=actor_id, line_count=len(texts), text_preview=preview)
            )

    # Extract social pressure shift from state_effects, fallback to social_outcome comparison
    social_pressure_shift: str | None = None
    state_effects = structured.get("state_effects")
    if isinstance(state_effects, list):
        for effect in state_effects:
            if isinstance(effect, dict) and effect.get("effect_type") == "pressure_shift":
                value = effect.get("value")
                if isinstance(value, str):
                    value = value.lower().strip()
                    if value in ("escalated", "high", "spike"):
                        social_pressure_shift = "escalated"
                        break
                    elif value in ("de-escalated", "eased"):
                        social_pressure_shift = "de-escalated"
                        break
                    else:
                        social_pressure_shift = "shifted"
    if not social_pressure_shift and social_outcome:
        prior_social = _opt_str(graph_state.get("prior_social_outcome"))
        if prior_social and prior_social != social_outcome:
            social_pressure_shift = "shifted"
        elif prior_social == social_outcome:
            social_pressure_shift = "held"

    # Extract carry-forward tension notes from state_effects and unresolved initiatives
    carry_forward_tension_notes: str | None = None
    tension_parts: list[str] = []
    if isinstance(state_effects, list):
        for effect in state_effects:
            if isinstance(effect, dict):
                effect_type = effect.get("effect_type")
                value = effect.get("value")
                if effect_type == "pressure_shift" and isinstance(value, str):
                    tension_parts.append(f"pressure: {value.lower()}")
                elif effect_type in ("accusation", "grievance", "repair_failure"):
                    tension_parts.append(f"{effect_type}")
                elif isinstance(value, str) and any(x in value.lower() for x in ("unresolved", "pending", "open")):
                    tension_parts.append(f"{effect_type}: {value[:40]}")
    if isinstance(initiative_events, list):
        for event in initiative_events:
            if isinstance(event, dict) and event.get("type") == "interrupt":
                tension_parts.append("unresolved interrupt")
                break
    if tension_parts:
        tension_str = ", ".join(tension_parts)[:280]
        carry_forward_tension_notes = tension_str if tension_str else None

    return PlannerTruth(
        selected_scene_function=_opt_str(
            graph_state.get("selected_scene_function"),
            structured.get("selected_scene_function"),
        ),
        responder_id=_opt_str(
            graph_state.get("responder_id"),
            structured.get("responder_id"),
            primary_responder_id,
        ),
        primary_responder_id=primary_responder_id,
        secondary_responder_ids=secondary_responder_ids,
        responder_scope=responder_scope,
        function_type=_opt_str(
            graph_state.get("function_type"), structured.get("function_type")
        ),
        pacing_mode=_opt_str(
            graph_state.get("pacing_mode"),
            structured.get("pacing_mode"),
            graph_state.get("selected_pacing_mode"),
        ),
        silence_mode=_opt_str(
            graph_state.get("silence_mode"),
            structured.get("silence_mode"),
            graph_state.get("selected_silence_mode"),
        ),
        spoken_line_count=spoken_line_count,
        action_line_count=action_line_count,
        initiative_summary=initiative_summary,
        last_actor_outcome_summary=last_actor_outcome_summary,
        scene_assessment_core=scene_assessment,
        scene_plan_ref=_opt_str(
            graph_state.get("scene_plan_ref"),
            graph_state.get("scene_plan_id"),
            structured.get("scene_plan_ref"),
        ),
        emotional_shift=_as_dict(
            graph_state.get("emotional_shift") or structured.get("emotional_shift")
        ),
        social_outcome=_opt_str(
            graph_state.get("social_outcome"), structured.get("social_outcome")
        ),
        dramatic_direction=_opt_str(
            graph_state.get("dramatic_direction"),
            structured.get("dramatic_direction"),
        ),
        dramatic_effect_gate=gate,
        social_state_summary=_social_state_summary_from_graph_state(graph_state),
        character_mind_summary=_as_dict(graph_state.get("character_mind_summary")),
        validation_status=_opt_str(validation.get("status")),
        validation_reason=_opt_str(validation.get("reason")),
        validator_layers_used=_resolve_validator_layers(validation, gate),
        continuity_impacts=[
            x for x in (graph_state.get("continuity_impacts") or []) if isinstance(x, dict)
        ],
        realized_secondary_responder_ids=realized_secondary_responder_ids,
        interruption_actor_id=interruption_actor_id,
        spoken_actor_summaries=spoken_actor_summaries,
        action_actor_summaries=action_actor_summaries,
        social_pressure_shift=social_pressure_shift,
        carry_forward_tension_notes=carry_forward_tension_notes,
    )


_PRESSURE_SIGNAL_ORDER = (
    "tension_escalation",
    "dignity_injury",
    "blame_pressure",
    "alliance_shift",
    "repair_attempt",
)


def _dominant_continuity_class(impacts: list[dict[str, Any]]) -> str | None:
    """Pick the most salient continuity-impact class in precedence order.

    The live continuity-impact list can carry multiple classes per turn; the
    pressure_state slot on BeatProgression needs a single dominant label so
    downstream director logic has a stable scalar to key off. Precedence is
    deliberately drama-weighted (escalation > dignity > blame > alliance >
    repair) rather than first-emitted.
    """
    if not isinstance(impacts, list):
        return None
    present = [
        str(x.get("class") or x.get("continuity_class") or "").strip()
        for x in impacts
        if isinstance(x, dict)
    ]
    present = [p for p in present if p]
    if not present:
        return None
    for label in _PRESSURE_SIGNAL_ORDER:
        if label in present:
            return label
    return present[0]


def _compose_beat_id(
    *, committed_scene_id: str, selected_scene_function: str | None, explicit: str | None
) -> str:
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    func = (selected_scene_function or "").strip() or "unspecified_function"
    scene = (committed_scene_id or "").strip() or "unknown_scene"
    return f"{scene}:{func}"


def _resolve_beat_progression(
    *,
    graph_state: dict[str, Any] | None,
    planner: PlannerTruth,
    committed_scene_id: str,
    prior_scene_id: str | None,
    situation_status: str,
    prior_beat: BeatProgression | None,
) -> BeatProgression:
    """Derive the committed beat identity and carry-forward decision.

    Scene-level facts (committed scene id, situation status) and planner truth
    (selected scene function, pacing, responders, dramatic direction) are the
    authoritative inputs. The prior beat, when present, is consulted only to
    decide *advanced* vs. *carried forward* — never to mask a genuine scene or
    scene-function shift.
    """
    gs = graph_state if isinstance(graph_state, dict) else {}
    explicit_beat = None
    for key in ("beat_id", "committed_beat_id"):
        raw = gs.get(key)
        if isinstance(raw, str) and raw.strip():
            explicit_beat = raw.strip()
            break

    beat_id = _compose_beat_id(
        committed_scene_id=committed_scene_id,
        selected_scene_function=planner.selected_scene_function,
        explicit=explicit_beat,
    )

    pressure = _dominant_continuity_class(planner.continuity_impacts)

    responder_focus: list[str] = []
    if planner.responder_id:
        responder_focus.append(planner.responder_id)
    for actor in planner.responder_scope:
        if actor and actor not in responder_focus:
            responder_focus.append(actor)
    responder_focus = responder_focus[:4]

    pacing_carry = planner.pacing_mode

    if situation_status == "blocked":
        return BeatProgression(
            beat_id=(prior_beat.beat_id if prior_beat else beat_id),
            beat_slot=(prior_beat.beat_slot if prior_beat else 0),
            pressure_state=pressure,
            pacing_carry_forward=pacing_carry,
            responder_focus_carry_forward=responder_focus,
            advanced=False,
            advancement_reason="blocked_turn_no_advance",
            continuity_carry_forward_reason="validation_or_rule_block",
            prior_beat_id=prior_beat.beat_id if prior_beat else None,
        )

    if prior_beat is None:
        return BeatProgression(
            beat_id=beat_id,
            beat_slot=0,
            pressure_state=pressure,
            pacing_carry_forward=pacing_carry,
            responder_focus_carry_forward=responder_focus,
            advanced=True,
            advancement_reason="initial_beat",
            continuity_carry_forward_reason=None,
            prior_beat_id=None,
        )

    if prior_beat.beat_id == beat_id:
        carry_reason = pressure or (
            "pacing_continuity" if pacing_carry else "no_signal"
        )
        return BeatProgression(
            beat_id=beat_id,
            beat_slot=max(0, int(prior_beat.beat_slot) + 1),
            pressure_state=pressure,
            pacing_carry_forward=pacing_carry,
            responder_focus_carry_forward=responder_focus,
            advanced=False,
            advancement_reason="continuity_carry_forward",
            continuity_carry_forward_reason=carry_reason,
            prior_beat_id=prior_beat.beat_id,
        )

    # Advanced to a new beat — decide the specific reason.
    if (committed_scene_id or "") != (prior_scene_id or ""):
        reason = "scene_transition"
    elif (
        planner.selected_scene_function
        and prior_beat.beat_id.endswith(f":{planner.selected_scene_function}") is False
    ):
        reason = "function_shift"
    else:
        reason = "beat_advanced"
    return BeatProgression(
        beat_id=beat_id,
        beat_slot=0,
        pressure_state=pressure,
        pacing_carry_forward=pacing_carry,
        responder_focus_carry_forward=responder_focus,
        advanced=True,
        advancement_reason=reason,
        continuity_carry_forward_reason=None,
        prior_beat_id=prior_beat.beat_id,
    )


def resolve_narrative_commit(
    *,
    turn_number: int,
    prior_scene_id: str,
    player_input: str,
    interpreted_input: dict[str, Any],
    generation: dict[str, Any] | None,
    runtime_projection: dict[str, Any],
    graph_state: dict[str, Any] | None = None,
    prior_beat_progression: BeatProgression | None = None,
) -> StoryNarrativeCommitRecord:
    """Compute the authoritative narrative commit without mutating session state."""
    ids_from_scene_rows = _scene_ids(runtime_projection)
    known_scene_ids = set(ids_from_scene_rows)
    if prior_scene_id:
        known_scene_ids.add(prior_scene_id)
    start_sid = runtime_projection.get("start_scene_id")
    scenes_raw = runtime_projection.get("scenes", [])
    if (
        isinstance(start_sid, str)
        and start_sid.strip()
        and isinstance(scenes_raw, list)
        and len(scenes_raw) > 0
        and not ids_from_scene_rows
    ):
        # Legibility failure: scene rows present but no id/scene_id extracted (broken projection).
        logger.warning(
            "story_runtime.runtime_projection scene rows have no usable id/scene_id; "
            "commit resolver would lack scene vocabulary aside from prior_scene_id. "
            "start_scene_id=%r scene_count=%s",
            start_sid.strip(),
            len(scenes_raw),
        )
    transition_map = _transition_map(runtime_projection)
    has_transition_rules = bool(transition_map)
    terminal_ids = _terminal_scene_ids(runtime_projection)

    proposed_scene_id, selected_source, candidate_sources, model_raw = _resolve_scene_proposal(
        player_input=player_input,
        interpreted_input=interpreted_input,
        known_scene_ids=known_scene_ids,
        generation=generation,
    )

    kind = interpreted_input.get("kind")

    open_pressures = prepare_open_pressures(interpreted_input)
    consequences = build_base_consequences(kind=kind, model_raw=model_raw)

    work = eval_core_transition_rules(
        proposed_scene_id=proposed_scene_id,
        prior_scene_id=prior_scene_id,
        known_scene_ids=known_scene_ids,
        has_transition_rules=has_transition_rules,
        transition_map=transition_map,
        model_raw=model_raw,
        consequences=consequences,
    )
    overlay_terminal_scene(work, terminal_ids=terminal_ids)

    at_terminal_scene = work.committed_scene_id in terminal_ids
    summary = build_interpretation_summary(
        interpreted_input=interpreted_input,
        model_raw=model_raw,
        selected_source=selected_source,
        prior_scene_id=prior_scene_id,
        committed_scene_id=work.committed_scene_id,
        situation_status=work.situation_status,
    )

    planner_truth = _planner_truth_from_graph_state(
        graph_state=graph_state,
        generation=generation,
    )

    beat_progression = _resolve_beat_progression(
        graph_state=graph_state,
        planner=planner_truth,
        committed_scene_id=work.committed_scene_id,
        prior_scene_id=prior_scene_id or None,
        situation_status=work.situation_status,
        prior_beat=prior_beat_progression,
    )

    return StoryNarrativeCommitRecord(
        turn_number=turn_number,
        prior_scene_id=prior_scene_id or None,
        proposed_scene_id=proposed_scene_id,
        committed_scene_id=work.committed_scene_id,
        situation_status=work.situation_status,  # type: ignore[arg-type]
        allowed=work.allowed,
        authoritative_reason=work.authoritative_reason,
        commit_reason_code=work.commit_reason_code,  # type: ignore[arg-type]
        selected_candidate_source=selected_source,
        candidate_sources=candidate_sources,
        model_structured_proposed_scene_id=model_raw,
        committed_interpretation_summary=summary,
        committed_consequences=work.committed_consequences,
        open_pressures=open_pressures,
        resolved_pressures=[],
        is_terminal=at_terminal_scene,
        planner_truth=planner_truth,
        beat_progression=beat_progression,
    )
