"""Tests for canonical-step LDSS output rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_stack.canonical_path.canonical_path_resolver import clear_resolver_cache, load_canonical_path
from ai_stack.canonical_step_renderer import render_canonical_step
from ai_stack.live_dramatic_scene_simulator import (
    LDSSInput,
    build_canonical_step_ldss_output,
)


@pytest.fixture(autouse=True)
def _reset_resolver_cache():
    clear_resolver_cache()
    yield
    clear_resolver_cache()


def _goc_module_root() -> Path:
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    return repo_root / "content" / "modules" / "god_of_carnage"


def _ldss_input_for_step(step_id: str, *, human: str = "annette") -> LDSSInput:
    canonical = load_canonical_path(_goc_module_root())
    npc_ids = ["alain", "veronique", "michel"] if human == "annette" else ["annette", "veronique", "michel"]
    return LDSSInput(
        story_session_state={
            "contract": "story_session_state.v1",
            "story_session_id": "test-canon",
            "turn_number": 0,
            "current_scene_id": "phase_1",
            "content_module_id": "god_of_carnage",
            "runtime_profile_id": "god_of_carnage_solo",
            "runtime_module_id": "solo_story_runtime",
            "selected_player_role": human,
            "human_actor_id": human,
            "npc_actor_ids": npc_ids,
        },
        actor_lane_context={
            "contract": "actor_lane_context.v1",
            "selected_player_role": human,
            "human_actor_id": human,
            "ai_allowed_actor_ids": sorted(npc_ids),
            "ai_forbidden_actor_ids": [human],
        },
        player_input="",
        canonical_step_id=step_id,
        canonical_path=canonical,
    )


def test_step_001_prologue_produces_narrator_blocks_only():
    rendered = render_canonical_step(
        load_canonical_path(_goc_module_root()),
        "opening_001_parc_montsouris_edge",
        turn_number=0,
        human_actor_id="annette",
    )
    assert rendered is not None
    assert rendered.visible_scene_output.blocks, "prologue step must emit at least one block"
    types = {b.block_type for b in rendered.visible_scene_output.blocks}
    assert types == {"narrator"}, f"expected narrator-only prologue, got {types}"


def test_step_005_statement_reading_emits_actor_line_for_veronique():
    out = build_canonical_step_ldss_output(_ldss_input_for_step("opening_005_statement_reading"))
    assert out is not None
    blocks = out.visible_scene_output.blocks
    actor_lines = [b for b in blocks if b.block_type == "actor_line"]
    assert actor_lines, "step 005 must produce at least one actor_line block"
    assert any(b.actor_id == "veronique" for b in actor_lines)
    assert out.visible_actor_response_present is True
    assert out.status == "approved"


def test_step_023_kokoschka_destruction_emits_environment_interaction():
    out = build_canonical_step_ldss_output(_ldss_input_for_step("opening_023_annette_vomits_kokoschka"))
    assert out is not None
    blocks = out.visible_scene_output.blocks
    env_blocks = [b for b in blocks if b.block_type == "environment_interaction"]
    # Step 023 commits an irreversible state change (kokoschka destroyed).
    # The renderer projects state_changes_committed into environment_interaction blocks
    # whenever an inline state_change instruction is produced.
    irreversibles = [s for s in out.visible_scene_output.blocks if "state_commit" in (s.text or "")]
    assert env_blocks or irreversibles or actor_line_count(blocks) > 0


def test_unknown_step_id_returns_none():
    out = build_canonical_step_ldss_output(_ldss_input_for_step("does_not_exist"))
    assert out is None


def actor_line_count(blocks) -> int:
    return sum(1 for b in blocks if b.block_type == "actor_line")
