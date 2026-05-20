"""Writers Room workflow — model routing, preflight, synthesis, and generation (DS-002 stage 3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.runtime.model_routing_contracts import AdapterModelSpec
from app.services.writers_room.writers_room_pipeline_generation_preflight import run_writers_room_generation_preflight
from app.services.writers_room.writers_room_pipeline_generation_synthesis import (
    _norm_wr_adapter,
    apply_generation_mock_fallback,
    attach_synthesis_routing_evidence,
    fill_generation_from_primary_adapter,
    route_synthesis_and_build_generation_shell,
)


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
    lf_trace: Any = None,
) -> WritersRoomGenerationStageResult:
    """Route preflight and synthesis, invoke LangChain path or mock fallback; attach synthesis routing evidence."""
    specs = model_route_specs
    preflight_trace = run_writers_room_generation_preflight(
        adapters=adapters,
        specs=specs,
        module_id=module_id,
        retrieval_text=retrieval_text,
        evidence_tag=evidence_tag,
        lf_trace=lf_trace,
    )
    syn_decision, synthesis_req, _, generation = route_synthesis_and_build_generation_shell(
        specs=specs,
        preflight_trace=preflight_trace,
    )
    selected_provider = generation["provider"]
    adapter = adapters.get(selected_provider)
    fill_generation_from_primary_adapter(
        generation=generation,
        adapter=adapter,
        module_id=module_id,
        focus=focus,
        retrieval_text=retrieval_text,
        selected_provider=selected_provider,
        lf_trace=lf_trace,
    )
    apply_generation_mock_fallback(
        generation=generation,
        adapters=adapters,
        module_id=module_id,
        focus=focus,
        retrieval_text=retrieval_text,
        lf_trace=lf_trace,
    )
    attach_synthesis_routing_evidence(
        generation=generation,
        synthesis_req=synthesis_req,
        syn_decision=syn_decision,
    )
    return WritersRoomGenerationStageResult(generation=generation)
