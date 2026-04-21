"""Strict live governance: fail-closed posture without silent default-registry fallback."""

from __future__ import annotations

import pytest

from app.story_runtime import StoryRuntimeManager
from app.story_runtime.live_governance import LiveStoryGovernanceError, is_governed_resolved_config_operational


def _minimal_governed_config() -> dict:
    return {
        "config_version": "cfg_test_fixture",
        "generation_execution_mode": "mock_only",
        "providers": [{"provider_id": "mock_default", "provider_type": "mock"}],
        "models": [
            {
                "model_id": "mock_deterministic",
                "provider_id": "mock_default",
                "model_name": "mock-deterministic",
                "model_role": "mock",
                "timeout_seconds": 5,
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


def test_is_governed_resolved_config_operational_requires_config_version() -> None:
    cfg = _minimal_governed_config()
    assert is_governed_resolved_config_operational(cfg) is True
    cfg_bad = {**cfg, "config_version": ""}
    assert is_governed_resolved_config_operational(cfg_bad) is False


def test_strict_mode_blocks_default_registry_without_allow_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOS_ALLOW_UNGOVERNED_STORY_RUNTIME", "0")
    mgr = StoryRuntimeManager(session_store=None, governed_runtime_config=None)
    assert mgr.runtime_config_status().get("live_execution_blocked") is True
    assert mgr.runtime_config_status().get("governed_runtime_active") is False
    with pytest.raises(LiveStoryGovernanceError):
        mgr._assert_live_player_governance()


def test_governed_config_enables_live_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOS_ALLOW_UNGOVERNED_STORY_RUNTIME", "0")
    cfg = _minimal_governed_config()
    mgr = StoryRuntimeManager(session_store=None, governed_runtime_config=cfg)
    st = mgr.runtime_config_status()
    assert st.get("governed_runtime_active") is True
    assert st.get("live_execution_blocked") is False
    mgr._assert_live_player_governance()


def test_reload_config_returns_ok_false_when_fetch_returns_none(client, internal_api_key, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WOS_ALLOW_UNGOVERNED_STORY_RUNTIME", "0")

    def _boom(**_kwargs):
        return None

    monkeypatch.setattr("app.runtime.runtime_config_client.fetch_resolved_runtime_config", _boom)
    r = client.post(
        "/api/internal/story/runtime/reload-config",
        headers={"X-Play-Service-Key": internal_api_key},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is False
    assert body.get("runtime_config_status", {}).get("live_execution_blocked") is True
