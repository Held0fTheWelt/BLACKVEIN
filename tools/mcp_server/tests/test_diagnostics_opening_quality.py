"""Synthetic-payload tests for the opening-quality diagnostic.

Pins the three-state classification contract (see
``tools/mcp_server/diagnostics/opening_quality.py`` module docstring) plus
the trace-selection and JSON-RPC unwrap helpers. No Langfuse, no live
MCP server, no network — every fixture is shaped by hand to mirror the
real wire format observed against the running launcher.
"""

from __future__ import annotations

import json

from tools.mcp_server.diagnostics.opening_quality import (
    Classification,
    _classify,
    _extract_tool_result,
    _parse_responses,
    _select_trace_ids,
)


# --- Classification: HEALTHY_LIVE_OPENING ------------------------------------


def test_classify_healthy_live_opening_from_scores_payload_only():
    scores = {
        "trace_id": "trace_healthy",
        "trace_name": "world-engine.session.create",
        "is_opening_trace": True,
        "deterministic_scores": {
            "opening_shape_contract_pass": 1,
            "live_runtime_contract_pass": 1,
            "live_opening_contract_pass": 1,
            "fallback_absent": 1,
            "non_mock_generation_pass": 1,
        },
        "final_adapter": "openai",
    }
    row = _classify(scores, {})
    assert row.classification is Classification.HEALTHY_LIVE_OPENING
    assert row.is_opening_trace is True
    assert row.final_adapter == "openai"
    assert row.notes == []


def test_classify_healthy_uses_evidence_deterministic_when_score_payload_lacks_it():
    """``build_opening_quality_context`` puts gates under
    ``evidence.deterministic`` rather than top-level ``deterministic_scores``;
    the classifier must accept either source."""
    scores = {
        "trace_id": "trace_healthy_ctx",
        "trace_name": "world-engine.session.create",
        "is_opening_trace": True,
    }
    context = {
        "evidence": {
            "deterministic": {
                "opening_shape_contract_pass": 1.0,
                "live_runtime_contract_pass": 1.0,
                "live_opening_contract_pass": 1.0,
            },
            "path_summary": {"final_adapter": "openai"},
        }
    }
    row = _classify(scores, context)
    assert row.classification is Classification.HEALTHY_LIVE_OPENING
    assert row.final_adapter == "openai"


# --- Classification: DEGRADED_FALLBACK_OPENING -------------------------------


def test_classify_degraded_fallback_opening_with_explicit_final_adapter():
    """Synthetic payload that mirrors the historical evidence shape where
    ``final_adapter`` IS exposed (e.g. via direct Langfuse score-metadata
    access). ADR-0033 §13.1/§13.7 says this is the contractually correct
    degraded state."""
    scores = {
        "trace_id": "c828854ea0d5c29d7ea41f8a25d15772",
        "trace_name": "world-engine.session.create",
        "is_opening_trace": True,
        "deterministic_scores": {
            "opening_shape_contract_pass": 1,
            "live_runtime_contract_pass": 0,
            "live_opening_contract_pass": 0.0,
            "fallback_absent": 0,
            "non_mock_generation_pass": 0,
            "live_runtime_visible_surface_pass": 0,
        },
        "final_adapter": "ldss_fallback",
        "fallback_reason": "dramatic_effect_reject_empty_fluency",
        "degradation_chain": [
            "dramatic_effect_reject_empty_fluency",
            "ldss_fallback_after_live_opening_failure",
        ],
    }
    row = _classify(scores, {})
    assert row.classification is Classification.DEGRADED_FALLBACK_OPENING
    assert row.final_adapter == "ldss_fallback"
    assert row.fallback_reason == "dramatic_effect_reject_empty_fluency"
    assert row.degradation_chain == [
        "dramatic_effect_reject_empty_fluency",
        "ldss_fallback_after_live_opening_failure",
    ]
    assert any("ADR-0033" in n for n in row.notes), (
        f"degraded fallback must surface ADR-0033 reference, got notes={row.notes}"
    )


def test_classify_degraded_fallback_opening_from_gate_pair_signature_alone():
    """The MCP score tool today does NOT expose ``final_adapter``; the
    classifier must still recognise the LDSS-fallback state from the
    canonical gate pair (``fallback_absent==0`` AND
    ``non_mock_generation_pass==0``) per ADR-0033 §13.1. This pins the
    real-world Langfuse payload shape observed in production."""
    scores = {
        "trace_id": "3167411fe9a372acca63cf9490afb945",
        "trace_name": "world-engine.session.create",
        "is_opening_trace": True,
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "deterministic_scores": {
            "opening_shape_contract_pass": 1,
            "live_runtime_contract_pass": 0,
            "live_opening_contract_pass": 0.0,
            "fallback_absent": 0,
            "non_mock_generation_pass": 0,
            "live_runtime_visible_surface_pass": 0,
            "actor_lane_safety_pass": 1,
            "rag_context_attached": 1,
            "usage_present": 1,
            "visible_output_present": 1,
        },
    }
    row = _classify(scores, {})
    assert row.classification is Classification.DEGRADED_FALLBACK_OPENING
    assert row.final_adapter is None, (
        "MCP score tool does not expose final_adapter; classifier must rely "
        "on the deterministic gate-pair signature instead."
    )
    assert any("gate-pair signature" in n for n in row.notes)


def test_classify_opening_failed_without_ldss_fallback_is_unclassified_with_warning():
    """Opening that fails gates but lacks BOTH ``final_adapter='ldss_fallback'``
    AND the gate-pair signature is a real regression suspect — must NOT be
    silently classified as healthy or degraded."""
    scores = {
        "trace_id": "trace_unknown",
        "trace_name": "world-engine.session.create",
        "is_opening_trace": True,
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "deterministic_scores": {
            "opening_shape_contract_pass": 1,
            "live_runtime_contract_pass": 0,
            "live_opening_contract_pass": 0,
            "fallback_absent": 1,  # explicitly NOT the LDSS-fallback signature
            "non_mock_generation_pass": 1,
        },
        "final_adapter": "openai",
    }
    row = _classify(scores, {})
    assert row.classification is Classification.UNCLASSIFIED
    assert any("regression suspected" in n for n in row.notes)


# --- Classification: TEST_TRACE ----------------------------------------------


def test_classify_pytest_origin_is_test_trace():
    """A trace from a pytest run must classify as TEST_TRACE regardless of
    its gate values; the live-runtime contract does not apply."""
    scores = {
        "trace_id": "d55b8daf7feb42e9cba594a6bf8a581f",
        "trace_name": "world-engine.turn.execute",
        "is_opening_trace": True,
        "trace_origin": "pytest",
        "execution_tier": "contract_test",
        "deterministic_scores": {
            "opening_shape_contract_pass": 1,
            "live_runtime_contract_pass": 0,
            "live_opening_contract_pass": 0.0,
            "fallback_absent": 1,
            "non_mock_generation_pass": 0,
        },
    }
    row = _classify(scores, {})
    assert row.classification is Classification.TEST_TRACE
    assert row.trace_origin == "pytest"
    assert row.execution_tier == "contract_test"
    assert any("live-runtime contract does not apply" in n for n in row.notes)


def test_classify_contract_test_tier_is_test_trace_even_without_pytest_origin():
    scores = {
        "trace_id": "t_test_tier",
        "trace_name": "world-engine.session.create",
        "is_opening_trace": True,
        "trace_origin": "ai_testing",
        "execution_tier": "contract_test",
        "deterministic_scores": {},
    }
    row = _classify(scores, {})
    assert row.classification is Classification.TEST_TRACE


# --- Classification: NON_OPENING_OK ------------------------------------------


def test_classify_non_opening_turn_execute_with_not_applicable_string():
    scores = {
        "trace_id": "trace_turn_execute",
        "trace_name": "world-engine.turn.execute",
        "is_opening_trace": False,
        "deterministic_scores": {
            "live_opening_contract_pass": "not_applicable",
        },
    }
    row = _classify(scores, {})
    assert row.classification is Classification.NON_OPENING_OK
    assert row.is_opening_trace is False


def test_classify_non_opening_with_absent_live_opening_score_is_ok():
    """Some turn.execute traces never emit ``live_opening_contract_pass``
    (it is opening-only). Absent should classify as NON_OPENING_OK."""
    scores = {
        "trace_id": "trace_turn_execute_2",
        "trace_name": "world-engine.turn.execute",
        "is_opening_trace": False,
        "deterministic_scores": {},
    }
    row = _classify(scores, {})
    assert row.classification is Classification.NON_OPENING_OK


def test_classify_non_opening_with_unexpected_pass_value_warns():
    scores = {
        "trace_id": "trace_weird",
        "trace_name": "world-engine.turn.execute",
        "is_opening_trace": False,
        "deterministic_scores": {"live_opening_contract_pass": 1},
    }
    row = _classify(scores, {})
    assert row.classification is Classification.UNCLASSIFIED
    assert any("expected 'not_applicable'" in n for n in row.notes)


# --- Classification: UNCLASSIFIED edge cases ---------------------------------


def test_classify_missing_payloads_returns_unclassified():
    row = _classify({}, {})
    assert row.classification is Classification.UNCLASSIFIED
    assert row.trace_id == ""


def test_classify_propagates_payload_error_markers_into_notes():
    row = _classify({"_error": "rpc_error"}, {"_error": "no_result"})
    assert row.classification is Classification.UNCLASSIFIED
    assert any("scores_payload error" in n for n in row.notes)
    assert any("context_payload error" in n for n in row.notes)


# --- Trace selection ---------------------------------------------------------


def test_select_trace_ids_picks_first_matrix_row_when_no_turn_execute_requested():
    matrix = {
        "rows": [
            {"trace_id": "open_1", "name": "world-engine.session.create"},
            {"trace_id": "open_2", "name": "world-engine.session.create"},
        ]
    }
    assert _select_trace_ids(matrix, with_turn_execute=False) == ["open_1"]


def test_select_trace_ids_adds_turn_execute_from_query_payload():
    matrix = {"rows": [{"trace_id": "open_1", "name": "world-engine.session.create"}]}
    query = {
        "traces": [
            {"trace_id": "tx_1", "name": "world-engine.session.create"},
            {"trace_id": "tx_2", "name": "world-engine.turn.execute"},
            {"trace_id": "tx_3", "name": "world-engine.turn.execute"},
        ]
    }
    selected = _select_trace_ids(matrix, with_turn_execute=True, query_payload=query)
    assert selected == ["open_1", "tx_2"]


def test_select_trace_ids_skips_turn_execute_pick_when_already_chosen_as_opening():
    matrix = {"rows": [{"trace_id": "shared", "name": "world-engine.session.create"}]}
    query = {
        "traces": [
            {"trace_id": "shared", "name": "world-engine.turn.execute"},
            {"trace_id": "tx_other", "name": "world-engine.turn.execute"},
        ]
    }
    selected = _select_trace_ids(matrix, with_turn_execute=True, query_payload=query)
    assert selected == ["shared", "tx_other"]


def test_select_trace_ids_respects_overrides():
    selected = _select_trace_ids({}, with_turn_execute=True, override=["a", "b", "c"])
    assert selected == ["a", "b"]


def test_select_trace_ids_returns_empty_when_nothing_matches():
    selected = _select_trace_ids({}, with_turn_execute=True, query_payload={"traces": []})
    assert selected == []


# --- JSON-RPC unwrap ---------------------------------------------------------


def test_extract_tool_result_unwraps_mcp_content_text_json():
    rpc = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "content": [{"type": "text", "text": json.dumps({"ok": True, "rows": [1, 2]})}]
        },
    }
    payload = _extract_tool_result(rpc)
    assert payload == {"ok": True, "rows": [1, 2]}


def test_extract_tool_result_returns_error_marker_for_rpc_error():
    rpc = {"jsonrpc": "2.0", "id": 2, "error": {"code": -32601, "message": "method not found"}}
    payload = _extract_tool_result(rpc)
    assert payload["_error"] == "rpc_error"


def test_extract_tool_result_returns_error_marker_for_non_json_text():
    rpc = {"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "not json"}]}}
    payload = _extract_tool_result(rpc)
    assert payload["_error"] == "result_text_not_json"


def test_extract_tool_result_handles_none_response():
    payload = _extract_tool_result(None)
    assert payload["_error"] == "non_dict_response"


def test_parse_responses_skips_blank_lines_and_notifications():
    stdout = "\n".join(
        [
            "",
            json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}),
            "not-json-line-from-stderr-bleed",
            json.dumps({"jsonrpc": "2.0", "id": 2, "result": {"content": []}}),
        ]
    )
    parsed = _parse_responses(stdout)
    assert set(parsed.keys()) == {1, 2}


# --- Report dataclass shape --------------------------------------------------


def test_classification_row_serialises_through_report_to_dict():
    """Pin the public to_dict() shape so consumers (CI summary, dashboards)
    can rely on the field names without reading source."""
    from tools.mcp_server.diagnostics.opening_quality import OpeningQualityReport

    row = _classify(
        {
            "trace_id": "t1",
            "trace_name": "world-engine.session.create",
            "is_opening_trace": True,
            "deterministic_scores": {
                "opening_shape_contract_pass": 1,
                "live_runtime_contract_pass": 1,
                "live_opening_contract_pass": 1,
            },
            "final_adapter": "openai",
        },
        {},
    )
    report = OpeningQualityReport(
        generated_at="2026-05-08T00:00:00+00:00",
        selected_trace_ids=["t1"],
        matrix={},
        judges={},
        query_traces=None,
        scores_by_trace={},
        contexts_by_trace={},
        rows=[row],
    )
    d = report.to_dict()
    assert d["selected_trace_ids"] == ["t1"]
    row_d = d["rows"][0]
    assert row_d["classification"] == "HEALTHY_LIVE_OPENING"
    assert row_d["trace_id"] == "t1"
    for key in (
        "deterministic_scores",
        "degradation_chain",
        "final_adapter",
        "fallback_reason",
        "trace_origin",
        "execution_tier",
        "notes",
    ):
        assert key in row_d, f"public report row missing {key!r}"


# --- Stable import-shape -----------------------------------------------------


def test_public_surface_imports_from_package_root():
    """Anything documented in the package ``__init__`` must keep importing."""
    from tools.mcp_server.diagnostics import (  # noqa: F401
        Classification,
        ClassificationRow,
        OpeningQualityReport,
        run_opening_quality_probe,
    )
