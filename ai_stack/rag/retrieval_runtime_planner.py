"""Runtime retrieval routing and authority helpers for bounded context packs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_stack.capabilities.capability_selector import (
    derive_turn_situation_from_runtime_context,
    select_capabilities,
)
from ai_stack.rag.rag_retrieval_dtos import RuntimeRetrievalConfig


RETRIEVAL_PLAN_SCHEMA_VERSION = "runtime_retrieval_plan.v1"
RETRIEVAL_AUTHORITY_SCHEMA_VERSION = "retrieval_authority_boundary.v1"


@dataclass(frozen=True, slots=True)
class RuntimeRetrievalPlan:
    """Bounded retrieval plan derived from runtime turn context."""

    turn_class: str
    active_actor: str
    beat_phase: str
    selected_capabilities: tuple[str, ...]
    profile: str
    max_chunks: int
    audience_scope: str
    authority_scope: str
    allowed_memory_lanes: tuple[str, ...]
    blocked_memory_lanes: tuple[str, ...]
    retrieval_mode: str
    query_hint_tokens: tuple[str, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RETRIEVAL_PLAN_SCHEMA_VERSION,
            "turn_class": self.turn_class,
            "active_actor": self.active_actor,
            "beat_phase": self.beat_phase,
            "selected_capabilities": list(self.selected_capabilities),
            "profile": self.profile,
            "max_chunks": int(self.max_chunks),
            "audience_scope": self.audience_scope,
            "authority_scope": self.authority_scope,
            "allowed_memory_lanes": list(self.allowed_memory_lanes),
            "blocked_memory_lanes": list(self.blocked_memory_lanes),
            "retrieval_mode": self.retrieval_mode,
            "query_hint_tokens": list(self.query_hint_tokens),
            "notes": list(self.notes),
        }


def _as_str(value: Any) -> str:
    return str(value or "").strip()


def _infer_beat_phase(state: dict[str, Any]) -> str:
    candidate = (
        _as_str(state.get("beat_phase"))
        or _as_str((state.get("scene_plan_record") or {}).get("beat_phase"))
        or _as_str((state.get("prior_planner_truth") or {}).get("beat_phase"))
    )
    return candidate or "unknown"


def _query_hint_tokens(state: dict[str, Any], selected_capabilities: tuple[str, ...]) -> tuple[str, ...]:
    tokens: list[str] = []
    tokens.extend([cap for cap in selected_capabilities[:6] if cap])
    for field in ("current_scene_id", "module_id", "selected_scene_function", "pacing_mode"):
        value = _as_str(state.get(field))
        if value:
            tokens.append(value)
    interp = state.get("interpreted_input")
    if isinstance(interp, dict):
        for field in ("input_kind", "intent", "player_input_kind", "selected_handling_path"):
            value = _as_str(interp.get(field))
            if value:
                tokens.append(value)
    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(token)
    return tuple(deduped[:12])


def _lane_policy_for_actor(active_actor: str, selected_capabilities: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    allowed = ["scene_event_log", "beat_history", "world_state_history", "callback_web"]
    blocked = ["agent_private_memory"]
    if active_actor == "npc":
        allowed.extend(["relationship_memory", "agent_private_memory", "knowledge_boundary"])
    elif active_actor == "narrator":
        allowed.extend(["relationship_memory", "knowledge_boundary"])
    else:
        allowed.extend(["relationship_memory"])
    if "dramatic_irony" in selected_capabilities:
        if "knowledge_boundary" not in allowed:
            allowed.append("knowledge_boundary")
    if active_actor == "narrator" and "agent_private_memory" not in blocked:
        blocked.append("agent_private_memory")
    return tuple(allowed), tuple(blocked)


def build_runtime_retrieval_plan(
    *,
    state: dict[str, Any],
    retrieval_config: RuntimeRetrievalConfig,
    authority_scope: str = "runtime_generation",
) -> RuntimeRetrievalPlan:
    """Build a retrieval plan from turn class, capabilities, actor, and beat phase."""
    interpreted_input = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
    actor_lane = state.get("actor_lane_context") if isinstance(state.get("actor_lane_context"), dict) else {}
    active_actor = "player"
    if actor_lane.get("active_actor_lane") in {"npc", "narrator", "player"}:
        active_actor = str(actor_lane.get("active_actor_lane"))
    elif bool(state.get("selected_responder_set")):
        active_actor = "npc"
    elif int(state.get("turn_number") or 0) <= 0:
        active_actor = "narrator"

    situation, warnings = derive_turn_situation_from_runtime_context(
        turn_number=state.get("turn_number"),
        raw_player_input=state.get("player_input"),
        input_kind=interpreted_input.get("input_kind"),
        active_actor=active_actor,
        npc_decision_required=bool(state.get("selected_responder_set")),
        action_resolution_required=bool(state.get("player_action_frame")),
        world_state_change_requested=bool(state.get("proposed_state_effects")),
    )
    selection = select_capabilities(situation)
    turn_class = str(situation.turn_kind.value)
    selected_caps = tuple(selection.enforced) + tuple(selection.observed)
    runtime_projection = state.get("runtime_intelligence_projection")
    if not isinstance(runtime_projection, dict):
        ledger = state.get("turn_aspect_ledger")
        if isinstance(ledger, dict):
            runtime_projection = (
                ledger.get("runtime_intelligence_projection")
                if isinstance(ledger.get("runtime_intelligence_projection"), dict)
                else None
            )
    projection_caps: list[str] = []
    if isinstance(runtime_projection, dict):
        cap_sel = runtime_projection.get("capability_selection")
        if isinstance(cap_sel, dict):
            projection_caps = [
                str(item).strip()
                for item in (cap_sel.get("selected_capabilities") or cap_sel.get("enforced") or [])
                if str(item).strip()
            ]
    if projection_caps:
        selected_caps = tuple(dict.fromkeys([*projection_caps, *selected_caps]))
    beat_phase = _infer_beat_phase(state)
    allowed_lanes, blocked_lanes = _lane_policy_for_actor(active_actor, selected_caps)
    audience_scope = (
        "npc_self" if active_actor == "npc" else "narrator" if active_actor == "narrator" else "player_visible"
    )
    plan_notes = [*selection.warnings, *warnings]
    if authority_scope == "operator_diagnostic":
        audience_scope = "operator_diagnostic"
        allowed_lanes = tuple([*allowed_lanes, "operator_diagnostics", "validator_evidence"])
    return RuntimeRetrievalPlan(
        turn_class=turn_class,
        active_actor=active_actor,
        beat_phase=beat_phase,
        selected_capabilities=selected_caps,
        profile=retrieval_config.retrieval_profile,
        max_chunks=max(1, int(retrieval_config.max_chunks)),
        audience_scope=audience_scope,
        authority_scope=authority_scope,
        allowed_memory_lanes=allowed_lanes,
        blocked_memory_lanes=blocked_lanes,
        retrieval_mode=retrieval_config.retrieval_execution_mode,
        query_hint_tokens=_query_hint_tokens(state, selected_caps),
        notes=tuple(str(item) for item in plan_notes if str(item).strip()),
    )


def build_retrieval_authority_metadata(
    *,
    plan: RuntimeRetrievalPlan,
    retrieval_policy_version: str,
    corpus_fingerprint: str | None = None,
    authority_level: str = "retrieved_unverified",
) -> dict[str, Any]:
    """Build machine-readable authority metadata for retrieval payloads."""
    return {
        "schema_version": RETRIEVAL_AUTHORITY_SCHEMA_VERSION,
        "authority_level": authority_level,
        "authority_scope": plan.authority_scope,
        "audience_scope": plan.audience_scope,
        "turn_class": plan.turn_class,
        "active_actor": plan.active_actor,
        "selected_capabilities": list(plan.selected_capabilities),
        "retrieval_policy_version": retrieval_policy_version,
        "corpus_fingerprint": str(corpus_fingerprint or ""),
        "canonical_commit_required_for_truth": True,
        "may_inform_prompts_only": True,
    }


def apply_authority_boundary_guard(
    *,
    retrieval_payload: dict[str, Any],
    consumer: str,
    authority_critical: bool,
) -> dict[str, Any]:
    """Attach guard flags and fail-closed metadata for retrieval consumers."""
    payload = retrieval_payload if isinstance(retrieval_payload, dict) else {}
    auth = payload.get("retrieval_authority")
    auth_level = str((auth or {}).get("authority_level") or "").strip().lower() if isinstance(auth, dict) else ""
    unverified = auth_level in {"", "retrieved_unverified", "diagnostic_only"}
    payload["boundary_guard"] = {
        "schema_version": RETRIEVAL_AUTHORITY_SCHEMA_VERSION,
        "consumer": consumer,
        "authority_critical": bool(authority_critical),
        "retrieval_unverified": bool(unverified),
        "blocked_as_authority_truth": bool(authority_critical and unverified),
        "canonical_commit_required_for_truth": True,
    }
    return payload

