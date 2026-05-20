"""StorySession W5 storage tests (ADR-0063, Phase 1 shadow-only).

Verifies:
- ``story_session_to_payload`` / ``story_session_from_payload`` round-trip
  ``w5_history`` and ``w5_latest_snapshot`` with no information loss.
- Legacy payloads without W5 fields default to ``[]`` / ``None``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.story_runtime.manager import (
    StorySession,
    story_session_from_payload,
    story_session_to_payload,
)


def _build_session(**overrides) -> StorySession:
    defaults = dict(
        session_id="sess_w5_rt_1",
        module_id="god_of_carnage",
        runtime_projection={},
        created_at=datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 20, 12, 0, 5, tzinfo=timezone.utc),
        turn_counter=0,
        current_scene_id="opening",
    )
    defaults.update(overrides)
    return StorySession(**defaults)


def _example_snapshot(turn_number: int) -> dict:
    return {
        "schema_version": "w5_snapshot.v1",
        "snapshot_id": f"w5s_rt_{turn_number}",
        "story_session_id": "sess_w5_rt_1",
        "turn_number": turn_number,
        "actors": {
            "annette": {
                "actor_id": "annette",
                "actor_type": "human",
                "actor_role_in_scene": "host",
                "involvement_type": "primary",
                "where": [
                    {
                        "schema_version": "w5_fact.v1",
                        "fact_id": f"w5f_rt_{turn_number}",
                        "actor_id": "annette",
                        "dimension": "where",
                        "key": "scene_location",
                        "value": "foyer",
                        "source": "participant_state_move",
                        "source_event_id": f"ct_{turn_number:03d}",
                        "truth_level": "observed",
                        "confidence": 1.0,
                        "valid_from_turn": turn_number,
                        "valid_until_turn": None,
                        "last_confirmed_turn": turn_number,
                        "visibility": "public",
                        "actor_knowledge_scope": [],
                        "status": "active",
                        "superseded_by_fact_id": None,
                        "contradicted_by_fact_id": None,
                    }
                ],
                "what": [],
                "how": [],
                "why": [],
                "freshness_status": "fresh",
                "last_confirmed_turn": turn_number,
            }
        },
        "conflicts": [],
        "derived_from_event_ids": [f"ct_{turn_number:03d}"],
        "created_at": f"w5:turn:{turn_number}",
    }


def test_storysession_w5_defaults_are_empty_for_new_session() -> None:
    session = _build_session()
    assert session.w5_history == []
    assert session.w5_latest_snapshot is None


def test_storysession_w5_round_trip_through_payload() -> None:
    snap_1 = _example_snapshot(1)
    snap_2 = _example_snapshot(2)
    session = _build_session(
        turn_counter=2,
        w5_history=[snap_1, snap_2],
        w5_latest_snapshot=snap_2,
    )

    payload = story_session_to_payload(session)
    assert payload["w5_history"] == [snap_1, snap_2]
    assert payload["w5_latest_snapshot"] == snap_2

    restored = story_session_from_payload(payload)
    assert restored.w5_history == [snap_1, snap_2]
    assert restored.w5_latest_snapshot == snap_2


def test_storysession_legacy_payload_without_w5_fields_defaults_safely() -> None:
    """Older session payloads without w5_history / w5_latest_snapshot must load.

    They must default to ``[]`` and ``None`` respectively and must not raise.
    """

    legacy_payload = {
        "format_version": 1,
        "session_id": "sess_legacy_1",
        "module_id": "god_of_carnage",
        "runtime_projection": {},
        "created_at": "2026-05-20T12:00:00+00:00",
        "updated_at": "2026-05-20T12:00:05+00:00",
        "turn_counter": 0,
        "current_scene_id": "opening",
        "session_input_language": "de",
        "session_output_language": "de",
        "history": [],
        "diagnostics": [],
        "narrative_threads": {},
        "last_thread_update_trace": None,
        "prior_continuity_impacts": [],
        "hierarchical_memory": {},
        "environment_state": {},
        "runtime_world": {},
        "content_provenance": {},
        "canonical_step_id": None,
        # Note: no w5_history or w5_latest_snapshot keys.
    }

    restored = story_session_from_payload(legacy_payload)
    assert restored.w5_history == []
    assert restored.w5_latest_snapshot is None


def test_storysession_w5_history_is_append_only_in_round_trip() -> None:
    """Multiple snapshots survive in order through serialize/deserialize."""

    snapshots = [_example_snapshot(i) for i in range(1, 5)]
    session = _build_session(
        turn_counter=4,
        w5_history=list(snapshots),
        w5_latest_snapshot=snapshots[-1],
    )
    restored = story_session_from_payload(story_session_to_payload(session))
    assert [s["snapshot_id"] for s in restored.w5_history] == [
        s["snapshot_id"] for s in snapshots
    ]
    assert restored.w5_latest_snapshot == snapshots[-1]
