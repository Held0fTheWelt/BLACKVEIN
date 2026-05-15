from __future__ import annotations

import json

from app.story_runtime.consequence_cascade_store import JsonConsequenceCascadeStore
from story_runtime_core.consequences import CONSEQUENCE_CASCADE_RECORD_SCHEMA_VERSION


def _record(cascade_id: str, session_id: str = "session-1") -> dict:
    return {
        "schema_version": CONSEQUENCE_CASCADE_RECORD_SCHEMA_VERSION,
        "cascade_id": cascade_id,
        "story_session_id": session_id,
        "atoms": [],
        "edges": [],
        "snapshot": {"atom_count": 0, "edge_count": 0},
        "created_at": "2026-05-15T00:00:00+00:00",
        "updated_at": "2026-05-15T00:00:00+00:00",
    }


def test_consequence_cascade_store_roundtrips_json(tmp_path) -> None:
    store = JsonConsequenceCascadeStore(tmp_path / "consequence_cascades")
    store.save("cascade-1", _record("cascade-1"))

    loaded = store.load("cascade-1")

    assert loaded["cascade_id"] == "cascade-1"
    assert loaded["story_session_id"] == "session-1"
    assert not list((tmp_path / "consequence_cascades").glob("*.tmp"))
    raw = json.loads(
        (tmp_path / "consequence_cascades" / "cascade-1.json").read_text(encoding="utf-8")
    )
    assert raw["schema_version"] == CONSEQUENCE_CASCADE_RECORD_SCHEMA_VERSION


def test_consequence_cascade_store_filters_by_session_and_skips_corrupt_files(tmp_path) -> None:
    store = JsonConsequenceCascadeStore(tmp_path / "consequence_cascades")
    store.save("cascade-1", _record("cascade-1", "session-1"))
    store.save("cascade-2", _record("cascade-2", "session-2"))
    (tmp_path / "consequence_cascades" / "broken.json").write_text("{broken", encoding="utf-8")

    rows = store.load_for_session("session-1")

    assert [row["cascade_id"] for row in rows] == ["cascade-1"]
