"""Phase 2 Stage B — Dual Mode Block Stream.

Produces ``block_stream_event.v1`` events in parallel with the existing
``visible_scene_output.blocks.v1`` bundle. The bundle remains the canonical
primary output; the event stream is a parallel diagnostic channel.

Dual Mode rules (ADR-0058 §8 + Stage B):
* Bundle path is unchanged and remains primary.
* ``block_stream_events`` list is appended to ``visible_scene_output`` dict.
* ``director_pulse`` section is appended to ``diagnostics`` dict.
* All output is read-only diagnostic. No mutation of session state.
* No Pi/Π runtime keys. No hardcoded NPC/room IDs.
* Feature-flagged: off by default (``PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED``).
* Silence is always recorded, even when stream is empty.

Typewriter compatibility:
* ``block_stream_event_to_block_shape()`` — narrow shim so the current
  typewriter renderer can optionally render a single event using the same
  block renderer path, behind a dev-mode flag.

Parity classification (bundle ↔ event stream):
    aligned           — counts match, block_types match in order
    count_mismatch    — different number of events vs bundle blocks
    type_mismatch     — same count but block_type sequence differs
    event_missing     — stream empty, bundle non-empty
    bundle_missing    — bundle empty, stream non-empty
    not_applicable    — neither stream nor bundle has content

Governance:
* ADR-0058 — Director-Driven Pulse and Block-Stream-Bus
* ADR-0059 — Semantic NPC Motivation Score
* ADR-0039 — No Pi/Π runtime keys; semantic names only
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from ai_stack.director_pulse_contracts import (
    BLOCK_TYPE_ACTOR_ACTION,
    BLOCK_TYPE_ACTOR_LINE,
    BLOCK_TYPE_ENVIRONMENT_INTERACTION,
    BLOCK_TYPE_NARRATOR,
    BLOCK_TYPE_SOUFFLEUSE,
    BLOCK_STREAM_TYPES,
    CUT_IN_UNINTERRUPTED,
    LANE_PLAYER_HINT,
    LANE_VISIBLE_SCENE_OUTPUT,
    SCHEMA_BLOCK_STREAM_EVENT,
    TRIGGER_MOTIVATION_THRESHOLD_CROSSED,
    build_block_stream_event,
    build_director_tick_decision,
    build_npc_motivation_score,
)
from ai_stack.director_pulse_shadow import evaluate_director_tick

# ── Feature flag ──────────────────────────────────────────────────────────────
# Default: off. Set PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED=true to enable.

_ENV_FLAG = "PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED"


def is_dual_mode_enabled() -> bool:
    """Return True when the dual-mode event stream is active."""
    return os.environ.get(_ENV_FLAG, "false").strip().lower() in ("1", "true", "yes")


# ── Block-type normalisation ──────────────────────────────────────────────────
# Maps LDSS/live-runtime block_type strings to the closed Pulse-MVP enum.
# Unknown types fall back to narrator (safe, descriptive).

_BLOCK_TYPE_MAP: dict[str, str] = {
    "narrator": BLOCK_TYPE_NARRATOR,
    "actor_line": BLOCK_TYPE_ACTOR_LINE,
    "actor_action": BLOCK_TYPE_ACTOR_ACTION,
    "environment_interaction": BLOCK_TYPE_ENVIRONMENT_INTERACTION,
    "souffleuse": BLOCK_TYPE_SOUFFLEUSE,
    # common aliases in live-runtime output
    "system_boot": BLOCK_TYPE_NARRATOR,
    "system_degraded_notice": BLOCK_TYPE_NARRATOR,
    "player_input_outcome": BLOCK_TYPE_NARRATOR,
    "player_input": BLOCK_TYPE_NARRATOR,
}


def _normalise_block_type(raw: str | None) -> str:
    return _BLOCK_TYPE_MAP.get(str(raw or "").lower(), BLOCK_TYPE_NARRATOR)


def _lane_for_block_type(block_type: str) -> str:
    return LANE_PLAYER_HINT if block_type == BLOCK_TYPE_SOUFFLEUSE else LANE_VISIBLE_SCENE_OUTPUT


def _new_id() -> str:
    return str(uuid.uuid4())


# ── Core conversion ───────────────────────────────────────────────────────────


def bundle_blocks_to_stream_events(
    blocks: list[dict[str, Any]],
    *,
    tick_id: str,
    source: str = "director",
) -> list[dict[str, Any]]:
    """Convert each bundle block into one ``block_stream_event.v1``.

    One block = one event. The bundle list is walked in order; each block dict
    is preserved as ``block_payload`` (a copy, not mutated). ``tick_id`` links
    every event back to the tick decision produced for this turn.

    Pure function. No I/O. No LLM call.

    Args:
        blocks: List of block dicts from ``visible_scene_output.blocks``.
        tick_id: Tick ID from the director_tick_decision produced this turn.
        source: Actor/source label for the event (default "director").

    Returns:
        List of ``block_stream_event.v1`` dicts (one per bundle block).
        Empty when ``blocks`` is empty.
    """
    events: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        raw_type = str(block.get("block_type") or "")
        pulse_type = _normalise_block_type(raw_type)
        lane = _lane_for_block_type(pulse_type)
        event = build_block_stream_event(
            tick_id=tick_id,
            block_type=pulse_type,
            block_payload=dict(block),
            cut_in_state=CUT_IN_UNINTERRUPTED,
            lane=lane,
            source=source,
        )
        events.append(event)
    return events


# ── Parity diagnostics ────────────────────────────────────────────────────────

_PARITY_ALIGNED = "aligned"
_PARITY_COUNT_MISMATCH = "count_mismatch"
_PARITY_TYPE_MISMATCH = "type_mismatch"
_PARITY_EVENT_MISSING = "event_missing"
_PARITY_BUNDLE_MISSING = "bundle_missing"
_PARITY_NOT_APPLICABLE = "not_applicable"


def compute_parity_diagnostics(
    bundle_blocks: list[dict[str, Any]],
    stream_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Classify bundle ↔ event-stream parity for this turn.

    Pure function. Read-only. Does not alter either list.

    Returns:
        dict with keys:
            ``bundle_block_count``       — int
            ``event_count``              — int
            ``event_stream_shadow_only`` — always True (Phase 2 stage B)
            ``parity_status``            — one of the PARITY_* strings
            ``parity_warnings``          — list[str] (empty when aligned)
            ``fallback_bundle_available``— True when bundle is non-empty
    """
    bundle_count = len(bundle_blocks)
    event_count = len(stream_events)
    warnings: list[str] = []

    if bundle_count == 0 and event_count == 0:
        status = _PARITY_NOT_APPLICABLE
    elif event_count == 0 and bundle_count > 0:
        status = _PARITY_EVENT_MISSING
        warnings.append(
            f"event stream empty but bundle has {bundle_count} block(s); "
            "dual mode may not have been enabled when envelope was built"
        )
    elif bundle_count == 0 and event_count > 0:
        status = _PARITY_BUNDLE_MISSING
        warnings.append(
            f"event stream has {event_count} event(s) but bundle is empty"
        )
    elif bundle_count != event_count:
        status = _PARITY_COUNT_MISMATCH
        warnings.append(
            f"bundle has {bundle_count} block(s) but stream has {event_count} event(s)"
        )
    else:
        # Same count — compare block_type sequence
        bundle_types = [
            _normalise_block_type(str(b.get("block_type") or ""))
            for b in bundle_blocks
            if isinstance(b, dict)
        ]
        stream_types = [
            str(e.get("block_type") or "")
            for e in stream_events
            if isinstance(e, dict)
        ]
        if bundle_types != stream_types:
            status = _PARITY_TYPE_MISMATCH
            warnings.append(
                f"block_type sequence differs: bundle={bundle_types} stream={stream_types}"
            )
        else:
            status = _PARITY_ALIGNED

    return {
        "bundle_block_count": bundle_count,
        "event_count": event_count,
        "event_stream_shadow_only": True,
        "parity_status": status,
        "parity_warnings": warnings,
        "fallback_bundle_available": bundle_count > 0,
    }


# ── Typewriter compatibility shim ─────────────────────────────────────────────


def block_stream_event_to_block_shape(event: dict[str, Any]) -> dict[str, Any]:
    """Extract block payload from a block_stream_event for typewriter rendering.

    The current typewriter renderer consumes the block dict directly from
    ``visible_scene_output.blocks``. This shim extracts ``block_payload``
    so the renderer can optionally consume an individual stream event using
    the same code path without modification.

    Pure function. Does not mutate the event.

    Args:
        event: A ``block_stream_event.v1`` dict.

    Returns:
        The ``block_payload`` dict from the event, augmented with
        ``_stream_event_id`` and ``_tick_id`` for traceability.
        Returns an empty dict when the event is malformed.
    """
    if not isinstance(event, dict):
        return {}
    payload = event.get("block_payload")
    if not isinstance(payload, dict):
        return {}
    return {
        **payload,
        "_stream_event_id": event.get("event_id", ""),
        "_tick_id": event.get("tick_id", ""),
        "_lane": event.get("lane", LANE_VISIBLE_SCENE_OUTPUT),
    }


# ── Top-level augmentation ────────────────────────────────────────────────────


def augment_envelope_with_block_stream(
    envelope: dict[str, Any],
    *,
    npc_ids: list[str] | None = None,
    scene_energy_output: dict[str, Any] | None = None,
    social_pressure_output: dict[str, Any] | None = None,
    relationship_state_output: dict[str, Any] | None = None,
    narrative_momentum_output: dict[str, Any] | None = None,
    actor_pressure_profiles: dict[str, Any] | None = None,
    npc_motivation_score_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Augment an existing ``scene_turn_envelope.v2`` dict with dual-mode fields.

    Called from manager._finalize_committed_turn() after the envelope is built.
    Returns a new dict (shallow copy at top level); the original envelope is
    not mutated.

    Adds:
    * ``visible_scene_output.block_stream_events`` — list of block_stream_event.v1
    * ``diagnostics.director_pulse`` — tick decision, npc scores, parity

    Hard guarantees:
    * ``visible_scene_output.blocks`` is unchanged.
    * ``visible_scene_output.contract`` is unchanged.
    * All existing diagnostic keys are preserved.
    * Returns the original envelope dict unchanged if input is malformed.

    Args:
        envelope: Existing ``scene_turn_envelope.v2`` dict (from to_dict()).
        npc_ids: NPC actor IDs for motivation scoring (None → inferred from envelope).
        scene_energy_output: Structured scene_energy capability output.
        social_pressure_output: Structured social_pressure capability output.
        relationship_state_output: Structured relationship_dynamics output.
        narrative_momentum_output: Structured narrative_momentum output.
        actor_pressure_profiles: Loaded actor_pressure_profiles.yaml data.
        npc_motivation_score_policy: runtime_intelligence.npc_motivation_score policy.

    Returns:
        Augmented envelope dict (new top-level dict, sharing inner refs).
    """
    if not isinstance(envelope, dict):
        return envelope

    # Resolve NPC IDs from envelope if not supplied
    resolved_npc_ids: list[str] = list(npc_ids or [])
    if not resolved_npc_ids:
        raw = envelope.get("npc_actor_ids") or []
        resolved_npc_ids = [str(a) for a in raw if str(a).strip()]

    # Run one Director tick for this turn — no state mutation, no LLM call.
    pulse_result = evaluate_director_tick(
        npc_ids=resolved_npc_ids,
        scene_energy_output=scene_energy_output,
        social_pressure_output=social_pressure_output,
        relationship_state_output=relationship_state_output,
        narrative_momentum_output=narrative_momentum_output,
        actor_pressure_profiles=actor_pressure_profiles,
        npc_motivation_score_policy=npc_motivation_score_policy,
        trigger_kind=TRIGGER_MOTIVATION_THRESHOLD_CROSSED,
    )
    tick_id: str = pulse_result["director_tick_decision"]["tick_id"]

    # Extract existing bundle blocks (read-only reference)
    vso = envelope.get("visible_scene_output")
    bundle_blocks: list[dict[str, Any]] = []
    if isinstance(vso, dict) and isinstance(vso.get("blocks"), list):
        bundle_blocks = [b for b in vso["blocks"] if isinstance(b, dict)]

    # Determine source from tick decision
    chosen_actor = pulse_result["director_tick_decision"].get("chosen_actor_id") or "director"

    # Convert bundle blocks → stream events
    stream_events = bundle_blocks_to_stream_events(
        bundle_blocks,
        tick_id=tick_id,
        source=chosen_actor,
    )

    # Compute parity
    parity = compute_parity_diagnostics(bundle_blocks, stream_events)

    # Build augmented visible_scene_output (contract + blocks unchanged)
    new_vso: dict[str, Any] = {
        **(vso if isinstance(vso, dict) else {}),
        "block_stream_events": stream_events,
    }

    # Classify which inputs came from real capability outputs vs defaults.
    # Imported here to avoid circular import (phase2_stream_readiness → director_pulse_contracts).
    try:
        from ai_stack.phase2_stream_readiness import classify_motivation_score_sources
        score_sources = classify_motivation_score_sources(None)
        # Override per actual inputs passed
        score_sources["scene_energy"] = "real_capability_output" if scene_energy_output else "default_score"
        score_sources["social_pressure"] = "real_capability_output" if social_pressure_output else "default_score"
        score_sources["relationship_axis_pressure"] = "real_capability_output" if relationship_state_output else "default_score"
        score_sources["narrative_momentum"] = "real_capability_output" if narrative_momentum_output else "default_score"
    except Exception:
        score_sources = {}

    # Build augmented diagnostics (all existing keys preserved)
    existing_diag = envelope.get("diagnostics") or {}
    new_diag: dict[str, Any] = {
        **existing_diag,
        "director_pulse": {
            "director_tick_decision": pulse_result["director_tick_decision"],
            "npc_motivation_scores": pulse_result["npc_motivation_scores"],
            "player_cut_in_event": pulse_result.get("player_cut_in_event"),
            "parity": parity,
            "motivation_score_sources": score_sources,
            "shadow_only": True,
            "dual_mode_enabled": True,
        },
    }

    return {
        **envelope,
        "visible_scene_output": new_vso,
        "diagnostics": new_diag,
    }


__all__ = [
    "is_dual_mode_enabled",
    "bundle_blocks_to_stream_events",
    "compute_parity_diagnostics",
    "block_stream_event_to_block_shape",
    "augment_envelope_with_block_stream",
    "PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED",
]

# Export the flag name as a constant for use in tests and manager
PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED = _ENV_FLAG
