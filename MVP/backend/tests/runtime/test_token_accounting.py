"""Focused token accounting tests for C2 follow-up exact/proxy behavior."""

from __future__ import annotations

from typing import Any

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.supervisor_orchestrator import SupervisorOrchestrator


class TokenAccountingAdapter(StoryAIAdapter):
    """Adapter that can emit exact usage selectively by agent id."""

    def __init__(self, *, exact_agents: set[str]) -> None:
        self.exact_agents = exact_agents

    @property
    def adapter_name(self) -> str:
        return "token-accounting-adapter"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        agent_id = (request.metadata.get("agent_invocation") or {}).get("agent_id", "unknown")
        if agent_id == "finalizer":
            payload = dict(request.metadata.get("supervisor_merge_payload") or {})
            payload["rationale"] = "finalized"
        else:
            payload = {
                "scene_interpretation": f"{agent_id} summary",
                "detected_triggers": [],
                "proposed_state_deltas": [],
                "rationale": f"{agent_id} rationale",
            }

        metadata: dict[str, Any] = {}
        if agent_id in self.exact_agents:
            metadata = {
                "provider_name": "provider-x",
                "model_name": "model-y",
                "usage": {
                    "input_tokens": 8,
                    "output_tokens": 4,
                    "total_tokens": 12,
                },
            }
        return AdapterResponse(raw_output=f"{agent_id} output", structured_payload=payload, backend_metadata=metadata)


def _base_request(session: Any) -> AdapterRequest:
    return AdapterRequest(
        session_id=session.session_id,
        turn_number=session.turn_counter + 1,
        current_scene_id=session.current_scene_id,
        canonical_state=session.canonical_state,
        recent_events=[],
        operator_input="token accounting test",
        request_role_structured_output=True,
        metadata={},
    )


def test_exact_accounting_tracks_turn_and_agent_token_usage(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    orchestrator = SupervisorOrchestrator()
    adapter = TokenAccountingAdapter(
        exact_agents={"scene_reader", "trigger_analyst", "delta_planner", "dialogue_planner", "finalizer"}
    )

    outcome = orchestrator.orchestrate(
        base_request=_base_request(session),
        adapter=adapter,
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    consumed = outcome.budget_summary["consumed"]
    assert consumed["token_usage_mode"] == "exact"
    assert consumed["proxy_fallback_count"] == 0
    assert consumed["consumed_total_tokens"] == 60
    assert all(inv.token_usage is not None for inv in outcome.invocations)


def test_mixed_accounting_reports_proxy_fallback_count(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    orchestrator = SupervisorOrchestrator()
    adapter = TokenAccountingAdapter(exact_agents={"scene_reader", "finalizer"})

    outcome = orchestrator.orchestrate(
        base_request=_base_request(session),
        adapter=adapter,
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    consumed = outcome.budget_summary["consumed"]
    assert consumed["token_usage_mode"] == "mixed"
    assert consumed["proxy_fallback_count"] >= 1


def test_proxy_mode_stays_compatible_when_no_exact_usage(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    orchestrator = SupervisorOrchestrator()
    adapter = TokenAccountingAdapter(exact_agents=set())

    outcome = orchestrator.orchestrate(
        base_request=_base_request(session),
        adapter=adapter,
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    consumed = outcome.budget_summary["consumed"]
    assert consumed["token_usage_mode"] == "proxy"
    assert consumed["proxy_fallback_count"] == len(outcome.invocations)
    assert consumed["consumed_total_tokens"] == consumed["token_proxy_units"]
