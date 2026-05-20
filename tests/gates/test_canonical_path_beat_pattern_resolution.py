"""Gate: every canonical_path beat resolves through the beat library.

Enforces the structural integrity of the canonical_path content:
  * resolver loads with no blocking diagnostics
  * every step's mandatory_beats use a known beat_pattern_ref OR an inline
    director_instruction
  * every required pattern parameter is supplied
  * every next_point.step_id refers to an existing step
  * the first→last step chain visits all 38 steps exactly once

Failure of any of these blocks merges: the canonical_path is the
authoritative source for runtime rendering, so a broken pattern_ref or
a typo'd next_point breaks live play.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GOC_MODULE_ROOT = REPO_ROOT / "content" / "modules" / "god_of_carnage"


@pytest.fixture(scope="module")
def canonical_path():
    from ai_stack.story_runtime.canonical_path.canonical_path_resolver import (
        clear_resolver_cache,
        load_canonical_path,
    )

    clear_resolver_cache()
    bundle = load_canonical_path(GOC_MODULE_ROOT)
    yield bundle
    clear_resolver_cache()


def test_resolver_loads_with_no_blocking_diagnostics(canonical_path):
    fatal = [d for d in canonical_path.diagnostics if "missing required params" not in d]
    assert not fatal, (
        "canonical_path has structural diagnostics that would degrade runtime: "
        + repr(fatal)
    )


def test_resolver_loads_thirty_eight_steps(canonical_path):
    assert len(canonical_path.steps) == 38, (
        f"expected 38 canonical steps, got {len(canonical_path.steps)}: "
        + ", ".join(s.id for s in canonical_path.steps)
    )


def test_every_beat_pattern_ref_resolves(canonical_path):
    pattern_ids = set(canonical_path.beat_patterns.keys())
    unresolved: list[str] = []
    for step in canonical_path.steps:
        for beat in step.mandatory_beats:
            if beat.pattern_id and beat.pattern_id not in pattern_ids:
                unresolved.append(f"{step.id}#{beat.id} -> {beat.pattern_id}")
    assert not unresolved, "unresolved beat_pattern_refs: " + ", ".join(unresolved)


def test_every_beat_pattern_has_required_params(canonical_path):
    missing: list[str] = []
    for step in canonical_path.steps:
        for beat in step.mandatory_beats:
            if not beat.pattern_id:
                continue
            pattern = canonical_path.beat_patterns.get(beat.pattern_id)
            if pattern is None:
                continue
            for name in pattern.required_param_names():
                if name and name not in beat.pattern_params:
                    missing.append(f"{step.id}#{beat.id} ({beat.pattern_id}) -> missing {name!r}")
    assert not missing, "beats missing required pattern params: " + ", ".join(missing)


def test_every_beat_carries_a_director_instruction(canonical_path):
    empty: list[str] = []
    for step in canonical_path.steps:
        for beat in step.mandatory_beats:
            if not beat.director_instruction:
                empty.append(f"{step.id}#{beat.id}")
    assert not empty, "beats without director_instruction: " + ", ".join(empty)


def test_every_next_step_id_exists(canonical_path):
    ids = set(canonical_path.steps_by_id.keys())
    dangling: list[str] = []
    for step in canonical_path.steps:
        nxt = step.next_step_id()
        if nxt and nxt not in ids:
            dangling.append(f"{step.id} -> {nxt}")
    assert not dangling, "dangling next_point.step_id references: " + ", ".join(dangling)


def test_chain_walks_all_thirty_eight_steps_without_cycles(canonical_path):
    visited: list[str] = []
    current = canonical_path.first_step_id()
    while current and current not in visited:
        visited.append(current)
        current = canonical_path.next_step_id_after(current)
    assert visited[0] == "opening_001_parc_montsouris_edge"
    assert visited[-1] == "opening_038_handoff_or_terminal"
    assert len(visited) == 38, f"chain visits {len(visited)} steps, expected 38"
