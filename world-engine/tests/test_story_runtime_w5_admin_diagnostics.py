"""Story-runtime W5 admin diagnostics surface tests (Phase 4B)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.story_runtime.manager import StoryRuntimeManager, StorySession


def _fact(actor_id: str, dim: str, key: str, value: Any, truth: str = "observed") -> dict[str, Any]:
    return {
        "schema_version": "w5_fact.v1",
        "fact_id": f"f_{actor_id}_{dim}_{key}",
        "actor_id": actor_id,
        "dimension": dim,
        "key": key,
        "value": value,
        "source": "committed_action" if dim != "where" else "participant_state_move",
        "source_event_id": "ct_004",
        "truth_level": truth,
        "confidence": 1.0,
        "valid_from_turn": 4,
        "valid_until_turn": None,
        "last_confirmed_turn": 4,
        "visibility": "public" if dim != "why" else "private_to_actor",
        "actor_knowledge_scope": [],
        "status": "active",
        "superseded_by_fact_id": None,
        "contradicted_by_fact_id": None,
    }


def _snapshot() -> dict[str, Any]:
    return {
        "schema_version": "w5_snapshot.v1",
        "snapshot_id": "w5s_runtime_admin",
        "story_session_id": "sess_runtime_admin",
        "turn_number": 4,
        "actors": {
            "michel": {
                "actor_id": "michel",
                "actor_type": "npc",
                "actor_role_in_scene": "mediator",
                "involvement_type": "primary",
                "where": [_fact("michel", "where", "scene_location", "study")],
                "what": [_fact("michel", "what", "current_action", "listens")],
                "how": [_fact("michel", "how", "tone", "dry")],
                "why": [_fact("michel", "why", "motive", "avoid_blame", truth="inferred")],
                "freshness_status": "fresh",
                "last_confirmed_turn": 4,
            }
        },
        "conflicts": [
            {
                "conflict_id": "conf_michel_where",
                "actor_id": "michel",
                "dimension": "where",
                "competing_fact_ids": ["f_michel_where_scene_location"],
                "resolution_status": "unresolved",
                "resolver_source": None,
            }
        ],
        "derived_from_event_ids": ["ct_004"],
        "created_at": "w5:turn:4",
    }


class _Proxy:
    _latest_w5_validation_outcome = staticmethod(
        StoryRuntimeManager._latest_w5_validation_outcome
    )

    def __init__(self, session: StorySession) -> None:
        self._session = session

    def get_session(self, session_id: str) -> StorySession:
        assert session_id == self._session.session_id
        return self._session


def _session(*, malformed: bool = False) -> StorySession:
    validation_outcome = {
        "status": "rejected",
        "w5_validation": {
            "w5_validation_enabled": True,
            "w5_validation_ran": True,
            "w5_validation_failed": True,
            "w5_validation_failure_codes": ["w5_actor_not_present"],
            "w5_snapshot_id": "w5s_runtime_admin",
            "w5_validation_source": "w5_snapshot",
        },
    }
    snapshot = {"bad": "snapshot"} if malformed else _snapshot()
    return StorySession(
        session_id="sess_runtime_admin",
        module_id="god_of_carnage",
        runtime_projection={"human_actor_id": "annette", "npc_actor_ids": ["michel"]},
        created_at=datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 20, 12, 0, 5, tzinfo=timezone.utc),
        turn_counter=4,
        current_scene_id="opening",
        diagnostics=[{"turn_number": 4, "validation_outcome": validation_outcome}],
        w5_history=[snapshot],
        w5_latest_snapshot=snapshot,
    )


def test_story_runtime_w5_admin_views_are_read_only_and_semantic() -> None:
    proxy = _Proxy(_session())
    snapshot = StoryRuntimeManager.get_w5_admin_snapshot(proxy, "sess_runtime_admin")
    assert snapshot["snapshot_id"] == "w5s_runtime_admin"
    assert snapshot["stats"]["has_how"] is True
    assert snapshot["actor_summaries"]["michel"]["how"]["value"] == "dry"
    assert snapshot["raw_w5_history_exposed"] is False

    actor = StoryRuntimeManager.get_w5_admin_actor(proxy, "sess_runtime_admin", "michel")
    assert actor["dimensions"]["where"]["facts"][0]["value"] == "study"
    assert actor["dimensions"]["what"]["facts"][0]["value"] == "listens"
    assert actor["dimensions"]["how"]["facts"][0]["key"] == "tone"
    assert actor["dimensions"]["why"]["facts"][0]["truth_level"] == "inferred"
    assert actor["read_only"] is True

    conflicts = StoryRuntimeManager.get_w5_admin_conflicts(proxy, "sess_runtime_admin")
    assert conflicts["unresolved_count"] == 1
    assert conflicts["conflicts"][0]["resolution_status"] == "unresolved"


def test_story_runtime_projection_previews_and_validation_use_typed_builders() -> None:
    proxy = _Proxy(_session())
    narrator = StoryRuntimeManager.get_w5_admin_narrator_projection(proxy, "sess_runtime_admin", actor_id="michel")
    assert narrator["projection"]["target_consumer"] == "narrator"
    assert narrator["projection"]["how_summary"]["facts"]["tone"] == "dry"
    assert narrator["projection"]["truth_attribution"]["why_summary.facts.motive"] == "inferred"

    npc = StoryRuntimeManager.get_w5_admin_npc_projection(proxy, "sess_runtime_admin", "michel")
    assert npc["projection"]["target_consumer"] == "npc"
    assert npc["projection"]["actor_id"] == "michel"
    assert npc["projection"]["why_summary"]["facts"]["motive"] == "avoid_blame"

    validation = StoryRuntimeManager.get_w5_admin_validation(proxy, "sess_runtime_admin")
    assert validation["validation"]["w5_validation_ran"] is True
    assert validation["validation"]["w5_validation_failure_codes"] == ["w5_actor_not_present"]

    metadata = StoryRuntimeManager.get_w5_runtime_metadata(proxy, "sess_runtime_admin")
    assert metadata["w5_snapshot_id"] == "w5s_runtime_admin"
    assert metadata["w5_actor_count"] == 1
    assert metadata["w5_conflict_count"] == 1
    assert metadata["w5_has_how"] is True


def test_story_runtime_w5_admin_views_handle_malformed_snapshot_without_500() -> None:
    proxy = _Proxy(_session(malformed=True))
    view = StoryRuntimeManager.get_w5_admin_snapshot(proxy, "sess_runtime_admin")
    assert view["status"] == "unavailable"
    assert view["diagnostic"]["safe_empty"] is True
    validation = StoryRuntimeManager.get_w5_admin_validation(proxy, "sess_runtime_admin")
    assert validation["status"] == "unavailable"
    assert validation["validation"]["w5_validation_fallback_reason"]
