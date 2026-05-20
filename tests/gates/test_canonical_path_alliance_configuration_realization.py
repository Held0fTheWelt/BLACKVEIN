"""Gate: alliance configurations declared in the theme_coverage_map must be
structurally realized by the canonical_path.

Enforces structural integrity of the cross-cutting alliance arc:

  * every phase (A..F) lists at least one step
  * every step a phase lists resolves to a real canonical_path step
  * ``committed_by_end_of_step`` resolves to a real step AND is one of
    that phase's own listed steps
  * phases appear in canonical sequence (phase B's first step is after
    phase A's last step in canonical order, and so on)
  * no canonical step is claimed by two different alliance phases
  * every phase has a non-empty ``configuration.axis``

Plus the two alliance shifts the script-content already commits:

  * phase_C (committed at step 028) writes alliance_configuration_history
    as ``commit_irreversible: true``
  * phase_F (committed at step 037) writes alliance_configuration_history
    as ``commit_irreversible: true``

These are the two observable rotations of the four-person alliance graph
and they are the script-fidelity backstop the LDSS depends on.
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


def _resolve_full_step_id(canonical_path, short: str) -> str | None:
    prefix = f"opening_{short}_"
    for step in canonical_path.steps:
        if step.id.startswith(prefix):
            return step.id
    return None


def _canonical_index(canonical_path, full_id: str) -> int:
    for i, step in enumerate(canonical_path.steps):
        if step.id == full_id:
            return i
    return -1


@pytest.fixture(scope="module")
def alliance_phases(canonical_path):
    cross = canonical_path.theme_coverage_map.get("theme_coverage_map", {}).get(
        "cross_cutting_arcs", {}
    )
    phases = cross.get("alliance_configurations") or []
    assert phases, "theme_coverage_map.cross_cutting_arcs.alliance_configurations must not be empty"
    return phases


def test_every_alliance_phase_has_at_least_one_step(alliance_phases):
    empty = [p.get("phase_id") for p in alliance_phases if not p.get("steps")]
    assert not empty, "alliance phases with no steps: " + ", ".join(empty)


def test_every_alliance_phase_step_resolves(alliance_phases, canonical_path):
    unresolved: list[str] = []
    for phase in alliance_phases:
        for short in phase.get("steps") or []:
            if _resolve_full_step_id(canonical_path, str(short)) is None:
                unresolved.append(f"{phase.get('phase_id')}#step={short}")
    assert not unresolved, "alliance phase step references unresolved: " + ", ".join(
        unresolved
    )


def test_committed_by_end_of_step_belongs_to_phase(alliance_phases, canonical_path):
    bad: list[str] = []
    for phase in alliance_phases:
        commit_short = phase.get("committed_by_end_of_step")
        if not commit_short:
            bad.append(f"{phase.get('phase_id')} has no committed_by_end_of_step")
            continue
        commit_short = str(commit_short)
        if _resolve_full_step_id(canonical_path, commit_short) is None:
            bad.append(
                f"{phase.get('phase_id')}#committed_by_end_of_step={commit_short} -> unresolved"
            )
            continue
        phase_steps = {str(s) for s in (phase.get("steps") or [])}
        if commit_short not in phase_steps:
            bad.append(
                f"{phase.get('phase_id')} commits at {commit_short} which is not in its own steps {sorted(phase_steps)}"
            )
    assert not bad, "alliance phase commit-step errors: " + ", ".join(bad)


def test_alliance_phases_appear_in_canonical_sequence(alliance_phases, canonical_path):
    last_max_index = -1
    out_of_order: list[str] = []
    for phase in alliance_phases:
        indices = []
        for short in phase.get("steps") or []:
            full_id = _resolve_full_step_id(canonical_path, str(short))
            if full_id is None:
                continue
            idx = _canonical_index(canonical_path, full_id)
            if idx >= 0:
                indices.append(idx)
        if not indices:
            continue
        phase_min, phase_max = min(indices), max(indices)
        if phase_min <= last_max_index:
            out_of_order.append(
                f"{phase.get('phase_id')} starts at canonical-index {phase_min} "
                f"which is not strictly after previous phase end {last_max_index}"
            )
        last_max_index = phase_max
    assert not out_of_order, "alliance phases out of canonical sequence: " + ", ".join(
        out_of_order
    )


def test_no_step_claimed_by_two_phases(alliance_phases):
    seen: dict[str, str] = {}
    collisions: list[str] = []
    for phase in alliance_phases:
        for short in phase.get("steps") or []:
            key = str(short)
            if key in seen and seen[key] != phase.get("phase_id"):
                collisions.append(
                    f"step {key} claimed by {seen[key]} AND {phase.get('phase_id')}"
                )
            else:
                seen[key] = phase.get("phase_id")
    assert not collisions, "alliance phase step collisions: " + ", ".join(collisions)


def test_every_alliance_phase_has_axis(alliance_phases):
    missing = []
    for phase in alliance_phases:
        cfg = phase.get("configuration") or {}
        axis = str(cfg.get("axis") or "").strip()
        if not axis:
            missing.append(phase.get("phase_id"))
    assert not missing, "alliance phases missing configuration.axis: " + ", ".join(
        str(m) for m in missing
    )


def test_phase_C_and_F_commit_alliance_configuration_history_irreversible(
    alliance_phases, canonical_path
):
    """The two observable alliance rotations (women_vs_men at 028 and ironic
    reset at 037) must write an irreversible alliance_configuration_history
    state change so the runtime cannot silently revert them."""
    expected = {
        "phase_C_alliance_shifts_to_women_vs_men": "028",
        "phase_F_ironic_reset": "037",
    }
    missing: list[str] = []
    for phase in alliance_phases:
        pid = phase.get("phase_id")
        if pid not in expected:
            continue
        expected_step = expected[pid]
        commit_short = str(phase.get("committed_by_end_of_step") or "")
        assert commit_short == expected_step, (
            f"{pid} should commit at step {expected_step}, got {commit_short}"
        )
        full_id = _resolve_full_step_id(canonical_path, expected_step)
        step = canonical_path.get_step(full_id) if full_id else None
        if step is None:
            missing.append(f"{pid} -> step {expected_step} not loaded")
            continue
        has_irreversible_alliance = any(
            isinstance(c, dict)
            and "alliance" in str(c.get("key") or "").lower()
            and c.get("commit_irreversible") is True
            for c in step.state_changes_committed
        )
        if not has_irreversible_alliance:
            missing.append(
                f"{pid}@{expected_step} -> {full_id} has no irreversible "
                "alliance_configuration commit"
            )
    assert not missing, "alliance commit assertions failed: " + ", ".join(missing)
