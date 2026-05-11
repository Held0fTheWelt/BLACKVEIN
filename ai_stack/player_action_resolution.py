"""Player action resolution contracts and deterministic resolver.

Stage 1 contract (PLAYER-ACTION-RESOLUTION-01):
- raw player input -> PlayerActionFrame
- target/entity resolution against scene affordances
- affordance status + commit policy emitted before validation seam
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import re
import yaml

from story_runtime_core.content_locale import resolve_content_modules_root


_QUESTION_RE = re.compile(r"\?\s*$")
_MOVE_RE = re.compile(
    r"(?is)^\s*(?:ich\s+)?(?:gehe?|lauf(?:e)?|bewege\s+mich|go|walk|move)\b"
)
_LOOK_RE = re.compile(
    r"(?is)\b(?:schaue?|schau|blicke?|look|watch|observe|peek)\b"
)
_TAKE_RE = re.compile(r"(?is)\b(?:nimm|nehme|greif|take|grab|pick\s+up)\b")
_GREET_RE = re.compile(r"(?is)\b(?:begr[üu]ße?|gr[üu]ße?|greet|hello|hi)\b")


def _normalize(value: str) -> str:
    low = str(value or "").strip().lower()
    low = re.sub(r"^[\s]+", "", low)
    low = re.sub(r"^(?:in\s+die|ins|in\s+den|in\s+das|in|zum|zur|zu|nach)\s+", "", low)
    low = re.sub(r"[.!:,;]+$", "", low)
    return low.strip()


def _infer_verb(raw_text: str, player_input_kind: str) -> str:
    low = str(raw_text or "").strip().lower()
    if player_input_kind in {"speech", "question"}:
        return "ask" if _QUESTION_RE.search(low) else "say"
    if player_input_kind == "perception":
        return "look_at"
    if _MOVE_RE.search(low):
        return "move_to"
    if _TAKE_RE.search(low):
        return "take"
    if _GREET_RE.search(low):
        return "greet"
    if _LOOK_RE.search(low):
        return "look_at"
    if player_input_kind == "action":
        return "interact"
    return "say"


def _infer_target_query(raw_text: str, interpreted_input: dict[str, Any], verb: str) -> str | None:
    captures = (
        interpreted_input.get("projection_captures")
        if isinstance(interpreted_input.get("projection_captures"), dict)
        else {}
    )
    room = str(captures.get("room") or "").strip()
    if room:
        return room
    if verb == "look_at":
        raw_low = str(raw_text or "").lower()
        if "fenster" in raw_low or "window" in raw_low:
            return "Fenster"
    return None


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
        "actors": _actor_rows_from_runtime_projection(runtime_projection),
    }
    return model


@dataclass(slots=True)
class ResolutionOutcome:
    affordance_status: str
    action_commit_policy: str
    resolved_target_id: str | None
    resolved_target_type: str | None
    target_resolution_source: str
    resolution_confidence: str
    access_status: str | None = None


def _resolve_target(target_query: str | None, affordance_model: dict[str, Any]) -> ResolutionOutcome:
    query = str(target_query or "").strip()
    nq = _normalize(query)
    if not nq:
        return ResolutionOutcome(
            affordance_status="ambiguous",
            action_commit_policy="needs_clarification",
            resolved_target_id=None,
            resolved_target_type=None,
            target_resolution_source="missing_target_query",
            resolution_confidence="low",
        )

    for row in affordance_model.get("locations") or []:
        if not isinstance(row, dict):
            continue
        aliases = [str(a).strip() for a in row.get("aliases") or [] if str(a).strip()]
        aliases.append(str(row.get("id") or "").strip())
        if nq in {_normalize(a) for a in aliases if a}:
            access = str(row.get("access") or "").strip() or None
            status = "allowed_offscreen" if access and ("offscreen" in access or "implied" in access) else "allowed"
            return ResolutionOutcome(
                affordance_status=status,
                action_commit_policy="commit_action",
                resolved_target_id=str(row.get("id") or "").strip() or None,
                resolved_target_type="location",
                target_resolution_source="scene_affordances.location_alias",
                resolution_confidence="high",
                access_status=access,
            )

    for row in affordance_model.get("objects") or []:
        if not isinstance(row, dict):
            continue
        aliases = [str(a).strip() for a in row.get("aliases") or [] if str(a).strip()]
        aliases.append(str(row.get("id") or "").strip())
        if nq in {_normalize(a) for a in aliases if a}:
            return ResolutionOutcome(
                affordance_status="allowed",
                action_commit_policy="commit_action",
                resolved_target_id=str(row.get("id") or "").strip() or None,
                resolved_target_type="object",
                target_resolution_source="scene_affordances.object_alias",
                resolution_confidence="high",
            )

    for row in affordance_model.get("actors") or []:
        if not isinstance(row, dict):
            continue
        aliases = [str(a).strip() for a in row.get("aliases") or [] if str(a).strip()]
        aliases.append(str(row.get("id") or "").strip())
        if nq in {_normalize(a) for a in aliases if a}:
            return ResolutionOutcome(
                affordance_status="allowed",
                action_commit_policy="commit_action",
                resolved_target_id=str(row.get("id") or "").strip() or None,
                resolved_target_type="actor",
                target_resolution_source="runtime_roster.actor_alias",
                resolution_confidence="high",
            )

    return ResolutionOutcome(
        affordance_status="unknown_target",
        action_commit_policy="needs_clarification",
        resolved_target_id=None,
        resolved_target_type=None,
        target_resolution_source="no_target_match",
        resolution_confidence="low",
    )


def resolve_player_action(
    *,
    raw_text: str,
    interpreted_input: dict[str, Any],
    module_id: str,
    runtime_projection: dict[str, Any],
    content_modules_root: Path | None = None,
) -> dict[str, Any]:
    pik = str(interpreted_input.get("player_input_kind") or "speech").strip().lower() or "speech"
    verb = _infer_verb(raw_text, pik)
    affordance_model = build_scene_affordance_model(
        module_id=module_id,
        runtime_projection=runtime_projection,
        content_modules_root=content_modules_root,
    )
    target_query = _infer_target_query(raw_text, interpreted_input, verb)

    if pik in {"speech", "question", "meta"}:
        outcome = ResolutionOutcome(
            affordance_status="allowed",
            action_commit_policy="commit_speech",
            resolved_target_id=None,
            resolved_target_type=None,
            target_resolution_source="speech_turn",
            resolution_confidence="high",
        )
    else:
        outcome = _resolve_target(target_query, affordance_model)
        if verb in {"look_at", "listen_to"} and outcome.affordance_status == "unknown_target":
            outcome = ResolutionOutcome(
                affordance_status="partial",
                action_commit_policy="commit_action",
                resolved_target_id=outcome.resolved_target_id,
                resolved_target_type=outcome.resolved_target_type,
                target_resolution_source=outcome.target_resolution_source,
                resolution_confidence=outcome.resolution_confidence,
                access_status=outcome.access_status,
            )

    actor_id = str(interpreted_input.get("actor_id") or interpreted_input.get("player_input_actor_id") or "").strip()
    narrator_expected = bool(interpreted_input.get("narrator_response_expected"))
    npc_expected = bool(interpreted_input.get("npc_response_expected"))
    if pik in {"action", "perception"}:
        narrator_expected = True
    if pik in {"action", "perception"} and verb in {"move_to", "look_at", "listen_to"}:
        npc_expected = False

    player_action_frame = {
        "actor_id": actor_id or None,
        "source_text": str(raw_text or "").strip(),
        "player_input_kind": pik,
        "verb": verb,
        "target_query": target_query,
        "resolved_target_id": outcome.resolved_target_id,
        "resolved_target_type": outcome.resolved_target_type,
        "resolution_confidence": outcome.resolution_confidence,
        "affordance_status": outcome.affordance_status,
        "action_commit_policy": outcome.action_commit_policy,
        "narrator_response_expected": narrator_expected,
        "npc_response_expected": npc_expected,
        "target_resolution_source": outcome.target_resolution_source,
        "access_status": outcome.access_status,
    }
    affordance_resolution = {
        "affordance_status": outcome.affordance_status,
        "action_commit_policy": outcome.action_commit_policy,
        "resolved_target_id": outcome.resolved_target_id,
        "resolved_target_type": outcome.resolved_target_type,
        "target_resolution_source": outcome.target_resolution_source,
        "resolution_confidence": outcome.resolution_confidence,
        "access_status": outcome.access_status,
    }
    return {
        "player_action_frame": player_action_frame,
        "affordance_resolution": affordance_resolution,
        "scene_affordance_model": affordance_model,
    }
