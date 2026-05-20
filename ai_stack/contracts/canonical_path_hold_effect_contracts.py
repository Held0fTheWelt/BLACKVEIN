"""Closed-enum contract surface for ``canonical_path_hold_effect.v1``.

This module is the PR-B delivery for the NPC Interactivity roadmap. It carries
the per-turn projection over the resolver's ``free_player_action_resolution.v1``
output that the manager's existing ``_turn_holds_canonical_path_for_free_player_action``
gate uses today implicitly via the ``player_action_frame.canonical_path_effect``
literal. PR-B makes the *reason* structured so diagnostic surfaces can read why
the hold fired without inspecting the raw frame literal.

Authoritative governance:

* :doc:`docs/ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference`
  (Phase-1 amendment names ``canonical_path_hold_effect.v1`` as a Phase-1
  contract; the hold is defined by ``player_freedom_policy``,
  ``canon_safety``, ``canonical_risk``, ``action_commit_policy``, and
  ``affordance_status`` only -- never by verb / room / actor whitelists).
* :doc:`docs/ADR/adr-0061-director-pause-mode-for-gathering-interruption`
  (Draft -- PR-C will consume the hold-effect dict to drive
  ``compute_gathering_state``).
* :doc:`docs/ADR/adr-0062-director-realization-thin-path` (composition path
  PR-B rides on).
* :doc:`docs/implementation_logs/pr_b_live_effect_propagation_piv` (PR-B
  PIV artifact -- enumerates consumers and guardrails).

Vocabulary discipline (ADR-0039 + Phase-1 amendment):

* Closed enums for ``effect_kind`` and ``source``. Any value outside the
  closed set is a contract violation.
* Semantic capability names only. No Pi / Pi-numbered runtime keys.
* No verb / room / actor / locale literal whitelists; the hold decision is
  derived from contract fields exclusively.
* The builder returns ``None`` for any action class that must not hold
  (unknown, criminal/impossible, high risk, non-commit). This is the
  fail-closed default and is asserted by PR-B tests.

This module is intentionally pure (no I/O) and reads only the
``free_player_action_resolution.v1`` payload plus the resolver's
``canonical_path_effect`` literal (already derived in
``ai_stack.story_runtime.player_action_resolution._canonical_path_effect_from_policy``).
It does not import the PR-0 diagnostic snapshot stub.
"""

from __future__ import annotations

from typing import Any, Final


SCHEMA_VERSION: Final[str] = "canonical_path_hold_effect.v1"


EFFECT_KIND_HOLD_CURRENT_STEP: Final[str] = "hold_current_step"

EFFECT_KINDS: Final[frozenset[str]] = frozenset({EFFECT_KIND_HOLD_CURRENT_STEP})


# Sources name the semantic provenance of the hold decision. The two closed
# values mirror the resolver's two ways to land on a successful free action
# (catalog-grounded mundane commit, or canon-safe plausible inference). A
# third value covers the case where the policy default fired even though the
# specific resolver path did not provide its own provenance label.
SOURCE_CONTENT_SEMANTIC_CATALOG: Final[str] = "content_semantic_catalog"
SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE: Final[str] = "ai_semantic_plausible_inference"
SOURCE_PLAYER_FREEDOM_POLICY_DEFAULT: Final[str] = "player_freedom_policy_default"

HOLD_EFFECT_SOURCES: Final[frozenset[str]] = frozenset(
    {
        SOURCE_CONTENT_SEMANTIC_CATALOG,
        SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE,
        SOURCE_PLAYER_FREEDOM_POLICY_DEFAULT,
    }
)


# ``until_condition`` is a semantic, content-agnostic predicate string. The
# closed values name the kinds of conditions that release the hold; the
# specific runtime test for each lives in the manager / Director surface,
# not in this module.
UNTIL_CONDITION_CANONICAL_STEP_PROGRESSION_AUTHORIZED: Final[str] = (
    "canonical_step_progression_authorized_by_content_marker"
)
UNTIL_CONDITION_PRESENCE_RESTORED: Final[str] = "required_presence_restored"
UNTIL_CONDITION_TURN_COMMIT_LIFE_CYCLE_END: Final[str] = "turn_commit_life_cycle_end"

HOLD_EFFECT_UNTIL_CONDITIONS: Final[frozenset[str]] = frozenset(
    {
        UNTIL_CONDITION_CANONICAL_STEP_PROGRESSION_AUTHORIZED,
        UNTIL_CONDITION_PRESENCE_RESTORED,
        UNTIL_CONDITION_TURN_COMMIT_LIFE_CYCLE_END,
    }
)


REQUIRED_CONTRACT_KEYS: Final[tuple[str, ...]] = (
    "schema_version",
    "effect_kind",
    "source",
    "until_condition",
    "reason",
    "current_canonical_step_id",
    "free_player_action_resolution",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _coerce_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolver_source(
    *,
    affordance_resolution: dict[str, Any] | None,
    free_player_action_resolution: dict[str, Any] | None,
) -> str:
    """Map the resolver's internal target-resolution-source to the closed enum."""
    raw: Any = None
    if isinstance(affordance_resolution, dict):
        raw = affordance_resolution.get("target_resolution_source")
    if raw is None and isinstance(free_player_action_resolution, dict):
        raw = free_player_action_resolution.get("target_resolution_source")
    text = _coerce_string(raw)
    if text is None:
        return SOURCE_PLAYER_FREEDOM_POLICY_DEFAULT
    lowered = text.lower()
    if "plausible_inference" in lowered or "plausible" in lowered:
        return SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE
    if "content_id" in lowered or "semantic_catalog" in lowered or "catalog" in lowered:
        return SOURCE_CONTENT_SEMANTIC_CATALOG
    return SOURCE_PLAYER_FREEDOM_POLICY_DEFAULT


def _reason_from_resolution(
    free_player_action_resolution: dict[str, Any],
) -> str:
    """Return a non-empty reason string sourced from contract fields.

    Reads the structured contract fields in priority order:

    1. ``classification_reason`` (set by PR-A when populated).
    2. ``canon_safety`` (closed enum value) plus ``canonical_risk``.
    3. A fail-closed default that names the policy default branch.

    The reason is a structured token, not a paraphrased prose string; tests
    assert that the token belongs to a closed-enum-shaped set or is one of
    the values produced by the resolver's contract surface.
    """
    classification = _coerce_string(free_player_action_resolution.get("classification_reason"))
    if classification is not None:
        return classification
    canon_safety = _coerce_string(free_player_action_resolution.get("canon_safety"))
    canonical_risk = _coerce_string(free_player_action_resolution.get("canonical_risk"))
    if canon_safety and canonical_risk:
        return f"{canon_safety}_{canonical_risk}"
    if canon_safety:
        return canon_safety
    return "canon_safe_free_player_action_default_hold"


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------


def build_canonical_path_hold_effect(
    *,
    free_player_action_resolution: dict[str, Any] | None,
    canonical_path_effect: Any,
    affordance_resolution: dict[str, Any] | None = None,
    current_canonical_step_id: Any = None,
    until_condition: str | None = None,
) -> dict[str, Any] | None:
    """Project the resolver contract onto ``canonical_path_hold_effect.v1``.

    Returns the structured hold-effect dict when the per-turn free player
    action is eligible to hold the canonical path; returns ``None``
    otherwise. Eligibility is derived from semantic contract fields only --
    never from raw input strings, verb whitelists, or room whitelists.

    Eligibility rule (fail-closed):

    1. ``canonical_path_effect`` must equal ``"hold_current_step"`` (the
       resolver's existing literal, derived from ``player_freedom_policy``).
    2. ``free_player_action_resolution.action_commit_policy`` must equal
       ``"commit_action"``.
    3. ``free_player_action_resolution.affordance_status`` must equal
       ``"allowed"``.
    4. ``free_player_action_resolution.canonical_risk`` must not equal
       ``"high"``. Medium-risk commits are allowed to hold (they ride the
       canonical pause), but high-risk commits never produce a hold.
    5. ``free_player_action_resolution.canon_safety`` may be ``None`` (the
       resolver projects safety values it cannot map onto the closed enum to
       ``None``); a ``None`` safety paired with a commit_action / allowed /
       non-high-risk policy still holds, because the resolver has already
       committed.

    Args:
        free_player_action_resolution: ``free_player_action_resolution.v1``
            dict emitted by the resolver. The function reads only the closed
            enum fields; never the raw input string.
        canonical_path_effect: The resolver's existing
            ``frame.canonical_path_effect`` literal (the source of truth the
            manager already gates on).
        affordance_resolution: optional ``affordance_resolution`` dict for
            provenance look-up (``target_resolution_source``).
        current_canonical_step_id: optional id of the canonical step the
            hold currently sits on. Carried opaque-as-string; used for
            diagnostic surfacing only.
        until_condition: optional override of the release predicate. When
            omitted, defaults to
            ``UNTIL_CONDITION_CANONICAL_STEP_PROGRESSION_AUTHORIZED``.

    Returns:
        Either a dict carrying every key in ``REQUIRED_CONTRACT_KEYS`` or
        ``None`` when the action is not eligible to hold.
    """
    if not isinstance(free_player_action_resolution, dict):
        return None
    if _coerce_string(canonical_path_effect) != EFFECT_KIND_HOLD_CURRENT_STEP:
        return None
    commit_policy = _coerce_string(free_player_action_resolution.get("action_commit_policy"))
    if commit_policy != "commit_action":
        return None
    affordance_status = _coerce_string(free_player_action_resolution.get("affordance_status"))
    if affordance_status != "allowed":
        return None
    canonical_risk = _coerce_string(free_player_action_resolution.get("canonical_risk"))
    if canonical_risk == "high":
        return None

    source = _resolver_source(
        affordance_resolution=affordance_resolution,
        free_player_action_resolution=free_player_action_resolution,
    )
    if source not in HOLD_EFFECT_SOURCES:
        # Defensive: closed-enum invariant.
        source = SOURCE_PLAYER_FREEDOM_POLICY_DEFAULT
    until = _coerce_string(until_condition) or UNTIL_CONDITION_CANONICAL_STEP_PROGRESSION_AUTHORIZED
    if until not in HOLD_EFFECT_UNTIL_CONDITIONS:
        until = UNTIL_CONDITION_CANONICAL_STEP_PROGRESSION_AUTHORIZED
    reason = _reason_from_resolution(free_player_action_resolution)
    step_id = _coerce_string(current_canonical_step_id)

    return {
        "schema_version": SCHEMA_VERSION,
        "effect_kind": EFFECT_KIND_HOLD_CURRENT_STEP,
        "source": source,
        "until_condition": until,
        "reason": reason,
        "current_canonical_step_id": step_id,
        "free_player_action_resolution": dict(free_player_action_resolution),
    }


__all__ = [
    "SCHEMA_VERSION",
    "EFFECT_KIND_HOLD_CURRENT_STEP",
    "EFFECT_KINDS",
    "SOURCE_CONTENT_SEMANTIC_CATALOG",
    "SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE",
    "SOURCE_PLAYER_FREEDOM_POLICY_DEFAULT",
    "HOLD_EFFECT_SOURCES",
    "UNTIL_CONDITION_CANONICAL_STEP_PROGRESSION_AUTHORIZED",
    "UNTIL_CONDITION_PRESENCE_RESTORED",
    "UNTIL_CONDITION_TURN_COMMIT_LIFE_CYCLE_END",
    "HOLD_EFFECT_UNTIL_CONDITIONS",
    "REQUIRED_CONTRACT_KEYS",
    "build_canonical_path_hold_effect",
]
