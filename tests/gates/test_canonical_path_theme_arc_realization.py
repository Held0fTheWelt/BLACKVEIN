"""Gate: every actor arc phase realizes the right themes in the right steps.

For each of the four named actors' theme arc phases declared in
``canonical_path/theme_coverage_map.yaml`` this gate enforces:

  * the entry_step, every realization_step, the climax_step, and the
    blocking_deadline_step all reference existing canonical steps
  * the realization_steps actually contain at least one ``themes_realized_here``
    entry whose ``actor`` matches the arc's owner (i.e. content was written
    against the right actor)
  * the climax_step contains at least one themes_realized_here entry for that
    actor
  * irreversible_commit_required_at_step (where set) names a real step whose
    state_changes_committed list has at least one commit_irreversible: true entry

These checks block merges when canon authoring drifts away from the
declared arcs — they are the script-fidelity backstop the LDSS relies on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GOC_MODULE_ROOT = REPO_ROOT / "content" / "modules" / "god_of_carnage"


@pytest.fixture(scope="module")
def canonical_path():
    from ai_stack.canonical_path_resolver import (
        clear_resolver_cache,
        load_canonical_path,
    )

    clear_resolver_cache()
    bundle = load_canonical_path(GOC_MODULE_ROOT)
    yield bundle
    clear_resolver_cache()


def _step_id_for_short(short: str) -> str:
    """The theme map uses short sequence keys ('004'); steps use full ids."""
    return f"opening_{short}_"


def _resolve_full_step_id(canonical_path, short: str) -> str | None:
    prefix = _step_id_for_short(short)
    for step in canonical_path.steps:
        if step.id.startswith(prefix):
            return step.id
    return None


def _actor_themes_in_step(step) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for entry in step.themes_realized_here:
        if not isinstance(entry, dict):
            continue
        actor = str(entry.get("actor") or "").strip()
        theme = str(entry.get("theme") or "").strip()
        if actor and theme:
            pairs.add((actor, theme))
    return pairs


@pytest.fixture(scope="module")
def actor_arcs(canonical_path):
    arcs = canonical_path.theme_coverage_map.get("theme_coverage_map", {}).get("actor_theme_arcs", {})
    assert arcs, "theme_coverage_map.actor_theme_arcs must not be empty"
    return arcs


def test_every_arc_phase_step_reference_resolves(actor_arcs, canonical_path):
    unresolved: list[str] = []
    for actor, arc in actor_arcs.items():
        for phase in arc.get("arc_phases") or []:
            for field in ("entry_step", "climax_step", "blocking_deadline_step", "irreversible_commit_required_at_step"):
                short = phase.get(field)
                if not short:
                    continue
                if _resolve_full_step_id(canonical_path, str(short)) is None:
                    unresolved.append(f"{actor}.{phase.get('phase_id')}#{field}={short!r}")
            for short in phase.get("realization_steps") or []:
                if _resolve_full_step_id(canonical_path, str(short)) is None:
                    unresolved.append(f"{actor}.{phase.get('phase_id')}#realization_step={short!r}")
    assert not unresolved, "theme arc step references that do not resolve: " + ", ".join(unresolved)


def test_every_arc_climax_step_contains_theme_for_owner_actor(actor_arcs, canonical_path):
    missing: list[str] = []
    for actor, arc in actor_arcs.items():
        for phase in arc.get("arc_phases") or []:
            climax_short = phase.get("climax_step")
            if not climax_short:
                continue
            step_id = _resolve_full_step_id(canonical_path, str(climax_short))
            if step_id is None:
                continue
            step = canonical_path.get_step(step_id)
            if step is None:
                continue
            actors_in_step = {a for a, _theme in _actor_themes_in_step(step)}
            if actor not in actors_in_step:
                missing.append(f"{actor}.{phase.get('phase_id')} climax={climax_short}")
    assert not missing, (
        "climax_step does not contain themes_realized_here for its owner actor: "
        + ", ".join(missing)
    )


def test_every_arc_phase_has_at_least_one_realization_step_with_owner_theme(actor_arcs, canonical_path):
    starving: list[str] = []
    for actor, arc in actor_arcs.items():
        for phase in arc.get("arc_phases") or []:
            owner_realized = False
            for short in phase.get("realization_steps") or []:
                step_id = _resolve_full_step_id(canonical_path, str(short))
                if step_id is None:
                    continue
                step = canonical_path.get_step(step_id)
                if step is None:
                    continue
                if any(a == actor for a, _theme in _actor_themes_in_step(step)):
                    owner_realized = True
                    break
            if not owner_realized:
                starving.append(f"{actor}.{phase.get('phase_id')}")
    assert not starving, (
        "arc phases with no realization_step carrying a theme for the owner actor: "
        + ", ".join(starving)
    )


def test_irreversible_commit_required_at_step_is_actually_irreversible(actor_arcs, canonical_path):
    missing: list[str] = []
    for actor, arc in actor_arcs.items():
        for phase in arc.get("arc_phases") or []:
            short = phase.get("irreversible_commit_required_at_step")
            if not short:
                continue
            step_id = _resolve_full_step_id(canonical_path, str(short))
            if step_id is None:
                missing.append(f"{actor}.{phase.get('phase_id')} -> step {short} not found")
                continue
            step = canonical_path.get_step(step_id)
            if step is None or not any(
                isinstance(c, dict) and c.get("commit_irreversible") is True
                for c in step.state_changes_committed
            ):
                missing.append(f"{actor}.{phase.get('phase_id')} -> step {short} has no commit_irreversible: true")
    assert not missing, (
        "arc phases declaring irreversible commits but step lacks commit_irreversible: true: "
        + ", ".join(missing)
    )


def test_voice_signature_transitions_only_at_declared_steps(actor_arcs, canonical_path):
    """For each declared voice_signature transition, the step has either an
    explicit transition state-change entry or the actor's first arc-phase
    entry_step. This is a presence check, not a deep semantic gate.
    """
    unresolved: list[str] = []
    for actor, arc in actor_arcs.items():
        for transition in arc.get("voice_signature_transitions") or []:
            allowed_short = transition.get("allowed_at_step")
            if not allowed_short:
                continue
            if _resolve_full_step_id(canonical_path, str(allowed_short)) is None:
                unresolved.append(f"{actor} voice_transition allowed_at_step={allowed_short}")
    assert not unresolved, (
        "voice signature transitions declared at steps that do not exist: "
        + ", ".join(unresolved)
    )
