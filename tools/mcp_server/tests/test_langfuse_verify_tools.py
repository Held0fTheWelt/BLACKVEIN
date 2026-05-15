from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

from ai_stack.npc_agency_contracts import NPC_AGENCY_CLAIM_BOUNDED_RUNTIME_STATUS
from tools.mcp_server.tools_registry import create_default_registry


def _registry():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            return create_default_registry()


def test_langfuse_verify_tools_registered():
    registry = _registry()
    assert registry.get("run_projection_tests") is not None
    assert registry.get("fetch_langfuse_trace") is not None
    assert registry.get("query_langfuse_traces") is not None
    assert registry.get("assert_langfuse_opening_contract") is not None
    assert registry.get("summarize_live_opening_matrix") is not None
    assert registry.get("summarize_runtime_aspect_matrix") is not None
    assert registry.get("summarize_beat_realization_failures") is not None
    assert registry.get("summarize_narrator_npc_authority") is not None
    assert registry.get("summarize_capability_realization") is not None
    assert registry.get("summarize_visible_projection_origin_loss") is not None
    assert registry.get("wos.evaluators.catalog") is not None
    assert registry.get("wos.evaluators.get") is not None
    assert registry.get("wos.evaluators.langfuse_sync_preview") is not None


def test_run_projection_tests_returns_structured_result():
    registry = _registry()
    tool = registry.get("run_projection_tests")
    with patch("tools.mcp_server.tools_registry_handlers_langfuse_verify.subprocess.run") as run_mock:
        preflight_proc = MagicMock()
        preflight_proc.returncode = 0
        preflight_proc.stdout = "import_ok=app.story_runtime\n"
        preflight_proc.stderr = ""
        world_engine_proc = MagicMock()
        world_engine_proc.returncode = 0
        world_engine_proc.stdout = "1 passed"
        world_engine_proc.stderr = ""
        ai_stack_proc = MagicMock()
        ai_stack_proc.returncode = 0
        ai_stack_proc.stdout = "1 passed"
        ai_stack_proc.stderr = ""
        run_mock.side_effect = [preflight_proc, world_engine_proc, ai_stack_proc]
        out = tool.handler({})
    assert run_mock.call_count == 3
    assert out["ok"] is True
    assert out["world_engine"]["ok"] is True
    assert out["ai_stack"]["ok"] is True
    assert out["world_engine"]["returncode"] == 0
    assert out["ai_stack"]["returncode"] == 0
    assert out["world_engine"]["command"][0] == sys.executable
    assert out["ai_stack"]["command"][0] == sys.executable
    assert out["world_engine"]["command"][1:5] == ["-m", "pytest", "tests/test_trace_middleware.py", "-q"]
    assert out["ai_stack"]["command"][1:5] == [
        "-m",
        "pytest",
        "ai_stack/tests/test_actor_lane_absence_governance.py",
        "-q",
    ]
    assert out["world_engine"]["cwd"].replace("\\", "/").endswith("/WorldOfShadows/world-engine")
    assert out["ai_stack"]["cwd"].replace("\\", "/").endswith("/WorldOfShadows")
    assert "world-engine" in out["world_engine"]["pythonpath"]
    assert "world-engine" not in out["ai_stack"]["pythonpath"].split(os.pathsep)[0]
    assert "1 passed" in out["world_engine"]["stdout_tail"]
    assert "1 passed" in out["ai_stack"]["stdout_tail"]
    assert run_mock.call_args_list[0].args[0][0] == sys.executable
    assert run_mock.call_args_list[1].args[0][0] == sys.executable
    assert run_mock.call_args_list[2].args[0][0] == sys.executable
    assert run_mock.call_args_list[0].kwargs["cwd"].replace("\\", "/").endswith("/WorldOfShadows/world-engine")
    assert run_mock.call_args_list[1].kwargs["cwd"].replace("\\", "/").endswith("/WorldOfShadows/world-engine")
    assert run_mock.call_args_list[2].kwargs["cwd"].replace("\\", "/").endswith("/WorldOfShadows")


def test_run_projection_tests_returns_preflight_diagnostics_on_import_error():
    registry = _registry()
    tool = registry.get("run_projection_tests")
    with patch("tools.mcp_server.tools_registry_handlers_langfuse_verify.subprocess.run") as run_mock:
        preflight_proc = MagicMock()
        preflight_proc.returncode = 1
        preflight_proc.stdout = ""
        preflight_proc.stderr = "ModuleNotFoundError: No module named 'app.story_runtime'"
        run_mock.return_value = preflight_proc
        out = tool.handler({})
    assert run_mock.call_count == 1
    assert out["ok"] is False
    assert out["world_engine"]["ok"] is False
    assert out["world_engine"]["command"][0] == sys.executable
    assert out["world_engine"]["cwd"].replace("\\", "/").endswith("/WorldOfShadows/world-engine")
    assert "world-engine" in out["world_engine"]["pythonpath"]
    assert "ModuleNotFoundError" in out["world_engine"]["stderr_tail"]
    assert out["ai_stack"]["ok"] is False
    assert out["ai_stack"]["returncode"] is None
    assert "skipped_due_to_world_engine_preflight_failure" in out["ai_stack"]["stderr_tail"]


def test_assert_live_opening_contract_reports_missing_field():
    registry = _registry()
    tool = registry.get("assert_langfuse_opening_contract")
    trace_payload = {
        "id": "lf-live-1",
        "metadata": {
            "trace_origin": "live_ui",
            "execution_tier": "live",
            "canonical_player_flow": True,
            "selected_player_role": "annette",
            "human_actor_id": "annette",
            "final_adapter": "openai",
            "quality_class": "healthy",
        },
        "scores": [
            {"name": "opening_shape_contract_pass", "value": 1.0},
            {"name": "live_runtime_contract_pass", "value": 1.0},
            {"name": "live_opening_contract_pass", "value": 0.0},
        ],
    }
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=trace_payload,
    ):
        out = tool.handler({"mode": "live", "langfuse_trace_id": "lf-live-1"})
    assert out["ok"] is False
    assert any(f["missing_field"] == "scores.live_opening_contract_pass" for f in out["failures"])


def test_query_langfuse_traces_filters_canonical_player_flow_false():
    registry = _registry()
    tool = registry.get("query_langfuse_traces")
    rows = [
        {
            "id": "lf-pytest-1",
            "metadata": {"trace_origin": "pytest", "canonical_player_flow": False},
            "scores": [{"name": "live_opening_contract_pass", "value": 0.0}],
        },
        {
            "id": "lf-live-1",
            "metadata": {"trace_origin": "live_ui", "canonical_player_flow": True},
            "scores": [{"name": "live_opening_contract_pass", "value": 1.0}],
        },
    ]
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_query_traces",
        return_value=[rows[0]],
    ):
        out = tool.handler({"trace_origin": "pytest", "canonical_player_flow": False, "limit": 10})
    assert out["ok"] is True
    assert out["count"] == 1
    assert out["traces"][0]["metadata"]["canonical_player_flow"] is False


def test_langfuse_query_traces_filters_by_staging_environment():
    """GOC-KNOWLEDGE-RUNTIME-INTEGRATION P1.4: MCP discovery must accept ``environment``
    so staging traces are findable when runtime is no longer ``live``."""
    from tools.mcp_server import tools_registry_handlers_langfuse_verify as mod

    rows = {
        "data": [
            {
                "id": "lf-staging-be",
                "name": "backend.turn.execute",
                "environment": "staging",
                "metadata": {"trace_origin": "live_ui", "execution_tier": "staging", "canonical_turn_id": "ct-1"},
            },
            {
                "id": "lf-prod-be",
                "name": "backend.turn.execute",
                "environment": "production",
                "metadata": {"trace_origin": "live_ui", "execution_tier": "live", "canonical_turn_id": "ct-2"},
            },
            {
                "id": "lf-staging-we",
                "name": "world-engine.turn.execute",
                "metadata": {"environment": "staging", "trace_origin": "live_ui", "canonical_turn_id": "ct-3"},
            },
        ]
    }
    with patch.object(mod, "_langfuse_public_get_json", return_value=rows):
        filtered = mod._langfuse_query_traces(
            limit=10,
            trace_origin=None,
            canonical_player_flow=None,
            environment="staging",
        )
    ids = sorted(row.get("id") for row in filtered)
    assert ids == ["lf-staging-be", "lf-staging-we"], (
        f"expected only staging traces, got: {ids}"
    )


def test_query_langfuse_traces_handler_forwards_environment_argument():
    """The MCP-exposed query_langfuse_traces handler must forward ``environment`` to
    the underlying query so staging is discoverable via tool args."""
    from tools.mcp_server import tools_registry_handlers_langfuse_verify as mod

    registry = _registry()
    tool = registry.get("query_langfuse_traces")
    with patch.object(mod, "_langfuse_query_traces", return_value=[]) as qm:
        tool.handler({"environment": "staging", "limit": 5})
    qm.assert_called_once()
    assert qm.call_args.kwargs.get("environment") == "staging"


# ---------------------------------------------------------------------------
# New tools registered
# ---------------------------------------------------------------------------


def test_new_judge_tools_registered():
    registry = _registry()
    assert registry.get("fetch_langfuse_trace_scores") is not None
    assert registry.get("summarize_opening_judge_scores") is not None
    assert registry.get("build_opening_quality_context") is not None


# ---------------------------------------------------------------------------
# fetch_langfuse_trace_scores
# ---------------------------------------------------------------------------


def _live_trace_with_scores(trace_id: str = "lf-live-1") -> dict:
    return {
        "id": trace_id,
        "name": "world-engine.session.create",
        "metadata": {
            "trace_origin": "live_ui",
            "execution_tier": "live",
            "canonical_player_flow": True,
            "selected_player_role": "annette",
            "human_actor_id": "annette",
        },
        "scores": [
            {
                "name": "live_runtime_contract_pass",
                "value": 1.0,
                "metadata": {
                    "turn_number": 0,
                    "first_actor_block_index": 3,
                    "narrator_block_count": 3,
                    "opening_shape_failure_reasons": [],
                    "opening_narration_normalized": True,
                    "opening_narration_source": "model_list_three_plus",
                },
            },
            {"name": "live_opening_contract_pass", "value": 1.0},
            {"name": "non_mock_generation_pass", "value": 1.0},
            {
                "name": "opening_experience_judge",
                "value": 0.8,
                "comment": "Strong atmospheric setup.",
                "metadata": {"category": "acceptable"},
            },
            {
                "name": "theatrical_style_judge",
                "value": 0.4,
                "comment": "Too generic.",
                "metadata": {"category": "flat"},
            },
        ],
    }


def test_fetch_langfuse_trace_scores_returns_split_scores():
    registry = _registry()
    tool = registry.get("fetch_langfuse_trace_scores")
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=_live_trace_with_scores(),
    ):
        out = tool.handler({"trace_id": "lf-live-1"})
    assert out["ok"] is True
    assert out["trace_id"] == "lf-live-1"
    assert out["trace_origin"] == "live_ui"
    assert out["execution_tier"] == "live"
    assert out["canonical_player_flow"] is True
    assert out["selected_player_role"] == "annette"
    # deterministic scores
    assert out["deterministic_scores"]["live_opening_contract_pass"] == 1.0
    assert out["deterministic_scores"]["non_mock_generation_pass"] == 1.0
    # judge scores separated
    assert "opening_experience_judge" in out["judge_scores"]
    assert "theatrical_style_judge" in out["judge_scores"]
    # judge scores not in deterministic
    assert "opening_experience_judge" not in out["deterministic_scores"]
    assert out["judge_scores"]["opening_experience_judge"]["category"] == "acceptable"
    assert out["judge_scores"]["theatrical_style_judge"]["category"] == "flat"
    assert out["judge_scores"]["theatrical_style_judge"]["reasoning"] == "Too generic."
    diag = out.get("opening_shape_diagnostics") or {}
    assert diag.get("first_actor_block_index") == 3
    assert diag.get("narrator_block_count") == 3
    assert diag.get("opening_narration_normalized") is True
    assert "llm_judge_interpretation" in out
    assert out["canonical_evaluator_definition_doc"].endswith(".csv")
    assert isinstance(out["judge_score_coverage_gaps"], list)
    assert isinstance(out["evaluator_column_metadata"], dict)


def test_fetch_langfuse_trace_scores_blocks_non_live_by_default():
    registry = _registry()
    tool = registry.get("fetch_langfuse_trace_scores")
    pytest_trace = {
        "id": "lf-pytest-1",
        "metadata": {"trace_origin": "pytest", "execution_tier": "mock_only", "canonical_player_flow": False},
        "scores": [],
    }
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=pytest_trace,
    ):
        out = tool.handler({"trace_id": "lf-pytest-1"})
    assert out["ok"] is False
    assert out["error"] == "trace_filtered_as_non_live"
    assert "hint" in out


def test_fetch_langfuse_trace_scores_allow_non_live_bypasses_filter():
    registry = _registry()
    tool = registry.get("fetch_langfuse_trace_scores")
    pytest_trace = {
        "id": "lf-pytest-1",
        "metadata": {"trace_origin": "pytest", "execution_tier": "mock_only", "canonical_player_flow": False},
        "scores": [{"name": "live_opening_contract_pass", "value": 0.0}],
    }
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=pytest_trace,
    ):
        out = tool.handler({"trace_id": "lf-pytest-1", "allow_non_live": True})
    assert out["ok"] is True
    assert out["trace_origin"] == "pytest"


def test_fetch_langfuse_trace_scores_requires_trace_id():
    registry = _registry()
    tool = registry.get("fetch_langfuse_trace_scores")
    out = tool.handler({})
    assert out["ok"] is False
    assert "trace_id" in out["error"]


def test_fetch_langfuse_trace_scores_reads_judge_category_from_label_metadata():
    """Langfuse categorical rows may expose the chosen label under metadata.label."""
    registry = _registry()
    tool = registry.get("fetch_langfuse_trace_scores")
    trace = {
        "id": "lf-label-1",
        "metadata": {
            "trace_origin": "live_ui",
            "execution_tier": "live",
            "canonical_player_flow": True,
        },
        "scores": [
            {"name": "live_opening_contract_pass", "value": 1.0},
            {
                "name": "opening_experience_judge",
                "value": 1.0,
                "comment": "Narrator-led intro.",
                "metadata": {"label": "excellent"},
            },
        ],
    }
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=trace,
    ):
        out = tool.handler({"trace_id": "lf-label-1"})
    assert out["ok"] is True
    assert out["judge_scores"]["opening_experience_judge"]["category"] == "excellent"
    assert "canonical_live_langfuse_filters" in out
    assert "categorical_judge_names" in out
    names = out["categorical_judge_names"]
    assert "player_action_resolution_judge" in names
    assert "turn_generation_categorical_evaluators" in out["canonical_live_langfuse_filters"]
    tge = out["canonical_live_langfuse_filters"]["turn_generation_categorical_evaluators"]
    assert tge["observation_filters"]["Name"] == ["story.model.generation"]
    assert tge["observation_filters"]["Trace Name"] == ["world-engine.turn.execute"]
    assert tge["alternate_backend_root_trace_names"] == ["backend.turn.execute"]
    assert tge["trace_metadata_when_available"]["opening_turn"] is False
    og = out["canonical_live_langfuse_filters"]["opening_generation_categorical_evaluators"]
    assert og["judges"][0] == "opening_experience_judge"
    assert og["observation_filters"]["Trace Name"] == ["world-engine.session.create"]
    assert og["trace_metadata_when_available"]["opening_turn"] is True
    assert og["trace_metadata_when_available"]["turn_number"] == 0


# ---------------------------------------------------------------------------
# summarize_opening_judge_scores
# ---------------------------------------------------------------------------


def test_summarize_opening_judge_scores_builds_matrix():
    registry = _registry()
    tool = registry.get("summarize_opening_judge_scores")
    rows = [
        {
            "id": "lf-a-1",
            "name": "world-engine.session.create",
            "metadata": {
                "trace_origin": "live_ui",
                "execution_tier": "live",
                "canonical_player_flow": True,
                "selected_player_role": "annette",
            },
            "scores": [
                {"name": "live_opening_contract_pass", "value": 1.0},
                {"name": "theatrical_style_judge", "value": 0.3, "comment": "flat", "metadata": {"category": "flat"}},
            ],
        },
        {
            "id": "lf-b-1",
            "name": "world-engine.session.create",
            "metadata": {
                "trace_origin": "live_ui",
                "execution_tier": "live",
                "canonical_player_flow": True,
                "selected_player_role": "alain",
            },
            "scores": [
                {"name": "live_opening_contract_pass", "value": 0.0},
            ],
        },
    ]
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_query_traces",
        return_value=rows,
    ):
        out = tool.handler({"roles": ["annette", "alain"], "limit_per_role": 5})
    assert out["ok"] is True
    assert out["count"] == 2
    annette_row = next(r for r in out["matrix"] if r["role"] == "annette")
    alain_row = next(r for r in out["matrix"] if r["role"] == "alain")
    assert annette_row["live_opening"] == "pass"
    assert annette_row["style_category"] == "flat"
    assert annette_row["main_issue"] == "theatrical_style_judge"
    assert alain_row["live_opening"] == "fail"
    assert alain_row["main_issue"] == "live_opening_fail"


def test_summarize_opening_judge_scores_passes_trace_name_to_query():
    registry = _registry()
    tool = registry.get("summarize_opening_judge_scores")
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_query_traces",
        return_value=[],
    ) as qm:
        tool.handler({"trace_name": "world-engine.session.create"})
    qm.assert_called_once()
    assert qm.call_args.kwargs.get("trace_name") == "world-engine.session.create"


def test_summarize_opening_judge_scores_respects_limit_per_role():
    registry = _registry()
    tool = registry.get("summarize_opening_judge_scores")
    rows = [
        {
            "id": f"lf-a-{i}",
            "metadata": {
                "trace_origin": "live_ui",
                "execution_tier": "live",
                "canonical_player_flow": True,
                "selected_player_role": "annette",
            },
            "scores": [{"name": "live_opening_contract_pass", "value": 1.0}],
        }
        for i in range(10)
    ]
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_query_traces",
        return_value=rows,
    ):
        out = tool.handler({"limit_per_role": 3})
    assert out["ok"] is True
    assert out["count"] <= 3


# ---------------------------------------------------------------------------
# build_opening_quality_context
# ---------------------------------------------------------------------------


def test_build_opening_quality_context_recommends_style_card():
    registry = _registry()
    tool = registry.get("build_opening_quality_context")
    trace = _live_trace_with_scores()
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=trace,
    ):
        out = tool.handler({"trace_id": "lf-live-1"})
    assert out["ok"] is True
    assert out["recommended_next_card"] == "OPEN-STYLE-01"
    assert "theatrical" in out["ai_context_summary"].lower() or "style" in out["ai_context_summary"].lower()
    assert "must_not_change" in out
    assert "evidence" in out
    assert "deterministic" in out["evidence"]
    assert "judges" in out["evidence"]


def test_build_opening_quality_context_recommends_runtime_repair_when_gate_fails():
    registry = _registry()
    tool = registry.get("build_opening_quality_context")
    trace = {
        "id": "lf-live-fail",
        "metadata": {
            "trace_origin": "live_ui",
            "execution_tier": "live",
            "canonical_player_flow": True,
            "selected_player_role": "alain",
            "human_actor_id": "alain",
        },
        "scores": [
            {"name": "live_opening_contract_pass", "value": 0.0},
            {"name": "live_runtime_contract_pass", "value": 0.0},
        ],
    }
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=trace,
    ):
        out = tool.handler({"trace_id": "lf-live-fail"})
    assert out["ok"] is True
    assert out["recommended_next_card"] == "RUNTIME-CONTRACT-01"
    assert "contract" in out["ai_context_summary"].lower() or "runtime" in out["ai_context_summary"].lower()


def test_build_opening_quality_context_blocks_non_live_traces():
    registry = _registry()
    tool = registry.get("build_opening_quality_context")
    trace = {
        "id": "lf-pytest-1",
        "metadata": {"trace_origin": "pytest", "canonical_player_flow": False},
        "scores": [],
    }
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=trace,
    ):
        out = tool.handler({"trace_id": "lf-pytest-1"})
    assert out["ok"] is False
    assert out["error"] == "trace_not_live_evidence"


def test_build_opening_quality_context_includes_reasoning_when_requested():
    registry = _registry()
    tool = registry.get("build_opening_quality_context")
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=_live_trace_with_scores(),
    ):
        out = tool.handler({"trace_id": "lf-live-1", "include_raw_reasoning": True})
    assert out["ok"] is True
    ts = out["evidence"]["judges"].get("theatrical_style_judge", {})
    assert ts.get("reasoning") == "Too generic."


def test_build_opening_quality_context_no_card_when_all_pass():
    registry = _registry()
    tool = registry.get("build_opening_quality_context")
    clean_trace = {
        "id": "lf-clean",
        "metadata": {
            "trace_origin": "live_ui",
            "execution_tier": "live",
            "canonical_player_flow": True,
            "selected_player_role": "annette",
        },
        "scores": [
            {"name": "live_opening_contract_pass", "value": 1.0},
            {"name": "live_runtime_contract_pass", "value": 1.0},
            {"name": "opening_experience_judge", "value": 1.0, "comment": "Strong.", "metadata": {"category": "excellent"}},
        ],
    }
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=clean_trace,
    ):
        out = tool.handler({"trace_id": "lf-clean"})
    assert out["ok"] is True
    assert out["recommended_next_card"] is None
    assert "No judge issues" in out["ai_context_summary"]


# ---------------------------------------------------------------------------
# MCP-LANGFUSE-VERIFY-03: normalized WoS evidence extraction
# ---------------------------------------------------------------------------


def _sparse_metadata_trace(trace_id: str = "lf-sparse-1") -> dict:
    """Trace where trace.metadata has only classification fields; WoS fields live in score metadata."""
    return {
        "id": trace_id,
        "metadata": {
            "trace_origin": "live_ui",
            "execution_tier": "live",
            "canonical_player_flow": True,
        },
        "scores": [
            {
                "name": "live_opening_contract_pass",
                "value": 1.0,
                "metadata": {
                    "session_id": "ses-sparse-001",
                    "selected_player_role": "annette",
                    "human_actor_id": "annette",
                    "final_adapter": "openai_gpt4",
                    "quality_class": "healthy",
                    "fallback_reason": None,
                },
            },
            {
                "name": "live_runtime_contract_pass",
                "value": 1.0,
                "metadata": {},
            },
            {
                "name": "opening_shape_contract_pass",
                "value": 1.0,
                "metadata": {},
            },
        ],
        "observations": [],
    }


def test_fetch_langfuse_trace_includes_normalized_evidence():
    registry = _registry()
    tool = registry.get("fetch_langfuse_trace")
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=_sparse_metadata_trace(),
    ):
        out = tool.handler({"langfuse_trace_id": "lf-sparse-1"})
    assert out["ok"] is True
    assert "normalized_wos_evidence" in out
    assert "evidence_sources" in out
    assert out["normalized_wos_evidence"] is not None
    assert out["evidence_sources"] is not None


def test_fetch_langfuse_trace_extracts_role_from_score_metadata():
    registry = _registry()
    tool = registry.get("fetch_langfuse_trace")
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=_sparse_metadata_trace(),
    ):
        out = tool.handler({"langfuse_trace_id": "lf-sparse-1"})
    ev = out["normalized_wos_evidence"]
    assert ev["selected_player_role"] == "annette"
    assert ev["human_actor_id"] == "annette"
    assert ev["final_adapter"] == "openai_gpt4"
    assert ev["quality_class"] == "healthy"
    assert ev["session_id"] == "ses-sparse-001"
    assert out["evidence_sources"]["score_source"] == "trace.scores"


def test_fetch_langfuse_trace_gate_scores_in_normalized_evidence():
    registry = _registry()
    tool = registry.get("fetch_langfuse_trace")
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=_sparse_metadata_trace(),
    ):
        out = tool.handler({"langfuse_trace_id": "lf-sparse-1"})
    ev = out["normalized_wos_evidence"]
    assert ev["live_opening_contract_pass"] == 1.0
    assert ev["live_runtime_contract_pass"] == 1.0
    assert ev["opening_shape_contract_pass"] == 1.0


def test_assert_opening_contract_extracts_role_from_score_metadata():
    registry = _registry()
    tool = registry.get("assert_langfuse_opening_contract")
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=_sparse_metadata_trace(),
    ):
        out = tool.handler({"mode": "live", "langfuse_trace_id": "lf-sparse-1"})
    assert out["ok"] is True, f"Unexpected failures: {out.get('failures')}"
    assert out["failures"] == []


def test_summarize_live_opening_matrix_enriches_from_score_metadata():
    registry = _registry()
    tool = registry.get("summarize_live_opening_matrix")
    rows = [_sparse_metadata_trace("lf-s-1"), _sparse_metadata_trace("lf-s-2")]
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_query_traces",
        return_value=rows,
    ):
        out = tool.handler({"limit": 10})
    assert out["ok"] is True
    assert out["count"] == 2
    for r in out["rows"]:
        assert r["selected_player_role"] == "annette", f"role missing in row: {r}"
        assert r["final_adapter"] == "openai_gpt4"
        assert r["quality_class"] == "healthy"
        assert r["live_opening_contract_pass"] == 1.0


def test_summarize_runtime_aspect_matrix_reads_ledger_from_path_summary():
    registry = _registry()
    tool = registry.get("summarize_runtime_aspect_matrix")
    trace_payload = {
        "id": "trace-aspect-matrix",
        "name": "world-engine.turn.execute",
        "environment": "staging",
        "output": {
            "contract": "story_runtime_path_observability.v1",
            "session_id": "session-aspect",
            "canonical_turn_id": "session-aspect:turn:1",
            "turn_number": 1,
            "raw_player_input": "Ich nehme ein Bier aus dem Kuehlschrank",
            "turn_aspect_ledger": {
                "session_id": "session-aspect",
                "canonical_turn_id": "session-aspect:turn:1",
                "turn_number": 1,
                "turn_aspect_ledger": {
                    "input": {
                        "status": "passed",
                        "actual": {
                            "raw_player_input": "Ich nehme ein Bier aus dem Kuehlschrank",
                            "input_kind": "action",
                        },
                    },
                    "action_resolution": {
                        "status": "passed",
                        "actual": {"action_kind": "object_interaction"},
                    },
                    "beat": {
                        "status": "partial",
                        "selected": {"selected_beat_id": "domestic_disruption"},
                        "actual": {"realized": False},
                        "failure_reason": "beat_realization_not_visible",
                    },
                    "narrator_authority": {
                        "status": "passed",
                        "expected": {"required": True},
                        "actual": {"narrator_block_present": True},
                    },
                    "npc_authority": {
                        "status": "passed",
                        "expected": {"policy": "social_reaction_only"},
                        "actual": {"npc_takeover_detected": False},
                    },
                    "npc_agency": {
                        "status": "passed",
                        "actual": {
                            "independent_planning_used": True,
                            "candidate_actor_ids": ["npc_primary", "npc_secondary"],
                            "missing_required_actor_ids": [],
                            "carry_forward_actor_ids": [],
                            "multi_npc_initiative_realized": True,
                            "forbidden_planned_actor_ids": [],
                            "forbidden_realized_actor_ids": [],
                            "long_horizon_state_present": True,
                            "intention_threads_active": 3,
                            "private_plan_resolution_present": True,
                            "private_plan_visibility_respected": True,
                            "unrealized_selected_private_plan_actor_ids": [],
                        },
                    },
                    "capability_selection": {
                        "status": "passed",
                        "selected": {"selected_capabilities": ["player.object_interaction.request"]},
                        "actual": {
                            "realized_capabilities": ["player.object_interaction.request"],
                            "forbidden_capability_realized": False,
                        },
                    },
                    "visible_projection": {
                        "status": "passed",
                        "actual": {"visible_block_origin_present": True},
                    },
                    "information_disclosure": {
                        "status": "passed",
                        "expected": {
                            "policy_present": True,
                            "policy_enabled": True,
                            "max_visible_units_per_turn": 1,
                            "commit_impact": "recover",
                        },
                        "selected": {
                            "selected_unit_ids": ["unit_alpha"],
                            "allowed_unit_ids": ["unit_alpha"],
                            "withheld_unit_ids": ["unit_beta"],
                            "forbidden_unit_ids": ["unit_beta"],
                        },
                        "actual": {
                            "contract_pass": True,
                            "visible_unit_ids": ["unit_alpha"],
                            "budget_used": 1,
                            "failure_codes": [],
                        },
                    },
                    "dramatic_irony": {
                        "status": "passed",
                        "expected": {
                            "policy_present": True,
                            "policy_enabled": True,
                            "allowed_surface_modes": ["misread_reaction"],
                            "direct_reveal_allowed": False,
                        },
                        "selected": {
                            "selected_opportunity_ids": ["opportunity_alpha"],
                            "selected_fact_ids": ["fact_alpha"],
                        },
                        "actual": {
                            "status": "selected",
                            "fact_count": 1,
                            "opportunity_count": 1,
                            "selected_opportunity_count": 1,
                            "realization_status": "realized",
                            "realized_opportunity_ids": ["opportunity_alpha"],
                            "visible_anchor_refs": ["opportunity_alpha"],
                            "leak_blocked": False,
                            "violation_codes": [],
                            "contract_pass": True,
                            "surface_mode_contract_pass": True,
                            "hidden_fact_echo_absent": True,
                        },
                    },
                    "narrative_aspect": {
                        "status": "passed",
                        "expected": {
                            "policy_present": True,
                            "candidate_aspects": ["aspect_alpha"],
                            "theme_tracking_policy_present": True,
                            "semantic_tracking_enabled": True,
                            "semantic_profile_aspects": ["aspect_alpha"],
                        },
                        "selected": {
                            "selected_aspects": ["aspect_alpha"],
                            "selected_theme_aspects": ["aspect_alpha"],
                        },
                        "actual": {
                            "realized_aspects": ["aspect_alpha"],
                            "realized_theme_aspects": ["aspect_alpha"],
                            "visible_when_required": True,
                            "semantic_classification_count": 1,
                            "semantic_weak_alignment_count": 0,
                            "semantic_classifications": [
                                {
                                    "aspect_id": "aspect_alpha",
                                    "status": "passed",
                                    "table_b_refs": ["pi_12"],
                                }
                            ],
                        },
                    },
                    "voice_consistency": {
                        "status": "passed",
                        "expected": {
                            "policy_present": True,
                            "semantic_classification_enabled": True,
                        },
                        "actual": {
                            "spoken_line_count": 1,
                            "finding_count": 0,
                            "blocking_finding_count": 0,
                            "drift_class_counts": {},
                            "semantic_classification_count": 1,
                            "semantic_cross_actor_confusion_count": 0,
                        },
                    },
                    "hierarchical_memory": {
                        "status": "passed",
                        "expected": {"policy_present": True, "policy_enabled": True},
                        "selected": {
                            "selected_tiers": ["turn", "session"],
                            "source_canonical_turn_id": "session-aspect:turn:1",
                        },
                        "actual": {
                            "write_allowed": True,
                            "written_item_count": 2,
                            "memory_present": True,
                            "context_item_count": 2,
                            "context_bounded": True,
                            "uncommitted_write_detected": False,
                        },
                    },
                },
            },
        },
        "scores": [
            {"name": "beat_realized", "value": 0.0},
            {"name": "npc_independent_planning_used", "value": 1.0},
            {"name": "npc_long_horizon_state_present", "value": 1.0},
            {"name": "npc_private_plan_resolution_present", "value": 1.0},
            {"name": "npc_private_plan_visibility_respected", "value": 1.0},
            {"name": "npc_intention_threads_carried_forward", "value": 1.0},
            {"name": "npc_required_initiatives_realized", "value": 1.0},
            {"name": "npc_carry_forward_closed", "value": 1.0},
            {"name": "information_disclosure_policy_present", "value": 1.0},
            {"name": "information_disclosure_target_selected", "value": 1.0},
            {"name": "information_disclosure_budget_pass", "value": 1.0},
            {"name": "information_disclosure_premature_reveal_absent", "value": 1.0},
            {"name": "information_disclosure_contract_pass", "value": 1.0},
            {"name": "dramatic_irony_policy_present", "value": 1.0},
            {"name": "dramatic_irony_opportunity_present", "value": 1.0},
            {"name": "dramatic_irony_contract_pass", "value": 1.0},
            {"name": "narrative_aspect_contract_pass", "value": 1.0},
            {"name": "theme_tracking_policy_present", "value": 1.0},
            {"name": "theme_tracking_selected", "value": 1.0},
            {"name": "theme_semantic_classification_present", "value": 1.0},
            {"name": "theme_weak_alignment_absent", "value": 1.0},
            {"name": "theme_tracking_contract_pass", "value": 1.0},
            {"name": "voice_semantic_classification_present", "value": 1.0},
            {"name": "voice_cross_actor_confusion_absent", "value": 1.0},
            {"name": "voice_forbidden_markers_absent", "value": 1.0},
            {"name": "voice_consistency_contract_pass", "value": 1.0},
            {"name": "hierarchical_memory_contract_pass", "value": 1.0},
            {"name": "memory_write_from_committed_turn", "value": 1.0},
        ],
    }
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=trace_payload,
    ):
        out = tool.handler({"trace_id": "trace-aspect-matrix"})

    assert out["ok"] is True
    row = out["rows"][0]
    assert row["session_id"] == "session-aspect"
    assert row["canonical_turn_id"] == "session-aspect:turn:1"
    assert row["environment"] == "staging"
    assert row["turn_aspect_ledger_present"] is True
    assert row["raw_input"].startswith("Ich nehme")
    assert row["action_kind"] == "object_interaction"
    assert row["selected_beat"] == "domestic_disruption"
    assert row["beat_realized"] is False
    assert row["npc_independent_planning_used"] is True
    assert row["npc_long_horizon_state_present"] is True
    assert row["npc_private_plan_resolution_present"] is True
    assert row["npc_private_plan_visibility_respected"] is True
    assert row["npc_intention_threads_carried_forward"] is True
    assert row["npc_required_initiatives_realized"] is True
    assert row["npc_carry_forward_closed"] is True
    assert row["npc_agency_candidate_actor_ids"] == ["npc_primary", "npc_secondary"]
    assert row["npc_agency_claim_readiness_status"] == NPC_AGENCY_CLAIM_BOUNDED_RUNTIME_STATUS
    assert row["npc_agency_full_claim_allowed"] is False
    assert row["information_disclosure_policy_present"] is True
    assert row["information_disclosure_selected_units"] == ["unit_alpha"]
    assert row["information_disclosure_visible_units"] == ["unit_alpha"]
    assert row["information_disclosure_withheld_units"] == ["unit_beta"]
    assert row["information_disclosure_budget_pass"] is True
    assert row["information_disclosure_contract_pass"] == 1.0
    assert row["dramatic_irony_policy_present"] is True
    assert row["dramatic_irony_opportunity_present"] is True
    assert row["dramatic_irony_selected_opportunities"] == ["opportunity_alpha"]
    assert row["dramatic_irony_realized_opportunities"] == ["opportunity_alpha"]
    assert row["dramatic_irony_realization_status"] == "realized"
    assert row["dramatic_irony_leak_blocked"] is False
    assert row["dramatic_irony_contract_pass"] is True
    assert row["dramatic_irony_violation_codes"] == []
    assert row["narrative_aspect_policy_present"] is True
    assert row["selected_narrative_aspects"] == ["aspect_alpha"]
    assert row["realized_narrative_aspects"] == ["aspect_alpha"]
    assert row["narrative_aspect_contract_pass"] == 1.0
    assert row["theme_tracking_policy_present"] is True
    assert row["selected_theme_aspects"] == ["aspect_alpha"]
    assert row["realized_theme_aspects"] == ["aspect_alpha"]
    assert row["theme_semantic_classification_present"] == 1.0
    assert row["theme_semantic_classification_count"] == 1
    assert row["theme_weak_alignment_count"] == 0
    assert row["theme_tracking_contract_pass"] == 1.0
    assert row["voice_consistency_policy_present"] is True
    assert row["voice_semantic_classification_enabled"] is True
    assert row["voice_semantic_classification_count"] == 1
    assert row["voice_cross_actor_confusion_absent"] is True
    assert row["voice_consistency_contract_pass"] == 1.0
    assert row["hierarchical_memory_present"] is True
    assert row["selected_memory_tiers"] == ["turn", "session"]
    assert row["memory_written_item_count"] == 2
    assert row["memory_context_bounded"] is True
    assert row["hierarchical_memory_contract_pass"] == 1.0
    assert row["main_failure"] == "beat_realization_not_visible"


def test_summarize_runtime_aspect_matrix_defaults_to_backend_and_world_engine_turn_traces():
    registry = _registry()
    tool = registry.get("summarize_runtime_aspect_matrix")
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_query_traces",
        return_value=[{"id": "backend-turn", "name": "backend.turn.execute", "observations": [{}]}],
    ) as query:
        out = tool.handler({"limit": 1, "environment": "staging"})

    assert out["ok"] is True
    kwargs = query.call_args.kwargs
    assert kwargs["trace_name"] is None
    assert kwargs["trace_names"] == ("backend.turn.execute", "world-engine.turn.execute")
    assert kwargs["environment"] == "staging"


def test_summarize_runtime_aspect_matrix_recovers_combined_filters_from_full_trace():
    registry = _registry()
    tool = registry.get("summarize_runtime_aspect_matrix")
    trace_payload = {
        "id": "trace-combined-filter",
        "name": "world-engine.turn.execute",
        "environment": "staging",
        "metadata": {"trace_origin": "live_ui", "execution_tier": "staging"},
        "output": {
            "contract": "story_runtime_path_observability.v1",
            "session_id": "session-combined",
            "trace_origin": "live_ui",
            "execution_tier": "staging",
            "environment": "staging",
            "canonical_turn_id": "session-combined:turn:2",
            "turn_aspect_ledger": {
                "session_id": "session-combined",
                "canonical_turn_id": "session-combined:turn:2",
                "turn_number": 2,
                "turn_aspect_ledger": {
                    "beat": {
                        "status": "passed",
                        "selected": {"selected_beat_id": "beat-2"},
                        "actual": {"realized": True},
                    },
                    "capability_selection": {
                        "status": "passed",
                        "selected": {"selected_capabilities": ["player.speech.request"]},
                        "actual": {"realized_capabilities": ["player.speech.request"]},
                    },
                    "narrator_authority": {"status": "not_applicable"},
                    "npc_authority": {
                        "status": "passed",
                        "expected": {"policy": "direct_response"},
                        "actual": {"npc_takeover_detected": False},
                    },
                    "visible_projection": {
                        "status": "passed",
                        "actual": {"visible_block_origin_present": True},
                    },
                },
            },
        },
    }
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_query_traces",
        side_effect=[
            [],
            [{"id": "trace-combined-filter", "name": "world-engine.turn.execute"}],
        ],
    ) as query:
        with patch(
            "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
            return_value=trace_payload,
        ):
            out = tool.handler(
                {
                    "limit": 10,
                    "trace_origin": "live_ui",
                    "execution_tier": "staging",
                    "environment": "staging",
                }
            )

    assert out["ok"] is True
    assert out["count"] == 1
    assert out["rows"][0]["trace_id"] == "trace-combined-filter"
    assert out["rows"][0]["environment"] == "staging"
    assert query.call_count == 2
