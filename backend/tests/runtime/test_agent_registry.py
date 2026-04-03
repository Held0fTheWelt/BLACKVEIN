"""Tests for C1 canonical agent registry."""

from app.runtime.agent_registry import AgentConfig, AgentRegistry, build_default_agent_registry


def test_default_registry_exposes_enabled_agents():
    registry = build_default_agent_registry()

    enabled_ids = {agent.agent_id for agent in registry.enabled_agents()}

    assert "scene_reader" in enabled_ids
    assert "trigger_analyst" in enabled_ids
    assert "delta_planner" in enabled_ids
    assert "dialogue_planner" in enabled_ids
    assert "finalizer" in enabled_ids


def test_registry_rejects_unknown_agent():
    registry = build_default_agent_registry()

    try:
        registry.require_enabled("unknown_agent")
        assert False, "expected ValueError for unknown agent"
    except ValueError as exc:
        assert "Unknown agent_id" in str(exc)


def test_registry_rejects_disabled_agent():
    registry = AgentRegistry(
        agents=[
            AgentConfig(
                agent_id="scene_reader",
                role="scene_reader",
                enabled=False,
                status="disabled",
            )
        ]
    )

    try:
        registry.require_enabled("scene_reader")
        assert False, "expected ValueError for disabled agent"
    except ValueError as exc:
        assert "disabled" in str(exc).lower()


def test_registry_exposes_model_selection_and_tool_policy():
    registry = build_default_agent_registry()

    agent = registry.require_enabled("delta_planner")

    assert agent.model_selection.model_profile == "default"
    assert "wos.guard.preview_delta" in agent.allowed_tools
    assert agent.budget_profile.max_tool_calls >= 1
