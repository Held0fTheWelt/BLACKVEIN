"""MVP2 tests — NPC Coercion & StateDeltaBoundary (Wave 2.3).

Proves:
- NPC actions cannot force/decide/assign human actor speech, action, movement, emotion, or belief
- NPC actions CAN pressure, challenge, address, or interrupt the human actor
- StateDeltaBoundary rejects protected path mutations
- selected_player_role, human_actor_id, actor_lanes are protected
- canonical_scene_order and canonical_characters are protected
- Allowed runtime paths (runtime_flags, admitted_objects, etc.) are accepted
- Commit seam enforces StateDeltaBoundary — protected mutation is rejected at commit time
"""

from __future__ import annotations

import sys
import os

import pytest

# Add repo root so ai_stack is importable (sibling service)
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app.runtime.actor_lane import (
    build_actor_lane_context,
    validate_npc_action_coercion,
)
from app.runtime.models import ActorLaneContext, StateDeltaBoundary, StateDeltaValidationResult
from app.runtime.state_delta import (
    build_default_goc_boundary,
    first_rejection,
    validate_state_delta,
    validate_state_deltas,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_ANNETTE_OWNERSHIP = {
    "human_actor_id": "annette",
    "npc_actor_ids": ["alain", "veronique", "michel"],
    "actor_lanes": {
        "annette": "human",
        "alain": "npc",
        "veronique": "npc",
        "michel": "npc",
    },
    "visitor_present": False,
    "content_hash": "sha256:test",
}


def _ctx() -> ActorLaneContext:
    return build_actor_lane_context(
        _ANNETTE_OWNERSHIP,
        selected_player_role="annette",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
    )


# ---------------------------------------------------------------------------
# Wave 2.3: NPC Coercion Rejection
# ---------------------------------------------------------------------------

def test_npc_action_cannot_force_human_response():
    """NPC forcing human to speak is rejected."""
    ctx = _ctx()
    result = validate_npc_action_coercion(
        {
            "actor_id": "alain",
            "target_actor_id": "annette",
            "action_type": "force_speech",
            "text": "Alain forces Annette to apologize.",
        },
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "npc_action_controls_human_actor"
    assert result.actor_id == "alain"


def test_npc_action_cannot_force_human_movement():
    ctx = _ctx()
    result = validate_npc_action_coercion(
        {
            "actor_id": "veronique",
            "target_actor_id": "annette",
            "action_type": "force_movement",
            "text": "Véronique makes Annette leave the room.",
        },
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "npc_action_controls_human_actor"


def test_npc_action_cannot_assign_human_emotion():
    ctx = _ctx()
    result = validate_npc_action_coercion(
        {
            "actor_id": "michel",
            "target_actor_id": "annette",
            "action_type": "assign_emotion",
            "text": "Michel decides that Annette feels ashamed.",
        },
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "npc_action_controls_human_actor"


def test_npc_action_cannot_force_human_decision_via_coercion_type():
    ctx = _ctx()
    result = validate_npc_action_coercion(
        {
            "actor_id": "alain",
            "target_actor_id": "annette",
            "coercion_type": "force_decision",
            "text": "Alain makes Annette decide.",
        },
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "npc_action_controls_human_actor"


def test_npc_action_coercive_text_with_confirmed_target_rejected():
    """Text-based coercion detection fires when structural target is confirmed."""
    ctx = _ctx()
    result = validate_npc_action_coercion(
        {
            "actor_id": "alain",
            "target_actor_id": "annette",
            "text": "Alain forces Annette to confess.",
        },
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "npc_action_controls_human_actor"


def test_npc_action_can_pressure_human_without_control():
    """NPC pressure is allowed — it influences but does not determine human outcome."""
    ctx = _ctx()
    result = validate_npc_action_coercion(
        {
            "actor_id": "alain",
            "target_actor_id": "annette",
            "action_type": "social_pressure",
            "text": "Alain pressures Annette to answer.",
        },
        ctx,
    )
    assert result.status == "approved"


def test_npc_action_can_challenge_human():
    ctx = _ctx()
    result = validate_npc_action_coercion(
        {
            "actor_id": "veronique",
            "target_actor_id": "annette",
            "text": "Véronique challenges Annette's framing.",
        },
        ctx,
    )
    assert result.status == "approved"


def test_npc_action_can_interrupt():
    ctx = _ctx()
    result = validate_npc_action_coercion(
        {
            "actor_id": "michel",
            "target_actor_id": "annette",
            "text": "Michel interrupts Annette.",
        },
        ctx,
    )
    assert result.status == "approved"


def test_npc_action_targeting_other_npc_not_coercion():
    """Coercion validation only applies when target is the human actor."""
    ctx = _ctx()
    result = validate_npc_action_coercion(
        {
            "actor_id": "alain",
            "target_actor_id": "veronique",
            "action_type": "force_speech",
            "text": "Alain forces Veronique to speak.",
        },
        ctx,
    )
    # NPC-to-NPC control is not a human-actor protection violation
    assert result.status == "approved"


def test_npc_action_without_target_is_approved():
    ctx = _ctx()
    result = validate_npc_action_coercion(
        {
            "actor_id": "michel",
            "text": "Michel looks around the room.",
        },
        ctx,
    )
    assert result.status == "approved"


def test_npc_coercion_rejected_error_code_is_correct():
    ctx = _ctx()
    result = validate_npc_action_coercion(
        {
            "actor_id": "alain",
            "target_actor_id": "annette",
            "action_type": "control_outcome",
        },
        ctx,
    )
    assert result.error_code == "npc_action_controls_human_actor"
    assert result.block_kind == "actor_action"
    assert result.human_actor_id == "annette"


# ---------------------------------------------------------------------------
# Wave 2.3: StateDeltaBoundary — protected path validation
# ---------------------------------------------------------------------------

def test_ai_delta_cannot_change_selected_player_role():
    result = validate_state_delta({"path": "selected_player_role", "operation": "replace", "value": "alain"})
    assert result.status == "rejected"
    assert result.error_code == "protected_state_mutation_rejected"


def test_ai_delta_cannot_change_human_actor_id():
    result = validate_state_delta({"path": "human_actor_id", "operation": "replace", "value": "alain"})
    assert result.status == "rejected"
    assert result.error_code == "protected_state_mutation_rejected"


def test_ai_delta_cannot_mutate_actor_lanes():
    result = validate_state_delta({"path": "actor_lanes", "operation": "replace", "value": {}})
    assert result.status == "rejected"
    assert result.error_code == "protected_state_mutation_rejected"


def test_ai_delta_cannot_mutate_actor_lanes_subpath():
    result = validate_state_delta({"path": "actor_lanes.annette", "operation": "set", "value": "npc"})
    assert result.status == "rejected"
    assert result.error_code == "protected_state_mutation_rejected"


def test_protected_state_mutation_canonical_scene_order():
    result = validate_state_delta({"path": "canonical_scene_order", "operation": "replace", "value": ["new_scene"]})
    assert result.status == "rejected"
    assert result.error_code == "protected_state_mutation_rejected"


def test_protected_state_mutation_canonical_characters():
    result = validate_state_delta({"path": "canonical_characters", "operation": "append", "value": {}})
    assert result.status == "rejected"
    assert result.error_code == "protected_state_mutation_rejected"


def test_protected_state_mutation_content_module_id():
    result = validate_state_delta({"path": "content_module_id", "operation": "replace", "value": "other_module"})
    assert result.status == "rejected"
    assert result.error_code == "protected_state_mutation_rejected"


def test_allowed_runtime_path_approved():
    for path in ["runtime_flags", "turn_memory", "scene_pressure", "admitted_objects", "relationship_runtime_pressure"]:
        result = validate_state_delta({"path": path, "operation": "set", "value": "x"})
        assert result.status == "approved", f"Allowed path {path!r} should be approved"


def test_allowed_runtime_subpath_approved():
    result = validate_state_delta({"path": "admitted_objects.water_glass", "operation": "set", "value": True})
    assert result.status == "approved"


def test_unknown_path_rejected_when_reject_unknown_true():
    boundary = StateDeltaBoundary(reject_unknown_paths=True)
    result = validate_state_delta({"path": "some_invented_field", "operation": "set", "value": "x"}, boundary)
    assert result.status == "rejected"
    assert result.error_code == "state_delta_boundary_violation"


def test_unknown_path_allowed_when_reject_unknown_false():
    boundary = StateDeltaBoundary(reject_unknown_paths=False)
    result = validate_state_delta({"path": "some_invented_field", "operation": "set", "value": "x"}, boundary)
    assert result.status == "approved"


def test_empty_path_rejected():
    result = validate_state_delta({"path": "", "operation": "set"})
    assert result.status == "rejected"


def test_validate_state_deltas_batch():
    deltas = [
        {"path": "runtime_flags", "operation": "set", "value": "x"},
        {"path": "canonical_scene_order", "operation": "replace", "value": []},
        {"path": "admitted_objects", "operation": "append", "value": "cup"},
    ]
    results = validate_state_deltas(deltas)
    assert results[0].status == "approved"
    assert results[1].status == "rejected"
    assert results[2].status == "approved"


def test_first_rejection_finds_blocked_delta():
    deltas = [
        {"path": "runtime_flags", "operation": "set"},
        {"path": "human_actor_id", "operation": "replace", "value": "alain"},
    ]
    results = validate_state_deltas(deltas)
    rejection = first_rejection(results)
    assert rejection is not None
    assert rejection.error_code == "protected_state_mutation_rejected"
    assert rejection.path == "human_actor_id"


def test_first_rejection_returns_none_when_all_approved():
    deltas = [
        {"path": "runtime_flags", "operation": "set"},
        {"path": "turn_memory", "operation": "append"},
    ]
    results = validate_state_deltas(deltas)
    assert first_rejection(results) is None


def test_default_goc_boundary_includes_all_protected():
    boundary = build_default_goc_boundary()
    assert "selected_player_role" in boundary.protected_paths
    assert "human_actor_id" in boundary.protected_paths
    assert "actor_lanes" in boundary.protected_paths
    assert "canonical_scene_order" in boundary.protected_paths
    assert "canonical_characters" in boundary.protected_paths
    assert "content_module_id" in boundary.protected_paths


# ---------------------------------------------------------------------------
# Wave 2.3: Commit seam enforces StateDeltaBoundary
# ---------------------------------------------------------------------------

def test_commit_seam_rejects_protected_state_mutation():
    """Protected path mutation is rejected at commit seam before any write."""
    from ai_stack.story_runtime.turn.god_of_carnage_turn_seams import run_commit_seam

    approved_validation = {"status": "approved"}
    protected_delta = [{"path": "selected_player_role", "operation": "replace", "value": "alain"}]

    result = run_commit_seam(
        module_id="god_of_carnage",
        validation_outcome=approved_validation,
        proposed_state_effects=[{"effect_type": "test", "description": "test"}],
        candidate_deltas=protected_delta,
    )
    assert result["commit_applied"] is False
    assert "state_delta_rejection" in result
    assert result["state_delta_rejection"]["error_code"] == "protected_state_mutation_rejected"


def test_commit_seam_rejects_human_actor_id_mutation():
    from ai_stack.story_runtime.turn.god_of_carnage_turn_seams import run_commit_seam

    result = run_commit_seam(
        module_id="god_of_carnage",
        validation_outcome={"status": "approved"},
        proposed_state_effects=[{"effect_type": "test", "description": "ok"}],
        candidate_deltas=[{"path": "human_actor_id", "operation": "replace", "value": "alain"}],
    )
    assert result["commit_applied"] is False
    assert result["state_delta_rejection"]["error_code"] == "protected_state_mutation_rejected"


def test_commit_seam_rejects_actor_lanes_mutation():
    from ai_stack.story_runtime.turn.god_of_carnage_turn_seams import run_commit_seam

    result = run_commit_seam(
        module_id="god_of_carnage",
        validation_outcome={"status": "approved"},
        proposed_state_effects=[{"effect_type": "test", "description": "ok"}],
        candidate_deltas=[{"path": "actor_lanes.annette", "operation": "set", "value": "npc"}],
    )
    assert result["commit_applied"] is False


def test_commit_seam_allows_safe_runtime_delta():
    from ai_stack.story_runtime.turn.god_of_carnage_turn_seams import run_commit_seam

    result = run_commit_seam(
        module_id="god_of_carnage",
        validation_outcome={"status": "approved"},
        proposed_state_effects=[{"effect_type": "test", "description": "ok"}],
        candidate_deltas=[{"path": "runtime_flags", "operation": "set", "value": "flag_x"}],
    )
    assert result["commit_applied"] is True


def test_commit_seam_no_deltas_works_as_before():
    """Existing commit seam behavior unchanged when no deltas supplied."""
    from ai_stack.story_runtime.turn.god_of_carnage_turn_seams import run_commit_seam

    result = run_commit_seam(
        module_id="god_of_carnage",
        validation_outcome={"status": "approved"},
        proposed_state_effects=[{"effect_type": "narrative_proposal", "description": "ok"}],
    )
    assert result["commit_applied"] is True
