from __future__ import annotations

import json

from app.story_runtime.branching_tree_store import JsonBranchingTreeStore


def _record(tree_id: str, session_id: str = "session-1") -> dict:
    return {
        "schema_version": "branching_tree_record.v1",
        "tree_id": tree_id,
        "story_session_id": session_id,
        "status": "simulated",
        "created_at": "2026-05-15T00:00:00+00:00",
        "updated_at": "2026-05-15T00:00:00+00:00",
    }


def test_branching_tree_store_roundtrips_json(tmp_path) -> None:
    store = JsonBranchingTreeStore(tmp_path / "branching_trees")
    store.save("tree-1", _record("tree-1"))

    loaded = store.load("tree-1")

    assert loaded["tree_id"] == "tree-1"
    assert loaded["story_session_id"] == "session-1"
    assert not list((tmp_path / "branching_trees").glob("*.tmp"))
    raw = json.loads((tmp_path / "branching_trees" / "tree-1.json").read_text(encoding="utf-8"))
    assert raw["schema_version"] == "branching_tree_record.v1"


def test_branching_tree_store_filters_by_session_and_skips_corrupt_files(tmp_path) -> None:
    store = JsonBranchingTreeStore(tmp_path / "branching_trees")
    store.save("tree-1", _record("tree-1", "session-1"))
    store.save("tree-2", _record("tree-2", "session-2"))
    (tmp_path / "branching_trees" / "broken.json").write_text("{broken", encoding="utf-8")

    rows = store.load_for_session("session-1")

    assert [row["tree_id"] for row in rows] == ["tree-1"]
