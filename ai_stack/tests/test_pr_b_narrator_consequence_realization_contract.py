"""PR-B acceptance tests for ``narrator_consequence_realization.v1``.

These tests prove that ``build_narrator_consequence_realization``:

* Returns a closed-enum dict on every call (no ``None`` fallback).
* For a ``requires_model_realization=True`` plan combined with a visible
  bundle that contains a ``narrator`` or ``environment_interaction`` block:
  emits ``visible_block_emitted=True``, ``realized_block_id`` non-null,
  ``non_realization_reason=None``.
* For a ``requires_model_realization=True`` plan with **no** such block:
  emits ``visible_block_emitted=False``, ``realized_block_id=None``, and an
  explicit ``non_realization_reason``.
* Carries the safety triple ``no_new_people`` / ``no_new_rooms`` /
  ``no_plot_facts`` as ``True``.
* Block must not require actor-line / actor-action speech (only
  ``narrator`` / ``environment_interaction``).
* Does not introduce hardcoded text snippets, verb / room whitelists, or
  active Pi / Pi-numbered runtime keys.

Per ADR-0039 and PR-B's PIV.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from ai_stack.narrator_consequence_realization_contracts import (
    BLOCK_TYPE_ENVIRONMENT_INTERACTION,
    BLOCK_TYPE_NARRATOR,
    NON_REALIZATION_REASON_BUNDLE_MISSING,
    NON_REALIZATION_REASON_NO_NARRATOR_BLOCK_IN_BUNDLE,
    NON_REALIZATION_REASON_PLAN_MISSING,
    NON_REALIZATION_REASON_REALIZATION_NOT_REQUIRED,
    NON_REALIZATION_REASON_VALIDATION_GATED,
    NON_REALIZATION_REASONS,
    REQUIRED_CONTRACT_KEYS,
    REQUIRED_SAFETY_KEYS,
    REALIZATION_BLOCK_TYPES,
    REALIZATION_SOURCES,
    SCHEMA_VERSION,
    SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE,
    SOURCE_NO_CONSEQUENCE_APPLICABLE,
    SOURCE_SCENE_AFFORDANCE_DETAIL,
    SOURCE_TEMPLATE_FALLBACK,
    build_narrator_consequence_realization,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Plan + bundle fixtures (no exact narrative prose)
# ---------------------------------------------------------------------------


def _plan_authored_mundane(transition_type: str = "movement") -> dict:
    return {
        "consequence_text": "[authored detail]",
        "consequence_type": "area_transition",
        "source": SOURCE_SCENE_AFFORDANCE_DETAIL,
        "requires_model_realization": False,
        "inferred_target": None,
        "local_context_updated": True,
        "affordances_available": ["look_at"],
        "transition_type": transition_type,
    }


def _plan_plausible_inference() -> dict:
    return {
        "consequence_text": None,
        "consequence_type": "plausible_object_interaction",
        "source": SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE,
        "requires_model_realization": True,
        "inferred_target": {
            "target_id": "inferred_local_container",
            "target_alias": "container",
            "semantic_inference": {
                "mode": "canon_safe_plausible_affordance",
                "canon_safety": "content_silent_mundane",
                "canonical_risk": "low",
            },
        },
        "local_context_updated": False,
        "affordances_available": [],
        "transition_type": "object_interaction",
    }


def _narrator_block(block_id: str = "block-narr-001") -> dict:
    return {
        "block_id": block_id,
        "block_type": BLOCK_TYPE_NARRATOR,
        "text": "[narrator text projected from authored consequence detail]",
    }


def _environment_block(block_id: str = "block-env-001") -> dict:
    return {
        "block_id": block_id,
        "block_type": BLOCK_TYPE_ENVIRONMENT_INTERACTION,
        "text": "[environment interaction projection]",
    }


def _actor_line_block(actor_id: str = "alain_reille") -> dict:
    return {
        "block_id": "block-actor-001",
        "block_type": "actor_line",
        "speaker_id": actor_id,
        "text": "[actor line text]",
    }


# ---------------------------------------------------------------------------
# Required-shape invariants
# ---------------------------------------------------------------------------


def test_realization_always_emits_required_keys() -> None:
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=_plan_authored_mundane(),
        visible_scene_blocks=[_narrator_block()],
    )
    for key in REQUIRED_CONTRACT_KEYS:
        assert key in realization, f"realization must carry required key: {key}"
    assert realization["schema_version"] == SCHEMA_VERSION


def test_realization_safety_triple_is_true_for_mundane_realization() -> None:
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=_plan_authored_mundane(),
        visible_scene_blocks=[_narrator_block()],
    )
    safety = realization["safety"]
    for key in REQUIRED_SAFETY_KEYS:
        assert safety.get(key) is True, (
            f"safety triple must be True for mundane realization: {key}"
        )


def test_realization_source_is_closed_enum() -> None:
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=_plan_plausible_inference(),
        visible_scene_blocks=[_narrator_block()],
    )
    assert realization["source"] in REALIZATION_SOURCES


def test_realization_block_type_is_closed_enum_when_emitted() -> None:
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=_plan_authored_mundane(),
        visible_scene_blocks=[_narrator_block()],
    )
    assert realization["block_type"] in REALIZATION_BLOCK_TYPES


# ---------------------------------------------------------------------------
# requires_model_realization=True success / non-realization paths
# ---------------------------------------------------------------------------


def test_realization_succeeds_when_requires_model_realization_and_narrator_block_present() -> None:
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=_plan_plausible_inference(),
        visible_scene_blocks=[_narrator_block("block-realized-1")],
    )
    assert realization["requires_model_realization"] is True
    assert realization["visible_block_emitted"] is True
    assert realization["realized_block_id"] == "block-realized-1"
    assert realization["non_realization_reason"] is None
    assert realization["block_type"] == BLOCK_TYPE_NARRATOR


def test_realization_succeeds_with_environment_interaction_block_too() -> None:
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=_plan_plausible_inference(),
        visible_scene_blocks=[_environment_block("block-env-1")],
    )
    assert realization["visible_block_emitted"] is True
    assert realization["realized_block_id"] == "block-env-1"
    assert realization["block_type"] == BLOCK_TYPE_ENVIRONMENT_INTERACTION


def test_realization_emits_explicit_reason_when_no_narrator_block_in_bundle() -> None:
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=_plan_plausible_inference(),
        visible_scene_blocks=[_actor_line_block()],
    )
    assert realization["requires_model_realization"] is True
    assert realization["visible_block_emitted"] is False
    assert realization["realized_block_id"] is None
    assert (
        realization["non_realization_reason"]
        == NON_REALIZATION_REASON_NO_NARRATOR_BLOCK_IN_BUNDLE
    )
    assert realization["non_realization_reason"] in NON_REALIZATION_REASONS


def test_realization_emits_explicit_reason_when_bundle_missing() -> None:
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=_plan_plausible_inference(),
        visible_scene_blocks=None,
    )
    assert realization["visible_block_emitted"] is False
    assert (
        realization["non_realization_reason"] == NON_REALIZATION_REASON_BUNDLE_MISSING
    )


def test_realization_emits_explicit_reason_when_plan_missing() -> None:
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=None,
        visible_scene_blocks=[],
    )
    assert realization["requires_model_realization"] is False
    assert realization["visible_block_emitted"] is False
    assert (
        realization["non_realization_reason"] == NON_REALIZATION_REASON_PLAN_MISSING
    )


def test_realization_emits_validation_gated_reason_when_lane_rejected() -> None:
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=_plan_plausible_inference(),
        visible_scene_blocks=[],
        validation_gated=True,
    )
    assert realization["visible_block_emitted"] is False
    assert (
        realization["non_realization_reason"] == NON_REALIZATION_REASON_VALIDATION_GATED
    )


def test_realization_when_not_required_uses_realization_not_required_reason() -> None:
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=_plan_authored_mundane(),
        visible_scene_blocks=[_actor_line_block()],
    )
    assert realization["requires_model_realization"] is False
    assert realization["visible_block_emitted"] is False
    assert (
        realization["non_realization_reason"] == NON_REALIZATION_REASON_REALIZATION_NOT_REQUIRED
    )


# ---------------------------------------------------------------------------
# Actor-lane discipline: actor blocks alone do not count as realization
# ---------------------------------------------------------------------------


def test_actor_blocks_do_not_count_as_narrator_realization() -> None:
    # Bundle contains an actor_line but no narrator block -- realization
    # contract must not classify the actor_line as a narrator block.
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=_plan_plausible_inference(),
        visible_scene_blocks=[_actor_line_block(), {"block_type": "actor_action", "text": "x"}],
    )
    assert realization["visible_block_emitted"] is False
    assert realization["block_type"] is None


def test_narrator_realization_does_not_require_actor_speech() -> None:
    # When a narrator block is present alongside actor lines, realization
    # still classifies as narrator -- the narrator block is the realization
    # surface, the actor line is a separate lane.
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=_plan_plausible_inference(),
        visible_scene_blocks=[_actor_line_block(), _narrator_block()],
    )
    assert realization["visible_block_emitted"] is True
    assert realization["block_type"] == BLOCK_TYPE_NARRATOR


# ---------------------------------------------------------------------------
# Vocabulary discipline
# ---------------------------------------------------------------------------


_REALIZATION_MODULE_PATH = (
    REPO_ROOT / "ai_stack" / "narrator_consequence_realization_contracts.py"
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
)


def test_pr_b_realization_module_has_no_active_pi_runtime_keys() -> None:
    text = _REALIZATION_MODULE_PATH.read_text(encoding="utf-8")
    assert not _ACTIVE_PI_TOKEN_RE.search(text), (
        "narrator_consequence_realization_contracts.py must use semantic capability names only"
    )


def test_pr_b_realization_module_does_not_define_pr_c_or_phase_2_symbols() -> None:
    text = _REALIZATION_MODULE_PATH.read_text(encoding="utf-8")
    for pattern in _PR_C_OR_PHASE_2_FORBIDDEN_DEFS:
        assert not pattern.search(text), (
            f"narrator_consequence_realization_contracts.py must not define "
            f"PR-C / Phase-2 runtime symbol matching {pattern.pattern}"
        )


def test_pr_b_realization_module_does_not_import_diagnostic_snapshot_stub() -> None:
    text = _REALIZATION_MODULE_PATH.read_text(encoding="utf-8")
    forbidden = re.compile(
        r"from\s+ai_stack\.runtime_diagnostic_snapshot_contracts\b|"
        r"import\s+ai_stack\.runtime_diagnostic_snapshot_contracts\b"
    )
    assert not forbidden.search(text), (
        "PR-B must not wire the PR-0 diagnostic snapshot stub into production"
    )


def test_pr_b_realization_module_does_not_contain_hardcoded_locale_or_verb_whitelist() -> None:
    text = _REALIZATION_MODULE_PATH.read_text(encoding="utf-8")
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
            f"narrator_consequence_realization_contracts.py must not contain "
            f"module-specific identifier '{tok}'"
        )
