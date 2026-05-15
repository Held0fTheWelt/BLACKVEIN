from __future__ import annotations

from story_runtime_core.branching import (
    BRANCHING_TIMELINE_EVENT_NODE_SELECTED,
    BRANCHING_TIMELINE_EVENT_SCHEMA_VERSION,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
    BRANCHING_TIMELINE_EVENT_TIMELINE_ARCHIVED,
    BRANCHING_TIMELINE_EVENT_TIMELINE_COMPACTED,
    BRANCHING_TIMELINE_EVENT_TREE_CREATED,
    BRANCHING_TIMELINE_EVENT_TYPES,
    BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION,
    BRANCHING_TIMELINE_SNAPSHOT_SCHEMA_VERSION,
    BRANCHING_TIMELINE_STATUS_ARCHIVED,
    BRANCHING_TREE_STATUS_SIMULATED,
    append_branch_timeline_event,
    archive_branch_timeline,
    default_branch_timeline_bounds,
    make_branch_timeline_event,
    make_branch_timeline_record,
)


def _fingerprint(value: str = "fp-1") -> dict:
    return {
        "fingerprint": value,
        "session_id": "session-timeline",
        "turn_counter": 3,
        "history_count": 4,
        "current_scene_id": "scene_1",
    }


def _event(timeline: dict, event_type: str, *, tree_id: str = "tree-a", index: int = 0) -> dict:
    return make_branch_timeline_event(
        event_type=event_type,
        story_session_id=timeline["story_session_id"],
        timeline_id=timeline["timeline_id"],
        tree_id=tree_id,
        node_id="node-a" if event_type == BRANCHING_TIMELINE_EVENT_NODE_SELECTED else None,
        session_fingerprint=_fingerprint(f"fp-{index}"),
        details={"tree_status": BRANCHING_TREE_STATUS_SIMULATED, "index": index},
        occurred_at=f"2026-05-15T00:00:{index:02d}+00:00",
    )


def test_branch_timeline_records_lifecycle_events_as_bounded_evidence() -> None:
    timeline = make_branch_timeline_record(
        story_session_id="session-timeline",
        module_id="module-alpha",
        runtime_profile_id="profile-alpha",
        root_session_fingerprint=_fingerprint(),
    )

    for event_type in (
        BRANCHING_TIMELINE_EVENT_TREE_CREATED,
        BRANCHING_TIMELINE_EVENT_NODE_SELECTED,
        BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
    ):
        timeline = append_branch_timeline_event(timeline, _event(timeline, event_type))

    event_types = [event["event_type"] for event in timeline["events"]]
    assert timeline["schema_version"] == BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION
    assert timeline["snapshot"]["schema_version"] == BRANCHING_TIMELINE_SNAPSHOT_SCHEMA_VERSION
    assert set(event_types).issubset(set(BRANCHING_TIMELINE_EVENT_TYPES))
    assert {event["schema_version"] for event in timeline["events"]} == {BRANCHING_TIMELINE_EVENT_SCHEMA_VERSION}
    assert timeline["snapshot"]["selection_count"] == 1
    assert timeline["snapshot"]["replay_commit_count"] == 1
    assert timeline["snapshot"]["committed_tree_count"] == 1


def test_branch_timeline_compaction_preserves_bounds_and_contract_events() -> None:
    bounds = default_branch_timeline_bounds()
    bounds["max_events"] = 8
    timeline = make_branch_timeline_record(
        story_session_id="session-timeline",
        root_session_fingerprint=_fingerprint(),
        bounds=bounds,
    )

    for index in range(bounds["max_events"] + 5):
        timeline = append_branch_timeline_event(
            timeline,
            _event(
                timeline,
                BRANCHING_TIMELINE_EVENT_TREE_CREATED,
                tree_id=f"tree-{index}",
                index=index,
            ),
        )

    event_types = [event["event_type"] for event in timeline["events"]]
    assert len(timeline["events"]) <= timeline["bounds"]["max_events"]
    assert timeline["snapshot"]["event_count"] <= timeline["bounds"]["max_events"]
    assert timeline["snapshot"]["compacted_event_count"] > 0
    assert BRANCHING_TIMELINE_EVENT_TIMELINE_COMPACTED in event_types
    assert set(event_types).issubset(set(BRANCHING_TIMELINE_EVENT_TYPES))


def test_branch_timeline_archive_is_visible_in_snapshot() -> None:
    timeline = make_branch_timeline_record(
        story_session_id="session-timeline",
        root_session_fingerprint=_fingerprint(),
    )

    archived = archive_branch_timeline(timeline, reason="test_archive")

    assert archived["status"] == BRANCHING_TIMELINE_STATUS_ARCHIVED
    assert archived["snapshot"]["status"] == BRANCHING_TIMELINE_STATUS_ARCHIVED
    assert archived["snapshot"]["last_event_type"] == BRANCHING_TIMELINE_EVENT_TIMELINE_ARCHIVED
