"""Extra coverage for ai_turn_executor branches (MCP, policy fallback, restore, role path)."""

import asyncio
from unittest.mock import MagicMock, patch

from app.runtime.ai_failure_recovery import RestorePolicy
from app.runtime.ai_turn_executor import execute_turn_with_ai
from app.runtime.w2_models import ExecutionFailureReason, GuardOutcome
from tests.runtime.test_ai_turn_executor import DeterministicAIAdapter, VALID_PAYLOAD


def test_mcp_enrichment_attaches_to_adapter_request(
    god_of_carnage_module, god_of_carnage_module_with_state
):
    """When mcp_enrichment_enabled, build_mcp_enrichment result is stored on request metadata."""
    session = god_of_carnage_module_with_state
    session.metadata["mcp_enrichment_enabled"] = True
    session.metadata["_mcp_client_override"] = MagicMock()

    captured = {}

    class CaptureAdapter(DeterministicAIAdapter):
        def generate(self, request):
            captured["metadata_keys"] = list((request.metadata or {}).keys())
            return super().generate(request)

    adapter = CaptureAdapter(payload=VALID_PAYLOAD)

    with patch(
        "app.mcp_client.enrichment.build_mcp_enrichment",
        return_value={"enriched": True},
    ):
        with patch(
            "app.observability.trace.get_trace_id",
            return_value="trace-test",
        ):
            asyncio.run(
                execute_turn_with_ai(
                    session,
                    current_turn=session.turn_counter + 1,
                    adapter=adapter,
                    module=god_of_carnage_module,
                )
            )

    assert "mcp_context_enrichment" in captured.get("metadata_keys", [])


def test_invalid_action_type_triggers_policy_fallback(
    god_of_carnage_module, god_of_carnage_module_with_state
):
    """Unknown delta_type fails validate_action_type and activates fallback responder path."""
    session = god_of_carnage_module_with_state
    payload = {
        "scene_interpretation": "Scene",
        "detected_triggers": [],
        "proposed_state_deltas": [
            {
                "target_path": "characters.veronique.emotional_state",
                "next_value": 50,
                "delta_type": "__not_a_real_action_type__",
                "rationale": "bad type",
            }
        ],
        "rationale": "root",
    }
    adapter = DeterministicAIAdapter(payload=payload)

    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=adapter,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "success"
    assert result.failure_reason == ExecutionFailureReason.VALIDATION_ERROR
    assert len(result.accepted_deltas) == 0


def test_role_structured_payload_uses_responder_gate(
    god_of_carnage_module, god_of_carnage_module_with_state
):
    """Role-structured adapter output flows through process_role_structured_decision."""
    session = god_of_carnage_module_with_state
    if "characters" not in session.canonical_state:
        session.canonical_state["characters"] = {}
    session.canonical_state["characters"].setdefault("veronique", {})["emotional_state"] = 40

    role_payload = {
        "interpreter": {
            "scene_reading": "Reading",
            "detected_tensions": [],
            "trigger_candidates": [],
        },
        "director": {
            "conflict_steering": "Steer",
            "escalation_level": 3,
            "recommended_direction": "hold",
        },
        "responder": {
            "response_impulses": [],
            "state_change_candidates": [
                {
                    "target_path": "characters.veronique.emotional_state",
                    "proposed_value": 55,
                    "rationale": "shift",
                }
            ],
            "trigger_assertions": [],
            "scene_transition_candidate": None,
        },
    }
    adapter = DeterministicAIAdapter(payload=role_payload)

    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=adapter,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "success"
    assert result.guard_outcome in (
        GuardOutcome.ACCEPTED,
        GuardOutcome.REJECTED,
        GuardOutcome.PARTIALLY_ACCEPTED,
    )


def test_restore_apply_raises_valueerror_then_safe_turn(
    god_of_carnage_module, god_of_carnage_module_with_state
):
    """ValueError from RestorePolicy.apply_restore falls through to safe-turn path."""
    session = god_of_carnage_module_with_state
    initial = session.canonical_state.copy()
    adapter = DeterministicAIAdapter(error="fail")

    with patch.object(
        RestorePolicy,
        "apply_restore",
        side_effect=ValueError("snapshot invalid"),
    ):
        result = asyncio.run(
            execute_turn_with_ai(
                session,
                current_turn=session.turn_counter + 1,
                adapter=adapter,
                module=god_of_carnage_module,
            )
        )

    assert result.execution_status == "success"
    assert result.updated_canonical_state == initial
    assert result.failure_reason == ExecutionFailureReason.GENERATION_ERROR
