from __future__ import annotations

from unittest.mock import patch

from ai_stack.mcp.mcp_canonical_surface import canonical_mcp_tool_descriptors_by_name

from tools.mcp_server.tools_registry import create_default_registry


def _registry():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            return create_default_registry()


def test_evaluator_mcp_tools_registered_and_aliases():
    registry = _registry()
    names = set(registry.list_tool_names())
    assert "wos.evaluators.catalog" in names
    assert "wos.evaluators.get" in names
    assert "wos.evaluators.langfuse_sync_preview" in names
    assert registry.get("wos_evaluators_catalog") is not None
    assert registry.get("wos_evaluators_get") is not None
    assert registry.get("wos_evaluators_langfuse_sync_preview") is not None
    assert registry.get("wos_evaluators_catalog").name == "wos.evaluators.catalog"


def test_canonical_descriptors_for_evaluator_tools():
    by_name = canonical_mcp_tool_descriptors_by_name()
    for n in ("wos.evaluators.catalog", "wos.evaluators.get", "wos.evaluators.langfuse_sync_preview"):
        d = by_name[n]
        assert d.authority_source == "langfuse_evaluator_catalog"
        assert d.mcp_suite.value == "wos-ai"
        assert d.narrative_mutation_risk == "none_observation_only"


def test_evaluators_catalog_omits_prompts_by_default():
    registry = _registry()
    out = registry.get("wos.evaluators.catalog").handler({})
    assert out["ok"] is True
    first = out["evaluators"][0]
    assert first.get("prompt_omitted") is True
    assert first.get("prompt") is None
    assert "langfuse_filter_templates" in out
    assert out["langfuse_filter_templates"]["opening_generation"]["trace_name"] == "world-engine.session.create"
    assert out["langfuse_filter_templates"]["turn_generation"]["legacy_trace_names"] == ["backend.turn.execute"]


def test_evaluators_get_full_player_action_resolution():
    registry = _registry()
    out = registry.get("wos.evaluators.get").handler({"name": "player_action_resolution_judge"})
    assert out["ok"] is True
    ev = out["evaluator"]
    assert ev["name"] == "player_action_resolution_judge"
    assert ev["prompt"] and "qualitative review signal only" in ev["prompt"].lower()
    assert ev["score_reasoning_prompt"]
    assert ev["category_selection_prompt"]


def test_evaluators_langfuse_sync_preview_shape():
    registry = _registry()
    out = registry.get("wos.evaluators.langfuse_sync_preview").handler({"name": "player_action_resolution_judge"})
    assert out["ok"] is True
    prev = out["langfuse_sync_preview"]
    assert prev["name"] == "player_action_resolution_judge"
    assert prev["score_type"] == "categorical"
    assert prev["categories"] == ["resolved_well", "partially_resolved", "misresolved", "not_resolved"]
    assert prev["allow_multiple_matches"] is False
    assert prev["prompt"] and prev["score_reasoning_prompt"] and prev["category_selection_prompt"]
    assert "observation_filters" in prev and "trace_metadata_filters" in prev
    assert "legacy_trace_names" in prev
    assert prev["qualitative_only"] is True
    assert prev["runtime_gate"] is False
    assert prev["replaces_deterministic_gates"] is False
    assert "gate_override_warning" in prev
    assert "deterministic" in prev["gate_override_warning"].lower()
    assert prev["langfuse_filter_group"] == "turn_generation"
    assert "opening_generation" in prev["langfuse_filter_group_templates"]
    assert "turn_generation" in prev["langfuse_filter_group_templates"]
    assert prev.get("optional_trace_metadata_hint")
    assert prev.get("recommended_adapter_exclusions_if_metadata_negation_supported")


def test_evaluators_get_unknown_name_returns_structured_error():
    registry = _registry()
    out = registry.get("wos.evaluators.get").handler({"name": "not_a_real_evaluator"})
    assert out["ok"] is False
    assert out["error"]["code"] == "evaluator_not_found"
    assert "available" in out["error"]


def test_evaluator_handlers_are_pure_catalog_reads():
    registry = _registry()
    a = registry.get("wos.evaluators.catalog").handler({"include_prompts": False})
    b = registry.get("wos.evaluators.catalog").handler({"include_prompts": False})
    assert a == b
    get_twice = registry.get("wos.evaluators.get").handler({"name": "player_action_resolution_judge"})
    assert get_twice == registry.get("wos.evaluators.get").handler({"name": "player_action_resolution_judge"})
