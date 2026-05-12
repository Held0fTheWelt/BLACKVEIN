"""Player action resolution: ontology-driven verbs, entity registry matching, affordance contracts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ai_stack.action_ontology import infer_verb_and_action_kind
from ai_stack.action_resolution_contracts import (
    AffordanceResolutionContract,
    PlayerActionFrameContract,
    ResolvedTarget,
    collapse_ws,
    fold_match,
    fold_unicode,
    longest_embedded_alias_match,
    strip_directional_prefixes,
)
from story_runtime_core.content_locale import (
    greeting_imperative_addressee_fragment,
    resolve_content_modules_root,
)


def _normalize(value: str) -> str:
    low = str(value or "").strip().lower()
    low = re.sub(r"^[\s]+", "", low)
    low = re.sub(r"^(?:in\s+die|ins|in\s+den|in\s+das|in|zum|zur|zu|nach)\s+", "", low)
    low = re.sub(r"[.!:,;]+$", "", low)
    return low.strip()


# Verbs whose missing direct object should surface as unknown_target (not vague ambiguous).
_OBJECT_ACTION_VERBS: frozenset[str] = frozenset(
    {"activate", "deactivate", "open", "place", "take"}
)

_DE_ARTICLE = r"(?:den|die|das|einen|eine|ein|einem|einer|dem|der|des)"


def _strip_leading_german_article(phrase: str) -> str:
    p = str(phrase or "").strip()
    if not p:
        return ""
    return re.sub(
        rf"(?is)^{_DE_ARTICLE}\s+",
        "",
        p,
        count=1,
    ).strip()


def _extract_german_imperative_object_phrase(raw_text: str, verb: str) -> str | None:
    """Accusative object head for imperative / separable-verb lines (regex-driven, no noun tables)."""
    t = str(raw_text or "").strip()
    if not t:
        return None
    art = _DE_ARTICLE
    v = str(verb or "").strip().lower()
    if v == "activate":
        m = re.search(rf"(?is)\bschalt(?:e|est|et|en)?\s+{art}\s+(.+?)\s+(?:ein|an)\b", t)
        if m:
            return collapse_ws(_strip_leading_german_article(m.group(1)))
        m = re.search(rf"(?is)\bmacht?\s+{art}\s+(.+?)\s+an\b", t)
        if m:
            return collapse_ws(_strip_leading_german_article(m.group(1)))
        return None
    if v == "deactivate":
        m = re.search(rf"(?is)\bschalt(?:e|est|et|en)?\s+{art}\s+(.+?)\s+aus\b", t)
        if m:
            return collapse_ws(_strip_leading_german_article(m.group(1)))
        m = re.search(rf"(?is)\bmacht?\s+{art}\s+(.+?)\s+aus\b", t)
        if m:
            return collapse_ws(_strip_leading_german_article(m.group(1)))
        return None
    if v == "open":
        m = re.search(rf"(?is)\böffn(?:e|est|et|en)?\s+{art}\s+([^\n.?!]+)", t)
        if m:
            return collapse_ws(_strip_leading_german_article(m.group(1)))
        m = re.search(rf"(?is)\bmacht?\s+{art}\s+(.+?)\s+auf\b", t)
        if m:
            return collapse_ws(_strip_leading_german_article(m.group(1)))
        return None
    if v == "place":
        m = re.search(rf"(?is)\bleg(?:e|est|et|en)?\s+{art}\s+(.+?)\s+auf\s+{art}\s+([^\n.?!]+)", t)
        if m:
            return collapse_ws(_strip_leading_german_article(m.group(1)))
        return None
    if v == "take":
        m = re.search(rf"(?is)\b(?:nimm|nehme)\s+{art}\s+([^\n.?!]+)", t)
        if m:
            return collapse_ws(_strip_leading_german_article(m.group(1)))
        return None
    return None


def _load_characters_blob(module_id: str, *, content_modules_root: Path | None = None) -> dict[str, Any]:
    root = resolve_content_modules_root(content_modules_root)
    path = root / str(module_id).strip() / "characters.yaml"
    if not path.exists():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    ch = payload.get("characters")
    return ch if isinstance(ch, dict) else {}


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
        aliases = [str(a).strip() for a in r.get("aliases") or [] if str(a).strip()]
        base_slug = aid.split("_")[0].lower() if aid else ""
        for _ck, blob in chars.items():
            if not isinstance(blob, dict):
                continue
            cid = str(blob.get("id") or "").strip().lower()
            name = str(blob.get("name") or "").strip()
            slug = str(_ck).strip().lower()
            if not name:
                continue
            if aid.lower() == cid or aid.lower().startswith(slug) or base_slug == slug or base_slug == cid:
                if name not in aliases:
                    aliases.append(name)
                # ASCII folding companion for accented display names
                ascii_name = name.encode("ascii", "ignore").decode("ascii").strip()
                if ascii_name and ascii_name not in aliases and ascii_name.lower() != name.lower():
                    aliases.append(ascii_name)
        r["aliases"] = aliases
        out.append(r)
    return out


def _actor_rows_from_runtime_projection(runtime_projection: dict[str, Any]) -> list[dict[str, Any]]:
    actor_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    lanes = runtime_projection.get("actor_lanes")
    if isinstance(lanes, dict):
        for actor_id in lanes.keys():
            aid = str(actor_id or "").strip()
            if not aid or aid in seen:
                continue
            seen.add(aid)
            alias = aid.replace("_", " ").split(" ")[0].strip().capitalize()
            actor_rows.append({"id": aid, "aliases": [aid, alias], "type": "actor"})
    for key in ("human_actor_id", "selected_player_role"):
        aid = str(runtime_projection.get(key) or "").strip()
        if aid and aid not in seen:
            seen.add(aid)
            alias = aid.replace("_", " ").split(" ")[0].strip().capitalize()
            actor_rows.append({"id": aid, "aliases": [aid, alias], "type": "actor"})
    for aid_raw in runtime_projection.get("npc_actor_ids") or []:
        aid = str(aid_raw or "").strip()
        if aid and aid not in seen:
            seen.add(aid)
            alias = aid.replace("_", " ").split(" ")[0].strip().capitalize()
            actor_rows.append({"id": aid, "aliases": [aid, alias], "type": "actor"})
    return actor_rows


def _load_scene_affordances(
    module_id: str,
    *,
    content_modules_root: Path | None = None,
) -> dict[str, Any]:
    root = resolve_content_modules_root(content_modules_root)
    path = root / module_id / "locale" / "scene_affordances.yaml"
    if not path.exists():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    scene_affordances = payload.get("scene_affordances")
    return scene_affordances if isinstance(scene_affordances, dict) else {}


def build_scene_affordance_model(
    *,
    module_id: str,
    runtime_projection: dict[str, Any],
    content_modules_root: Path | None = None,
) -> dict[str, Any]:
    scene_affordances = _load_scene_affordances(
        module_id,
        content_modules_root=content_modules_root,
    )
    raw_actors = _actor_rows_from_runtime_projection(runtime_projection)
    actors = _enrich_actor_aliases(raw_actors, module_id=module_id, content_modules_root=content_modules_root)
    model: dict[str, Any] = {
        "module_id": module_id,
        "current_area": scene_affordances.get("current_area"),
        "inferred_area_policy": scene_affordances.get("inferred_area_policy"),
        "locations": scene_affordances.get("locations")
        if isinstance(scene_affordances.get("locations"), list)
        else [],
        "objects": scene_affordances.get("objects")
        if isinstance(scene_affordances.get("objects"), list)
        else [],
        "actors": actors,
    }
    return model


def _entity_rows_for_scan(affordance_model: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cat in ("locations", "objects", "actors"):
        for row in affordance_model.get(cat) or []:
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _infer_target_query(
    raw_text: str,
    interpreted_input: dict[str, Any],
    verb: str,
    action_kind: str,
    *,
    module_id: str,
    lang: str,
    affordance_model: dict[str, Any],
    content_modules_root: Path | None = None,
) -> str | None:
    captures = (
        interpreted_input.get("projection_captures")
        if isinstance(interpreted_input.get("projection_captures"), dict)
        else {}
    )
    room = str(captures.get("room") or "").strip()
    if room:
        return strip_directional_prefixes(room, lang=lang)
    if verb == "greet" and action_kind == "social_action":
        frag = greeting_imperative_addressee_fragment(
            raw_text,
            lang=lang,
            module_id=module_id,
            content_modules_root=content_modules_root,
        )
        if frag:
            return collapse_ws(frag)
    lg = str(lang or "de").strip().lower()[:2] or "de"
    if lg == "de" and (action_kind == "object_interaction" or verb in {"activate", "deactivate", "open", "place"}):
        frag = _extract_german_imperative_object_phrase(raw_text, verb)
        if frag:
            return collapse_ws(frag)
    pik = str(interpreted_input.get("player_input_kind") or "").strip().lower()
    if pik in {"action", "perception", "mixed"} and verb in {
        "look_at",
        "listen_to",
        "move_to",
        "take",
        "interact",
        "activate",
        "deactivate",
        "open",
        "place",
    }:
        ent_rows = _entity_rows_for_scan(affordance_model)
        eid, alias, _ln = longest_embedded_alias_match(raw_text, rows=ent_rows)
        if alias:
            return collapse_ws(alias)
    return None


def _infer_source_query(raw_text: str, *, lang: str, verb: str) -> str | None:
    """Extract a generic source/container phrase for transitive object actions."""
    text = str(raw_text or "").strip()
    if not text:
        return None
    lg = str(lang or "de").strip().lower()[:2] or "de"
    if lg == "de" and verb in {"take", "open", "place"}:
        m = re.search(rf"(?is)\baus\s+{_DE_ARTICLE}\s+([^\n.?!,;]+)", text)
        if m:
            return collapse_ws(_strip_leading_german_article(m.group(1)))
        m = re.search(rf"(?is)\bvon\s+{_DE_ARTICLE}\s+([^\n.?!,;]+)", text)
        if m:
            return collapse_ws(_strip_leading_german_article(m.group(1)))
    if lg == "en" and verb in {"take", "open", "place"}:
        m = re.search(r"(?is)\b(?:from|out of)\s+(?:the|a|an)?\s*([^\n.?!,;]+)", text)
        if m:
            return collapse_ws(m.group(1))
    return None


def _resolve_target(
    target_query: str | None,
    affordance_model: dict[str, Any],
    *,
    verb: str,
) -> tuple[str, str, str | None, str | None, str | None, str | None]:
    """Return tuple: status, policy, target_id, target_type, source, access."""
    query = str(target_query or "").strip()
    nq = _normalize(query)
    if not nq and verb == "stand_up":
        return (
            "allowed",
            "commit_action",
            None,
            None,
            "posture_local_no_target",
            None,
        )
    if not nq:
        if verb in _OBJECT_ACTION_VERBS:
            return (
                "unknown_target",
                "needs_clarification",
                None,
                None,
                "missing_object_interaction_target",
                None,
            )
        return (
            "ambiguous",
            "needs_clarification",
            None,
            None,
            "missing_target_query",
            None,
        )

    for row in affordance_model.get("locations") or []:
        if not isinstance(row, dict):
            continue
        aliases = [str(a).strip() for a in row.get("aliases") or [] if str(a).strip()]
        aliases.append(str(row.get("id") or "").strip())
        if any(fold_match(nq, a) or fold_match(nq, _normalize(a)) for a in aliases if a):
            access = str(row.get("access") or "").strip() or None
            status = "allowed_offscreen" if access and ("offscreen" in access or "implied" in access) else "allowed"
            tid = str(row.get("id") or "").strip() or None
            return (
                status,
                "commit_action",
                tid,
                "location",
                "scene_affordances.location_alias",
                access,
            )

    for row in affordance_model.get("objects") or []:
        if not isinstance(row, dict):
            continue
        aliases = [str(a).strip() for a in row.get("aliases") or [] if str(a).strip()]
        aliases.append(str(row.get("id") or "").strip())
        if any(fold_match(nq, a) or fold_match(nq, _normalize(a)) for a in aliases if a):
            tid = str(row.get("id") or "").strip() or None
            return ("allowed", "commit_action", tid, "object", "scene_affordances.object_alias", None)

    for row in affordance_model.get("actors") or []:
        if not isinstance(row, dict):
            continue
        aliases = [str(a).strip() for a in row.get("aliases") or [] if str(a).strip()]
        aliases.append(str(row.get("id") or "").strip())
        if any(fold_match(nq, a) or fold_match(nq, _normalize(a)) for a in aliases if a):
            tid = str(row.get("id") or "").strip() or None
            return ("allowed", "commit_action", tid, "actor", "runtime_roster.actor_alias", None)

    folded_q = fold_unicode(nq)
    if len(folded_q) >= 2:
        for row in affordance_model.get("locations") or []:
            if not isinstance(row, dict):
                continue
            aliases = [str(a).strip() for a in row.get("aliases") or [] if str(a).strip()]
            for a in aliases:
                if fold_unicode(a) in folded_q or folded_q in fold_unicode(a):
                    access = str(row.get("access") or "").strip() or None
                    status = "allowed_offscreen" if access and ("offscreen" in access or "implied" in access) else "allowed"
                    tid = str(row.get("id") or "").strip() or None
                    return (
                        status,
                        "commit_action",
                        tid,
                        "location",
                        "scene_affordances.location_substring",
                        access,
                    )
        for row in affordance_model.get("objects") or []:
            if not isinstance(row, dict):
                continue
            aliases = [str(a).strip() for a in row.get("aliases") or [] if str(a).strip()]
            for a in aliases:
                if fold_unicode(a) in folded_q or folded_q in fold_unicode(a):
                    tid = str(row.get("id") or "").strip() or None
                    return ("allowed", "commit_action", tid, "object", "scene_affordances.object_substring", None)
        for row in affordance_model.get("actors") or []:
            if not isinstance(row, dict):
                continue
            aliases = [str(a).strip() for a in row.get("aliases") or [] if str(a).strip()]
            for a in aliases:
                if fold_unicode(a) in folded_q or folded_q in fold_unicode(a):
                    tid = str(row.get("id") or "").strip() or None
                    return ("allowed", "commit_action", tid, "actor", "runtime_roster.actor_substring", None)

    return ("unknown_target", "needs_clarification", None, None, "no_target_match", None)


def _resolve_entity_query(
    query: str | None,
    affordance_model: dict[str, Any],
) -> tuple[str | None, str | None, str | None]:
    """Resolve a non-authoritative source/container query without changing commit policy."""
    nq = _normalize(str(query or ""))
    if not nq:
        return None, None, None
    for cat, target_type in (("locations", "location"), ("objects", "object"), ("actors", "actor")):
        for row in affordance_model.get(cat) or []:
            if not isinstance(row, dict):
                continue
            aliases = [str(a).strip() for a in row.get("aliases") or [] if str(a).strip()]
            aliases.append(str(row.get("id") or "").strip())
            if any(fold_match(nq, a) or fold_match(nq, _normalize(a)) for a in aliases if a):
                return str(row.get("id") or "").strip() or None, target_type, f"scene_affordances.{target_type}_alias"
    folded_q = fold_unicode(nq)
    if len(folded_q) >= 2:
        for cat, target_type in (("locations", "location"), ("objects", "object"), ("actors", "actor")):
            for row in affordance_model.get(cat) or []:
                if not isinstance(row, dict):
                    continue
                aliases = [str(a).strip() for a in row.get("aliases") or [] if str(a).strip()]
                for alias in aliases:
                    if fold_unicode(alias) in folded_q or folded_q in fold_unicode(alias):
                        return (
                            str(row.get("id") or "").strip() or None,
                            target_type,
                            f"scene_affordances.{target_type}_substring",
                        )
    return None, None, "no_source_match"


def resolve_player_action(
    *,
    raw_text: str,
    interpreted_input: dict[str, Any],
    module_id: str,
    runtime_projection: dict[str, Any],
    content_modules_root: Path | None = None,
) -> dict[str, Any]:
    pik = str(interpreted_input.get("player_input_kind") or "speech").strip().lower() or "speech"
    lang = str(interpreted_input.get("lang") or interpreted_input.get("session_output_language") or "de").strip().lower()[:2] or "de"
    # Upstream intent can label bounded German device imperatives as ``speech``. If the
    # action-only ontology path resolves a concrete object-interaction verb, treat as
    # ``action`` so affordances and P0 evidence match resolver semantics (no NPC speech lane).
    if pik in {"speech", "question"}:
        v_act, ak_act = infer_verb_and_action_kind(
            raw_text,
            module_id=module_id,
            player_input_kind="action",
            content_modules_root=content_modules_root,
        )
        if ak_act == "object_interaction" and v_act in _OBJECT_ACTION_VERBS:
            pik = "action"
    verb, action_kind = infer_verb_and_action_kind(
        raw_text,
        module_id=module_id,
        player_input_kind=pik,
        content_modules_root=content_modules_root,
    )
    affordance_model = build_scene_affordance_model(
        module_id=module_id,
        runtime_projection=runtime_projection,
        content_modules_root=content_modules_root,
    )
    speech_text: str | None = None
    if pik == "mixed":
        caps = interpreted_input.get("projection_captures") if isinstance(interpreted_input.get("projection_captures"), dict) else {}
        st = str(caps.get("speech") or "").strip()
        speech_text = st or None
        if verb not in {"stand_up"}:
            verb, action_kind = infer_verb_and_action_kind(
                raw_text,
                module_id=module_id,
                player_input_kind="action",
                content_modules_root=content_modules_root,
            )

    target_query = _infer_target_query(
        raw_text,
        interpreted_input,
        verb,
        action_kind,
        module_id=module_id,
        lang=lang,
        affordance_model=affordance_model,
        content_modules_root=content_modules_root,
    )
    source_query = _infer_source_query(raw_text, lang=lang, verb=verb)

    if pik in {"speech", "question", "meta"}:
        status, policy, tid, ttyp, src, access = (
            "allowed",
            "commit_speech",
            None,
            None,
            "speech_turn",
            None,
        )
    else:
        status, policy, tid, ttyp, src, access = _resolve_target(
            target_query,
            affordance_model,
            verb=verb,
        )
        if verb in {"look_at", "listen_to"} and status == "unknown_target":
            status, policy = "partial", "commit_action"

    actor_id = str(interpreted_input.get("actor_id") or interpreted_input.get("player_input_actor_id") or "").strip()
    selected_actor_id = str(
        runtime_projection.get("human_actor_id")
        or runtime_projection.get("selected_player_role")
        or actor_id
        or ""
    ).strip() or None
    narrator_expected = bool(interpreted_input.get("narrator_response_expected"))
    npc_expected = bool(interpreted_input.get("npc_response_expected"))
    if pik in {"action", "perception", "mixed"}:
        narrator_expected = True
    if pik in {"action", "perception", "mixed"} and verb in {
        "move_to",
        "look_at",
        "listen_to",
        "stand_up",
        "take",
        "activate",
        "deactivate",
        "open",
        "place",
    }:
        npc_expected = False
    if pik == "mixed":
        npc_expected = bool(interpreted_input.get("npc_response_expected", True))

    matched_alias = None
    if target_query and tid:
        matched_alias = target_query.strip()

    res_conf = "high" if tid else ("medium" if status == "partial" else "low")
    rt = ResolvedTarget.from_outcome(
        resolved_target_id=tid,
        resolved_target_type=ttyp,
        matched_alias=matched_alias,
        resolution_confidence=res_conf,
        access_status=access,
    )
    aff = AffordanceResolutionContract(
        status=status,
        action_commit_policy=policy,
        reason=None,
        resolved_target=rt,
        target_resolution_source=src,
        access_status=access,
    )

    rt_for_frame = None if pik in {"speech", "question", "meta"} else rt
    resolved_source = None
    source_resolution_source = None
    if source_query and pik not in {"speech", "question", "meta"}:
        src_id, src_type, source_resolution_source = _resolve_entity_query(source_query, affordance_model)
        if src_id:
            resolved_source = ResolvedTarget.from_outcome(
                resolved_target_id=src_id,
                resolved_target_type=src_type,
                matched_alias=source_query,
                resolution_confidence="high",
                access_status=None,
            )
    frame = PlayerActionFrameContract(
        raw_text=str(raw_text or "").strip(),
        input_kind=pik,
        action_kind=action_kind,
        verb=verb,
        speech_text=speech_text,
        target_query=target_query,
        resolved_target=rt_for_frame,
        affordance_resolution=aff,
        narrator_response_expected=narrator_expected,
        npc_response_expected=npc_expected,
        actor_id=actor_id or None,
        selected_actor_id=selected_actor_id,
        source_query=source_query,
        resolved_source=resolved_source,
        source_resolution_source=source_resolution_source,
        validation_surface=None,
        projection_rule_id=str(interpreted_input.get("deterministic_intent_rule") or "").strip() or None,
    )

    return {
        "player_action_frame": frame.to_dict(),
        "affordance_resolution": aff.to_dict(),
        "scene_affordance_model": affordance_model,
    }
