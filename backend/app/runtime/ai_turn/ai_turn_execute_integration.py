"""Integration: vollständiger AI-Turn-Pfad (Pre-Adapter → Routing/Gen → Tool-Loop → Parse-Pipeline)."""

from __future__ import annotations

from typing import Any

from app.content.module_models import ContentModule
from app.runtime.ai_adapter import StoryAIAdapter
from app.runtime.ai_turn.ai_turn_execute_integration_phases import (
    run_after_first_response_tail,
    run_routing_and_first_response_phase,
)
from app.runtime.ai_turn.ai_turn_pre_adapter import build_ai_turn_pre_adapter_state
from app.runtime.runtime_models import SessionState
from app.runtime.turn.turn_execution_types import TurnExecutionResult


async def run_execute_turn_with_ai_integration(
    session: SessionState,
    current_turn: int,
    adapter: StoryAIAdapter,
    module: ContentModule,
    *,
    operator_input: str = "",
    recent_events: list[dict[str, Any]] | None = None,
    preview_diagnostics_before_parse: dict[str, Any] | None = None,
) -> TurnExecutionResult:
    from app.observability.langfuse_adapter import get_langfuse_adapter

    lf_adapter = get_langfuse_adapter()
    lf_trace = None

    try:
        # Start Langfuse trace for this turn execution
        try:
            lf_trace = lf_adapter.start_trace(
                name="turn_execution",
                session_id=session.session_id,
                module_id=session.module_id,
                turn_id=str(current_turn),
                metadata={"adapter_name": session.adapter_name, "scene_id": session.current_scene_id},
            )
        except Exception:
            pass  # Langfuse errors never break the main flow

        pa = build_ai_turn_pre_adapter_state(session)
        routing = run_routing_and_first_response_phase(
            session=session,
            current_turn=current_turn,
            module=module,
            operator_input=operator_input,
            recent_events=recent_events,
            pa=pa,
            adapter=adapter,
            preview_diagnostics_before_parse=preview_diagnostics_before_parse,
        )
        result = await run_after_first_response_tail(
            session=session,
            current_turn=current_turn,
            module=module,
            recent_events=recent_events,
            pa=pa,
            routing=routing,
        )

        # Record generation completion
        if lf_trace and routing.fa and routing.fa.outcome and routing.fa.outcome.call_result:
            try:
                call_result = routing.fa.outcome.call_result
                narrative_text = result.decision.narrative_text if result.decision else ""
                lf_adapter.record_generation(
                    name="story_turn_generation",
                    model=session.adapter_name,
                    provider=session.adapter_name,
                    prompt=operator_input[:2000] if operator_input else "",
                    completion=narrative_text[:2000] if narrative_text else "",
                    tokens_prompt=call_result.metadata.get("prompt_tokens") if call_result.metadata else None,
                    tokens_completion=call_result.metadata.get("completion_tokens") if call_result.metadata else None,
                    metadata={
                        "turn": current_turn,
                        "scene_id": session.current_scene_id,
                        "execution_status": result.execution_status,
                    },
                    trace=lf_trace,
                )
            except Exception:
                pass  # Langfuse errors never break the main flow

        return result
    finally:
        # End trace
        if lf_trace:
            try:
                lf_adapter.end_trace(lf_trace)
            except Exception:
                pass
