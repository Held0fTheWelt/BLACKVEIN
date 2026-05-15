from __future__ import annotations

import json

from app.story_runtime.branch_timeline_store import JsonBranchTimelineStore
from story_runtime_core.branching import (
    BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION,
    BRANCHING_TIMELINE_STATUS_ACTIVE,
)


def _record(timeline_id: str, session_id: str = "session-1") -> dict:
    return {
        "schema_version": BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION,
        "timeline_id": timeline_id,
        "story_session_id": session_id,
        "status": BRANCHING_TIMELINE_STATUS_ACTIVE,
        "events": [],
        "created_at": "2026-05-15T00:00:00+00:00",
        "updated_at": "2026-05-15T00:00:00+00:00",
    }


def test_branch_timeline_store_roundtrips_json(tmp_path) -> None:
    store = JsonBranchTimelineStore(tmp_path / "branch_timelines")
    store.save("timeline-1", _record("timeline-1"))

    loaded = store.load("timeline-1")

    assert loaded["timeline_id"] == "timeline-1"
    assert loaded["story_session_id"] == "session-1"
    assert not list((tmp_path / "branch_timelines").glob("*.tmp"))
    raw = json.loads((tmp_path / "branch_timelines" / "timeline-1.json").read_text(encoding="utf-8"))
    assert raw["schema_version"] == BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION


def test_branch_timeline_store_filters_by_session_and_skips_corrupt_files(tmp_path) -> None:
    store = JsonBranchTimelineStore(tmp_path / "branch_timelines")
    store.save("timeline-1", _record("timeline-1", "session-1"))
    store.save("timeline-2", _record("timeline-2", "session-2"))
    (tmp_path / "branch_timelines" / "broken.json").write_text("{broken", encoding="utf-8")

    rows = store.load_for_session("session-1")

    assert [row["timeline_id"] for row in rows] == ["timeline-1"]
