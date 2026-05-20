"""Closed-enum contract surface for ``free_player_action_resolution.v1``.

This module is the PR-A delivery for the NPC Interactivity roadmap. It carries
the per-turn projection over the existing player-action resolver output that
ADR-0057's Phase-1 amendment names as ``free_player_action_resolution.v1`` and
that ADR-0061 (Draft) and PR-B / PR-C will compose against.

Authoritative governance:

* :doc:`docs/ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference`
  (Phase-1 amendment lists the eight required fields and their closed enums).
* :doc:`docs/ADR/adr-0061-director-pause-mode-for-gathering-interruption`
  (Draft -- Director derives ``presence_breaks_gathering`` from this contract's
  evidence; the resolver carries only a preliminary signal).
* :doc:`docs/ADR/adr-0062-director-realization-thin-path` (composition path
  that the resolver output rides on).
* :doc:`docs/implementation_logs/pr_a_resolver_contract_closure_piv` (PR-A PIV
  artifact -- enumerates the consumers and the guardrails).

The contract is a per-turn dict; it is not a runtime aspect ledger row, it is
not a new graph node, and it does not own Director authority. The dict is
emitted by ``ai_stack.player_action_resolution.resolve_player_action`` on every
return path and embedded inside the existing ``player_action_frame`` payload so
graph-state propagation flows it through without further executor changes.

Vocabulary discipline (ADR-0039 + Phase-1 amendment):

* Closed enums for ``resolved_target_type``, ``affordance_status``,
  ``canon_safety``, ``canonical_risk``, ``action_commit_policy``. Any value
  outside the closed set is a contract violation.
* Semantic capability names only. No Pi / Pi-numbered runtime keys.
* No verb / room / actor / locale literal whitelists.
* ``presence_breaks_gathering`` is **Director-final**; PR-A emits the
  preliminary value (always ``False`` here) plus the evidence triple
  (``target_location``, ``participation_relevance``, ``visibility_audibility``)
  so PR-C's ``compute_gathering_state`` can derive the final value.
"""

from __future__ import annotations

from typing import Any, Final


SCHEMA_VERSION: Final[str] = "free_player_action_resolution.v1"


RESOLVED_TARGET_TYPE_LOCATION: Final[str] = "location"
RESOLVED_TARGET_TYPE_OBJECT: Final[str] = "object"
RESOLVED_TARGET_TYPE_ACTOR: Final[str] = "actor"
RESOLVED_TARGET_TYPE_NONE: Final[str] = "none"

RESOLVED_TARGET_TYPES: Final[frozenset[str]] = frozenset(
    {
        RESOLVED_TARGET_TYPE_LOCATION,
        RESOLVED_TARGET_TYPE_OBJECT,
        RESOLVED_TARGET_TYPE_ACTOR,
        RESOLVED_TARGET_TYPE_NONE,
    }
)


AFFORDANCE_STATUS_ALLOWED: Final[str] = "allowed"
AFFORDANCE_STATUS_UNKNOWN_TARGET: Final[str] = "unknown_target"

AFFORDANCE_STATUSES: Final[frozenset[str]] = frozenset(
    {AFFORDANCE_STATUS_ALLOWED, AFFORDANCE_STATUS_UNKNOWN_TARGET}
)


CANON_SAFETY_CANON_COMPATIBLE: Final[str] = "canon_compatible"
CANON_SAFETY_CONTENT_SILENT_MUNDANE: Final[str] = "content_silent_mundane"
CANON_SAFETY_NON_LOAD_BEARING: Final[str] = "non_load_bearing"
CANON_SAFETY_REVERSIBLE_LOCAL_DETAIL: Final[str] = "reversible_local_detail"

CANON_SAFETY_VALUES: Final[frozenset[str]] = frozenset(
    {
        CANON_SAFETY_CANON_COMPATIBLE,
        CANON_SAFETY_CONTENT_SILENT_MUNDANE,
        CANON_SAFETY_NON_LOAD_BEARING,
        CANON_SAFETY_REVERSIBLE_LOCAL_DETAIL,
    }
)


CANONICAL_RISK_LOW: Final[str] = "low"
CANONICAL_RISK_MEDIUM: Final[str] = "medium"
CANONICAL_RISK_HIGH: Final[str] = "high"

CANONICAL_RISKS: Final[frozenset[str]] = frozenset(
    {CANONICAL_RISK_LOW, CANONICAL_RISK_MEDIUM, CANONICAL_RISK_HIGH}
)


ACTION_COMMIT_POLICY_COMMIT_ACTION: Final[str] = "commit_action"
ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION: Final[str] = "needs_clarification"

ACTION_COMMIT_POLICIES: Final[frozenset[str]] = frozenset(
    {ACTION_COMMIT_POLICY_COMMIT_ACTION, ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION}
)


PRESENCE_AUTHORITY_DIRECTOR_FINAL: Final[str] = "director_final"
PRESENCE_PROVENANCE_PRELIMINARY: Final[str] = "preliminary_resolver_signal"


REQUIRED_CONTRACT_KEYS: Final[tuple[str, ...]] = (
    "schema_version",
    "resolved_target_type",
    "resolved_target_id",
    "target_location",
    "presence_breaks_gathering",
    "presence_breaks_gathering_authority",
    "presence_breaks_gathering_provenance",
    "presence_breaks_gathering_evidence",
    "affordance_status",
    "canon_safety",
    "canonical_risk",
    "action_commit_policy",
    "classification_reason",
)


def _coerce_string(value: Any) -> str | None:
    """Return a stripped non-empty string or ``None``.

    Conservative coercion -- empty strings, whitespace, and non-string values
    collapse to ``None`` so callers cannot smuggle an unexpected sentinel
    through the contract.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_resolved_target_type(raw: Any) -> str:
    """Project the inner-frame ``resolved_target_type`` onto the closed enum.

    The frame may return ``""`` / ``None`` for ambiguous / meta paths; those
    project to ``"none"``. Any value outside the closed set is mapped to
    ``"none"`` to keep the contract enum strictly closed; the original raw
    value remains observable inside the resolver-internal
    ``target_resolution_source`` and ``classification_reason`` strings.
    """
    text = _coerce_string(raw)
    if text is None:
        return RESOLVED_TARGET_TYPE_NONE
    lowered = text.lower()
    if lowered in RESOLVED_TARGET_TYPES:
        return lowered
    return RESOLVED_TARGET_TYPE_NONE


def _normalize_action_commit_policy(raw: Any) -> str:
    """Map the wider commit-policy vocabulary onto the contract's two enums.

    The resolver's internal vocabulary includes ``commit_action``,
    ``commit_speech``, ``no_commit``, ``needs_clarification``,
    ``recover_or_reject``. Only ``commit_action`` projects onto the contract
    ``commit_action``; every other case is a non-commit decision and projects
    onto ``needs_clarification``, which is the fail-closed default.
    """
    text = _coerce_string(raw)
    if text is None:
        return ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION
    if text.lower() == ACTION_COMMIT_POLICY_COMMIT_ACTION:
        return ACTION_COMMIT_POLICY_COMMIT_ACTION
    return ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION


def _normalize_affordance_status(
    *,
    raw_status: Any,
    commit_policy: str,
) -> str:
    """Project the wider affordance-status vocabulary onto the closed enum.

    The internal vocabulary includes ``allowed``, ``allowed_offscreen``,
    ``ambiguous``, ``blocked``, ``partial``, ``prevented``, ``skipped``,
    ``unknown_target``. The contract enum is only ``{allowed, unknown_target}``.

    Projection rule (per ADR-0057 amendment §"Contract 1"):

    * ``commit_action`` always projects to ``allowed`` (we have a target the
      runtime is willing to act on, even if the access path is implied or
      offscreen).
    * Any non-commit policy projects to ``unknown_target`` so the contract
      surfaces the missing / unsafe / non-actionable case as a single closed
      enum value, regardless of internal vocabulary nuance. The original
      internal status remains observable via ``classification_reason`` for
      diagnostics.
    """
    if commit_policy == ACTION_COMMIT_POLICY_COMMIT_ACTION:
        return AFFORDANCE_STATUS_ALLOWED
    text = _coerce_string(raw_status)
    if text is not None and text.lower() == AFFORDANCE_STATUS_ALLOWED:
        # Defensive: an "allowed" status with a non-commit policy is a
        # resolver inconsistency; fail-closed to unknown_target so the
        # contract never carries a silent allowance without a commit.
        return AFFORDANCE_STATUS_UNKNOWN_TARGET
    return AFFORDANCE_STATUS_UNKNOWN_TARGET


def _normalize_canon_safety(raw: Any) -> str | None:
    """Return a closed-enum value or ``None`` for non-mundane cases.

    The contract allows ``None`` -- in that case ``canonical_risk`` carries the
    risk band. Only the four closed values pass through; everything else
    (including the resolver's internal ``hidden_or_load_bearing_fact`` or
    other risk-band tokens) collapses to ``None``.
    """
    text = _coerce_string(raw)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in CANON_SAFETY_VALUES:
        return lowered
    return None


def _normalize_canonical_risk(
    *,
    raw_risk: Any,
    commit_policy: str,
) -> str:
    """Return the canonical-risk band, applying the fail-closed default.

    Rule:

    * If the semantic payload reports an explicit closed-enum value, use it.
    * Otherwise, fail-closed: a ``needs_clarification`` policy yields
      ``medium``; a ``commit_action`` policy yields ``low`` only when the
      payload is also explicitly ``low`` or the canon-safety value is one of
      the mundane closed-enum values; otherwise ``medium``.
    """
    text = _coerce_string(raw_risk)
    if text is not None:
        lowered = text.lower()
        if lowered in CANONICAL_RISKS:
            return lowered
    if commit_policy == ACTION_COMMIT_POLICY_COMMIT_ACTION:
        return CANONICAL_RISK_LOW
    return CANONICAL_RISK_MEDIUM


def _derive_target_location(
    *,
    resolved_target_type: str,
    resolved_target_id: str | None,
    target_location_hint: Any,
) -> str | None:
    """Return the target location id when applicable, otherwise ``None``.

    For a movement (``location`` target), ``target_location`` mirrors
    ``resolved_target_id``. For object / actor / none targets, an explicit
    ``target_location_hint`` from the semantic payload or environment frame
    may carry the containing location; otherwise ``None``.
    """
    if resolved_target_type == RESOLVED_TARGET_TYPE_LOCATION:
        return _coerce_string(resolved_target_id)
    hint = _coerce_string(target_location_hint)
    return hint if hint else None


def _derive_classification_reason(
    *,
    resolved_target_id: str | None,
    target_resolution_source: Any,
    affordance_reason: Any,
    semantic_reason: Any,
) -> str | None:
    """Return a non-empty reason string when the resolved id is missing.

    The contract requires a ``classification_reason`` whenever
    ``resolved_target_id`` is ``None``. The reason is sourced, in priority
    order, from:

    1. the semantic-payload reasoning summary (if present),
    2. the affordance contract's reason string,
    3. the resolver-internal ``target_resolution_source`` token.

    When the id **is** bound, the reason is allowed to be ``None``.
    """
    if _coerce_string(resolved_target_id) is not None:
        # The reason field is still emitted when present, but it is not
        # required by the contract when the id is bound.
        for candidate in (semantic_reason, affordance_reason):
            text = _coerce_string(candidate)
            if text is not None:
                return text
        return None
    for candidate in (semantic_reason, affordance_reason, target_resolution_source):
        text = _coerce_string(candidate)
        if text is not None:
            return text
    return "semantic_resolution_missing_target"


def _participation_relevance_from_semantic(semantic: dict[str, Any] | None) -> str | None:
    """Pull a ``participation_relevance`` evidence string when present.

    PR-A only carries the resolver's own evidence; the Director composes the
    final ``presence_breaks_gathering`` in PR-C. Missing evidence is allowed
    and surfaces as ``None``.
    """
    if not isinstance(semantic, dict):
        return None
    evidence = semantic.get("presence_breaks_gathering_evidence")
    if isinstance(evidence, dict):
        text = _coerce_string(evidence.get("participation_relevance"))
        if text is not None:
            return text
    for key in (
        "participation_relevance",
        "gathering_participation_relevance",
        "participation",
    ):
        value = semantic.get(key)
        text = _coerce_string(value)
        if text is not None:
            return text
    return None


def _visibility_audibility_from_semantic(semantic: dict[str, Any] | None) -> str | None:
    """Pull a ``visibility_audibility`` evidence string when present."""
    if not isinstance(semantic, dict):
        return None
    evidence = semantic.get("presence_breaks_gathering_evidence")
    if isinstance(evidence, dict):
        text = _coerce_string(evidence.get("visibility_audibility"))
        if text is not None:
            return text
    for key in (
        "visibility_audibility",
        "visibility",
        "audibility",
        "gathering_visibility_audibility",
    ):
        value = semantic.get(key)
        text = _coerce_string(value)
        if text is not None:
            return text
    return None


def build_free_player_action_resolution(
    *,
    affordance_resolution: dict[str, Any] | None,
    player_action_frame: dict[str, Any] | None,
    semantic_payload: dict[str, Any] | None,
    target_resolution_source: Any = None,
    target_location_hint: Any = None,
) -> dict[str, Any]:
    """Project the resolver's per-turn data onto ``free_player_action_resolution.v1``.

    Inputs are read-only; the function returns a fresh dict carrying exactly
    the keys listed in ``REQUIRED_CONTRACT_KEYS`` plus the ``schema_version``
    constant. Callers (the resolver and its tests) are responsible for passing
    the affordance contract dict, the frame dict, and the upstream semantic
    payload that the resolver classified.

    Args:
        affordance_resolution: ``AffordanceResolutionContract.to_dict()`` output
            or an equivalent structured dict.
        player_action_frame: ``PlayerActionFrameContract.to_dict()`` output or
            an equivalent structured dict.
        semantic_payload: the AI semantic payload the resolver classified
            (``semantic_action`` / ``ai_semantic_resolution``); may be empty.
        target_resolution_source: the resolver-internal source token used when
            no explicit reason was captured in the affordance contract.
        target_location_hint: optional containing-location hint for non-location
            targets (object inside a room, actor at a room); ``None`` when the
            resolver has no such hint.

    Returns:
        A dict with the closed-enum projection and the preliminary
        ``presence_breaks_gathering`` triple (value + authority + provenance
        + evidence). Every field listed in ``REQUIRED_CONTRACT_KEYS`` is
        present.
    """
    aff = affordance_resolution if isinstance(affordance_resolution, dict) else {}
    frame = player_action_frame if isinstance(player_action_frame, dict) else {}
    semantic = semantic_payload if isinstance(semantic_payload, dict) else None

    raw_resolved_target_id = (
        frame.get("resolved_target_id")
        if frame.get("resolved_target_id") is not None
        else aff.get("resolved_target_id")
    )
    raw_resolved_target_type = (
        frame.get("resolved_target_type")
        if frame.get("resolved_target_type") is not None
        else aff.get("resolved_target_type")
    )
    raw_affordance_status = (
        aff.get("affordance_status")
        if aff.get("affordance_status") is not None
        else frame.get("affordance_status")
    )
    raw_action_commit_policy = (
        aff.get("action_commit_policy")
        if aff.get("action_commit_policy") is not None
        else frame.get("action_commit_policy")
    )

    semantic_inference = frame.get("semantic_inference")
    semantic_inference = semantic_inference if isinstance(semantic_inference, dict) else {}
    canon_safety_raw = (
        semantic_inference.get("canon_safety")
        if semantic_inference
        else None
    )
    if canon_safety_raw is None and isinstance(semantic, dict):
        canon_safety_raw = semantic.get("canon_safety") or semantic.get("canonical_safety")
    canonical_risk_raw = (
        semantic_inference.get("canonical_risk")
        if semantic_inference
        else None
    )
    if canonical_risk_raw is None and isinstance(semantic, dict):
        canonical_risk_raw = semantic.get("canonical_risk") or semantic.get("canon_risk")
    semantic_reason = None
    if isinstance(semantic, dict):
        semantic_reason = semantic.get("reason") or semantic.get("reasoning_summary")

    commit_policy = _normalize_action_commit_policy(raw_action_commit_policy)
    affordance_status = _normalize_affordance_status(
        raw_status=raw_affordance_status,
        commit_policy=commit_policy,
    )
    resolved_target_id = _coerce_string(raw_resolved_target_id)
    resolved_target_type = _normalize_resolved_target_type(raw_resolved_target_type)
    canon_safety = _normalize_canon_safety(canon_safety_raw)
    canonical_risk = _normalize_canonical_risk(
        raw_risk=canonical_risk_raw,
        commit_policy=commit_policy,
    )
    target_location = _derive_target_location(
        resolved_target_type=resolved_target_type,
        resolved_target_id=resolved_target_id,
        target_location_hint=target_location_hint,
    )
    classification_reason = _derive_classification_reason(
        resolved_target_id=resolved_target_id,
        target_resolution_source=(
            target_resolution_source
            if target_resolution_source is not None
            else aff.get("target_resolution_source")
        ),
        affordance_reason=aff.get("reason"),
        semantic_reason=semantic_reason,
    )

    presence_evidence: dict[str, Any] = {
        "target_location": (
            semantic.get("presence_breaks_gathering_evidence", {}).get("target_location")
            if isinstance(semantic, dict)
            and isinstance(semantic.get("presence_breaks_gathering_evidence"), dict)
            else target_location
        ),
        "participation_relevance": _participation_relevance_from_semantic(semantic),
        "visibility_audibility": _visibility_audibility_from_semantic(semantic),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "resolved_target_type": resolved_target_type,
        "resolved_target_id": resolved_target_id,
        "target_location": target_location,
        # Director-final field (ADR-0057 amendment + ADR-0061 Draft). PR-A
        # carries the conservative ``False`` default and exposes the evidence
        # triple so PR-C's ``compute_gathering_state`` can derive the final
        # value without re-walking the resolver.
        "presence_breaks_gathering": False,
        "presence_breaks_gathering_authority": PRESENCE_AUTHORITY_DIRECTOR_FINAL,
        "presence_breaks_gathering_provenance": PRESENCE_PROVENANCE_PRELIMINARY,
        "presence_breaks_gathering_evidence": presence_evidence,
        "affordance_status": affordance_status,
        "canon_safety": canon_safety,
        "canonical_risk": canonical_risk,
        "action_commit_policy": commit_policy,
        "classification_reason": classification_reason,
    }


__all__ = [
    "SCHEMA_VERSION",
    "RESOLVED_TARGET_TYPE_LOCATION",
    "RESOLVED_TARGET_TYPE_OBJECT",
    "RESOLVED_TARGET_TYPE_ACTOR",
    "RESOLVED_TARGET_TYPE_NONE",
    "RESOLVED_TARGET_TYPES",
    "AFFORDANCE_STATUS_ALLOWED",
    "AFFORDANCE_STATUS_UNKNOWN_TARGET",
    "AFFORDANCE_STATUSES",
    "CANON_SAFETY_CANON_COMPATIBLE",
    "CANON_SAFETY_CONTENT_SILENT_MUNDANE",
    "CANON_SAFETY_NON_LOAD_BEARING",
    "CANON_SAFETY_REVERSIBLE_LOCAL_DETAIL",
    "CANON_SAFETY_VALUES",
    "CANONICAL_RISK_LOW",
    "CANONICAL_RISK_MEDIUM",
    "CANONICAL_RISK_HIGH",
    "CANONICAL_RISKS",
    "ACTION_COMMIT_POLICY_COMMIT_ACTION",
    "ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION",
    "ACTION_COMMIT_POLICIES",
    "PRESENCE_AUTHORITY_DIRECTOR_FINAL",
    "PRESENCE_PROVENANCE_PRELIMINARY",
    "REQUIRED_CONTRACT_KEYS",
    "build_free_player_action_resolution",
]
