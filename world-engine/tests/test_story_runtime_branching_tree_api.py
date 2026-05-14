from __future__ import annotations

from typing import Any


def _headers(internal_api_key: str) -> dict[str, str]:
    return {"X-Play-Service-Key": internal_api_key}


class _BranchingTreeApiStub:
    def __init__(self) -> None:
        self.created: dict[str, Any] | None = None

    def create_branching_tree(self, **kwargs: Any) -> dict[str, Any]:
        self.created = dict(kwargs)
        return {
            "schema_version": "branching_tree_record.v1",
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
    assert created.json()["branching_tree"]["schema_version"] == "branching_tree_record.v1"
    assert stub.created["max_depth"] == 1

    listed = client.get("/api/story/sessions/session-api/branching/trees", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["branching_trees"][0]["tree_id"] == "branch_tree_api"

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
