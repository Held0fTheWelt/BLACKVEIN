from __future__ import annotations

from unittest.mock import MagicMock, patch

from ai_stack.langfuse.langfuse_evidence import (
    ADR0041_LANGFUSE_EVIDENCE_SCHEMA_VERSION,
    build_adr0041_langfuse_evidence_payload,
    try_emit_adr0041_langfuse_runtime_intelligence_evidence,
)


def test_build_adr0041_langfuse_evidence_payload_json_safe():
    projection = {
        "validator_dispatch_report": {"mode": "plan_enforced", "feature_flag_enabled": True},
        "readiness_aggregation_decision": {"aggregated_readiness": "ok"},
        "readiness_co_authority_preview": {"x": 1},
        "readiness_co_authority_enforcement": {},
    }
    payload = build_adr0041_langfuse_evidence_payload(
        projection=projection, story_session_id="ses-1"
    )
    assert payload["schema_version"] == ADR0041_LANGFUSE_EVIDENCE_SCHEMA_VERSION
    assert payload["story_session_id"] == "ses-1"
    assert payload["validator_dispatch_mode"] == "plan_enforced"
    assert payload["validator_dispatch_feature_flag_enabled"] is True
    assert payload["readiness_aggregation_present"] is True
    assert payload["readiness_aggregation_aggregated"] == "ok"
    assert payload["readiness_co_authority_preview_present"] is True
    assert payload["readiness_co_authority_enforcement_present"] is False
    assert payload["proof_level"] == "local_only"
    assert payload["live_or_staging_evidence"] is False


def test_try_emit_skips_when_langfuse_disabled():
    adapter = MagicMock()
    adapter.is_enabled.return_value = False
    with patch(
        "app.observability.langfuse_adapter.LangfuseAdapter.get_instance",
        return_value=adapter,
    ):
        out = try_emit_adr0041_langfuse_runtime_intelligence_evidence(projection={}, story_session_id="")
    assert out["emitted"] is False
    assert out["reason"] == "langfuse_disabled_or_not_ready"
    assert out["live_or_staging_evidence"] is False


def test_try_emit_skips_without_parent_observation():
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    adapter.resolve_parent_observation_for_nested_span.return_value = None
    with patch(
        "app.observability.langfuse_adapter.LangfuseAdapter.get_instance",
        return_value=adapter,
    ):
        out = try_emit_adr0041_langfuse_runtime_intelligence_evidence(projection={}, story_session_id="")
    assert out["emitted"] is False
    assert out["reason"] == "no_active_langfuse_parent_observation"
    adapter.record_wos_nested_span_observation.assert_not_called()


def test_try_emit_nested_span_and_scores_never_sets_live_claim():
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    adapter.resolve_parent_observation_for_nested_span.return_value = object()
    adapter.record_wos_nested_span_observation.return_value = {
        "emitted": True,
        "langfuse_trace_id": "a" * 32,
        "langfuse_observation_id": "obs-xyz",
        "proof_level": "local_only",
        "live_or_staging_evidence": False,
    }
    adapter.record_adr0041_langfuse_scores.return_value = {"emitted": True}
    projection = {
        "validator_dispatch_report": {"mode": "plan_enforced", "feature_flag_enabled": True},
        "readiness_aggregation_decision": {"aggregated_readiness": "x"},
        "readiness_co_authority_preview": {"p": 1},
    }
    with patch(
        "app.observability.langfuse_adapter.LangfuseAdapter.get_instance",
        return_value=adapter,
    ):
        out = try_emit_adr0041_langfuse_runtime_intelligence_evidence(
            projection=projection, story_session_id="s"
        )
    assert out["emitted"] is True
    assert out["live_or_staging_evidence"] is False
    assert out["proof_level"] == "local_only"
    assert out["score_emission"]["emitted"] is True
    adapter.record_wos_nested_span_observation.assert_called_once()
    adapter.record_adr0041_langfuse_scores.assert_called_once()
