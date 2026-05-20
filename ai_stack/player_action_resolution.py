"""Player action resolution through AI-provided semantics and content grounding.

This module intentionally does not infer verbs from raw language. It accepts a
semantic resolution produced by the AI layer and grounds its target ids against
the content-derived interaction surface. Without that semantic resolution it
returns an explicit clarification/AI-required contract instead of falling back
to hidden maps.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ai_stack.action_resolution_contracts import (
    AffordanceResolutionContract,
    PlayerActionFrameContract,
    ResolvedTarget,
    fold_unicode,
    fold_match,
)
from ai_stack.environment_state_contracts import (
    environment_state_to_player_local_context,
    scene_affordance_model_with_environment_state,
)
from ai_stack.story_runtime.canonical_path.canonical_path_hold_effect_contracts import (
    build_canonical_path_hold_effect,
)
from ai_stack.free_player_action_resolution_contracts import (
    build_free_player_action_resolution,
)
from ai_stack.language_io.language_adapter import build_interaction_surface, resolve_content_modules_root
from story_runtime_core.player_input_intent_contract import (
    is_mixed_player_input_kind,
    is_non_story_control_player_input_kind,
    is_perception_like_player_input_kind,
    is_speech_like_player_input_kind,
)


def _load_characters_blob(module_id: str, *, content_modules_root: Path | None = None) -> dict[str, Any]:
    root = resolve_content_modules_root(content_modules_root)
    module_dir = root / str(module_id).strip()
    char_dir = module_dir / "characters"
    if not char_dir.is_dir():
        return {}
    out: dict[str, Any] = {}
    for path in sorted(char_dir.rglob("*.yaml")):
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        blob = payload.get("character_document") or payload.get("character")
        if not isinstance(blob, dict):
            continue
        char_id = str(blob.get("id") or blob.get("canonical_id") or path.stem).strip()
        if char_id:
            out[char_id] = blob
    return out


def _enrich_actor_aliases(
    actor_rows: list[dict[str, Any]],
    *,
    module_id: str,
    content_modules_root: Path | None = None,
) -> list[dict[str, Any]]:
    chars = _load_characters_blob(module_id, content_modules_root=content_modules_root)
    out: list[dict[str, Any]] = []
    for row in actor_rows:
        if not isinstance(row, dict):
            continue
        r = dict(row)
        aid = str(r.get("id") or "").strip()
        terms = [str(a).strip() for a in r.get("content_terms") or [] if str(a).strip()]
        terms.append(aid) if aid and aid not in terms else None
        base_slug = aid.split("_")[0].lower() if aid else ""
        for key, blob in chars.items():
            if not isinstance(blob, dict):
                continue
            cid = str(blob.get("id") or "").strip().lower()
            name = str(blob.get("name") or "").strip()
            slug = str(key).strip().lower()
            if name and (aid.lower() == cid or aid.lower().startswith(slug) or base_slug in {slug, cid}):
                if name not in terms:
                    terms.append(name)
        r["content_terms"] = terms
        out.append(r)
    return out


def _actor_rows_from_runtime_projection(runtime_projection: dict[str, Any]) -> list[dict[str, Any]]:
    actor_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    lanes = runtime_projection.get("actor_lanes")
    if isinstance(lanes, dict):
        for actor_id in lanes.keys():
            aid = str(actor_id or "").strip()
            if aid and aid not in seen:
                seen.add(aid)
                actor_rows.append({"id": aid, "content_terms": [aid], "type": "actor"})
    for key in ("human_actor_id", "selected_player_role"):
        aid = str(runtime_projection.get(key) or "").strip()
        if aid and aid not in seen:
            seen.add(aid)
            actor_rows.append({"id": aid, "content_terms": [aid], "type": "actor"})
    for aid_raw in runtime_projection.get("npc_actor_ids") or []:
        aid = str(aid_raw or "").strip()
        if aid and aid not in seen:
            seen.add(aid)
            actor_rows.append({"id": aid, "content_terms": [aid], "type": "actor"})
    return actor_rows


def _load_interaction_surface(
    module_id: str,
    *,
    content_modules_root: Path | None = None,
) -> dict[str, Any]:
    return build_interaction_surface(module_id, content_modules_root=content_modules_root)


def build_scene_affordance_model(
    *,
    module_id: str,
    runtime_projection: dict[str, Any],
    content_modules_root: Path | None = None,
    environment_state: dict[str, Any] | None = None,
    environment_model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    surface = _load_interaction_surface(module_id, content_modules_root=content_modules_root)
    raw_actors = _actor_rows_from_runtime_projection(runtime_projection)
    actors = _enrich_actor_aliases(raw_actors, module_id=module_id, content_modules_root=content_modules_root)
    model: dict[str, Any] = {
        "module_id": module_id,
        "schema_version": surface.get("schema_version"),
        "current_area": surface.get("current_area"),
        "inferred_area_policy": surface.get("setting_id"),
        "semantic_resolution_contract": surface.get("semantic_resolution_contract"),
        "player_freedom_policy": surface.get("player_freedom_policy")
        if isinstance(surface.get("player_freedom_policy"), dict)
        else {},
        "locations": surface.get("locations") if isinstance(surface.get("locations"), list) else [],
        "objects": surface.get("objects") if isinstance(surface.get("objects"), list) else [],
        "actors": actors,
    }
    return scene_affordance_model_with_environment_state(
        model,
        environment_state=environment_state,
        environment_model=environment_model,
    )


def _terms(row: dict[str, Any]) -> list[str]:
    values = row.get("content_terms") if isinstance(row.get("content_terms"), list) else []
    out = [str(v).strip() for v in values if str(v).strip()]
    for key in ("id", "name", "display_name"):
        value = str(row.get(key) or "").strip()
        if value and value not in out:
            out.append(value)
    return out


def _access(row: dict[str, Any]) -> str | None:
    for key in ("playable_access", "access", "access_pattern"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return None


def _status_policy_for_access(access: str | None) -> tuple[str, str]:
    raw = str(access or "").strip().lower()
    if "prevented" in raw:
        return ("prevented", "no_commit")
    if "locked" in raw:
        return ("blocked", "no_commit")
    if "inferred_plausible" in raw:
        return ("allowed", "commit_action")
    if "offscreen" in raw or "implied" in raw:
        return ("allowed_offscreen", "commit_action")
    return ("allowed", "commit_action")


def _semantic_text(semantic: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = semantic.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _semantic_bool(semantic: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        if key not in semantic:
            continue
        value = semantic.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            text = value.strip().lower()
            if text in {"true", "yes", "1"}:
                return True
            if text in {"false", "no", "0", ""}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
    return False


def _slug_from_english_text(value: str) -> str:
    folded = fold_unicode(value)
    slug = re.sub(r"[^a-z0-9]+", "_", folded).strip("_")
    return slug[:64] or "target"


def _policy_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _player_freedom_policy(affordance_model: dict[str, Any]) -> dict[str, Any]:
    policy = affordance_model.get("player_freedom_policy")
    return policy if isinstance(policy, dict) else {}


def _catalog_silent_policy(affordance_model: dict[str, Any]) -> dict[str, Any]:
    policy = _player_freedom_policy(affordance_model)
    req = policy.get("semantic_resolution_requirements")
    req = req if isinstance(req, dict) else {}
    silent = req.get("if_catalog_silent")
    return silent if isinstance(silent, dict) else {}


def _semantic_allows_plausible_inference(
    semantic: dict[str, Any],
    *,
    affordance_model: dict[str, Any],
    action_kind: str,
    target_query: str | None,
    target_type: str | None,
) -> bool:
    if not target_query:
        return False
    policy = _player_freedom_policy(affordance_model)
    if not bool((policy.get("plausible_affordance_inference") or {}).get("enabled")):
        return False
    silent_policy = _catalog_silent_policy(affordance_model)
    if not silent_policy:
        return False
    ttype = str(target_type or "").strip().lower()
    allowed_types = set(_policy_values(silent_policy.get("allowed_target_types")))
    if allowed_types and ttype and ttype not in allowed_types:
        return False
    mode = _semantic_text(
        semantic,
        "inference_mode",
        "target_inference_mode",
        "plausible_inference_mode",
    ).lower()
    allowed_modes = set(_policy_values(silent_policy.get("allowed_inference_modes")))
    if not mode or (allowed_modes and mode not in allowed_modes):
        return False
    risk = _semantic_text(semantic, "canonical_risk", "canon_risk", "risk").lower()
    safety = _semantic_text(semantic, "canon_safety", "canonical_safety", "safety").lower()
    allowed_safety = set(_policy_values(silent_policy.get("allowed_canon_safety")))
    required_risk = str(silent_policy.get("require_canonical_risk") or "").strip().lower()
    if allowed_safety and safety not in allowed_safety:
        return False
    if required_risk and risk != required_risk:
        return False
    return True


def _inferred_target_from_semantics(
    semantic: dict[str, Any],
    *,
    affordance_model: dict[str, Any],
    action_kind: str,
    target_query: str | None,
    target_type: str | None,
) -> tuple[str, str, str, str, dict[str, Any]] | None:
    if not _semantic_allows_plausible_inference(
        semantic,
        affordance_model=affordance_model,
        action_kind=action_kind,
        target_query=target_query,
        target_type=target_type,
    ):
        return None
    silent_policy = _catalog_silent_policy(affordance_model)
    allowed_types = _policy_values(silent_policy.get("allowed_target_types"))
    inferred_type = str(target_type or semantic.get("inferred_target_type") or (allowed_types[0] if allowed_types else "")).strip().lower()
    if allowed_types and inferred_type not in set(allowed_types):
        return None
    inferred_type = inferred_type or "object"
    provided_id = _semantic_text(semantic, "inferred_target_id", "inferred_object_id")
    slug = _slug_from_english_text(provided_id or str(target_query or ""))
    prefix = str(silent_policy.get("runtime_target_id_prefix") or "inferred_local").strip() or "inferred_local"
    inferred_id = provided_id if provided_id else f"{prefix}_{slug}"
    mode = _semantic_text(
        semantic,
        "inference_mode",
        "target_inference_mode",
        "plausible_inference_mode",
    ) or "canon_safe_plausible_affordance"
    inference = {
        "mode": mode,
        "canon_safety": _semantic_text(semantic, "canon_safety", "canonical_safety") or "content_silent_mundane",
        "canonical_risk": _semantic_text(semantic, "canonical_risk", "canon_risk") or "low",
        "inferred_affordance_summary": _semantic_text(
            semantic,
            "inferred_affordance_summary",
            "inferred_detail_summary",
            "reasoning_summary",
        )
        or None,
        "policy": "canon_safe_mundane_affordance_gap",
    }
    return (inferred_id, inferred_type, "allowed", "commit_action", inference)


def _canonical_path_effect_from_policy(
    semantic: dict[str, Any],
    affordance_model: dict[str, Any],
    *,
    action_commit_policy: str,
) -> str | None:
    explicit = _semantic_text(semantic, "canonical_path_effect", "canonical_path_progression")
    if explicit:
        return explicit
    if action_commit_policy != "commit_action":
        return None
    policy = _player_freedom_policy(affordance_model)
    control = policy.get("canonical_path_control")
    control = control if isinstance(control, dict) else {}
    return str(control.get("default_for_free_player_action") or "").strip() or None


def _current_area_from_affordance_model(affordance_model: dict[str, Any]) -> str | None:
    state = affordance_model.get("environment_state")
    if isinstance(state, dict):
        for key in ("current_room_id", "current_location_id", "current_area"):
            value = str(state.get(key) or "").strip()
            if value:
                return value
    value = str(affordance_model.get("current_area") or "").strip()
    return value or None


def _target_location_hint_from_row(row: dict[str, Any] | None) -> str | None:
    if not isinstance(row, dict):
        return None
    for key in (
        "placement_location_id",
        "placement_room_id",
        "room_id",
        "location_id",
        "current_room_id",
    ):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return None


def _location_row_from_environment_model(
    affordance_model: dict[str, Any],
    location_id: str | None,
) -> dict[str, Any]:
    lid = str(location_id or "").strip()
    env_model = affordance_model.get("environment_model")
    env_model = env_model if isinstance(env_model, dict) else {}
    locations = env_model.get("locations") if isinstance(env_model.get("locations"), dict) else {}
    row = locations.get(lid)
    return row if isinstance(row, dict) else {}


def _visibility_audibility_evidence(
    *,
    affordance_model: dict[str, Any],
    target_location: str | None,
    current_area: str | None,
) -> str:
    target = str(target_location or "").strip()
    current = str(current_area or "").strip()
    if not target or not current:
        return "visibility_audibility_unknown:location_context_unavailable"
    if target == current:
        return "still_visible"
    target_row = _location_row_from_environment_model(affordance_model, target)
    visibility = target_row.get("visibility_from_room") if isinstance(target_row, dict) else {}
    visibility = visibility if isinstance(visibility, dict) else {}
    can_perceive = {str(item).strip() for item in (visibility.get("can_directly_perceive_room_ids") or [])}
    cannot_perceive = {str(item).strip() for item in (visibility.get("cannot_directly_perceive_room_ids") or [])}
    if current in can_perceive:
        return "still_audible"
    if current in cannot_perceive:
        return "not_audible"
    if target_row:
        return "visibility_audibility_unknown:topology_no_direct_classification"
    return "visibility_audibility_unknown:target_location_not_in_topology"


def _derive_presence_breaks_gathering_evidence(
    *,
    semantic: dict[str, Any],
    affordance_model: dict[str, Any],
    target_type: str | None,
    target_location: str | None,
    action_commit_policy: str,
    affordance_status: str,
) -> dict[str, Any]:
    current_area = _current_area_from_affordance_model(affordance_model)
    target = str(target_location or "").strip() or None
    ttype = str(target_type or "").strip().lower()
    policy = str(action_commit_policy or "").strip().lower()
    status = str(affordance_status or "").strip().lower()

    existing = semantic.get("presence_breaks_gathering_evidence")
    evidence = dict(existing) if isinstance(existing, dict) else {}
    for semantic_key, evidence_key in (
        ("participation_relevance", "participation_relevance"),
        ("gathering_participation_relevance", "participation_relevance"),
        ("visibility_audibility", "visibility_audibility"),
        ("gathering_visibility_audibility", "visibility_audibility"),
    ):
        if evidence.get(evidence_key) is None and semantic.get(semantic_key) is not None:
            evidence[evidence_key] = semantic.get(semantic_key)
    evidence.setdefault("target_location", target)

    if "participation_relevance" not in evidence or evidence.get("participation_relevance") is None:
        if policy != "commit_action" or status not in {"allowed", "allowed_offscreen", "partial"}:
            evidence["participation_relevance"] = "not_applicable:not_committed_action"
        elif ttype == "location" and target and current_area and target != current_area:
            evidence["participation_relevance"] = "broken"
        elif target and current_area and target == current_area:
            evidence["participation_relevance"] = "still_participating"
        elif ttype in {"object", "actor"} and current_area:
            evidence["participation_relevance"] = "still_participating"
        else:
            evidence["participation_relevance"] = "participation_unknown:location_context_unavailable"

    if "visibility_audibility" not in evidence or evidence.get("visibility_audibility") is None:
        evidence["visibility_audibility"] = _visibility_audibility_evidence(
            affordance_model=affordance_model,
            target_location=target,
            current_area=current_area,
        )

    return evidence


def _normalize_grounded_target_role(
    *,
    player_input_kind: str,
    action_kind: str,
    verb: str,
    resolved_target_type: str | None,
    action_commit_policy: str,
) -> tuple[str, str]:
    """Derive broad internal action role from grounded content, not surface verbs."""
    target_type = str(resolved_target_type or "").strip().lower()
    policy = str(action_commit_policy or "").strip().lower()
    if (
        target_type == "location"
        and policy == "commit_action"
        and not is_perception_like_player_input_kind(player_input_kind)
        and not is_speech_like_player_input_kind(player_input_kind)
    ):
        return "movement", "move_to"
    return action_kind, verb


def _row_by_id(
    affordance_model: dict[str, Any],
    target_id: str | None,
    target_type: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    tid = str(target_id or "").strip()
    if not tid:
        return None, None
    groups = (
        (("locations", "location"),)
        if target_type == "location"
        else (("objects", "object"),)
        if target_type == "object"
        else (("actors", "actor"),)
        if target_type == "actor"
        else (("locations", "location"), ("objects", "object"), ("actors", "actor"))
    )
    for group, resolved_type in groups:
        for row in affordance_model.get(group) or []:
            if isinstance(row, dict) and fold_match(tid, str(row.get("id") or "")):
                return row, resolved_type
    return None, None


def _resolve_query(
    query: str | None,
    affordance_model: dict[str, Any],
) -> tuple[str, str, str | None, str | None, str, str | None]:
    q = str(query or "").strip()
    if not q:
        return ("ambiguous", "needs_clarification", None, None, "semantic_resolution_missing_target", None)
    for group, target_type in (("locations", "location"), ("objects", "object"), ("actors", "actor")):
        for row in affordance_model.get(group) or []:
            if not isinstance(row, dict):
                continue
            if any(fold_match(q, term) for term in _terms(row)):
                access = _access(row)
                status, policy = _status_policy_for_access(access)
                return (
                    status,
                    policy,
                    str(row.get("id") or "").strip() or None,
                    target_type,
                    "content_semantic_catalog",
                    access,
                )
    return ("unknown_target", "needs_clarification", None, None, "semantic_catalog_no_match", None)


def _resolved_target(
    *,
    target_id: str | None,
    target_type: str | None,
    matched_alias: str | None,
    confidence: str,
    access: str | None,
) -> ResolvedTarget | None:
    if not target_id:
        return None
    return ResolvedTarget.from_outcome(
        resolved_target_id=target_id,
        resolved_target_type=target_type,
        matched_alias=matched_alias,
        resolution_confidence=confidence,
        access_status=access,
    )


def _semantic_payload(interpreted_input: dict[str, Any]) -> dict[str, Any]:
    for key in ("semantic_action", "semantic_resolution", "ai_semantic_resolution"):
        value = interpreted_input.get(key)
        if isinstance(value, dict) and value:
            return value
    return {}


def _contract_input_languages(interpreted_input: dict[str, Any]) -> tuple[str | None, str | None]:
    contract = interpreted_input.get("semantic_resolution_contract")
    if not isinstance(contract, dict):
        return None, None
    payload = contract.get("input")
    if not isinstance(payload, dict):
        return None, None
    input_language = str(payload.get("session_input_language") or "").strip().lower()[:2] or None
    output_language = str(payload.get("session_output_language") or "").strip().lower()[:2] or None
    return input_language, output_language


def _make_frame(
    *,
    raw_text: str,
    pik: str,
    action_kind: str,
    verb: str,
    speech_text: str | None,
    target_query: str | None,
    rt: ResolvedTarget | None,
    aff: AffordanceResolutionContract,
    narrator_expected: bool,
    npc_expected: bool,
    actor_id: str | None,
    selected_actor_id: str | None,
    source_query: str | None = None,
    resolved_source: ResolvedTarget | None = None,
    source_resolution_source: str | None = None,
    validation_surface: str | None = None,
    projection_rule_id: str | None = None,
    normalized_english_text: str | None = None,
    session_input_language: str | None = None,
    session_output_language: str | None = None,
    semantic_inference: dict[str, Any] | None = None,
    canonical_path_effect: str | None = None,
) -> PlayerActionFrameContract:
    return PlayerActionFrameContract(
        raw_text=str(raw_text or "").strip(),
        input_kind=pik,
        action_kind=action_kind,
        verb=verb,
        speech_text=speech_text,
        target_query=target_query,
        resolved_target=rt,
        affordance_resolution=aff,
        narrator_response_expected=narrator_expected,
        npc_response_expected=npc_expected,
        actor_id=actor_id or None,
        selected_actor_id=selected_actor_id,
        source_query=source_query,
        resolved_source=resolved_source,
        source_resolution_source=source_resolution_source,
        validation_surface=validation_surface,
        projection_rule_id=projection_rule_id,
        normalized_english_text=normalized_english_text,
        internal_resolution_language="en",
        session_input_language=session_input_language,
        session_output_language=session_output_language,
        semantic_inference=semantic_inference if isinstance(semantic_inference, dict) else None,
        canonical_path_effect=canonical_path_effect,
    )


def _finalize_resolution_envelope(
    *,
    frame: PlayerActionFrameContract,
    aff: AffordanceResolutionContract,
    scene_affordance_model: dict[str, Any],
    semantic_payload: dict[str, Any] | None,
    kanon_break: bool = False,
    kanon_break_reason: str | None = None,
    target_location_hint: Any = None,
) -> dict[str, Any]:
    """Compose the resolver return envelope including ``free_player_action_resolution.v1``.

    The envelope shape is preserved from the original four return paths of
    ``resolve_player_action`` (frame, affordance, scene affordance model,
    kanon_break, kanon_break_reason). PR-A adds:

    * the closed-enum contract dict under
      ``"free_player_action_resolution"`` at the envelope root, and
    * the same dict embedded inside the frame at
      ``frame_dict["free_player_action_resolution"]`` so existing graph-state
      propagation flows the contract through to downstream consumers without
      requiring executor / manager edits.
    """
    frame_dict = frame.to_dict()
    aff_dict = aff.to_dict()
    contract = build_free_player_action_resolution(
        affordance_resolution=aff_dict,
        player_action_frame=frame_dict,
        semantic_payload=semantic_payload,
        target_resolution_source=aff_dict.get("target_resolution_source"),
        target_location_hint=target_location_hint,
    )
    frame_dict["free_player_action_resolution"] = contract
    # PR-B: project canonical_path_hold_effect.v1 over the resolver contract +
    # the existing frame.canonical_path_effect literal. The builder returns
    # None for any action class that must not hold (unknown / criminal /
    # high-risk / non-commit / not "hold_current_step"); the dict is attached
    # to the envelope only when applicable so consumers can branch on its
    # presence without dispatch helpers.
    hold_effect = build_canonical_path_hold_effect(
        free_player_action_resolution=contract,
        canonical_path_effect=frame_dict.get("canonical_path_effect"),
        affordance_resolution=aff_dict,
    )
    if hold_effect is not None:
        frame_dict["canonical_path_hold_effect"] = hold_effect
    return {
        "player_action_frame": frame_dict,
        "affordance_resolution": aff_dict,
        "scene_affordance_model": scene_affordance_model,
        "kanon_break": bool(kanon_break),
        "kanon_break_reason": kanon_break_reason if kanon_break else None,
        "free_player_action_resolution": contract,
        "canonical_path_hold_effect": hold_effect,
    }


def resolve_player_action(
    *,
    raw_text: str,
    interpreted_input: dict[str, Any],
    module_id: str,
    runtime_projection: dict[str, Any],
    content_modules_root: Path | None = None,
    player_local_context: dict[str, Any] | None = None,
    environment_state: dict[str, Any] | None = None,
    environment_model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del player_local_context
    pik = str(interpreted_input.get("player_input_kind") or "ambiguous").strip().lower() or "ambiguous"
    actor_id = str(interpreted_input.get("actor_id") or interpreted_input.get("player_input_actor_id") or "").strip()
    selected_actor_id = str(
        runtime_projection.get("human_actor_id")
        or runtime_projection.get("selected_player_role")
        or actor_id
        or ""
    ).strip() or None

    if is_non_story_control_player_input_kind(pik):
        aff = AffordanceResolutionContract(
            status="skipped",
            action_commit_policy="no_commit",
            reason="meta_input_control_path",
            resolved_target=None,
            target_resolution_source="meta_control_path",
            access_status=None,
        )
        frame = _make_frame(
            raw_text=raw_text,
            pik=pik,
            action_kind="control",
            verb="meta",
            speech_text=None,
            target_query=None,
            rt=None,
            aff=aff,
            narrator_expected=False,
            npc_expected=False,
            actor_id=actor_id,
            selected_actor_id=selected_actor_id,
            validation_surface="meta_control_path",
            projection_rule_id=str(interpreted_input.get("deterministic_intent_rule") or "").strip() or None,
        )
        return _finalize_resolution_envelope(
            frame=frame,
            aff=aff,
            scene_affordance_model={},
            semantic_payload=None,
        )

    affordance_model = build_scene_affordance_model(
        module_id=module_id,
        runtime_projection=runtime_projection,
        content_modules_root=content_modules_root,
        environment_state=environment_state,
        environment_model=environment_model,
    )
    semantic = _semantic_payload(interpreted_input)
    contract = interpreted_input.get("semantic_resolution_contract")
    if isinstance(contract, dict):
        affordance_model["semantic_resolution_contract"] = contract
    session_input_language, session_output_language = _contract_input_languages(interpreted_input)

    if not semantic and not is_speech_like_player_input_kind(pik):
        aff = AffordanceResolutionContract(
            status="ambiguous",
            action_commit_policy="needs_clarification",
            reason="semantic_ai_resolution_required",
            resolved_target=None,
            target_resolution_source="semantic_ai_resolution_required",
            access_status=None,
        )
        frame = _make_frame(
            raw_text=raw_text,
            pik=pik,
            action_kind="semantic_resolution_required",
            verb="semantic_resolution_required",
            speech_text=None,
            target_query=None,
            rt=None,
            aff=aff,
            narrator_expected=True,
            npc_expected=False,
            actor_id=actor_id,
            selected_actor_id=selected_actor_id,
            validation_surface="semantic_ai_resolution_required",
            projection_rule_id=str(interpreted_input.get("deterministic_intent_rule") or "").strip() or None,
            session_input_language=session_input_language,
            session_output_language=session_output_language,
        )
        return _finalize_resolution_envelope(
            frame=frame,
            aff=aff,
            scene_affordance_model=affordance_model,
            semantic_payload=None,
        )

    if is_speech_like_player_input_kind(pik) and not semantic:
        aff = AffordanceResolutionContract(
            status="allowed",
            action_commit_policy="commit_speech",
            reason=None,
            resolved_target=None,
            target_resolution_source="speech_turn",
            access_status=None,
        )
        frame = _make_frame(
            raw_text=raw_text,
            pik=pik,
            action_kind="speech",
            verb="utterance",
            speech_text=str(raw_text or "").strip(),
            target_query=None,
            rt=None,
            aff=aff,
            narrator_expected=False,
            npc_expected=True,
            actor_id=actor_id,
            selected_actor_id=selected_actor_id,
            validation_surface="speech_without_action_resolution",
            session_input_language=session_input_language,
            session_output_language=session_output_language,
        )
        return _finalize_resolution_envelope(
            frame=frame,
            aff=aff,
            scene_affordance_model=affordance_model,
            semantic_payload=None,
        )

    pik = str(semantic.get("player_input_kind") or pik).strip().lower() or pik
    normalized_english_text = (
        str(
            semantic.get("normalized_english_text")
            or semantic.get("english_text")
            or semantic.get("internal_english_text")
            or ""
        ).strip()
        or None
    )
    action_kind = str(
        semantic.get("normalized_english_action_kind") or semantic.get("action_kind") or "semantic_action"
    ).strip() or "semantic_action"
    verb = str(semantic.get("normalized_english_verb") or semantic.get("verb") or "semantic_action").strip() or "semantic_action"
    speech_text = str(semantic.get("speech_text") or "").strip() or None
    if is_mixed_player_input_kind(pik) and not speech_text:
        caps = interpreted_input.get("projection_captures")
        if isinstance(caps, dict):
            speech_text = str(caps.get("speech") or "").strip() or None

    target_query = str(
        semantic.get("target_query_english")
        or semantic.get("english_target_query")
        or semantic.get("target_query")
        or ""
    ).strip() or None
    target_id = str(semantic.get("resolved_target_id") or semantic.get("target_id") or "").strip() or None
    target_type = str(semantic.get("resolved_target_type") or semantic.get("target_type") or "").strip() or None

    row, row_type = _row_by_id(affordance_model, target_id, target_type)
    semantic_inference: dict[str, Any] | None = None
    if row:
        access = _access(row)
        status, policy = _status_policy_for_access(access)
        tid = str(row.get("id") or target_id or "").strip() or None
        ttyp = row_type or target_type
        source = "ai_semantic_resolution.content_id"
    else:
        status, policy, tid, ttyp, source, access = _resolve_query(target_query, affordance_model)
        if status == "unknown_target":
            inferred = _inferred_target_from_semantics(
                semantic,
                affordance_model=affordance_model,
                action_kind=action_kind,
                target_query=target_query,
                target_type=target_type,
            )
            if inferred:
                tid, ttyp, status, policy, semantic_inference = inferred
                source = "ai_semantic_resolution.plausible_inference"
                access = "inferred_plausible"

    ai_policy = str(semantic.get("commit_policy") or "").strip()
    if status in {"unknown_target", "ambiguous"}:
        policy = "needs_clarification"
    elif ai_policy in {"commit_action", "commit_speech", "no_commit", "needs_clarification", "recover_or_reject"}:
        policy = ai_policy
    confidence = str(semantic.get("confidence") or ("high" if tid else "low")).strip() or "low"
    canonical_path_effect = _canonical_path_effect_from_policy(
        semantic,
        affordance_model,
        action_commit_policy=policy,
    )
    action_kind, verb = _normalize_grounded_target_role(
        player_input_kind=pik,
        action_kind=action_kind,
        verb=verb,
        resolved_target_type=ttyp,
        action_commit_policy=policy,
    )
    rt = _resolved_target(
        target_id=tid,
        target_type=ttyp,
        matched_alias=target_query,
        confidence=confidence,
        access=access,
    )
    aff = AffordanceResolutionContract(
        status=status,
        action_commit_policy=policy,
        reason=str(semantic.get("reason") or semantic.get("reasoning_summary") or "").strip() or None,
        resolved_target=rt,
        target_resolution_source=source,
        access_status=access,
    )

    source_query = str(
        semantic.get("source_query_english")
        or semantic.get("english_source_query")
        or semantic.get("source_query")
        or ""
    ).strip() or None
    resolved_source = None
    source_resolution_source = None
    source_id = str(semantic.get("resolved_source_id") or "").strip() or None
    if source_id:
        source_row, source_type = _row_by_id(affordance_model, source_id, None)
        if source_row:
            resolved_source = _resolved_target(
                target_id=str(source_row.get("id") or source_id),
                target_type=source_type,
                matched_alias=source_query,
                confidence=confidence,
                access=_access(source_row),
            )
            source_resolution_source = "ai_semantic_resolution.content_id"

    narrator_expected = bool(semantic.get("narrator_response_expected", interpreted_input.get("narrator_response_expected", True)))
    npc_expected = bool(semantic.get("npc_response_expected", interpreted_input.get("npc_response_expected", False)))
    target_location_hint = (
        _semantic_text(
            semantic,
            "target_location",
            "containing_location_id",
            "containing_location",
            "actor_location_id",
        )
        or None
    )
    evidence_target_location = (
        tid
        if str(ttyp or "").strip().lower() == "location"
        else target_location_hint
        or _target_location_hint_from_row(row)
        or (
            _current_area_from_affordance_model(affordance_model)
            if str(ttyp or "").strip().lower() in {"object", "actor"}
            else None
        )
    )
    semantic_for_contract = dict(semantic)
    semantic_for_contract["presence_breaks_gathering_evidence"] = (
        _derive_presence_breaks_gathering_evidence(
            semantic=semantic_for_contract,
            affordance_model=affordance_model,
            target_type=ttyp,
            target_location=evidence_target_location,
            action_commit_policy=policy,
            affordance_status=status,
        )
    )

    frame = _make_frame(
        raw_text=raw_text,
        pik=pik,
        action_kind=action_kind,
        verb=verb,
        speech_text=speech_text,
        target_query=target_query,
        rt=rt,
        aff=aff,
        narrator_expected=narrator_expected,
        npc_expected=npc_expected,
        actor_id=actor_id,
        selected_actor_id=selected_actor_id,
        source_query=source_query,
        resolved_source=resolved_source,
        source_resolution_source=source_resolution_source,
        validation_surface="ai_semantic_resolution",
        projection_rule_id=str(interpreted_input.get("deterministic_intent_rule") or "").strip() or None,
        normalized_english_text=normalized_english_text,
        session_input_language=session_input_language,
        session_output_language=session_output_language,
        semantic_inference=semantic_inference,
        canonical_path_effect=canonical_path_effect,
    )
    kanon_break = _semantic_bool(semantic, "kanon_break", "is_kanon_break", "canon_break")
    kanon_break_reason = (
        _semantic_text(semantic, "kanon_break_reason", "canon_break_reason") or None
    )
    if not kanon_break:
        kanon_break_reason = None
    return _finalize_resolution_envelope(
        frame=frame,
        aff=aff,
        scene_affordance_model=affordance_model,
        semantic_payload=semantic_for_contract,
        kanon_break=kanon_break,
        kanon_break_reason=kanon_break_reason,
        target_location_hint=target_location_hint,
    )
