"""StoryRuntimeManager W5 player-shell projection wiring tests (Phase 5A)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from app.story_runtime.manager import StoryRuntimeManager, StorySession


def _fact(
    fact_id: str,
    *,
    actor_id: str,
    dim: str,
    key: str,
    value: Any,
    source: str = "committed_action",
    truth: str = "observed",
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
        "source_event_id": "ct_003",
        "truth_level": truth,
        "confidence": 1.0,
        "valid_from_turn": 3,
        "valid_until_turn": None,
        "last_confirmed_turn": 3,
        "visibility": visibility,
        "actor_knowledge_scope": [],
        "status": "active",
        "superseded_by_fact_id": None,
        "contradicted_by_fact_id": None,
    }


def _snapshot(location: str = "salon_w5") -> dict[str, Any]:
    return {
        "schema_version": "w5_snapshot.v1",
        "snapshot_id": "w5s_player_shell_003",
        "story_session_id": "sess_player_view",
        "turn_number": 3,
        "actors": {
            "annette": {
                "actor_id": "annette",
                "actor_type": "human",
                "actor_role_in_scene": "player",
                "involvement_type": "primary",
                "where": [
                    _fact(
                        "w5f_where_annette",
                        actor_id="annette",
                        dim="where",
                        key="scene_location",
                        value=location,
                        source="participant_state_move",
                    )
                ],
                "what": [
                    _fact(
                        "w5f_what_annette",
                        actor_id="annette",
                        dim="what",
                        key="current_action",
                        value="listens",
                    )
                ],
                "how": [
                    _fact(
                        "w5f_how_annette",
                        actor_id="annette",
                        dim="how",
                        key="tone",
                        value="strained",
                    )
                ],
                "why": [
                    _fact(
                        "w5f_why_annette",
                        actor_id="annette",
                        dim="why",
                        key="motive",
                        value="keep_the_peace",
                        source="character_mind_record",
                        truth="inferred",
                        visibility="private_to_actor",
                    )
                ],
                "freshness_status": "fresh",
                "last_confirmed_turn": 3,
            }
        },
        "conflicts": [],
        "derived_from_event_ids": ["ct_003"],
        "created_at": "w5:turn:3",
    }


def _session(*, w5_latest: dict[str, Any] | None) -> StorySession:
    return StorySession(
        session_id="sess_player_view",
        module_id="god_of_carnage",
        runtime_projection={"human_actor_id": "annette"},
        created_at=datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 20, 12, 0, 5, tzinfo=timezone.utc),
        turn_counter=3,
        current_scene_id="opening",
        environment_state={"current_room_id": "fallback_salon"},
        runtime_world={"status": "initialized", "current_room_id": "fallback_salon"},
        w5_latest_snapshot=w5_latest,
    )


def _state(session: StorySession) -> dict[str, Any]:
    class _Proxy:
        _runtime_world_summary = staticmethod(StoryRuntimeManager._runtime_world_summary)

        def __init__(self, story_session: StorySession) -> None:
            self.story_session = story_session

        def get_session(self, session_id: str) -> StorySession:
            assert session_id == self.story_session.session_id
            return self.story_session

        def get_callback_web(self, *, session_id: str) -> dict[str, Any]:
            raise RuntimeError("not needed for this test")

        def get_consequence_cascade(self, *, session_id: str) -> dict[str, Any]:
            raise RuntimeError("not needed for this test")

    return StoryRuntimeManager.get_state(_Proxy(session), session.session_id)  # type: ignore[arg-type]


def test_player_view_flag_disabled_leaves_state_without_w5_player_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("W5_AST_FRONTEND_PLAYER_VIEW_ENABLED", raising=False)
    state = _state(_session(w5_latest=_snapshot()))
    assert "w5_player_view" not in state
    assert "w5_player_view" not in state["committed_state"]
    assert state["runtime_world"]["current_room_id"] == "fallback_salon"


def test_player_view_flag_enabled_adds_w5_projection_and_derives_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("W5_AST_FRONTEND_PLAYER_VIEW_ENABLED", "true")
    state = _state(_session(w5_latest=_snapshot("salon_w5")))
    view = state["w5_player_view"]
    assert view["target_consumer"] == "player_shell"
    assert view["actor_id"] == "annette"
    assert view["where_summary"]["current_visible_location"] == "salon_w5"
    assert view["how_summary"]["facts"]["tone"] == "strained"
    assert "tone" not in view["what_summary"]["facts"]
    assert view["truth_attribution"]["why_summary.facts.motive"] == "inferred"
    diag = state["w5_player_view_diagnostics"]
    assert diag["w5_player_view_used"] is True
    assert diag["w5_player_view_source"] == "w5_projection"
    assert diag["current_room_source"] == "w5_player_view"
    assert diag["w5_player_view_has_how"] is True
    assert diag["w5_player_view_has_inferred_why"] is True
    assert state["committed_state"]["w5_player_view"]["where_summary"]["scene_location"]["value"] == "salon_w5"


def test_player_view_malformed_snapshot_falls_back_to_fallback_current_room(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("W5_AST_FRONTEND_PLAYER_VIEW_ENABLED", "true")
    state = _state(_session(w5_latest={"schema_version": "w5_snapshot.v1", "bad": "shape"}))
    assert "w5_player_view" in state
    assert state["w5_player_view"] is None
    diag = state["w5_player_view_diagnostics"]
    assert diag["w5_player_view_used"] is False
    assert diag["w5_player_view_source"] == "fallback"
    assert diag["current_room_source"] == "fallback_current_room"
    assert diag["fallback_current_room_id"] == "fallback_salon"
