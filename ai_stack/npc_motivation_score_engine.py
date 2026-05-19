"""NPC Motivation Score Engine — principled-deterministic, per-NPC.

Computes per-NPC motivation scores from structured semantic capability outputs.
No LLM call per tick. Weights and thresholds are content-driven (module.yaml).

Score formula (ADR-0059):
    score(npc) = clamp(
        weighted_sum(scene_energy, social_pressure,
                     relationship_axis_pressure, narrative_momentum)
        * (0.5 + pressure_baseline * 0.5),
        0.0, 1.0
    )

Initiative selection: highest score above threshold wins. No fixed rotation.
Silence when nobody crosses threshold.

Governance:
* ADR-0059 — defines the score formula, inputs, and initiative selection.
* ADR-0058 — tick architecture; this engine is called once per tick evaluation.
* ADR-0039 — no Pi/Π runtime keys; no hardcoded actor IDs.
"""

from __future__ import annotations

from typing import Any

from ai_stack.director_pulse_contracts import (
    CAPABILITY_NAME_ACTOR_PRESSURE_PROFILES,
    CAPABILITY_NAME_NARRATIVE_MOMENTUM,
    CAPABILITY_NAME_PACING_RHYTHM,
    CAPABILITY_NAME_RELATIONSHIP_DYNAMICS,
    CAPABILITY_NAME_SCENE_ENERGY,
    CAPABILITY_NAME_SOCIAL_PRESSURE,
    build_npc_motivation_score,
)

# Fallback weights — used when module policy is absent or malformed.
# Specific modules override via runtime_intelligence.npc_motivation_score.score_weights.
_DEFAULT_WEIGHTS: dict[str, float] = {
    "scene_energy": 0.25,
    "social_pressure": 0.30,
    "relationship_axis_pressure": 0.25,
    "narrative_momentum": 0.20,
}

_DEFAULT_BASE_THRESHOLD: float = 0.55
_DEFAULT_PRESSURE_BASELINE: float = 0.50


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ── Capability output extractors ──────────────────────────────────────────────
# Each extractor reads structured output from one semantic capability.
# Field names are semantic; no Pi/Π runtime keys.


def _extract_scene_energy_score(output: dict[str, Any] | None) -> float:
    if not isinstance(output, dict):
        return _DEFAULT_PRESSURE_BASELINE
    energy_map = {
        "collapsed": 0.10,
        "low": 0.20,
        "contained": 0.40,
        "rising": 0.65,
        "volatile": 0.85,
    }
    level = str(output.get("energy_level") or "").lower()
    if level in energy_map:
        return energy_map[level]
    for key in ("score", "energy_score"):
        raw = output.get(key)
        if raw is not None:
            try:
                return _clamp(float(raw))
            except (TypeError, ValueError):
                pass
    return _DEFAULT_PRESSURE_BASELINE


def _extract_social_pressure_score(output: dict[str, Any] | None) -> float:
    if not isinstance(output, dict):
        return _DEFAULT_PRESSURE_BASELINE
    for key in ("score", "pressure_score"):
        raw = output.get(key)
        if raw is not None:
            try:
                return _clamp(float(raw))
            except (TypeError, ValueError):
                pass
    band_map = {"low": 0.25, "moderate": 0.55, "high": 0.80}
    band = str(output.get("band") or output.get("pressure_band") or "").lower()
    if band in band_map:
        return band_map[band]
    return _DEFAULT_PRESSURE_BASELINE


def _extract_relationship_axis_pressure(
    output: dict[str, Any] | None,
    npc_id: str,
) -> float:
    """Extract per-NPC relationship axis pressure from relationship_dynamics output."""
    if not isinstance(output, dict):
        return _DEFAULT_PRESSURE_BASELINE
    pairs = output.get("pair_states") or output.get("tracked_pairs") or {}
    if isinstance(pairs, dict):
        for key, pair in pairs.items():
            if not isinstance(pair, dict):
                continue
            ids_in_pair = {
                str(key).split("|")[0] if "|" in str(key) else "",
                str(key).split("|")[1] if "|" in str(key) and len(str(key).split("|")) > 1 else "",
                str(pair.get("actor_a") or ""),
                str(pair.get("actor_b") or ""),
            }
            if npc_id in ids_in_pair:
                for tension_key in ("tension_score", "tension"):
                    raw = pair.get(tension_key)
                    if raw is not None:
                        try:
                            return _clamp(float(raw))
                        except (TypeError, ValueError):
                            pass
    for key in ("aggregate_tension", "tension_score"):
        raw = output.get(key)
        if raw is not None:
            try:
                return _clamp(float(raw))
            except (TypeError, ValueError):
                pass
    return _DEFAULT_PRESSURE_BASELINE


def _extract_narrative_momentum_score(output: dict[str, Any] | None) -> float:
    if not isinstance(output, dict):
        return _DEFAULT_PRESSURE_BASELINE
    for key in ("score", "momentum_score"):
        raw = output.get(key)
        if raw is not None:
            try:
                return _clamp(float(raw))
            except (TypeError, ValueError):
                pass
    state_map = {
        "resting": 0.20,
        "building": 0.45,
        "driving": 0.65,
        "cresting": 0.85,
        "releasing": 0.40,
        "stalled": 0.20,
    }
    state = str(output.get("state") or output.get("momentum_state") or "").lower()
    if state in state_map:
        return state_map[state]
    return _DEFAULT_PRESSURE_BASELINE


def _extract_pressure_baseline(
    actor_pressure_profiles: dict[str, Any] | None,
    npc_id: str,
) -> float:
    """Derive per-NPC pressure baseline from content profiles.

    Uses the count and density of ``pressure_markers`` as a proxy for how
    readily this character takes initiative. A character with 5 markers is
    more initiative-prone than one with 2.

    No hardcoded actor IDs. The profile is looked up generically by npc_id.
    """
    if not isinstance(actor_pressure_profiles, dict):
        return _DEFAULT_PRESSURE_BASELINE
    profiles = actor_pressure_profiles.get("profiles") or {}
    if not isinstance(profiles, dict):
        return _DEFAULT_PRESSURE_BASELINE
    profile = profiles.get(npc_id)
    if not isinstance(profile, dict):
        return _DEFAULT_PRESSURE_BASELINE
    markers = profile.get("pressure_markers") or []
    count = len(markers) if isinstance(markers, list) else 0
    return _clamp(0.30 + count * 0.07)


# ── Policy extraction ─────────────────────────────────────────────────────────


def _extract_weights(policy: dict[str, Any] | None) -> dict[str, float]:
    if not isinstance(policy, dict):
        return dict(_DEFAULT_WEIGHTS)
    raw_weights = policy.get("score_weights") or {}
    if not isinstance(raw_weights, dict):
        return dict(_DEFAULT_WEIGHTS)
    result: dict[str, float] = {}
    for key, default in _DEFAULT_WEIGHTS.items():
        raw = raw_weights.get(key)
        try:
            result[key] = _clamp(float(raw), 0.0, 1.0) if raw is not None else default
        except (TypeError, ValueError):
            result[key] = default
    total = sum(result.values())
    if total > 0:
        result = {k: v / total for k, v in result.items()}
    return result


def _extract_base_threshold(policy: dict[str, Any] | None) -> float:
    if not isinstance(policy, dict):
        return _DEFAULT_BASE_THRESHOLD
    raw = policy.get("base_threshold")
    if raw is None:
        return _DEFAULT_BASE_THRESHOLD
    try:
        return _clamp(float(raw), 0.0, 1.0)
    except (TypeError, ValueError):
        return _DEFAULT_BASE_THRESHOLD


def _extract_actor_modifier(policy: dict[str, Any] | None, npc_id: str) -> float:
    """Read per-actor threshold modifier from policy. Generic dict lookup; no actor branches."""
    if not isinstance(policy, dict):
        return 1.0
    modifiers = policy.get("actor_pressure_modifiers") or {}
    if not isinstance(modifiers, dict):
        return 1.0
    raw = modifiers.get(npc_id)
    if raw is None:
        return 1.0
    try:
        return max(0.1, float(raw))
    except (TypeError, ValueError):
        return 1.0


# ── Public API ────────────────────────────────────────────────────────────────


def compute_npc_motivation_scores(
    *,
    npc_ids: list[str],
    tick_id: str,
    scene_energy_output: dict[str, Any] | None = None,
    social_pressure_output: dict[str, Any] | None = None,
    relationship_state_output: dict[str, Any] | None = None,
    narrative_momentum_output: dict[str, Any] | None = None,
    actor_pressure_profiles: dict[str, Any] | None = None,
    npc_motivation_score_policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Compute per-NPC motivation scores from structured capability outputs.

    Pure function. No LLM call. No I/O. No hardcoded actor IDs.
    Returns one ``npc_motivation_score.v1`` dict per npc_id in ``npc_ids``.
    Below-threshold NPCs are included (for diagnostic reproducibility).

    Args:
        npc_ids: NPCs present in the scene. Order does not affect output.
        tick_id: Tick reference from director_tick_decision.
        scene_energy_output: Structured output from scene_energy capability.
        social_pressure_output: Structured output from social_pressure capability.
        relationship_state_output: Structured output from relationship_dynamics capability.
        narrative_momentum_output: Structured output from narrative_momentum capability.
        actor_pressure_profiles: Loaded actor_pressure_profiles.yaml content.
        npc_motivation_score_policy: runtime_intelligence.npc_motivation_score from module.yaml.

    Returns:
        List of ``npc_motivation_score.v1`` dicts.
    """
    weights = _extract_weights(npc_motivation_score_policy)
    base_threshold = _extract_base_threshold(npc_motivation_score_policy)

    scene_energy_val = _extract_scene_energy_score(scene_energy_output)
    social_pressure_val = _extract_social_pressure_score(social_pressure_output)
    narrative_momentum_val = _extract_narrative_momentum_score(narrative_momentum_output)

    source_capabilities = [
        CAPABILITY_NAME_SCENE_ENERGY,
        CAPABILITY_NAME_SOCIAL_PRESSURE,
        CAPABILITY_NAME_RELATIONSHIP_DYNAMICS,
        CAPABILITY_NAME_NARRATIVE_MOMENTUM,
        CAPABILITY_NAME_ACTOR_PRESSURE_PROFILES,
        CAPABILITY_NAME_PACING_RHYTHM,
    ]

    results: list[dict[str, Any]] = []
    for npc_id in npc_ids:
        relationship_val = _extract_relationship_axis_pressure(relationship_state_output, npc_id)
        pressure_baseline = _extract_pressure_baseline(actor_pressure_profiles, npc_id)

        score_components = {
            "scene_energy": scene_energy_val,
            "social_pressure": social_pressure_val,
            "relationship_axis_pressure": relationship_val,
            "narrative_momentum": narrative_momentum_val,
            "pressure_baseline": pressure_baseline,
        }

        weighted_sum = (
            weights["scene_energy"] * scene_energy_val
            + weights["social_pressure"] * social_pressure_val
            + weights["relationship_axis_pressure"] * relationship_val
            + weights["narrative_momentum"] * narrative_momentum_val
        )
        # Pressure baseline scales the weighted score; high baseline → more eager
        combined = _clamp(weighted_sum * (0.5 + pressure_baseline * 0.5))

        actor_modifier = _extract_actor_modifier(npc_motivation_score_policy, npc_id)
        threshold = _clamp(base_threshold * actor_modifier)
        crossed = combined >= threshold

        results.append(
            build_npc_motivation_score(
                npc_id=npc_id,
                tick_id=tick_id,
                score=combined,
                score_components=score_components,
                threshold=threshold,
                crossed_threshold=crossed,
                source_capabilities=source_capabilities,
            )
        )

    return results


def select_initiative_actor(
    motivation_scores: list[dict[str, Any]],
) -> str | None:
    """Return the NPC id with the highest score above threshold, or None.

    No fixed speaker queue. No priority roster. No rotation scheme.
    If nobody crossed threshold → None (Director emits silence this tick).
    If multiple NPCs cross threshold → the one with the highest score wins.
    """
    best_id: str | None = None
    best_score: float = -1.0
    for record in motivation_scores:
        if not isinstance(record, dict):
            continue
        if not record.get("crossed_threshold"):
            continue
        raw = record.get("score")
        try:
            score_f = float(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if score_f > best_score:
            best_score = score_f
            best_id = str(record.get("npc_id") or "").strip() or None
    return best_id


__all__ = [
    "compute_npc_motivation_scores",
    "select_initiative_actor",
]
