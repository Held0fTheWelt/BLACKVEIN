"""Gate: object_theme_beats marked irreversible must commit at the named step.

For every cross_cutting_arcs.object_theme_beats entry that declares
``irreversible: true``, the canonical step it points at must have at
least one ``state_changes_committed`` entry with
``commit_irreversible: true``. This is the script-fidelity backstop
that prevents the LDSS from silently rendering an "irreversible"
object beat as a soft state change.

Covers (per the theme_coverage_map): Kokoschka catalog destruction at
023, phone destruction in tulip water at 033, tulips smashed at 035,
hamster ironic reveal at 037.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GOC_MODULE_ROOT = REPO_ROOT / "content" / "modules" / "god_of_carnage"


@pytest.fixture(scope="module")
def canonical_path():
    from ai_stack.canonical_path.canonical_path_resolver import (
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


@pytest.fixture(scope="module")
def object_theme_beats(canonical_path):
    cross = canonical_path.theme_coverage_map.get("theme_coverage_map", {}).get(
        "cross_cutting_arcs", {}
    )
    beats = cross.get("object_theme_beats") or []
    assert beats, "theme_coverage_map.cross_cutting_arcs.object_theme_beats must not be empty"
    return beats


def test_every_irreversible_object_beat_points_at_a_real_step(
    object_theme_beats, canonical_path
):
    unresolved: list[str] = []
    for obj in object_theme_beats:
        for beat in obj.get("beats") or []:
            if not beat.get("irreversible"):
                continue
            short = str(beat.get("step") or "").strip()
            if not short:
                unresolved.append(
                    f"{obj.get('object_id')} irreversible beat with no step"
                )
                continue
            if _resolve_full_step_id(canonical_path, short) is None:
                unresolved.append(
                    f"{obj.get('object_id')}#step={short} -> no canonical step"
                )
    assert not unresolved, "irreversible object beats with unresolved steps: " + ", ".join(
        unresolved
    )


def test_every_irreversible_object_beat_has_commit_irreversible_in_step(
    object_theme_beats, canonical_path
):
    missing: list[str] = []
    for obj in object_theme_beats:
        for beat in obj.get("beats") or []:
            if not beat.get("irreversible"):
                continue
            short = str(beat.get("step") or "").strip()
            step_id = _resolve_full_step_id(canonical_path, short)
            if step_id is None:
                continue
            step = canonical_path.get_step(step_id)
            if step is None:
                missing.append(f"{obj.get('object_id')}@{short} step not loaded")
                continue
            has_irreversible = any(
                isinstance(c, dict) and c.get("commit_irreversible") is True
                for c in step.state_changes_committed
            )
            if not has_irreversible:
                missing.append(
                    f"{obj.get('object_id')}@{short} -> "
                    f"{step_id} has no state_changes_committed.commit_irreversible: true"
                )
    assert not missing, (
        "irreversible object beats whose step lacks commit_irreversible: true: "
        + ", ".join(missing)
    )


def test_required_anchor_objects_have_irreversible_commit_at_expected_step(
    object_theme_beats, canonical_path
):
    """The four anchor objects must each have at least one irreversible commit at
    a specific step the theme_coverage_map declares. This is a coarse smoke test
    so future authoring drift on these four anchors can't go silent.
    """
    expected = {
        "kokoschka_catalog": "023",
        "alain_mobile_phone": "033",
        "tulips_bouquet": "035",
        "ethan_hamster": "037",
    }
    found: dict[str, str | None] = {object_id: None for object_id in expected}
    for obj in object_theme_beats:
        oid = obj.get("object_id")
        if oid not in expected:
            continue
        for beat in obj.get("beats") or []:
            if not beat.get("irreversible"):
                continue
            short = str(beat.get("step") or "").strip()
            if short == expected[oid]:
                found[oid] = short
                break
    missing = [oid for oid, hit in found.items() if hit is None]
    assert not missing, (
        "expected anchor objects missing an irreversible beat at the declared step: "
        + ", ".join(f"{oid}@{expected[oid]}" for oid in missing)
    )
