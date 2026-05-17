from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock

from app.story_runtime import StoryRuntimeManager
from app.story_runtime.runtime_world import initialize_runtime_world
from app.story_runtime.story_session_store import JsonStorySessionStore


def _disable_langfuse(monkeypatch: Any) -> None:
    adapter = MagicMock()
    adapter.is_enabled.return_value = False
    adapter.is_ready = False
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )


def _governed_config_with_session_loop_logging(*, enabled: bool = True, level: str = "info") -> dict[str, Any]:
    return {
        "config_version": "cfg_session_loop_logging_test",
        "generation_execution_mode": "mock_only",
        "world_engine_settings": {
            "session_loop_logging": {
                "enabled": enabled,
                "level": level,
                "include_runtime_world_summary": True,
                "include_projection_summary": True,
                "include_diagnostic_summary": True,
            }
        },
        "providers": [{"provider_id": "mock_default", "provider_type": "mock"}],
        "models": [
            {
                "model_id": "mock_deterministic",
                "provider_id": "mock_default",
                "model_name": "mock-deterministic",
                "model_role": "mock",
                "timeout_seconds": 5,
                "structured_output_capable": True,
            }
        ],
        "routes": [
            {
                "route_id": "narrative_live_generation_global",
                "preferred_model_id": "mock_deterministic",
                "fallback_model_id": "mock_deterministic",
                "mock_model_id": "mock_deterministic",
            }
        ],
    }


def test_runtime_world_initializes_from_runtime_projection() -> None:
    runtime_world = initialize_runtime_world(
        module_id="test_module",
        runtime_projection={
            "module_id": "test_module",
            "start_scene_id": "salon",
            "rooms": [
                {
                    "id": "salon",
                    "name": "Salon",
                    "adjacent_room_ids": ["hallway"],
                },
                {"id": "hallway", "name": "Hallway"},
            ],
            "props": [
                {
                    "id": "window",
                    "room_id": "salon",
                    "affordances": ["look_at"],
                }
            ],
            "human_actor_id": "annette",
            "npc_actor_ids": ["alain"],
            "actor_lanes": {"annette": "human", "alain": "npc"},
        },
        environment_model={
            "module_id": "test_module",
            "locations": {},
            "objects": {},
            "transitions": [],
        },
        environment_state={},
    )

    assert runtime_world["status"] == "initialized"
    assert runtime_world["commands_enabled"] is False
    assert runtime_world["narration_arrangement_enabled"] is False
    assert runtime_world["current_room_id"] == "salon"
    assert set(runtime_world["rooms"]) >= {"salon", "hallway"}
    assert runtime_world["props"]["window"]["source_kind"] == "projection"
    assert runtime_world["actors"]["annette"]["lane"] == "human"
    assert runtime_world["actors"]["alain"]["lane"] == "npc"
    assert any(exit_["from_room_id"] == "salon" and exit_["to_room_id"] == "hallway" for exit_ in runtime_world["exits"].values())
    assert runtime_world["diagnostic_summary"]["diagnostic_count"] >= 1


def test_story_session_create_persists_runtime_world(tmp_path, monkeypatch) -> None:
    _disable_langfuse(monkeypatch)
    store = JsonStorySessionStore(tmp_path)
    manager = StoryRuntimeManager(session_store=store, adapters={})

    session = manager.create_session(
        module_id="test_module",
        runtime_projection={
            "module_id": "test_module",
            "start_scene_id": "salon",
            "rooms": [{"id": "salon"}],
            "props": [{"id": "window", "room_id": "salon"}],
            "human_actor_id": "player",
            "actor_lanes": {"player": "human"},
        },
    )

    assert session.runtime_world["status"] == "initialized"
    assert session.runtime_world["rooms"]["salon"]["id"] == "salon"
    assert session.runtime_world["props"]["window"]["room_id"] == "salon"
    assert session.diagnostics[-1]["event_type"] == "runtime_world_initialized"

    restored = StoryRuntimeManager(session_store=store, adapters={})
    restored_session = restored.get_session(session.session_id)
    assert restored_session.runtime_world["status"] == "initialized"
    assert "salon" in restored_session.runtime_world["rooms"]

    state = restored.get_state(session.session_id)
    assert state["runtime_world"]["status"] == "initialized"
    assert state["session_loop"]["status"] == "runtime_engine_initialized"
    assert state["session_loop"]["runtime_world"]["room_count"] == 1


def test_story_session_create_emits_governed_session_loop_log(tmp_path, monkeypatch, caplog) -> None:
    _disable_langfuse(monkeypatch)
    store = JsonStorySessionStore(tmp_path)
    manager = StoryRuntimeManager(
        session_store=store,
        adapters={},
        governed_runtime_config=_governed_config_with_session_loop_logging(),
    )
    caplog.set_level(logging.INFO, logger="app.story_runtime.manager")

    session = manager.create_session(
        module_id="test_module",
        runtime_projection={
            "module_id": "test_module",
            "start_scene_id": "salon",
            "rooms": [{"id": "salon"}],
            "props": [{"id": "window", "room_id": "salon"}],
            "human_actor_id": "player",
            "actor_lanes": {"player": "human"},
        },
    )

    policy = manager.runtime_config_status()["session_loop_logging"]
    assert policy["enabled"] is True
    assert policy["source"] == "governed_runtime_config.world_engine_settings.session_loop_logging"
    assert any(
        "story_session_loop_event" in record.message
        and '"event": "runtime_engine_initialized"' in record.message
        and session.session_id in record.message
        and '"room_count": 1' in record.message
        for record in caplog.records
    )


def test_story_session_create_respects_disabled_session_loop_log(tmp_path, monkeypatch, caplog) -> None:
    _disable_langfuse(monkeypatch)
    store = JsonStorySessionStore(tmp_path)
    manager = StoryRuntimeManager(
        session_store=store,
        adapters={},
        governed_runtime_config=_governed_config_with_session_loop_logging(enabled=False),
    )
    caplog.set_level(logging.INFO, logger="app.story_runtime.manager")

    manager.create_session(
        module_id="test_module",
        runtime_projection={
            "module_id": "test_module",
            "start_scene_id": "salon",
            "rooms": [{"id": "salon"}],
            "human_actor_id": "player",
            "actor_lanes": {"player": "human"},
        },
    )

    assert manager.runtime_config_status()["session_loop_logging"]["enabled"] is False
    assert not any("story_session_loop_event" in record.message for record in caplog.records)
