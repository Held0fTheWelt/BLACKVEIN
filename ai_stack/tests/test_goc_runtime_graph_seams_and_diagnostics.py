"""Phase 1 GoC closure: non-preview path, seams, diagnostics (frozen contracts)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from story_runtime_core import RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from story_runtime_core.model_registry import build_default_registry

pytest.importorskip(
    "ai_stack.langgraph.langgraph_runtime",
    reason="LangGraph/LangChain stack required for GoC runtime graph tests",
)
from ai_stack.langgraph.langgraph_runtime import RuntimeTurnGraphExecutor
from ai_stack.rag import ContextPackAssembler, ContextRetriever, RagIngestionPipeline
from ai_stack.story_runtime.semantic_planner.goc_roadmap_semantic_surface import ROUTING_LABELS, TASK_TYPES
from ai_stack.story_runtime.turn.goc_turn_seams import (
    build_operator_canonical_turn_record,
    repro_metadata_complete,
    strip_director_overwrites_from_structured_output,
)
from ai_stack.goc_yaml_authority import (
    cached_goc_yaml_title,
    clear_goc_yaml_slice_cache,
    detect_builtin_yaml_title_conflict,
    load_goc_canonical_module_yaml,
    load_goc_yaml_slice_bundle,
)
from ai_stack.version import RUNTIME_TURN_GRAPH_VERSION


class JsonStructuredRuntimeAdapter(BaseModelAdapter):
    """Returns JSON matching RuntimeTurnStructuredOutput for LangChain parse path."""

    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        payload = {
            "narrative_response": (
                "Annette meets your stare and admits what she knew; the truth she withheld about "
                "the children finally surfaces as she confesses the hidden fact."
            ),
            "proposed_scene_id": None,
            "intent_summary": "escalation_probe",
        }
        return ModelCallResult(
            content=json.dumps(payload),
            success=True,
            metadata={"adapter": self.adapter_name},
        )


def _executor(tmp_path: Path) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage phase-1 gate corpus.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    return RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters={
            "mock": JsonStructuredRuntimeAdapter(),
            "openai": JsonStructuredRuntimeAdapter(),
            "ollama": JsonStructuredRuntimeAdapter(),
        },
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )


@pytest.fixture(autouse=True)
def _clear_goc_title_cache() -> None:
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()
    yield
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()


def test_goc_thin_path_turn_integrity_and_diagnostics(tmp_path: Path) -> None:
    graph = _executor(tmp_path)
    result = graph.run(
        session_id="s-goc-1",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I press Annette on why she withheld the truth.",
        trace_id="trace-goc-phase1",
        host_experience_template={
            "template_id": "god_of_carnage_solo",
            "title": "God of Carnage",
        },
    )

    assert result["graph_diagnostics"]["graph_version"] == RUNTIME_TURN_GRAPH_VERSION
    nodes = result["graph_diagnostics"]["nodes_executed"]
    for required in (
        "resolve_player_action",
        "director_compose_realization",
        "realize_via_capabilities",
        "route_model",
        "invoke_model",
        "proposal_normalize",
        "validate_seam",
        "commit_seam",
        "render_visible",
        "package_output",
    ):
        assert required in nodes
    for obsolete in (
        "goc_resolve_canonical_content",
        "director_assess_scene",
        "director_select_dramatic_parameters",
        "synthesize_context",
        "assemble_model_context",
    ):
        assert obsolete not in nodes

    repro = result["graph_diagnostics"].get("repro_metadata") or {}
    assert repro.get("repro_complete") is False
    assert repro_metadata_complete(repro) is False
    assert repro.get("retrieval_domain") is None

    assert isinstance(result.get("experiment_preview"), bool)
    assert (result.get("validation_outcome") or {}).get("status") in ("approved", "rejected")
    assert isinstance((result.get("committed_result") or {}).get("commit_applied"), bool)
    assert isinstance(result.get("proposed_state_effects"), list)
    assert "live_truth_surface_no_preview_placeholder" in (result.get("visibility_class_markers") or [])

    refs = result.get("diagnostics_refs") or []
    assert refs
    preview_refs = [r for r in refs if r.get("ref_type") == "experiment_preview"]
    assert preview_refs and isinstance(preview_refs[0].get("experiment_preview"), bool)

    yaml_mod = load_goc_canonical_module_yaml()
    assert yaml_mod.get("module_id") == "god_of_carnage"
    context = result.get("dramatic_context_summary") or {}
    assert context.get("contract") == "bounded_dramatic_context.v1"
    assert context.get("module_scope", {}).get("requested_module_supported") is True
    plan = result.get("realization_plan") or {}
    assert plan.get("schema_version") == "realization_plan.v1"
    assert result.get("realize_via_capabilities_used_capability")

    assert result.get("task_type") in TASK_TYPES
    routing = result.get("routing") or {}
    assert routing.get("route_reason_code") in ROUTING_LABELS
    assert routing.get("policy_id_used")
    assert routing.get("policy_version_used")
    assert routing.get("fallback_chain")
    assert routing.get("fallback_stage_reached") == "primary_only"

    op = build_operator_canonical_turn_record(result)
    assert op["turn_metadata"]["turn_id"] == "trace-goc-phase1"
    assert op["turn_metadata"]["turn_number"] is None
    assert result.get("retrieval") is None


def test_turn_number_when_host_supplied_is_scalar_not_envelope(tmp_path: Path) -> None:
    graph = _executor(tmp_path)
    result = graph.run(
        session_id="s-goc-turnn",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Hello.",
        trace_id="trace-turnn",
        turn_number=3,
        turn_id="explicit-turn-id",
        host_experience_template={
            "template_id": "god_of_carnage_solo",
            "title": "God of Carnage",
        },
    )
    metadata = build_operator_canonical_turn_record(result)["turn_metadata"]
    assert metadata["turn_number"] == 3
    assert metadata["turn_id"] == "explicit-turn-id"


def test_builtin_title_mismatch_is_detected_by_yaml_authority() -> None:
    marker = detect_builtin_yaml_title_conflict(
        host_template_id="god_of_carnage_solo",
        host_template_title="Wrong Title XYZ",
    )
    assert marker is not None
    assert marker.get("failure_class") == "scope_breach"
    assert marker.get("note") == "builtins_yaml_title_mismatch"


def test_model_structured_output_cannot_overwrite_director_fields() -> None:
    dirty = {
        "narrative_response": "ok",
        "selected_scene_function": "scene_pivot",
        "pacing_mode": "containment",
    }
    cleaned, markers = strip_director_overwrites_from_structured_output(dirty)
    assert cleaned is not None
    assert "selected_scene_function" not in cleaned
    assert "pacing_mode" not in cleaned
    assert markers


def test_empty_trace_yields_incomplete_repro_metadata(tmp_path: Path) -> None:
    graph = _executor(tmp_path)
    result = graph.run(
        session_id="s-goc-3",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="test",
        trace_id="",
    )
    repro = result["graph_diagnostics"].get("repro_metadata") or {}
    assert repro.get("repro_complete") is False


def test_yaml_title_is_stable_non_empty() -> None:
    assert cached_goc_yaml_title() == "God of Carnage"


def test_goc_yaml_slice_bundle_carries_runtime_law_surfaces() -> None:
    bundle = load_goc_yaml_slice_bundle()
    assert bundle.get("scene_phases")
    assert bundle.get("relationship_axes")
    assert bundle.get("relationships")
    assert bundle.get("canonical_path")
    assert bundle.get("phase_beat_policy")
    assert bundle.get("trigger_types") == {}
    assert bundle.get("phase_transitions") == {}
    assert bundle.get("transition_safeguards") == {}
    assert bundle.get("ending_types") == {}
    assert bundle.get("escalation_axes") == {}
    assert bundle.get("system_prompt_excerpt")
