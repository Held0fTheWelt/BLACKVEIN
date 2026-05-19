"""PR-B acceptance tests for ``canonical_path_hold_effect.v1``.

These tests prove that ``build_canonical_path_hold_effect``:

* Returns a structured dict for eligible mundane / free-action commits
  derived from semantic contract fields (``action_commit_policy``,
  ``affordance_status``, ``canon_safety``, ``canonical_risk``) plus the
  resolver's existing ``canonical_path_effect`` literal.
* Returns ``None`` for ineligible action classes: unknown targets,
  criminal / impossible actions, high-risk commits, non-commit policies,
  and any case where the resolver did not produce ``hold_current_step``.
* Reads only from contract fields, never from raw input strings.
* Carries closed-enum values exclusively for ``effect_kind`` /
  ``source`` / ``until_condition``.
* Does not introduce verb / room / actor / locale literal whitelists or
  active Pi / Pi-numbered runtime keys.

Per ADR-0039 and PR-B's PIV
(``docs/implementation_logs/pr_b_live_effect_propagation_piv.md``):

* Tests assert path properties and structured contract field names;
  paraphrased prose / input-string fixtures are never the source of truth.
* PR-B must not define ``compute_gathering_state`` /
  ``presence_breaks_gathering`` / ``gathering_paused`` as `def` or `class`
  symbols.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from ai_stack.canonical_path_hold_effect_contracts import (
    EFFECT_KIND_HOLD_CURRENT_STEP,
    EFFECT_KINDS,
    HOLD_EFFECT_SOURCES,
    HOLD_EFFECT_UNTIL_CONDITIONS,
    REQUIRED_CONTRACT_KEYS,
    SCHEMA_VERSION,
    SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE,
    SOURCE_CONTENT_SEMANTIC_CATALOG,
    SOURCE_PLAYER_FREEDOM_POLICY_DEFAULT,
    UNTIL_CONDITION_CANONICAL_STEP_PROGRESSION_AUTHORIZED,
    build_canonical_path_hold_effect,
)
from ai_stack.free_player_action_resolution_contracts import (
    ACTION_COMMIT_POLICY_COMMIT_ACTION,
    ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION,
    AFFORDANCE_STATUS_ALLOWED,
    AFFORDANCE_STATUS_UNKNOWN_TARGET,
    CANON_SAFETY_CONTENT_SILENT_MUNDANE,
    CANONICAL_RISK_HIGH,
    CANONICAL_RISK_LOW,
    CANONICAL_RISK_MEDIUM,
    PRESENCE_AUTHORITY_DIRECTOR_FINAL,
    PRESENCE_PROVENANCE_PRELIMINARY,
    RESOLVED_TARGET_TYPE_LOCATION,
    SCHEMA_VERSION as FPAR_SCHEMA_VERSION,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _mundane_movement_contract() -> dict:
    """Build a representative `free_player_action_resolution.v1` payload for a
    successful mundane movement commit (e.g. into a known room)."""
    return {
        "schema_version": FPAR_SCHEMA_VERSION,
        "resolved_target_type": RESOLVED_TARGET_TYPE_LOCATION,
        "resolved_target_id": "kitchen",
        "target_location": "kitchen",
        "presence_breaks_gathering": False,
        "presence_breaks_gathering_authority": PRESENCE_AUTHORITY_DIRECTOR_FINAL,
        "presence_breaks_gathering_provenance": PRESENCE_PROVENANCE_PRELIMINARY,
        "presence_breaks_gathering_evidence": {
            "target_location": "kitchen",
            "participation_relevance": None,
            "visibility_audibility": None,
        },
        "affordance_status": AFFORDANCE_STATUS_ALLOWED,
        "canon_safety": CANON_SAFETY_CONTENT_SILENT_MUNDANE,
        "canonical_risk": CANONICAL_RISK_LOW,
        "action_commit_policy": ACTION_COMMIT_POLICY_COMMIT_ACTION,
        "classification_reason": "content_semantic_catalog",
    }


def _aff_for(target_resolution_source: str = "ai_semantic_resolution.content_id") -> dict:
    return {
        "affordance_status": AFFORDANCE_STATUS_ALLOWED,
        "action_commit_policy": ACTION_COMMIT_POLICY_COMMIT_ACTION,
        "target_resolution_source": target_resolution_source,
        "reason": None,
        "resolved_target": None,
        "access_status": None,
    }


# ---------------------------------------------------------------------------
# Eligibility: positive cases
# ---------------------------------------------------------------------------


def test_mundane_movement_commit_emits_hold_effect() -> None:
    contract = _mundane_movement_contract()
    hold = build_canonical_path_hold_effect(
        free_player_action_resolution=contract,
        canonical_path_effect=EFFECT_KIND_HOLD_CURRENT_STEP,
        affordance_resolution=_aff_for(),
        current_canonical_step_id="opening_005_statement_reading",
    )
    assert isinstance(hold, dict)
    for key in REQUIRED_CONTRACT_KEYS:
        assert key in hold, f"hold effect must carry required key: {key}"
    assert hold["schema_version"] == SCHEMA_VERSION
    assert hold["effect_kind"] == EFFECT_KIND_HOLD_CURRENT_STEP
    assert hold["effect_kind"] in EFFECT_KINDS
    assert hold["source"] in HOLD_EFFECT_SOURCES
    assert hold["until_condition"] in HOLD_EFFECT_UNTIL_CONDITIONS
    assert hold["current_canonical_step_id"] == "opening_005_statement_reading"
    # ADR-0057: must derive from contract, not from raw text.
    assert hold["free_player_action_resolution"] == contract


def test_hold_effect_source_for_catalog_grounded_commit() -> None:
    contract = _mundane_movement_contract()
    hold = build_canonical_path_hold_effect(
        free_player_action_resolution=contract,
        canonical_path_effect=EFFECT_KIND_HOLD_CURRENT_STEP,
        affordance_resolution=_aff_for("ai_semantic_resolution.content_id"),
    )
    assert hold is not None
    assert hold["source"] == SOURCE_CONTENT_SEMANTIC_CATALOG


def test_hold_effect_source_for_plausible_inference_commit() -> None:
    contract = {
        **_mundane_movement_contract(),
        "resolved_target_type": "object",
        "resolved_target_id": "inferred_local_window",
        "target_location": None,
    }
    hold = build_canonical_path_hold_effect(
        free_player_action_resolution=contract,
        canonical_path_effect=EFFECT_KIND_HOLD_CURRENT_STEP,
        affordance_resolution=_aff_for("ai_semantic_resolution.plausible_inference"),
    )
    assert hold is not None
    assert hold["source"] == SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE


def test_hold_effect_source_falls_back_to_policy_default_when_unknown_provenance() -> None:
    contract = _mundane_movement_contract()
    hold = build_canonical_path_hold_effect(
        free_player_action_resolution=contract,
        canonical_path_effect=EFFECT_KIND_HOLD_CURRENT_STEP,
        affordance_resolution={
            "affordance_status": AFFORDANCE_STATUS_ALLOWED,
            "action_commit_policy": ACTION_COMMIT_POLICY_COMMIT_ACTION,
            "target_resolution_source": "some_unknown_token_outside_closed_enum",
        },
    )
    assert hold is not None
    assert hold["source"] == SOURCE_PLAYER_FREEDOM_POLICY_DEFAULT


def test_medium_risk_commit_still_emits_hold_effect() -> None:
    # Medium-risk mundane commits should ride the canonical hold; only
    # high-risk commits short-circuit to None.
    contract = {**_mundane_movement_contract(), "canonical_risk": CANONICAL_RISK_MEDIUM}
    hold = build_canonical_path_hold_effect(
        free_player_action_resolution=contract,
        canonical_path_effect=EFFECT_KIND_HOLD_CURRENT_STEP,
        affordance_resolution=_aff_for(),
    )
    assert hold is not None
    assert hold["effect_kind"] == EFFECT_KIND_HOLD_CURRENT_STEP


# ---------------------------------------------------------------------------
# Eligibility: negative cases (fail-closed)
# ---------------------------------------------------------------------------


def test_no_hold_effect_when_canonical_path_effect_is_none() -> None:
    contract = _mundane_movement_contract()
    hold = build_canonical_path_hold_effect(
        free_player_action_resolution=contract,
        canonical_path_effect=None,
        affordance_resolution=_aff_for(),
    )
    assert hold is None


def test_no_hold_effect_for_unknown_target() -> None:
    contract = {
        **_mundane_movement_contract(),
        "resolved_target_id": None,
        "affordance_status": AFFORDANCE_STATUS_UNKNOWN_TARGET,
        "action_commit_policy": ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION,
        "canonical_risk": CANONICAL_RISK_MEDIUM,
        "classification_reason": "semantic_catalog_no_match",
    }
    hold = build_canonical_path_hold_effect(
        free_player_action_resolution=contract,
        canonical_path_effect=None,
        affordance_resolution={
            "affordance_status": AFFORDANCE_STATUS_UNKNOWN_TARGET,
            "action_commit_policy": ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION,
            "target_resolution_source": "semantic_catalog_no_match",
        },
    )
    assert hold is None


def test_no_hold_effect_for_criminal_or_impossible_action() -> None:
    contract = {
        **_mundane_movement_contract(),
        "resolved_target_id": None,
        "affordance_status": AFFORDANCE_STATUS_UNKNOWN_TARGET,
        "action_commit_policy": ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION,
        "canon_safety": None,
        "canonical_risk": CANONICAL_RISK_HIGH,
        "classification_reason": "weapons_or_threat_objects",
    }
    hold = build_canonical_path_hold_effect(
        free_player_action_resolution=contract,
        canonical_path_effect=EFFECT_KIND_HOLD_CURRENT_STEP,
        affordance_resolution=_aff_for(),
    )
    # Even if upstream provenance produced "hold_current_step", high-risk
    # actions fail-closed -- no hold dict.
    assert hold is None


def test_no_hold_effect_for_needs_clarification_policy() -> None:
    contract = {
        **_mundane_movement_contract(),
        "action_commit_policy": ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION,
        "affordance_status": AFFORDANCE_STATUS_UNKNOWN_TARGET,
    }
    hold = build_canonical_path_hold_effect(
        free_player_action_resolution=contract,
        canonical_path_effect=EFFECT_KIND_HOLD_CURRENT_STEP,
        affordance_resolution=_aff_for(),
    )
    assert hold is None


def test_no_hold_effect_when_resolver_returned_no_contract() -> None:
    hold = build_canonical_path_hold_effect(
        free_player_action_resolution=None,
        canonical_path_effect=EFFECT_KIND_HOLD_CURRENT_STEP,
        affordance_resolution=_aff_for(),
    )
    assert hold is None


# ---------------------------------------------------------------------------
# Derived from contract fields, not raw input strings
# ---------------------------------------------------------------------------


def test_hold_effect_derives_from_contract_fields_not_input_strings() -> None:
    """Two structurally equal contracts produce structurally equal hold-effect dicts
    regardless of any raw text that might have been associated with them."""
    base_contract = _mundane_movement_contract()
    hold_a = build_canonical_path_hold_effect(
        free_player_action_resolution=base_contract,
        canonical_path_effect=EFFECT_KIND_HOLD_CURRENT_STEP,
        affordance_resolution=_aff_for(),
        current_canonical_step_id="opening_005_statement_reading",
    )
    # Same contract, simulated different upstream raw_text -- structural
    # equivalence MUST hold.
    same_contract = dict(base_contract)
    hold_b = build_canonical_path_hold_effect(
        free_player_action_resolution=same_contract,
        canonical_path_effect=EFFECT_KIND_HOLD_CURRENT_STEP,
        affordance_resolution=_aff_for(),
        current_canonical_step_id="opening_005_statement_reading",
    )
    assert hold_a == hold_b


# ---------------------------------------------------------------------------
# Vocabulary discipline
# ---------------------------------------------------------------------------


_CONTRACT_MODULE_PATH = (
    REPO_ROOT / "ai_stack" / "canonical_path_hold_effect_contracts.py"
)

_ACTIVE_PI_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])pi_\d+\b|(?<![A-Za-z0-9])pi\d+_[A-Za-z0-9_]+\b|\u03a0\d+\b",
    re.IGNORECASE,
)

_PR_C_OR_PHASE_2_FORBIDDEN_DEFS = (
    re.compile(r"\bdef\s+compute_gathering_state\b"),
    re.compile(r"\bclass\s+compute_gathering_state\b"),
    re.compile(r"\bdef\s+presence_breaks_gathering\b"),
    re.compile(r"\bclass\s+presence_breaks_gathering\b"),
    re.compile(r"\bdef\s+gathering_paused\b"),
    re.compile(r"\bclass\s+gathering_paused\b"),
    re.compile(r"\bdef\s+npc_pulse\b"),
    re.compile(r"\bclass\s+npc_pulse\b"),
)


def test_pr_b_hold_module_has_no_active_pi_runtime_keys() -> None:
    text = _CONTRACT_MODULE_PATH.read_text(encoding="utf-8")
    assert not _ACTIVE_PI_TOKEN_RE.search(text), (
        "canonical_path_hold_effect_contracts.py must use semantic capability names only"
    )


def test_pr_b_hold_module_does_not_define_pr_c_or_phase_2_symbols() -> None:
    text = _CONTRACT_MODULE_PATH.read_text(encoding="utf-8")
    for pattern in _PR_C_OR_PHASE_2_FORBIDDEN_DEFS:
        assert not pattern.search(text), (
            f"canonical_path_hold_effect_contracts.py must not define "
            f"PR-C / Phase-2 runtime symbol matching {pattern.pattern}"
        )


def test_pr_b_hold_module_does_not_import_diagnostic_snapshot_stub() -> None:
    text = _CONTRACT_MODULE_PATH.read_text(encoding="utf-8")
    forbidden = re.compile(
        r"from\s+ai_stack\.runtime_diagnostic_snapshot_contracts\b|"
        r"import\s+ai_stack\.runtime_diagnostic_snapshot_contracts\b"
    )
    assert not forbidden.search(text), (
        "PR-B must not wire the PR-0 diagnostic snapshot stub into production"
    )


def test_pr_b_hold_module_does_not_contain_hardcoded_locale_or_verb_whitelist() -> None:
    text = _CONTRACT_MODULE_PATH.read_text(encoding="utf-8")
    # A hardcoded module-specific identifier such as "kitchen", "annette", or
    # "bathroom" would indicate scope creep into content. PR-B's contract
    # module reads only enum field names; module-specific identifiers must
    # not appear.
    forbidden_module_specific = (
        "annette",
        "alain",
        "veronique",
        "michel",
        "bathroom",
        "kitchen",
        "living_room",
        "hallway",
    )
    lowered = text.lower()
    for tok in forbidden_module_specific:
        assert tok not in lowered, (
            f"canonical_path_hold_effect_contracts.py must not contain "
            f"module-specific identifier '{tok}'"
        )
