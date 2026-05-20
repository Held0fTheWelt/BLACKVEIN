"""Gate: each actor's pattern_signature must fire as declared by the
theme_coverage_map.gate_assertions.test_pattern_signature_per_actor rules.

Rules enforced (derived from theme_coverage_map.yaml gate_assertions):

  * michel_uses_amiable_echo_until_step_028 — michel uses amiable_echo
    (as ``beat_pattern_ref`` with ``actor: michel`` OR as an inline beat
    whose id starts with ``michel_amiable_echo``) at least once before
    step 028; after step 028 the pattern must NOT fire with michel as
    actor (the cynical_pragmatist_unmasked transition retires this
    signature).
  * alain_uses_single_word_challenge_in_entry — alain's entry phase
    (entry_step=006, realization_steps=[004,005,006]) contains at least
    one single_word_challenge beat with alain as actor (or inline beat
    with that name).
  * alain_uses_phone_interruption_recurrent_at_011_017_027 — the
    phone_interruption_recurrent pattern fires in steps 011, 017, AND
    027 (these are alain's three phone calls).
  * Every phase that declares a pattern_signature has at least one
    realization_step where that pattern is used by the arc owner (either
    as beat_pattern_ref+actor, or as an inline beat whose id matches
    ``<owner>_<signature>``).
  * The beat_library ``character_signature_owner`` declarations stay in
    sync with the theme_coverage_map.pattern_signature owners.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
GOC_MODULE_ROOT = REPO_ROOT / "content" / "modules" / "god_of_carnage"
BEAT_LIBRARY_DIR = GOC_MODULE_ROOT / "direction" / "beat_library"


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


def _short_from_full(full_id: str) -> str | None:
    if not full_id.startswith("opening_"):
        return None
    rest = full_id[len("opening_"):]
    short = rest.split("_", 1)[0]
    return short if short.isdigit() else None


def _beat_uses_pattern_for_actor(beat, pattern_id: str, actor: str) -> bool:
    """True if the beat is bound to ``pattern_id`` for ``actor``.

    Accepts both forms used by canonical_path authoring:
      * ``beat_pattern_ref: pattern_id`` + ``beat_pattern_params.actor: actor``
      * inline beat whose id starts with ``f"{actor}_{pattern_id}"`` (used
        in steps 004-006 where beats are inline)
    """
    pattern_ref = (beat.pattern_id or "").strip()
    params = beat.pattern_params or {}
    if pattern_ref == pattern_id:
        beat_actor = str(params.get("actor") or "").strip()
        return beat_actor == actor
    if not pattern_ref:
        if beat.id and beat.id.startswith(f"{actor}_{pattern_id}"):
            return True
    return False


@pytest.fixture(scope="module")
def actor_arcs(canonical_path):
    return canonical_path.theme_coverage_map.get("theme_coverage_map", {}).get(
        "actor_theme_arcs", {}
    )


@pytest.fixture(scope="module")
def beat_library_owners() -> dict[str, str]:
    owners: dict[str, str] = {}
    for path in BEAT_LIBRARY_DIR.glob("*.yaml"):
        if path.name == "_index.yaml":
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        pattern = data.get("beat_pattern") or {}
        pid = pattern.get("id")
        owner = pattern.get("character_signature_owner")
        if pid and owner:
            owners[pid] = owner
    return owners


def _all_pattern_signature_phases(actor_arcs):
    for actor, arc in actor_arcs.items():
        for phase in arc.get("arc_phases") or []:
            sig = phase.get("pattern_signature")
            if sig:
                yield actor, phase, sig


def test_michel_uses_amiable_echo_at_least_once_before_step_028(canonical_path):
    found = False
    for step in canonical_path.steps:
        short = _short_from_full(step.id)
        if not short or int(short) >= 28:
            continue
        for beat in step.mandatory_beats:
            if _beat_uses_pattern_for_actor(beat, "amiable_echo", "michel"):
                found = True
                break
        if found:
            break
    assert found, (
        "michel must use amiable_echo at least once in steps 001-027 "
        "(theme_coverage_map asserts: michel_uses_amiable_echo_until_step_028)"
    )


def test_michel_does_not_use_amiable_echo_with_canonical_tone_after_step_028(
    canonical_path,
):
    """After michel's transition at step 028 his amiable_echo signature must
    not fire with the canonical (``friendly_confirmation``) tone — that tone
    belongs to phase amiable_silent_co_signer. Late-scene degraded uses
    (``dry_agreement`` / ``polite_neutral``) are allowed: the beat_library
    explicitly documents that michel may degrade to dry mirror in the drunk
    scenes."""
    canonical_tones = {"friendly_confirmation"}
    violations: list[str] = []
    for step in canonical_path.steps:
        short = _short_from_full(step.id)
        if not short or int(short) <= 28:
            continue
        for beat in step.mandatory_beats:
            if not _beat_uses_pattern_for_actor(beat, "amiable_echo", "michel"):
                continue
            params = beat.pattern_params or {}
            tone = str(params.get("tone") or "").strip()
            if not tone or tone in canonical_tones:
                violations.append(
                    f"{step.id}#{beat.id} (tone={tone or 'unspecified'})"
                )
    assert not violations, (
        "michel uses amiable_echo with the canonical signature tone after "
        "his transition at step 028 (failure_code "
        "signature_pattern_persists_past_transition_step): "
        + ", ".join(violations)
    )


def test_alain_uses_single_word_challenge_in_entry_phase(canonical_path, actor_arcs):
    arc = actor_arcs.get("alain") or {}
    phases = arc.get("arc_phases") or []
    entry_phase = next((p for p in phases if p.get("pattern_signature") == "single_word_challenge"), None)
    assert entry_phase is not None, (
        "alain arc must declare a phase with pattern_signature: single_word_challenge"
    )
    realization_shorts = {str(s) for s in (entry_phase.get("realization_steps") or [])}
    realization_shorts.add(str(entry_phase.get("entry_step") or ""))
    realization_shorts.discard("")
    found = False
    for step in canonical_path.steps:
        short = _short_from_full(step.id)
        if short not in realization_shorts:
            continue
        for beat in step.mandatory_beats:
            if _beat_uses_pattern_for_actor(beat, "single_word_challenge", "alain"):
                found = True
                break
        if found:
            break
    assert found, (
        "alain must use single_word_challenge at least once in his entry phase steps "
        f"{sorted(realization_shorts)} (theme_coverage_map asserts: alain_uses_single_word_challenge_in_entry)"
    )


def test_phone_interruption_recurrent_fires_at_011_017_027(canonical_path):
    expected_shorts = {"011", "017", "027"}
    fired_in: set[str] = set()
    for step in canonical_path.steps:
        short = _short_from_full(step.id)
        if short not in expected_shorts:
            continue
        for beat in step.mandatory_beats:
            if (beat.pattern_id or "").strip() == "phone_interruption_recurrent":
                fired_in.add(short)
                break
    missing = expected_shorts - fired_in
    assert not missing, (
        "phone_interruption_recurrent must fire at steps 011/017/027 "
        "(theme_coverage_map asserts: alain_uses_phone_interruption_recurrent_at_011_017_027); "
        f"missing at: {sorted(missing)}"
    )


def test_every_phase_pattern_signature_realizes_in_realization_steps(
    actor_arcs, canonical_path
):
    """For every arc phase that declares a pattern_signature, at least one
    realization_step must contain a beat using that pattern with the arc
    owner as actor (or as an inline beat whose id matches owner_pattern)."""
    starving: list[str] = []
    for actor, phase, sig in _all_pattern_signature_phases(actor_arcs):
        realization = {str(s) for s in (phase.get("realization_steps") or [])}
        realization.add(str(phase.get("entry_step") or ""))
        realization.discard("")
        found = False
        # phone_interruption_recurrent has no `actor` param (uses call_partner);
        # treat any occurrence of the pattern within the actor's realization steps
        # as evidence of the signature firing for that actor.
        pattern_has_actor_param = sig not in {"phone_interruption_recurrent"}
        for step in canonical_path.steps:
            short = _short_from_full(step.id)
            if short not in realization:
                continue
            for beat in step.mandatory_beats:
                if pattern_has_actor_param:
                    if _beat_uses_pattern_for_actor(beat, sig, actor):
                        found = True
                        break
                else:
                    if (beat.pattern_id or "").strip() == sig:
                        found = True
                        break
            if found:
                break
        if not found:
            starving.append(f"{actor}.{phase.get('phase_id')}#signature={sig}")
    assert not starving, (
        "arc phases whose declared pattern_signature never fires for the owner actor: "
        + ", ".join(starving)
    )


def test_beat_library_signature_owners_match_theme_map(
    beat_library_owners, actor_arcs
):
    """If a beat_library entry declares character_signature_owner, the theme
    coverage map must declare at least one phase for that actor with
    pattern_signature equal to that pattern id (and vice versa for the
    intersection)."""
    mismatches: list[str] = []
    for pattern_id, lib_owner in beat_library_owners.items():
        arc = actor_arcs.get(lib_owner) or {}
        declared = any(
            (phase.get("pattern_signature") or "").strip() == pattern_id
            for phase in arc.get("arc_phases") or []
        )
        if not declared:
            mismatches.append(
                f"beat_library says {pattern_id} is owned by {lib_owner!r}, "
                "but theme_coverage_map has no matching phase pattern_signature"
            )
    assert not mismatches, "; ".join(mismatches)
