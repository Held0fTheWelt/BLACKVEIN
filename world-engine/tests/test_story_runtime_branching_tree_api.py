from __future__ import annotations

from typing import Any

from story_runtime_core.branching import (
    BRANCHING_TIMELINE_EVENT_TREE_CREATED,
    BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION,
    BRANCHING_TIMELINE_STATUS_ACTIVE,
    BRANCHING_TIMELINE_STATUS_ARCHIVED,
    BRANCHING_TREE_RECORD_SCHEMA_VERSION,
)


def _headers(internal_api_key: str) -> dict[str, str]:
    return {"X-Play-Service-Key": internal_api_key}


class _BranchingTreeApiStub:
    def __init__(self) -> None:
        self.created: dict[str, Any] | None = None

    def create_branching_tree(self, **kwargs: Any) -> dict[str, Any]:
        self.created = dict(kwargs)
        return {
            "schema_version": BRANCHING_TREE_RECORD_SCHEMA_VERSION,
            "tree_id": "branch_tree_api",
            "story_session_id": kwargs["session_id"],
            "status": "simulated",
            "selectable_node_ids": ["node-api"],
        }

    def list_branching_trees(self, *, session_id: str) -> list[dict[str, Any]]:
        return [{"tree_id": "branch_tree_api", "story_session_id": session_id, "status": "simulated"}]

    def get_branching_tree(self, *, session_id: str, tree_id: str) -> dict[str, Any]:
        return {"tree_id": tree_id, "story_session_id": session_id, "status": "simulated"}

    def select_branching_tree_node(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "session_id": kwargs["session_id"],
            "tree_id": kwargs["tree_id"],
            "selection": {
                "schema_version": "branching_tree_selection.v1",
                "status": "committed",
                "selected_node_id": kwargs["node_id"],
            },
            "committed_events": [],
            "branching_tree": {"tree_id": kwargs["tree_id"], "status": "committed"},
        }

    def expire_branching_tree(self, *, session_id: str, tree_id: str, reason: str) -> dict[str, Any]:
        return {
            "tree_id": tree_id,
            "story_session_id": session_id,
            "status": "expired",
            "stale_reason": reason,
        }

    def get_branch_timeline(self, *, session_id: str) -> dict[str, Any]:
        return {
            "schema_version": BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION,
            "timeline_id": "branch_timeline_api",
            "story_session_id": session_id,
            "status": BRANCHING_TIMELINE_STATUS_ACTIVE,
            "events": [
                {
                    "event_type": BRANCHING_TIMELINE_EVENT_TREE_CREATED,
                    "tree_id": "branch_tree_api",
                }
            ],
            "snapshot": {"event_count": 1},
        }

    def list_branch_timeline_events(self, *, session_id: str) -> list[dict[str, Any]]:
        return self.get_branch_timeline(session_id=session_id)["events"]

    def compact_branch_timeline(self, *, session_id: str) -> dict[str, Any]:
        timeline = self.get_branch_timeline(session_id=session_id)
        timeline["snapshot"] = {"event_count": len(timeline["events"])}
        return timeline

    def archive_branch_timeline(self, *, session_id: str, reason: str) -> dict[str, Any]:
        timeline = self.get_branch_timeline(session_id=session_id)
        timeline["status"] = BRANCHING_TIMELINE_STATUS_ARCHIVED
        timeline["archive_reason"] = reason
        return timeline


def test_branching_tree_internal_api_surface(client, internal_api_key) -> None:
    stub = _BranchingTreeApiStub()
    client.app.state.story_manager = stub
    headers = _headers(internal_api_key)

    created = client.post(
        "/api/story/sessions/session-api/branching/trees",
        headers=headers,
        json={"max_depth": 1, "max_branching": 1},
    )
    assert created.status_code == 200
    assert created.json()["branching_tree"]["schema_version"] == BRANCHING_TREE_RECORD_SCHEMA_VERSION
    assert created.json()["branch_timeline"]["schema_version"] == BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION
    assert stub.created["max_depth"] == 1

    listed = client.get("/api/story/sessions/session-api/branching/trees", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["branching_trees"][0]["tree_id"] == "branch_tree_api"

    timeline = client.get("/api/story/sessions/session-api/branching/timeline", headers=headers)
    assert timeline.status_code == 200
    assert timeline.json()["branch_timeline"]["schema_version"] == BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION

    events = client.get("/api/story/sessions/session-api/branching/timeline/events", headers=headers)
    assert events.status_code == 200
    assert events.json()["branch_timeline_events"][0]["event_type"] == BRANCHING_TIMELINE_EVENT_TREE_CREATED

    compacted = client.post("/api/story/sessions/session-api/branching/timeline/compact", headers=headers)
    assert compacted.status_code == 200
    assert compacted.json()["branch_timeline"]["snapshot"]["event_count"] >= 1

    archived = client.post(
        "/api/story/sessions/session-api/branching/timeline/archive",
        headers=headers,
        json={"reason": "api_test"},
    )
    assert archived.status_code == 200
    assert archived.json()["branch_timeline"]["status"] == BRANCHING_TIMELINE_STATUS_ARCHIVED

    fetched = client.get(
        "/api/story/sessions/session-api/branching/trees/branch_tree_api",
        headers=headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["branching_tree"]["status"] == "simulated"

    selected = client.post(
        "/api/story/sessions/session-api/branching/trees/branch_tree_api/select",
        headers=headers,
        json={"node_id": "node-api"},
    )
    assert selected.status_code == 200
    assert selected.json()["selection"]["status"] == "committed"

    expired = client.post(
        "/api/story/sessions/session-api/branching/trees/branch_tree_api/expire",
        headers=headers,
        json={"reason": "test_expired"},
    )
    assert expired.status_code == 200
    assert expired.json()["branching_tree"]["status"] == "expired"
