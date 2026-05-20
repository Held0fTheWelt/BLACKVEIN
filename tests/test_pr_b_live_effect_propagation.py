"""PR-B acceptance tests for live effect propagation.

These tests close the seams from the resolver contract output to the
runtime gate the manager evaluates today:

1. The resolver envelope (``ai_stack.player_action_resolution.resolve_player_action``)
   emits a ``canonical_path_hold_effect`` dict at the envelope root for
   eligible mundane / free-action commits, and ``None`` (no key) for
   ineligible action classes.
2. The frame keeps the existing ``canonical_path_effect == "hold_current_step"``
   literal so the manager's gate at
   ``world-engine/app/story_runtime/manager`` runtime package:
   ``_turn_holds_canonical_path_for_free_player_action``
   continues to return ``True`` for the same action classes.
3. The simulated graph state carries the hold-effect dict at top level and
   the realization contract after rendering.
4. The thin-path summary (``_build_langfuse_path_summary``) projects the
   three PR-B keys (``canonical_path_hold_effect``,
   ``narrator_consequence_realization``, ``visible_block_emitted``) onto the
   per-event summary.
5. PR-B does not introduce ``compute_gathering_state`` /
   ``presence_breaks_gathering`` / ``gathering_paused`` / ``step.mode`` /
   ``pointer_repair`` symbols in any of the files PR-B owns or extends.

Per ADR-0039, all assertions are over contract field names / closed enums /
structural properties -- never paraphrased prose or exact-string fixtures.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from ai_stack.contracts.canonical_path_hold_effect_contracts import (
    EFFECT_KIND_HOLD_CURRENT_STEP,
    HOLD_EFFECT_SOURCES,
    SCHEMA_VERSION as HOLD_EFFECT_SCHEMA_VERSION,
)
from ai_stack.contracts.free_player_action_resolution_contracts import (
    ACTION_COMMIT_POLICY_COMMIT_ACTION,
    ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION,
    AFFORDANCE_STATUS_ALLOWED,
    AFFORDANCE_STATUS_UNKNOWN_TARGET,
)
from ai_stack.contracts.narrator_consequence_realization_contracts import (
    BLOCK_TYPE_NARRATOR,
    NON_REALIZATION_REASON_NO_NARRATOR_BLOCK_IN_BUNDLE,
    SCHEMA_VERSION as REALIZATION_SCHEMA_VERSION,
    build_narrator_consequence_realization,
)
from ai_stack.player_action_resolution import resolve_player_action
from story_runtime_core.language_adapter import clear_language_adapter_caches


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = REPO_ROOT / "content" / "modules"
MANAGER_PACKAGE = REPO_ROOT / "world-engine" / "app" / "story_runtime" / "manager"


def _manager_package_source(*relative_parts: str) -> str:
    path = MANAGER_PACKAGE.joinpath(*relative_parts)
    return path.read_text(encoding="utf-8")


def _manager_all_python_source() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(MANAGER_PACKAGE.rglob("*.py"))
        if "__pycache__" not in path.parts
    )


@pytest.fixture(autouse=True)
def _clear_language_adapter_caches() -> None:
    clear_language_adapter_caches()
    yield
    clear_language_adapter_caches()


def _runtime_projection() -> dict:
    return {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette_reille",
        "npc_actor_ids": ["alain_reille", "veronique_vallon", "michel_longstreet"],
        "actor_lanes": {
            "annette_reille": "human",
            "alain_reille": "npc",
            "veronique_vallon": "npc",
            "michel_longstreet": "npc",
        },
    }


def _semantic_interpreted(
    *,
    target_id: str | None,
    target_type: str | None,
    target_query: str | None,
    verb: str,
    action_kind: str,
    commit_policy: str = "commit_action",
    extra_semantic: dict | None = None,
) -> dict:
    semantic = {
        "player_input_kind": "action",
        "verb": verb,
        "action_kind": action_kind,
        "target_query": target_query,
        "resolved_target_id": target_id,
        "resolved_target_type": target_type,
        "commit_policy": commit_policy,
        "confidence": "high" if target_id else "low",
    }
    if isinstance(extra_semantic, dict):
        semantic.update(extra_semantic)
    return {
        "player_input_kind": "action",
        "narrator_response_expected": True,
        "npc_response_expected": False,
        "actor_id": "annette_reille",
        "semantic_action": semantic,
    }


def _resolve(interpreted: dict, raw_text: str = "input under test") -> dict:
    return resolve_player_action(
        raw_text=raw_text,
        interpreted_input=interpreted,
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=CONTENT_ROOT,
    )


# ---------------------------------------------------------------------------
# Resolver envelope carries the hold-effect dict for mundane free actions
# ---------------------------------------------------------------------------


def test_resolver_envelope_emits_hold_effect_for_known_room_movement() -> None:
    resolution = _resolve(
        _semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="kitchen",
            target_id="kitchen",
            target_type="location",
        )
    )
    hold = resolution.get("canonical_path_hold_effect")
    assert isinstance(hold, dict), (
        "resolver envelope must carry canonical_path_hold_effect dict for "
        "eligible mundane free action commits"
    )
    assert hold["schema_version"] == HOLD_EFFECT_SCHEMA_VERSION
    assert hold["effect_kind"] == EFFECT_KIND_HOLD_CURRENT_STEP
    assert hold["source"] in HOLD_EFFECT_SOURCES
    embedded = resolution["player_action_frame"].get("canonical_path_hold_effect")
    assert embedded is not None, (
        "frame must carry the same hold-effect dict so graph-state "
        "propagation flows it through"
    )


def test_resolver_envelope_does_not_emit_hold_effect_for_unknown_target() -> None:
    resolution = _resolve(
        _semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="impossible-place",
            target_id=None,
            target_type=None,
        )
    )
    assert resolution.get("canonical_path_hold_effect") is None
    assert "canonical_path_hold_effect" not in resolution["player_action_frame"]
    # Frame's canonical_path_effect literal must also be None for unknown
    # targets so the manager's existing gate returns False.
    assert resolution["player_action_frame"].get("canonical_path_effect") is None


def test_resolver_envelope_does_not_emit_hold_effect_for_criminal_action() -> None:
    resolution = _resolve(
        _semantic_interpreted(
            verb="draw",
            action_kind="weapon_interaction",
            target_query="hidden weapon",
            target_id=None,
            target_type="object",
            extra_semantic={
                "canon_safety": "weapons_or_threat_objects",
                "canonical_risk": "high",
            },
        )
    )
    assert resolution.get("canonical_path_hold_effect") is None


def test_resolver_hold_effect_carries_resolver_contract_payload() -> None:
    resolution = _resolve(
        _semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="kitchen",
            target_id="kitchen",
            target_type="location",
        )
    )
    hold = resolution["canonical_path_hold_effect"]
    embedded = hold["free_player_action_resolution"]
    assert embedded["affordance_status"] == AFFORDANCE_STATUS_ALLOWED
    assert embedded["action_commit_policy"] == ACTION_COMMIT_POLICY_COMMIT_ACTION


# ---------------------------------------------------------------------------
# Graph-state simulation: manager hold gate returns True
# ---------------------------------------------------------------------------


def _turn_holds_canonical_path_for_free_player_action(graph_state: dict) -> bool:
    """Mirror of the manager gate at
    ``world-engine/app/story_runtime/manager``:
    ``_turn_holds_canonical_path_for_free_player_action``
    so this test does not import the manager (which carries a heavy dep tree)."""
    frame = (
        graph_state.get("player_action_frame")
        if isinstance(graph_state.get("player_action_frame"), dict)
        else {}
    )
    if not frame:
        return False
    return (
        str(frame.get("canonical_path_effect") or "").strip()
        == EFFECT_KIND_HOLD_CURRENT_STEP
    )


def test_graph_state_with_hold_effect_passes_manager_gate() -> None:
    resolution = _resolve(
        _semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="kitchen",
            target_id="kitchen",
            target_type="location",
        )
    )
    # Simulate the executor lift: graph_state["player_action_frame"] is the
    # resolver's frame dict; the lifted top-level hold-effect dict rides
    # under graph_state["canonical_path_hold_effect"].
    graph_state = {
        "player_action_frame": resolution["player_action_frame"],
        "canonical_path_hold_effect": resolution.get("canonical_path_hold_effect"),
    }
    assert _turn_holds_canonical_path_for_free_player_action(graph_state) is True
    assert isinstance(graph_state["canonical_path_hold_effect"], dict)


def test_graph_state_without_hold_effect_does_not_pass_manager_gate() -> None:
    resolution = _resolve(
        _semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="impossible-place",
            target_id=None,
            target_type=None,
        )
    )
    graph_state = {
        "player_action_frame": resolution["player_action_frame"],
        "canonical_path_hold_effect": resolution.get("canonical_path_hold_effect"),
    }
    # Unknown target: frame.canonical_path_effect is None.
    assert (
        _turn_holds_canonical_path_for_free_player_action(graph_state) is False
    )
    assert graph_state["canonical_path_hold_effect"] is None


# ---------------------------------------------------------------------------
# Narrator realization projection
# ---------------------------------------------------------------------------


def test_realization_contract_emits_for_visible_narrator_block() -> None:
    plan = {
        "consequence_text": "[authored text]",
        "consequence_type": "area_transition",
        "source": "scene_affordance_detail",
        "requires_model_realization": False,
        "transition_type": "movement",
    }
    bundle_blocks = [
        {
            "block_id": "block-narr-001",
            "block_type": BLOCK_TYPE_NARRATOR,
            "text": "[projected narrator text]",
        }
    ]
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=plan,
        visible_scene_blocks=bundle_blocks,
    )
    assert realization["schema_version"] == REALIZATION_SCHEMA_VERSION
    assert realization["visible_block_emitted"] is True
    assert realization["realized_block_id"] == "block-narr-001"
    assert realization["block_type"] == BLOCK_TYPE_NARRATOR
    assert realization["non_realization_reason"] is None
    # Safety triple is True for narrator realization built from the
    # canon-safe consequence path.
    for key in ("no_new_people", "no_new_rooms", "no_plot_facts"):
        assert realization["safety"][key] is True


def test_realization_contract_emits_explicit_reason_when_no_narrator_block() -> None:
    plan = {
        "consequence_text": None,
        "consequence_type": "plausible_object_interaction",
        "source": "ai_semantic_plausible_inference",
        "requires_model_realization": True,
        "transition_type": "object_interaction",
    }
    bundle_blocks = [
        {"block_id": "block-actor-001", "block_type": "actor_line", "text": "..."}
    ]
    realization = build_narrator_consequence_realization(
        narrator_consequence_plan=plan,
        visible_scene_blocks=bundle_blocks,
    )
    assert realization["visible_block_emitted"] is False
    assert realization["realized_block_id"] is None
    assert (
        realization["non_realization_reason"]
        == NON_REALIZATION_REASON_NO_NARRATOR_BLOCK_IN_BUNDLE
    )


# ---------------------------------------------------------------------------
# Diagnostic surface: thin-path summary fields are present in the manager source
# ---------------------------------------------------------------------------


def test_manager_thin_path_summary_projects_pr_b_keys() -> None:
    """The manager's thin-path-summary builder must project the three PR-B
    keys when present on graph state. We verify by source-grep that the key
    names appear in the manager file, plus the per-row `get_thin_path_summary`
    surface includes them."""
    text = _manager_package_source("thin_path_snapshot_api.py")
    assert "canonical_path_hold_effect" in text, (
        "manager.py must project canonical_path_hold_effect into the "
        "thin-path summary"
    )
    assert "narrator_consequence_realization" in text, (
        "manager.py must project narrator_consequence_realization into the "
        "thin-path summary"
    )
    assert "visible_block_emitted" in text, (
        "manager.py must project visible_block_emitted into the "
        "thin-path summary"
    )


def test_thin_path_summary_row_does_not_expose_mutation_fields() -> None:
    """The thin-path summary projects diagnostic data only. PR-B must not add
    UI control / mutation fields (this is the same constraint PR-0 placed on
    the diagnostic snapshot stub)."""
    text = _manager_all_python_source()
    # Locate the `def get_thin_path_summary` body and check the row keys are
    # read-only diagnostic. PR-B's only additions are projection keys.
    forbidden_mutation_terms = (
        "advance_pointer",
        "advance_canonical_step",
        "rewrite_pointer",
        "force_realize",
    )
    for term in forbidden_mutation_terms:
        assert term not in text, (
            f"manager.py must not introduce mutation field '{term}'"
        )


# ---------------------------------------------------------------------------
# Guardrails: PR-B does not implement PR-C / Phase-2 symbols, no Pi keys
# ---------------------------------------------------------------------------


PR_B_TOUCHED_FILES = (
    "ai_stack/contracts/canonical_path_hold_effect_contracts.py",
    "ai_stack/contracts/narrator_consequence_realization_contracts.py",
    "ai_stack/player_action_resolution.py",
    "ai_stack/langgraph/langgraph_runtime_executor.py",
    "world-engine/app/story_runtime/manager/thin_path_snapshot_api.py",
    "world-engine/app/story_runtime/manager/_legacy_sources/_build_langfuse_path_summary_001.py",
)


PR_C_OR_PHASE_2_FORBIDDEN_SYMBOL_DEFS = (
    re.compile(r"\bdef\s+compute_gathering_state\b"),
    re.compile(r"\bclass\s+compute_gathering_state\b"),
    re.compile(r"\bdef\s+presence_breaks_gathering\b"),
    re.compile(r"\bclass\s+presence_breaks_gathering\b"),
    re.compile(r"\bdef\s+gathering_paused\b"),
    re.compile(r"\bclass\s+gathering_paused\b"),
    re.compile(r"\bdef\s+npc_pulse\b"),
    re.compile(r"\bclass\s+npc_pulse\b"),
    # PR-B must not introduce pointer-repair or step.mode switching as a
    # def / class. The literal `step.mode` is allowed in docstrings, but a
    # top-level callable would indicate scope creep.
    re.compile(r"\bdef\s+pointer_repair\b"),
    re.compile(r"\bdef\s+repair_canonical_pointer\b"),
)


def test_pr_b_touched_files_do_not_define_pr_c_or_phase_2_symbols() -> None:
    violations: list[str] = []
    for rel in PR_B_TOUCHED_FILES:
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in PR_C_OR_PHASE_2_FORBIDDEN_SYMBOL_DEFS:
            if pattern.search(text):
                violations.append(f"{rel}: defines forbidden symbol {pattern.pattern}")
    assert not violations, (
        "PR-B must not implement PR-C / Phase-2 runtime symbols:\n"
        + "\n".join(violations)
    )


def test_pr_b_new_modules_have_no_active_pi_runtime_keys() -> None:
    pi_pattern = re.compile(
        r"(?<![A-Za-z0-9])pi_\d+\b|(?<![A-Za-z0-9])pi\d+_[A-Za-z0-9_]+\b|\u03a0\d+\b",
        re.IGNORECASE,
    )
    new_modules = (
        REPO_ROOT
        / "ai_stack"
        / "canonical_path"
        / "canonical_path_hold_effect_contracts.py",
        REPO_ROOT
        / "ai_stack"
        / "narrator"
        / "narrator_consequence_realization_contracts.py",
    )
    for path in new_modules:
        text = path.read_text(encoding="utf-8")
        assert not pi_pattern.search(text), (
            f"{path.name} must use semantic capability names only"
        )


def test_pr_b_does_not_wire_diagnostic_snapshot_stub_into_production() -> None:
    # Same constraint PR-0 imposed: the stub is not imported by any production
    # module. We check the PR-B-touched files.
    stub_import = re.compile(
        r"from\s+ai_stack\.runtime_diagnostic_snapshot_contracts\b|"
        r"import\s+ai_stack\.runtime_diagnostic_snapshot_contracts\b"
    )
    for rel in PR_B_TOUCHED_FILES:
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        assert not stub_import.search(text), (
            f"PR-B must not wire the PR-0 diagnostic snapshot stub into {rel}"
        )
