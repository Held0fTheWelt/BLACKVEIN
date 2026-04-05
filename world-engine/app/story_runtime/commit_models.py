"""Bounded narrative commit models and resolver for the story runtime (Task B).

This is not a full world-state simulation: commits record session-local, legal
scene progression and interpretation linkage only.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

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


def _scene_ids(runtime_projection: dict[str, Any]) -> set[str]:
    scenes = runtime_projection.get("scenes", [])
    scene_ids: set[str] = set()
    if isinstance(scenes, list):
        for scene in scenes:
            if isinstance(scene, dict):
                scene_id = scene.get("id")
                if isinstance(scene_id, str) and scene_id.strip():
                    scene_ids.add(scene_id.strip())
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
                sid = scene.get("id")
                if isinstance(sid, str) and sid.strip():
                    ids.add(sid.strip())
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


def resolve_narrative_commit(
    *,
    turn_number: int,
    prior_scene_id: str,
    player_input: str,
    interpreted_input: dict[str, Any],
    generation: dict[str, Any] | None,
    runtime_projection: dict[str, Any],
) -> StoryNarrativeCommitRecord:
    """Compute the authoritative narrative commit without mutating session state."""
    known_scene_ids = _scene_ids(runtime_projection)
    if prior_scene_id:
        known_scene_ids.add(prior_scene_id)
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
    conf = interpreted_input.get("confidence")
    ambiguity = interpreted_input.get("ambiguity")

    open_pressures: list[str] = []
    if isinstance(ambiguity, str) and ambiguity.strip():
        open_pressures.append(f"interpretation_ambiguity:{ambiguity.strip()}")

    committed_scene_id = prior_scene_id
    allowed = False
    code: CommitReasonCode = "no_scene_proposal"
    situation: SituationStatus = "continue"
    auth_reason = "No scene change was proposed; the session remains in the current scene."

    consequences: list[str] = [f"interpretation_kind:{_interpretation_kind_tag(kind)}"]

    if model_raw is not None:
        consequences.append(f"model_proposal_considered:{model_raw}")

    if not proposed_scene_id:
        if model_raw is not None and known_scene_ids and model_raw not in known_scene_ids:
            auth_reason = (
                "The model proposed a scene that is not in the runtime projection; "
                "no scene candidate was selected for progression."
            )
        else:
            auth_reason = "No scene change was proposed; the session remains in the current scene."
        code = "no_scene_proposal"
        situation = "continue"
    elif proposed_scene_id == prior_scene_id:
        code = "already_in_scene"
        situation = "continue"
        auth_reason = "A scene was proposed but it matches the current scene; no transition applies."
        consequences.append(f"scene_continue:{prior_scene_id}")
    elif known_scene_ids and proposed_scene_id not in known_scene_ids:
        code = "unknown_target_scene"
        situation = "blocked"
        auth_reason = "The proposed target scene is unknown to this runtime projection; progression is blocked."
        consequences.append("proposal_blocked:unknown_target_scene")
    elif not has_transition_rules:
        code = "transition_hints_missing"
        situation = "blocked"
        auth_reason = "Transition hints are missing in the runtime projection; progression is blocked."
        consequences.append("proposal_blocked:transition_hints_missing")
    else:
        allowed_targets = transition_map.get(prior_scene_id, set())
        if proposed_scene_id not in allowed_targets:
            code = "illegal_transition_not_allowed"
            situation = "blocked"
            auth_reason = (
                "The proposed transition is not allowed by runtime transition hints; progression is blocked."
            )
            consequences.append("proposal_blocked:illegal_transition")
        else:
            committed_scene_id = proposed_scene_id
            allowed = True
            code = "legal_transition_committed"
            situation = "transitioned"
            auth_reason = f"Legal transition committed from {prior_scene_id!r} to {committed_scene_id!r}."
            consequences.append(f"scene_transition:{prior_scene_id}->{committed_scene_id}")

    at_terminal_scene = committed_scene_id in terminal_ids
    # Blocked progression stays blocked even when the current scene is terminal.
    if at_terminal_scene and situation != "blocked":
        situation = "terminal"
        if code == "legal_transition_committed":
            auth_reason = (
                f"Legal transition committed to terminal scene {committed_scene_id!r}."
            )
        elif code == "already_in_scene":
            auth_reason = f"The session remains on terminal scene {committed_scene_id!r}."
        elif code == "no_scene_proposal":
            auth_reason = f"No scene change proposed; session remains on terminal scene {committed_scene_id!r}."
        else:
            auth_reason = f"The session is at terminal scene {committed_scene_id!r}."

    model_considered = model_raw is not None
    state_changed = committed_scene_id != prior_scene_id
    interpretation_influenced = selected_source is not None or str(kind or "").lower() == "explicit_command"
    local_continuation_only = (not state_changed) and situation == "continue"

    summary: dict[str, Any] = {
        "interpreted_kind": kind,
        "interpretation_confidence": conf,
        "interpretation_ambiguity": ambiguity,
        "interpretation_influenced_progression": interpretation_influenced,
        "model_proposal_considered": model_considered,
        "proposal_changed_committed_state": state_changed,
        "local_narrative_continuation_only": local_continuation_only,
        "note": (
            "Bounded interpretation-to-progression linkage only; not a full canonical world-state delta."
        ),
    }

    return StoryNarrativeCommitRecord(
        turn_number=turn_number,
        prior_scene_id=prior_scene_id or None,
        proposed_scene_id=proposed_scene_id,
        committed_scene_id=committed_scene_id,
        situation_status=situation,
        allowed=allowed,
        authoritative_reason=auth_reason,
        commit_reason_code=code,
        selected_candidate_source=selected_source,
        candidate_sources=candidate_sources,
        model_structured_proposed_scene_id=model_raw,
        committed_interpretation_summary=summary,
        committed_consequences=consequences,
        open_pressures=open_pressures,
        resolved_pressures=[],
        is_terminal=at_terminal_scene,
    )
