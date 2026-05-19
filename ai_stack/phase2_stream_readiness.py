"""Phase 2 Stage B→C Stream Readiness Diagnostics.

Assesses whether the block_stream_events channel is ready to become
the primary rendering path (Stage C). Reports explicit blockers so the
promotion decision is evidence-based, not guessed.

Readiness levels:
    local_only      — events present, parity aligned, no live WS loop
    candidate       — local_only + frontend adapter supported
    primary_ready   — candidate + WS session loop ready + parity proven

Governance:
* ADR-0058 — Director-Driven Pulse and Block-Stream-Bus
* ADR-0039 — No Pi/Π runtime keys; semantic names only
"""

from __future__ import annotations

from typing import Any

from ai_stack.director_pulse_contracts import (
    CUT_KIND_EM_DASH,
    CUT_KIND_NO_ACTIVE_BLOCK,
    CUT_KIND_SKIP_TO_END,
    CUT_KINDS,
    resolve_cut_kind_for_block_type,
)

# ── Readiness proof levels ────────────────────────────────────────────────────

PROOF_LEVEL_NONE = "none"
PROOF_LEVEL_LOCAL_ONLY = "local_only"
PROOF_LEVEL_CANDIDATE = "candidate"
PROOF_LEVEL_PRIMARY_READY = "primary_ready"

# ── Motivation score source labels ────────────────────────────────────────────

SCORE_SOURCE_REAL = "real_capability_output"
SCORE_SOURCE_DEFAULT = "default_score"


# ── Capability output extraction from graph_state ─────────────────────────────


def extract_capability_outputs_from_graph_state(
    graph_state: dict[str, Any] | None,
) -> dict[str, dict[str, Any] | None]:
    """Extract the structured capability outputs that feed NPC motivation scoring.

    Reads well-known graph_state keys produced by the LangGraph runtime.
    Returns None for any capability that did not produce a structured output
    this turn.

    Args:
        graph_state: The committed graph state dict from the story runtime.

    Returns:
        dict with keys:
            ``scene_energy_output`` — scene_energy_transition dict or None
            ``social_pressure_output`` — social_pressure_state dict or None
            ``relationship_state_output`` — relationship_state dict or None
            ``narrative_momentum_output`` — narrative_momentum_state dict or None
    """
    if not isinstance(graph_state, dict):
        return {
            "scene_energy_output": None,
            "social_pressure_output": None,
            "relationship_state_output": None,
            "narrative_momentum_output": None,
        }

    # scene_energy_transition has "energy_level" field → used by _extract_scene_energy_score
    scene_energy_raw = graph_state.get("scene_energy_transition")
    scene_energy_output = scene_energy_raw if isinstance(scene_energy_raw, dict) else None

    # social_pressure_state has "band" field → used by _extract_social_pressure_score
    social_raw = graph_state.get("social_pressure_state")
    social_pressure_output = social_raw if isinstance(social_raw, dict) else None

    # relationship_state_record has pair_states → used by _extract_relationship_axis_pressure
    relationship_raw = (
        graph_state.get("relationship_state_record")
        or graph_state.get("relationship_state")
    )
    relationship_state_output = relationship_raw if isinstance(relationship_raw, dict) else None

    # narrative_momentum_state has "state" field → used by _extract_narrative_momentum_score
    momentum_raw = graph_state.get("narrative_momentum_state")
    narrative_momentum_output = momentum_raw if isinstance(momentum_raw, dict) else None

    return {
        "scene_energy_output": scene_energy_output,
        "social_pressure_output": social_pressure_output,
        "relationship_state_output": relationship_state_output,
        "narrative_momentum_output": narrative_momentum_output,
    }


def classify_motivation_score_sources(
    graph_state: dict[str, Any] | None,
) -> dict[str, str]:
    """Report which motivation inputs came from real capability outputs vs defaults.

    Returns a dict mapping each score component to its source label.
    Used in diagnostics to distinguish real from default-scored signals.
    """
    outputs = extract_capability_outputs_from_graph_state(graph_state)
    return {
        "scene_energy": SCORE_SOURCE_REAL if outputs["scene_energy_output"] else SCORE_SOURCE_DEFAULT,
        "social_pressure": SCORE_SOURCE_REAL if outputs["social_pressure_output"] else SCORE_SOURCE_DEFAULT,
        "relationship_axis_pressure": SCORE_SOURCE_REAL if outputs["relationship_state_output"] else SCORE_SOURCE_DEFAULT,
        "narrative_momentum": SCORE_SOURCE_REAL if outputs["narrative_momentum_output"] else SCORE_SOURCE_DEFAULT,
    }


# ── Cut-in readiness ──────────────────────────────────────────────────────────


def compute_cut_in_readiness(
    *,
    active_block_id: str | None = None,
    active_block_type: str | None = None,
    player_input_present: bool = False,
    ws_session_loop_supported: bool = False,
) -> dict[str, Any]:
    """Assess cut-in readiness as a diagnostic/pre-live classification.

    Does NOT perform a live interruption. Reports whether the session
    infrastructure supports it and what the cut_kind would be.

    Args:
        active_block_id: ID of the block currently being delivered, if any.
        active_block_type: Block type of active block (determines cut_kind).
        player_input_present: True when a player input arrived mid-delivery.
        ws_session_loop_supported: True when the WS session loop can deliver
            interruptions in real time (currently False — Stage B/C pre-live).

    Returns:
        dict with keys:
            ``active_block_id``          — str or None
            ``active_block_type``        — str or None
            ``computed_cut_kind``        — one of the CUT_KINDS values
            ``player_input_present``     — bool
            ``live_interruption_supported`` — bool (False until WS loop ready)
            ``diagnostic_only``          — always True in Stage B/C
            ``blocker``                  — reason string or None
    """
    cut_kind = resolve_cut_kind_for_block_type(active_block_type)
    blocker: str | None = None

    if not ws_session_loop_supported:
        blocker = "ws_session_loop_not_ready"
    elif not active_block_id:
        blocker = "no_active_block"

    return {
        "active_block_id": active_block_id,
        "active_block_type": active_block_type,
        "computed_cut_kind": cut_kind,
        "player_input_present": player_input_present,
        "live_interruption_supported": ws_session_loop_supported and not blocker,
        "diagnostic_only": True,
        "blocker": blocker,
    }


# ── Stream readiness ──────────────────────────────────────────────────────────


def compute_stream_readiness(
    envelope: dict[str, Any],
    *,
    graph_state: dict[str, Any] | None = None,
    ws_session_loop_supported: bool = False,
    frontend_event_adapter_deployed: bool = True,
) -> dict[str, Any]:
    """Assess readiness of the block_stream_events channel for Stage C promotion.

    Pure function. Does not mutate envelope. Reads envelope diagnostics
    to derive parity and event count. Reports explicit blockers so the
    Stage C promotion decision is evidence-based.

    Args:
        envelope: A ``scene_turn_envelope.v2`` dict, already augmented with
            dual-mode fields (from Stage B).
        graph_state: Committed graph state (used to classify motivation sources).
        ws_session_loop_supported: Whether the WS/session loop supports live
            interruption. False until Stage C infrastructure is ready.
        frontend_event_adapter_deployed: Whether the frontend event adapter
            JS function is present and usable. True when
            ``loadTurnFromEventStream`` is deployed.

    Returns:
        dict with keys:
            ``event_stream_present``          — bool
            ``bundle_fallback_available``      — bool
            ``parity_status``                 — parity_status string
            ``parity_warnings``               — list[str]
            ``frontend_event_adapter_supported`` — bool
            ``motivation_score_sources``       — dict (per-component source labels)
            ``can_be_primary_candidate``       — bool
            ``blockers``                      — list[str]
            ``proof_level``                   — one of the PROOF_LEVEL_* strings
            ``ws_session_loop_supported``      — bool (passed-through)
            ``cut_in_readiness``              — cut-in diagnostic dict
    """
    if not isinstance(envelope, dict):
        return {
            "event_stream_present": False,
            "bundle_fallback_available": False,
            "parity_status": "not_applicable",
            "parity_warnings": ["envelope is not a dict"],
            "frontend_event_adapter_supported": False,
            "motivation_score_sources": {},
            "can_be_primary_candidate": False,
            "blockers": ["envelope_invalid"],
            "proof_level": PROOF_LEVEL_NONE,
            "ws_session_loop_supported": ws_session_loop_supported,
            "cut_in_readiness": compute_cut_in_readiness(),
        }

    vso = envelope.get("visible_scene_output") or {}
    diag = envelope.get("diagnostics") or {}
    pulse = diag.get("director_pulse") or {}
    parity = pulse.get("parity") or {}

    # Event stream present?
    stream_events = vso.get("block_stream_events")
    event_stream_present = isinstance(stream_events, list) and len(stream_events) > 0

    # Bundle present?
    bundle_blocks = vso.get("blocks")
    bundle_fallback_available = isinstance(bundle_blocks, list) and len(bundle_blocks) > 0

    # Parity
    parity_status = str(parity.get("parity_status") or "not_applicable")
    parity_warnings: list[str] = list(parity.get("parity_warnings") or [])

    # Motivation score sources
    score_sources = classify_motivation_score_sources(graph_state)
    default_sources = [k for k, v in score_sources.items() if v == SCORE_SOURCE_DEFAULT]

    # Compute blockers
    blockers: list[str] = []

    if not event_stream_present and bundle_fallback_available:
        blockers.append("event_stream_empty_dual_mode_may_be_off")
    elif not event_stream_present and not bundle_fallback_available:
        blockers.append("both_stream_and_bundle_empty")

    if parity_status not in ("aligned",):
        blockers.append(f"parity_not_aligned:{parity_status}")

    if not frontend_event_adapter_deployed:
        blockers.append("frontend_event_adapter_not_deployed")

    if not ws_session_loop_supported:
        blockers.append("ws_session_loop_not_ready")

    if default_sources:
        blockers.append(f"motivation_inputs_defaulted:{','.join(sorted(default_sources))}")

    # Determine proof level
    parity_ok = parity_status == "aligned" and event_stream_present
    if not parity_ok:
        proof_level = PROOF_LEVEL_NONE
    elif not frontend_event_adapter_deployed:
        proof_level = PROOF_LEVEL_LOCAL_ONLY
    elif not ws_session_loop_supported:
        proof_level = PROOF_LEVEL_CANDIDATE
    else:
        proof_level = PROOF_LEVEL_PRIMARY_READY

    # Primary candidate: parity aligned, events present, frontend adapter ready
    can_be_primary_candidate = (
        parity_ok
        and frontend_event_adapter_deployed
        and not event_stream_present is False
    )

    cut_in_readiness = compute_cut_in_readiness(
        ws_session_loop_supported=ws_session_loop_supported,
    )

    return {
        "event_stream_present": event_stream_present,
        "bundle_fallback_available": bundle_fallback_available,
        "parity_status": parity_status,
        "parity_warnings": parity_warnings,
        "frontend_event_adapter_supported": frontend_event_adapter_deployed,
        "motivation_score_sources": score_sources,
        "can_be_primary_candidate": can_be_primary_candidate,
        "blockers": blockers,
        "proof_level": proof_level,
        "ws_session_loop_supported": ws_session_loop_supported,
        "cut_in_readiness": cut_in_readiness,
    }


__all__ = [
    "PROOF_LEVEL_NONE",
    "PROOF_LEVEL_LOCAL_ONLY",
    "PROOF_LEVEL_CANDIDATE",
    "PROOF_LEVEL_PRIMARY_READY",
    "SCORE_SOURCE_REAL",
    "SCORE_SOURCE_DEFAULT",
    "extract_capability_outputs_from_graph_state",
    "classify_motivation_score_sources",
    "compute_cut_in_readiness",
    "compute_stream_readiness",
]
