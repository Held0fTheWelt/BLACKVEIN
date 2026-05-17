"""Player action resolution through AI-provided semantics and content grounding.

This module intentionally does not infer verbs from raw language. It accepts a
semantic resolution produced by the AI layer and grounds its target ids against
the content-derived interaction surface. Without that semantic resolution it
returns an explicit clarification/AI-required contract instead of falling back
to hidden maps.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ai_stack.action_resolution_contracts import (
    AffordanceResolutionContract,
    PlayerActionFrameContract,
    ResolvedTarget,
    fold_match,
)
from ai_stack.environment_state_contracts import (
    environment_state_to_player_local_context,
    scene_affordance_model_with_environment_state,
)
from story_runtime_core.content_locale import build_interaction_surface, resolve_content_modules_root
from story_runtime_core.player_input_intent_contract import (
    is_mixed_player_input_kind,
    is_non_story_control_player_input_kind,
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
    if "offscreen" in raw or "implied" in raw:
        return ("allowed_offscreen", "commit_action")
    return ("allowed", "commit_action")


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
    )


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
        return {"player_action_frame": frame.to_dict(), "affordance_resolution": aff.to_dict(), "scene_affordance_model": {}}

    affordance_model = build_scene_affordance_model(
        module_id=module_id,
        runtime_projection=runtime_projection,
        content_modules_root=content_modules_root,
        environment_state=environment_state,
        environment_model=environment_model,
    )
    semantic = _semantic_payload(interpreted_input)

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
        )
        return {
            "player_action_frame": frame.to_dict(),
            "affordance_resolution": aff.to_dict(),
            "scene_affordance_model": affordance_model,
        }

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
        )
        return {
            "player_action_frame": frame.to_dict(),
            "affordance_resolution": aff.to_dict(),
            "scene_affordance_model": affordance_model,
        }

    pik = str(semantic.get("player_input_kind") or pik).strip().lower() or pik
    action_kind = str(semantic.get("action_kind") or "semantic_action").strip() or "semantic_action"
    verb = str(semantic.get("verb") or "semantic_action").strip() or "semantic_action"
    speech_text = str(semantic.get("speech_text") or "").strip() or None
    if is_mixed_player_input_kind(pik) and not speech_text:
        caps = interpreted_input.get("projection_captures")
        if isinstance(caps, dict):
            speech_text = str(caps.get("speech") or "").strip() or None

    target_query = str(semantic.get("target_query") or "").strip() or None
    target_id = str(semantic.get("resolved_target_id") or semantic.get("target_id") or "").strip() or None
    target_type = str(semantic.get("resolved_target_type") or semantic.get("target_type") or "").strip() or None

    row, row_type = _row_by_id(affordance_model, target_id, target_type)
    if row:
        access = _access(row)
        status, policy = _status_policy_for_access(access)
        tid = str(row.get("id") or target_id or "").strip() or None
        ttyp = row_type or target_type
        source = "ai_semantic_resolution.content_id"
    else:
        status, policy, tid, ttyp, source, access = _resolve_query(target_query, affordance_model)

    ai_policy = str(semantic.get("commit_policy") or "").strip()
    if ai_policy in {"commit_action", "commit_speech", "no_commit", "needs_clarification", "recover_or_reject"}:
        policy = ai_policy
    confidence = str(semantic.get("confidence") or ("high" if tid else "low")).strip() or "low"
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

    source_query = str(semantic.get("source_query") or "").strip() or None
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
    )
    return {
        "player_action_frame": frame.to_dict(),
        "affordance_resolution": aff.to_dict(),
        "scene_affordance_model": affordance_model,
    }
