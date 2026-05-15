"""Policy-driven improvisational coherence derivation and validation."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from ai_stack.improvisational_coherence_contracts import (
    IMPROV_ACCEPT,
    IMPROV_ACCEPTANCE_MODES,
    IMPROV_ADVANCE_CLASSES,
    IMPROV_FAILURE_CONTRADICTS_COMMITTED_TRUTH,
    IMPROV_FAILURE_FORCED_PLAYER_REVISION,
    IMPROV_FAILURE_NO_PLAYABLE_BOUNDARY_REASON,
    IMPROV_FAILURE_PLAYER_CONTRIBUTION_DROPPED,
    IMPROV_FAILURE_SCENE_ANCHOR_MISSING,
    IMPROV_FAILURE_UNBOUNDED_WORLD_EXPANSION,
    IMPROV_REDIRECT_WITH_ACKNOWLEDGEMENT,
    IMPROVISATIONAL_COHERENCE_SCHEMA_VERSION,
    ImprovisationalCoherenceTarget,
    ImprovisationalCoherenceValidation,
    normalize_improvisational_coherence_policy,
)


_TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None:
        return []
    return [value]


def _clean_str_list(value: Any) -> list[str]:
    out: list[str] = []
    for item in _as_list(value):
        text = _text(item)
        if text and text not in out:
            out.append(text)
    return out


def _stable_id(*parts: Any) -> str:
    material = "|".join(
        " ".join(_TOKEN_RE.findall(str(part or "").casefold())) for part in parts
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"turn_contribution:{digest}"


def _runtime_policy_improvisational_coherence(
    module_runtime_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    direct = raw.get("improvisational_coherence_policy")
    if isinstance(direct, dict):
        return normalize_improvisational_coherence_policy(direct)
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    nested = governance.get("improvisational_coherence")
    return normalize_improvisational_coherence_policy(nested if isinstance(nested, dict) else {})


def _contribution_kind(
    *,
    interpreted_input: dict[str, Any] | None,
    semantic_move_record: dict[str, Any] | None,
) -> str | None:
    semantic = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    interpreted = interpreted_input if isinstance(interpreted_input, dict) else {}
    for value in (
        semantic.get("move_type"),
        semantic.get("semantic_move"),
        interpreted.get("player_input_kind"),
        interpreted.get("kind"),
    ):
        text = _text(value)
        if text:
            return text
    return None


def _visible_actor_ids(selected_responder_set: list[dict[str, Any]] | None) -> list[str]:
    out: list[str] = []
    for row in selected_responder_set or []:
        if not isinstance(row, dict):
            continue
        actor_id = _text(row.get("actor_id") or row.get("responder_id"))
        if actor_id and actor_id not in out:
            out.append(actor_id)
    return out


def _anchor_refs(
    *,
    current_scene_id: str | None,
    selected_scene_function: str | None,
    contribution_kind: str | None,
    pacing_rhythm_target: dict[str, Any] | None,
    scene_energy_target: dict[str, Any] | None,
    max_anchor_refs: int,
) -> list[dict[str, Any]]:
    rhythm = pacing_rhythm_target if isinstance(pacing_rhythm_target, dict) else {}
    energy = scene_energy_target if isinstance(scene_energy_target, dict) else {}
    refs = [
        {"source": "scene", "field": "current_scene_id", "value": _text(current_scene_id)},
        {
            "source": "scene_plan_record",
            "field": "selected_scene_function",
            "value": _text(selected_scene_function),
        },
        {
            "source": "semantic_move_record",
            "field": "move_type",
            "value": _text(contribution_kind),
        },
        {
            "source": "pacing_rhythm_target",
            "field": "cadence",
            "value": _text(rhythm.get("cadence")),
        },
        {
            "source": "scene_energy_target",
            "field": "target_transition",
            "value": _text(energy.get("target_transition")),
        },
    ]
    return [ref for ref in refs if ref["value"]][: max(1, max_anchor_refs)]


def _requires_boundary(kind: str | None, selected_scene_function: str | None) -> bool:
    value = _text(kind).lower()
    scene_function = _text(selected_scene_function).lower()
    if value in {"meta", "explicit_command", "off_scope", "system_request", "navigation_command"}:
        return True
    if scene_function in {"scene_pivot"} and value in {"perception", "question"}:
        return True
    return False


def derive_improvisational_coherence(
    *,
    player_input: str | None = None,
    interpreted_input: dict[str, Any] | None = None,
    semantic_move_record: dict[str, Any] | None = None,
    scene_plan_record: dict[str, Any] | None = None,
    selected_scene_function: str | None = None,
    current_scene_id: str | None = None,
    selected_responder_set: list[dict[str, Any]] | None = None,
    scene_energy_target: dict[str, Any] | None = None,
    pacing_rhythm_target: dict[str, Any] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select a bounded yes-and target from player input and structured state."""
    policy = _runtime_policy_improvisational_coherence(module_runtime_policy)
    plan = scene_plan_record if isinstance(scene_plan_record, dict) else {}
    scene_function = _text(
        selected_scene_function
        or plan.get("selected_scene_function")
        or plan.get("scene_function")
    )
    contribution_kind = _contribution_kind(
        interpreted_input=interpreted_input,
        semantic_move_record=semantic_move_record,
    )
    raw_input_present = bool(_text(player_input))
    if not policy.get("enabled") or not raw_input_present:
        return {
            "policy": policy,
            "target": ImprovisationalCoherenceTarget(
                policy_enabled=bool(policy.get("enabled")),
                commit_impact=str(policy.get("default_commit_impact") or "diagnostic"),
                require_structured_events=bool(policy.get("require_structured_events")),
                rationale_codes=["improvisational_coherence_not_applicable"],
            ).to_dict(),
        }

    boundary_required = _requires_boundary(contribution_kind, scene_function)
    allowed_modes = _clean_str_list(policy.get("allowed_acceptance_modes")) or [IMPROV_ACCEPT]
    acceptance_mode = (
        IMPROV_REDIRECT_WITH_ACKNOWLEDGEMENT
        if boundary_required and IMPROV_REDIRECT_WITH_ACKNOWLEDGEMENT in allowed_modes
        else IMPROV_ACCEPT
    )
    allowed_advance_classes = [
        item for item in _clean_str_list(policy.get("allowed_advance_classes")) if item in IMPROV_ADVANCE_CLASSES
    ]
    if not allowed_advance_classes:
        allowed_advance_classes = ["beat_deepen"]
    refs = _anchor_refs(
        current_scene_id=current_scene_id,
        selected_scene_function=scene_function,
        contribution_kind=contribution_kind,
        pacing_rhythm_target=pacing_rhythm_target,
        scene_energy_target=scene_energy_target,
        max_anchor_refs=int(policy.get("max_anchor_refs") or 6),
    )
    target = ImprovisationalCoherenceTarget(
        policy_enabled=True,
        commit_impact=str(policy.get("default_commit_impact") or "recover"),
        require_structured_events=bool(policy.get("require_structured_events")),
        min_anchor_refs=int(policy.get("min_anchor_refs") or 1),
        contribution_id=_stable_id(
            player_input,
            contribution_kind,
            current_scene_id,
            scene_function,
        ),
        contribution_kind=contribution_kind,
        acceptance_mode=acceptance_mode,
        allowed_acceptance_modes=allowed_modes,
        allowed_advance_classes=allowed_advance_classes,
        required_anchor_refs=refs,
        selected_scene_function=scene_function or None,
        visible_actor_ids=_visible_actor_ids(selected_responder_set),
        requires_playable_boundary_reason=(
            boundary_required and bool(policy.get("boundary_reason_required"))
        ),
        boundary_reason_code="playable_scene_boundary" if boundary_required else None,
        rationale_codes=[
            "improvisational_coherence_policy_enabled",
            "player_contribution_selected",
            "playable_boundary_required" if boundary_required else "accept_player_contribution",
        ],
        source_evidence=refs,
    ).to_dict()
    return {"policy": policy, "target": target}


def compact_improvisational_coherence_context(
    target: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return model-visible context without raw player text."""
    src = target if isinstance(target, dict) else {}
    if not src or not src.get("policy_enabled"):
        return {}
    return {
        "schema_version": src.get("schema_version"),
        "contribution_id": src.get("contribution_id"),
        "contribution_kind": src.get("contribution_kind"),
        "acceptance_mode": src.get("acceptance_mode"),
        "allowed_acceptance_modes": src.get("allowed_acceptance_modes") or [],
        "allowed_advance_classes": src.get("allowed_advance_classes") or [],
        "min_anchor_refs": int(src.get("min_anchor_refs") or 0),
        "required_anchor_refs": src.get("required_anchor_refs") or [],
        "visible_actor_ids": src.get("visible_actor_ids") or [],
        "requires_playable_boundary_reason": bool(
            src.get("requires_playable_boundary_reason")
        ),
        "boundary_reason_code": src.get("boundary_reason_code"),
    }


def _event_rows(structured_output: dict[str, Any] | None) -> list[dict[str, Any]]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    events = structured.get("improvisational_coherence_events")
    return [row for row in events if isinstance(row, dict)] if isinstance(events, list) else []


def _anchor_sources(anchor_refs: Any) -> set[str]:
    out: set[str] = set()
    for ref in _as_list(anchor_refs):
        if isinstance(ref, dict):
            source = _text(ref.get("source"))
            if source:
                out.add(source)
            value = _text(ref.get("value"))
            if value:
                out.add(value)
        else:
            text = _text(ref)
            if text:
                out.add(text)
    return out


def _matching_event(
    events: list[dict[str, Any]],
    contribution_id: str | None,
) -> dict[str, Any] | None:
    if not events:
        return None
    if contribution_id:
        for row in events:
            if _text(row.get("contribution_id")) == contribution_id:
                return row
    return events[0] if len(events) == 1 else None


def validate_improvisational_coherence_realization(
    *,
    improvisational_coherence_target: dict[str, Any] | None,
    structured_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate structured yes-and events against the selected target."""
    target = (
        improvisational_coherence_target
        if isinstance(improvisational_coherence_target, dict)
        else {}
    )
    if not target or not bool(target.get("policy_enabled")):
        return ImprovisationalCoherenceValidation(
            schema_version=IMPROVISATIONAL_COHERENCE_SCHEMA_VERSION,
            status="not_applicable",
            contract_pass=True,
            target=target,
        ).to_dict()

    events = _event_rows(structured_output)
    contribution_id = _text(target.get("contribution_id")) or None
    event = _matching_event(events, contribution_id)
    failure_codes: list[str] = []
    if bool(target.get("require_structured_events")) and event is None:
        failure_codes.append(IMPROV_FAILURE_PLAYER_CONTRIBUTION_DROPPED)

    allowed_modes = set(_clean_str_list(target.get("allowed_acceptance_modes")))
    allowed_classes = set(_clean_str_list(target.get("allowed_advance_classes")))
    required_sources = _anchor_sources(target.get("required_anchor_refs"))
    actual_anchor_sources: set[str] = set()
    actual: dict[str, Any] = {
        "structured_events_present": bool(events),
        "event_count": len(events),
        "contribution_acknowledged": event is not None,
        "contribution_id": contribution_id,
    }

    if event is not None:
        acceptance_mode = _text(event.get("acceptance_mode"))
        advance_class = _text(event.get("advance_class"))
        anchor_refs = event.get("anchor_refs") if isinstance(event.get("anchor_refs"), list) else []
        actual_anchor_sources = _anchor_sources(anchor_refs)
        actual.update(
            {
                "acceptance_mode": acceptance_mode,
                "advance_class": advance_class,
                "anchor_refs": anchor_refs,
                "boundary_reason_code": _text(event.get("boundary_reason_code")) or None,
                "forced_player_revision": bool(
                    event.get("forced_player_revision")
                    or event.get("forced_player_speech")
                    or event.get("forces_player_revision")
                ),
                "contradicts_committed_truth": bool(
                    event.get("contradicts_committed_truth")
                ),
            }
        )
        if acceptance_mode and acceptance_mode not in allowed_modes:
            failure_codes.append(IMPROV_FAILURE_UNBOUNDED_WORLD_EXPANSION)
        if advance_class and advance_class not in allowed_classes:
            failure_codes.append(IMPROV_FAILURE_UNBOUNDED_WORLD_EXPANSION)
        min_anchor_refs = max(0, int(target.get("min_anchor_refs") or 1))
        if len(anchor_refs) < min_anchor_refs or (
            required_sources and actual_anchor_sources.isdisjoint(required_sources)
        ):
            failure_codes.append(IMPROV_FAILURE_SCENE_ANCHOR_MISSING)
        if actual["contradicts_committed_truth"]:
            failure_codes.append(IMPROV_FAILURE_CONTRADICTS_COMMITTED_TRUTH)
        if actual["forced_player_revision"]:
            failure_codes.append(IMPROV_FAILURE_FORCED_PLAYER_REVISION)
        if bool(target.get("requires_playable_boundary_reason")) and not actual.get(
            "boundary_reason_code"
        ):
            failure_codes.append(IMPROV_FAILURE_NO_PLAYABLE_BOUNDARY_REASON)

    deduped_failures = list(dict.fromkeys(failure_codes))
    actual.update(
        {
            "anchor_sources": sorted(actual_anchor_sources),
            "failure_codes": deduped_failures,
            "contract_pass": not deduped_failures,
        }
    )
    return ImprovisationalCoherenceValidation(
        schema_version=IMPROVISATIONAL_COHERENCE_SCHEMA_VERSION,
        status="rejected" if deduped_failures else "approved",
        contract_pass=not deduped_failures,
        failure_codes=deduped_failures,
        feedback_code=deduped_failures[0] if deduped_failures else None,
        target=target,
        actual=actual,
        source_evidence=[
            {
                "source": "structured_output",
                "field": "improvisational_coherence_events",
                "present": bool(events),
            }
        ],
    ).to_dict()


def build_improvisational_coherence_aspect_record(
    *,
    target: dict[str, Any] | None,
    validation: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    source: str = "runtime",
) -> dict[str, Any]:
    """Build a RuntimeAspectLedger-compatible improvisational aspect record."""
    target_dict = target if isinstance(target, dict) else {}
    validation_dict = validation if isinstance(validation, dict) else {}
    policy_dict = (
        policy
        if isinstance(policy, dict)
        else normalize_improvisational_coherence_policy(None)
    )
    failure_codes = [
        code
        for code in _clean_str_list(validation_dict.get("failure_codes"))
        if code
    ]
    validation_status = _text(validation_dict.get("status")).lower()
    applicable = bool(target_dict.get("policy_enabled"))
    if not validation_dict:
        aspect_status = "partial" if applicable else "not_applicable"
    elif validation_status == "approved":
        aspect_status = "passed"
    elif validation_status == "not_applicable":
        aspect_status = "not_applicable"
        applicable = False
    elif validation_status == "degraded":
        aspect_status = "partial"
    else:
        aspect_status = "failed"
    actual = (
        dict(validation_dict.get("actual"))
        if isinstance(validation_dict.get("actual"), dict)
        else {}
    )
    actual.update(
        {
            "validation_status": validation_status or None,
            "contract_pass": validation_dict.get("contract_pass"),
            "failure_codes": failure_codes,
        }
    )
    return {
        "applicable": applicable,
        "status": aspect_status,
        "expected": {
            "schema_version": target_dict.get("schema_version")
            or IMPROVISATIONAL_COHERENCE_SCHEMA_VERSION,
            "policy_present": bool(policy_dict.get("enabled") or target_dict),
            "policy_enabled": bool(target_dict.get("policy_enabled")),
            "commit_impact": target_dict.get("commit_impact")
            or policy_dict.get("default_commit_impact"),
            "require_structured_events": bool(target_dict.get("require_structured_events")),
            "min_anchor_refs": int(
                target_dict.get("min_anchor_refs")
                if target_dict.get("min_anchor_refs") is not None
                else policy_dict.get("min_anchor_refs") or 0
            ),
            "allowed_acceptance_modes": target_dict.get("allowed_acceptance_modes")
            or policy_dict.get("allowed_acceptance_modes")
            or [],
            "allowed_advance_classes": target_dict.get("allowed_advance_classes")
            or policy_dict.get("allowed_advance_classes")
            or [],
        },
        "selected": {
            "contribution_id": target_dict.get("contribution_id"),
            "contribution_kind": target_dict.get("contribution_kind"),
            "acceptance_mode": target_dict.get("acceptance_mode"),
            "min_anchor_refs": int(target_dict.get("min_anchor_refs") or 0),
            "selected_scene_function": target_dict.get("selected_scene_function"),
            "visible_actor_ids": target_dict.get("visible_actor_ids") or [],
            "required_anchor_refs": target_dict.get("required_anchor_refs") or [],
            "requires_playable_boundary_reason": bool(
                target_dict.get("requires_playable_boundary_reason")
            ),
            "boundary_reason_code": target_dict.get("boundary_reason_code"),
        },
        "actual": actual,
        "reasons": failure_codes
        or (
            ["improvisational_coherence_target_selected"]
            if applicable and not validation_dict
            else []
        ),
        "source": source,
        "failure_class": "recoverable_dramatic_failure" if failure_codes else None,
        "failure_reason": failure_codes[0] if failure_codes else None,
    }
