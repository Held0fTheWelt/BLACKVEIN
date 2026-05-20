"""Tests for ai_stack.story_runtime.canonical_path.canonical_path_resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_stack.story_runtime.canonical_path.canonical_path_resolver import (
    CanonicalPathResolveError,
    clear_resolver_cache,
    load_canonical_path,
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


def test_load_canonical_path_returns_all_thirty_eight_steps():
    canonical_path = load_canonical_path(_goc_module_root())
    assert canonical_path is not None

    assert len(canonical_path.steps) == 38
    assert canonical_path.first_step_id() == "opening_001_parc_montsouris_edge"
    last = canonical_path.steps[-1]
    assert last.id == "opening_038_handoff_or_terminal"


def test_every_beat_pattern_ref_resolves_to_a_known_pattern():
    canonical_path = load_canonical_path(_goc_module_root())
    pattern_ids = set(canonical_path.beat_patterns.keys())
    assert pattern_ids, "beat library must load at least one pattern"

    unresolved = []
    for step in canonical_path.steps:
        for beat in step.mandatory_beats:
            if beat.pattern_id and beat.pattern_id not in pattern_ids:
                unresolved.append(f"{step.id}#{beat.id} -> {beat.pattern_id}")

    assert not unresolved, "unresolved beat_pattern_refs: " + ", ".join(unresolved)


def test_next_step_chain_walks_from_first_to_last_without_gaps():
    canonical_path = load_canonical_path(_goc_module_root())
    visited: list[str] = []
    current = canonical_path.first_step_id()
    while current:
        visited.append(current)
        current = canonical_path.next_step_id_after(current)
        if current in visited:
            break

    assert visited[0] == "opening_001_parc_montsouris_edge"
    assert visited[-1] == "opening_038_handoff_or_terminal"
    assert len(visited) == 38, f"expected 38-step chain, got {len(visited)}"


def test_resolve_step_005_has_paraphrase_required_with_facts_beat():
    canonical_path = load_canonical_path(_goc_module_root())
    step = canonical_path.get_step("opening_005_statement_reading")
    assert step is not None
    assert step.mode == "scripted_mandatory_dialog"

    facts_bearing = [
        beat for beat in step.mandatory_beats
        if "npc_speak" in beat.director_instruction
    ]
    assert facts_bearing, "step 005 must produce at least one npc_speak beat"
    speak = facts_bearing[0].director_instruction["npc_speak"]
    assert speak["actor"] == "veronique"
    assert speak["required_facts"], "step 005 npc_speak must carry required_facts"


def test_resolver_diagnostics_empty_for_canonical_god_of_carnage():
    canonical_path = load_canonical_path(_goc_module_root())
    blocking = [d for d in canonical_path.diagnostics if "missing required params" not in d]
    assert not blocking, "canonical_path has unexpected resolver diagnostics: " + repr(blocking)


def test_load_canonical_path_raises_when_directory_missing(tmp_path):
    with pytest.raises(CanonicalPathResolveError):
        load_canonical_path(tmp_path)
