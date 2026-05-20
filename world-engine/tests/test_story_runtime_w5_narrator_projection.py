"""StoryRuntimeManager narrator-projection wiring tests (ADR-0063 Phase 2).

Exercises ``_maybe_enrich_blocks_with_w5_narrator_projection`` directly so we
can verify both flag states without booting the full runtime.

Asserted behavior:

- When ``W5_AST_NARRATOR_PROJECTION_ENABLED`` is disabled, narrator
  ``source_facts`` does NOT contain ``w5_projection`` — i.e. behavior is
  identical to pre-Phase-2.
- When the flag is enabled, narrator ``source_facts`` DOES contain the typed
  projection payload with the five W5 summaries.
- The projection in ``source_facts`` carries semantic values, not just keys.
- When ``w5_latest_snapshot`` is malformed, the helper falls back to legacy
  behavior and records a diagnostic — the turn is not failed in Phase 2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from app.story_runtime.manager import StoryRuntimeManager, StorySession


def _make_session(
    *,
    w5_latest: dict | None,
    w5_history: list[dict] | None = None,
    runtime_projection: dict[str, Any] | None = None,
) -> StorySession:
    return StorySession(
        session_id="sess_proj_wired",
        module_id="god_of_carnage",
        runtime_projection=runtime_projection or {},
        created_at=datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 20, 12, 0, 5, tzinfo=timezone.utc),
        turn_counter=3,
        current_scene_id="opening",
        w5_history=list(w5_history or []),
        w5_latest_snapshot=w5_latest,
    )


def _snapshot_with_five_dimensions(
    turn: int = 3,
    *,
    actor_id: str = "veronique",
    location: str = "parlor",
    current_action: str = "accuses",
    tone: str = "sharp",
) -> dict[str, Any]:
    """A fully-populated persisted snapshot dict for one actor."""

    def _f(
        fact_id: str,
        dim: str,
        key: str,
        value: Any,
        source: str,
        truth: str,
        visibility: str = "public",
    ) -> dict[str, Any]:
        return {
            "schema_version": "w5_fact.v1",
            "fact_id": fact_id,
            "actor_id": actor_id,
            "dimension": dim,
            "key": key,
            "value": value,
            "source": source,
            "source_event_id": f"ct_{turn:03d}",
            "truth_level": truth,
            "confidence": 1.0,
            "valid_from_turn": turn,
            "valid_until_turn": None,
            "last_confirmed_turn": turn,
            "visibility": visibility,
            "actor_knowledge_scope": [],
            "status": "active",
            "superseded_by_fact_id": None,
            "contradicted_by_fact_id": None,
        }

    return {
        "schema_version": "w5_snapshot.v1",
        "snapshot_id": f"w5s_wired_{turn}",
        "story_session_id": "sess_proj_wired",
        "turn_number": turn,
        "actors": {
            actor_id: {
                "actor_id": actor_id,
                "actor_type": "human",
                "actor_role_in_scene": "aggressor",
                "involvement_type": "primary",
                "where": [
                    _f("w5f_w_1", "where", "scene_location", location,
                       "participant_state_move", "observed"),
                ],
                "what": [
                    _f("w5f_what_1", "what", "interaction_type", "confrontation",
                       "committed_action", "observed"),
                    _f("w5f_what_2", "what", "current_action", current_action,
                       "committed_action", "observed"),
                ],
                "how": [
                    _f("w5f_how_1", "how", "tone", tone,
                       "committed_action", "observed"),
                    _f("w5f_how_2", "how", "intensity", "rising",
                       "director_composition", "director_assigned"),
                ],
                "why": [
                    _f("w5f_why_1", "why", "motive", "defend_son",
                       "character_mind_record", "inferred",
                       visibility="private_to_actor"),
                ],
                "freshness_status": "fresh",
                "last_confirmed_turn": turn,
            }
        },
        "conflicts": [],
        "derived_from_event_ids": [f"ct_{turn:03d}"],
        "created_at": f"w5:turn:{turn}",
    }


def _legacy_block() -> dict[str, Any]:
    """A narrator source_block as built by god_of_carnage_narrator_path._block()."""

    return {
        "id": "opening-narrator-path-1",
        "block_type": "narrator",
        "text": "...",
        "source_facts": {
            "transition_from_previous": {
                "kind": "location_or_scene_shift",
                "location_changed": True,
                "scene_changed": True,
                "previous_location": {"id": "foyer"},
                "current_location": {"id": "parlor"},
            },
            "location": {"id": "parlor"},
        },
    }


def _enrich(session: StorySession, blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Call the bound method via the class so we don't have to fully construct
    # a StoryRuntimeManager. The method only touches ``self`` for the static
    # flag check; we pass the instance as the first arg using a minimal proxy.
    class _Proxy:
        _w5_ast_narrator_projection_enabled = staticmethod(
            StoryRuntimeManager._w5_ast_narrator_projection_enabled
        )

    return StoryRuntimeManager._maybe_enrich_blocks_with_w5_narrator_projection(
        _Proxy(),  # type: ignore[arg-type]
        session=session,
        source_blocks=blocks,
    )


def test_flag_disabled_does_not_add_w5_projection_to_source_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("W5_AST_NARRATOR_PROJECTION_ENABLED", raising=False)
    session = _make_session(w5_latest=_snapshot_with_five_dimensions())
    blocks = [_legacy_block()]
    enriched = _enrich(session, blocks)
    assert enriched is blocks  # untouched
    assert "w5_projection" not in enriched[0]["source_facts"]
    # Legacy fields preserved exactly.
    assert (
        enriched[0]["source_facts"]["transition_from_previous"]["location_changed"]
        is True
    )


def test_flag_disabled_via_explicit_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("W5_AST_NARRATOR_PROJECTION_ENABLED", "false")
    session = _make_session(w5_latest=_snapshot_with_five_dimensions())
    enriched = _enrich(session, [_legacy_block()])
    assert "w5_projection" not in enriched[0]["source_facts"]


def test_flag_enabled_adds_typed_projection_with_five_summaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("W5_AST_NARRATOR_PROJECTION_ENABLED", "true")
    session = _make_session(w5_latest=_snapshot_with_five_dimensions())
    enriched = _enrich(session, [_legacy_block()])
    proj = enriched[0]["source_facts"]["w5_projection"]
    assert proj["schema_version"] == "w5_projection.v1"
    assert proj["target_consumer"] == "narrator"
    # All five dimensions are present with semantic values.
    assert proj["who_summary"]["actor_type"] == "human"
    assert proj["where_summary"]["current_location"] == "parlor"
    assert proj["what_summary"]["facts"]["interaction_type"] == "confrontation"
    assert proj["what_summary"]["facts"]["current_action"] == "accuses"
    # how_summary is first-class — not folded into what.
    assert proj["how_summary"]["facts"]["tone"] == "sharp"
    assert proj["how_summary"]["facts"]["intensity"] == "rising"
    assert "tone" not in proj["what_summary"]["facts"]
    assert proj["why_summary"]["facts"]["motive"] == "defend_son"
    # truth_attribution preserved.
    assert proj["truth_attribution"]["why_summary.facts.motive"] == "inferred"
    assert proj["truth_attribution"]["how_summary.facts.intensity"] == "director_assigned"
    # Legacy fields stay in place as fallback.
    assert (
        enriched[0]["source_facts"]["transition_from_previous"]["location_changed"]
        is True
    )


def test_flag_enabled_centers_projection_on_session_human_actor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("W5_AST_NARRATOR_PROJECTION_ENABLED", "true")
    current = _snapshot_with_five_dimensions(
        actor_id="veronique",
        location="parlor",
        current_action="accuses",
        tone="sharp",
    )
    alain = _snapshot_with_five_dimensions(
        actor_id="alain",
        location="foyer",
        current_action="deflects",
        tone="controlled",
    )
    current["actors"].update(alain["actors"])
    session = _make_session(
        w5_latest=current,
        runtime_projection={"human_actor_id": "veronique"},
    )

    enriched = _enrich(session, [_legacy_block()])
    proj = enriched[0]["source_facts"]["w5_projection"]
    assert proj["actor_id"] == "veronique"
    assert proj["where_summary"]["current_location"] == "parlor"
    assert proj["what_summary"]["facts"]["current_action"] == "accuses"
    assert proj["how_summary"]["facts"]["tone"] == "sharp"


def test_flag_enabled_legacy_location_changed_parity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase 2 parity: when ``transition_from_previous.location_changed`` is
    True, the W5 ``where_summary.location_changed`` must also be True.
    """

    monkeypatch.setenv("W5_AST_NARRATOR_PROJECTION_ENABLED", "true")
    previous = _snapshot_with_five_dimensions(turn=2, location="foyer")
    current = _snapshot_with_five_dimensions(turn=3, location="parlor")
    session = _make_session(w5_latest=current, w5_history=[previous, current])

    blocks = [_legacy_block()]
    assert blocks[0]["source_facts"]["transition_from_previous"]["location_changed"] is True
    enriched = _enrich(session, blocks)
    proj = enriched[0]["source_facts"]["w5_projection"]
    assert proj["where_summary"]["location_changed"] is True
    assert proj["where_summary"]["previous_location"] == "foyer"
    assert proj["where_summary"]["current_location"] == "parlor"


def test_flag_enabled_with_malformed_snapshot_falls_back_and_records_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("W5_AST_NARRATOR_PROJECTION_ENABLED", "true")
    bad = {"schema_version": "w5_snapshot.v1", "this_is": "garbage"}
    session = _make_session(w5_latest=bad)
    enriched = _enrich(session, [_legacy_block()])
    # No w5_projection added.
    assert "w5_projection" not in enriched[0]["source_facts"]
    # Diagnostic recorded.
    kinds = [d.get("diagnostic_kind") for d in session.diagnostics]
    assert "w5_narrator_projection_failed" in kinds


def test_flag_enabled_with_no_snapshot_returns_safe_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("W5_AST_NARRATOR_PROJECTION_ENABLED", "true")
    session = _make_session(w5_latest=None)
    enriched = _enrich(session, [_legacy_block()])
    proj = enriched[0]["source_facts"]["w5_projection"]
    assert proj["target_consumer"] == "narrator"
    assert proj["where_summary"]["location_changed"] is False
    assert proj["who_summary"] == {}
