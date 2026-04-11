"""Writers Room workflow — model routing, preflight, synthesis, and generation (DS-002 stage 3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_stack import invoke_writers_room_adapter_with_langchain

from app.runtime.model_routing import route_model
from app.runtime.model_routing_contracts import (
    AdapterModelSpec,
    LatencyBudget,
    RoutingRequest,
    TaskKind,
    WorkflowPhase,
)
from app.runtime.model_routing_evidence import attach_stage_routing_evidence


def _norm_wr_adapter(name: str | None) -> str:
    return (name or "").strip().lower()


@dataclass(frozen=True)
class WritersRoomGenerationStageResult:
    """Bounded preflight + synthesis routing and primary/fallback model generation."""

    generation: dict[str, Any]


def run_writers_room_generation_stage(
    *,
    adapters: dict[str, Any],
    model_route_specs: list[AdapterModelSpec],
    module_id: str,
    focus: str,
    retrieval_text: str,
    evidence_tag: str,
) -> WritersRoomGenerationStageResult:
    """Route preflight and synthesis, invoke LangChain path or mock fallback; attach synthesis routing evidence."""
    specs = model_route_specs
    preflight_req = RoutingRequest(
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        requires_structured_output=False,
        latency_budget=LatencyBudget.strict,
    )
    pre_decision = route_model(preflight_req, specs=specs)
    preflight_trace: dict[str, Any] = {
        "stage": "preflight",
        "workflow_phase": WorkflowPhase.preflight.value,
        "task_kind": TaskKind.cheap_preflight.value,
        "decision": pre_decision.model_dump(mode="json"),
    }
    pre_adapter = (
        adapters.get(pre_decision.selected_adapter_name)
        if pre_decision.selected_adapter_name
        else None
    )
    if pre_adapter and pre_decision.selected_adapter_name:
        pre_prompt = (
            f"Writers-Room retrieval preflight for module={module_id}. "
            f"In one or two sentences, is retrieved context likely sufficient for a canon review? "
            f"(yes/no + brief reason). evidence_tier={evidence_tag}.\n"
            f"Context excerpt:\n{(retrieval_text or '')[:1800]}"
        )
        try:
            pre_call = pre_adapter.generate(
                pre_prompt, timeout_seconds=5.0, retrieval_context=retrieval_text or None
            )
            preflight_trace["bounded_model_call"] = True
            preflight_trace["adapter_key"] = pre_decision.selected_adapter_name
            preflight_trace["call_success"] = pre_call.success
            preflight_trace["content_excerpt"] = (pre_call.content or "").strip()[:500]
        except Exception as exc:  # noqa: BLE001 — bounded diagnostic; workflow continues
            preflight_trace["bounded_model_call"] = True
            preflight_trace["adapter_key"] = pre_decision.selected_adapter_name
            preflight_trace["call_error"] = str(exc)
    else:
        preflight_trace["bounded_model_call"] = False
        preflight_trace["skip_reason"] = "no_eligible_adapter_or_missing_provider_adapter"

    attach_stage_routing_evidence(preflight_trace, preflight_req)

    synthesis_req = RoutingRequest(
        workflow_phase=WorkflowPhase.generation,
        task_kind=TaskKind.narrative_formulation,
        requires_structured_output=True,
    )
    syn_decision = route_model(synthesis_req, specs=specs)
    synthesis_trace: dict[str, Any] = {
        "stage": "synthesis",
        "workflow_phase": WorkflowPhase.generation.value,
        "task_kind": TaskKind.narrative_formulation.value,
        "decision": syn_decision.model_dump(mode="json"),
    }
    selected_provider = syn_decision.selected_adapter_name or "mock"
    adapter = adapters.get(selected_provider)
    generation: dict[str, Any] = {
        "provider": selected_provider,
        "success": False,
        "content": "",
        "error": None,
        "adapter_invocation_mode": None,
        "raw_fallback_reason": None,
        "metadata": {},
        "task_2a_routing": {"preflight": preflight_trace, "synthesis": synthesis_trace},
    }
    if adapter:
        wr_result = invoke_writers_room_adapter_with_langchain(
            adapter=adapter,
            module_id=module_id,
            focus=focus,
            retrieval_context=retrieval_text or None,
            timeout_seconds=12.0,
        )
        generation["success"] = wr_result.call.success
        generation["error"] = wr_result.call.metadata.get("error") if not wr_result.call.success else None
        generation["adapter_invocation_mode"] = "langchain_structured_primary"
        if wr_result.parsed_output is not None:
            notes = (wr_result.parsed_output.review_notes or "").strip()
            generation["content"] = notes or wr_result.call.content
            generation["metadata"] = {
                "langchain_prompt_used": True,
                "langchain_parser_error": None,
                "structured_output": wr_result.parsed_output.model_dump(mode="json"),
            }
        elif wr_result.call.success:
            generation["content"] = wr_result.call.content
            generation["metadata"] = {
                "langchain_prompt_used": True,
                "langchain_parser_error": wr_result.parser_error,
                "structured_output": None,
            }
        else:
            generation["content"] = ""
            generation["metadata"] = {
                "langchain_prompt_used": True,
                "langchain_parser_error": wr_result.parser_error,
                "structured_output": None,
            }
    else:
        generation["error"] = f"adapter_not_registered:{selected_provider}"
        generation["raw_fallback_reason"] = "primary_adapter_missing"

    if not generation["success"]:
        fallback = adapters.get("mock")
        fallback_prompt = (
            f"Writers-Room review for module={module_id}.\n"
            f"Focus: {focus}\n"
            f"Use evidence from retrieved context and produce concise recommendations.\n\n"
            f"{retrieval_text}"
        )
        if fallback:
            call = fallback.generate(fallback_prompt, timeout_seconds=5.0, retrieval_context=retrieval_text or None)
            generation["provider"] = "mock"
            generation["success"] = call.success
            generation["content"] = call.content
            generation["error"] = call.metadata.get("error") if not call.success else None
            generation["adapter_invocation_mode"] = "raw_adapter_fallback"
            generation["raw_fallback_reason"] = (
                generation.get("raw_fallback_reason") or "primary_failed_or_unavailable"
            )
            generation["metadata"] = {
                "langchain_prompt_used": False,
                "langchain_parser_error": None,
                "structured_output": None,
                "bypass_note": (
                    "Mock/raw fallback skips LangChain structured parse because default mock output is not JSON; "
                    "graph-runtime primary path uses the same pattern."
                ),
            }

    syn_stage = generation["task_2a_routing"]["synthesis"]
    syn_executed = str(generation.get("provider") or "").strip() or None
    syn_bounded = generation.get("adapter_invocation_mode") is not None
    syn_dev_note = None
    if syn_executed and syn_decision.selected_adapter_name:
        if _norm_wr_adapter(syn_executed) != _norm_wr_adapter(syn_decision.selected_adapter_name):
            syn_dev_note = str(generation.get("raw_fallback_reason") or "executed_adapter_differs_from_routed")
    attach_stage_routing_evidence(
        syn_stage,
        synthesis_req,
        executed_adapter_name=syn_executed,
        bounded_model_call=syn_bounded,
        skip_reason=None,
        execution_deviation_note=syn_dev_note,
    )

    return WritersRoomGenerationStageResult(generation=generation)
