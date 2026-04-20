"""Canonical agent registry for bounded supervisor orchestration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AgentBudgetProfile(BaseModel):
    """Bounded execution limits for one subagent invocation."""

    max_attempts: int = 1
    max_tool_calls: int = 1
    per_tool_timeout_ms: int = 1500
    max_retries_per_tool_call: int = 0
    max_agent_duration_ms: int = 3000
    max_agent_tokens: int = 0


class SupervisorTurnPolicy(BaseModel):
    """Bounded policy controls shared across one orchestrated turn."""

    max_turn_duration_ms: int = 12000
    max_total_agent_calls: int = 8
    max_total_tool_calls: int = 8
    max_total_tokens: int = 0
    max_failed_agent_calls: int = 2
    max_degraded_steps: int = 3
    skip_optional_agents_under_pressure: bool = True
    continue_after_optional_failure: bool = True
    allow_finalizer_fallback: bool = True
    consume_budget_on_failed_tool_call: bool = True


class AgentModelSelection(BaseModel):
    """Model/profile selection metadata for one agent."""

    adapter_name: str | None = None
    model_profile: str = "default"


class AgentConfig(BaseModel):
    """Runtime-usable canonical agent definition."""

    agent_id: str
    role: str
    enabled: bool = True
    allowed_tools: list[str] = Field(default_factory=list)
    model_selection: AgentModelSelection = Field(default_factory=AgentModelSelection)
    budget_profile: AgentBudgetProfile = Field(default_factory=AgentBudgetProfile)
    execution_mode: Literal["sequential"] = "sequential"
    participation: Literal["required", "optional"] = "required"
    description: str = ""
    status: Literal["enabled", "disabled"] = "enabled"

    def is_enabled(self) -> bool:
        return self.enabled and self.status == "enabled"


class AgentRegistry:
    """Deterministic in-process agent registry."""

    def __init__(
        self,
        agents: list[AgentConfig],
        *,
        supervisor_policy: SupervisorTurnPolicy | None = None,
    ):
        by_id: dict[str, AgentConfig] = {}
        for config in agents:
            by_id[config.agent_id] = config
        self._agents = by_id
        self.supervisor_policy = supervisor_policy or SupervisorTurnPolicy()

    def get(self, agent_id: str) -> AgentConfig | None:
        return self._agents.get(agent_id)

    def require_enabled(self, agent_id: str) -> AgentConfig:
        agent = self.get(agent_id)
        if agent is None:
            raise ValueError(f"Unknown agent_id: {agent_id}")
        if not agent.is_enabled():
            raise ValueError(f"Agent is disabled: {agent_id}")
        return agent

    def enabled_agents(self) -> list[AgentConfig]:
        return [agent for agent in self._agents.values() if agent.is_enabled()]

    def all_agents(self) -> list[AgentConfig]:
        return list(self._agents.values())


def build_default_agent_registry() -> AgentRegistry:
    """Build the initial C1 agent set."""
    return AgentRegistry(
        agents=[
            AgentConfig(
                agent_id="scene_reader",
                role="scene_reader",
                description="Reads the current scene and recent context.",
                allowed_tools=[
                    "wos.read.current_scene",
                    "wos.read.recent_history",
                ],
                budget_profile=AgentBudgetProfile(max_attempts=1, max_tool_calls=1),
            ),
            AgentConfig(
                agent_id="trigger_analyst",
                role="trigger_analyst",
                description="Analyzes trigger candidates and narrative tensions.",
                allowed_tools=[
                    "wos.read.allowed_actions",
                    "wos.read.recent_history",
                ],
                budget_profile=AgentBudgetProfile(max_attempts=1, max_tool_calls=1),
            ),
            AgentConfig(
                agent_id="delta_planner",
                role="delta_planner",
                description="Plans bounded state deltas using available evidence.",
                allowed_tools=[
                    "wos.guard.preview_delta",
                    "wos.read.allowed_actions",
                ],
                budget_profile=AgentBudgetProfile(
                    max_attempts=1,
                    max_tool_calls=2,
                    per_tool_timeout_ms=1800,
                ),
            ),
            AgentConfig(
                agent_id="dialogue_planner",
                role="dialogue_planner",
                description="Prepares dialogue and response framing hints.",
                allowed_tools=[],
                budget_profile=AgentBudgetProfile(max_attempts=1, max_tool_calls=0),
                participation="optional",
            ),
            AgentConfig(
                agent_id="finalizer",
                role="finalizer",
                description="Produces the final canonical decision payload.",
                allowed_tools=[],
                budget_profile=AgentBudgetProfile(max_attempts=1, max_tool_calls=0),
            ),
        ]
    )
