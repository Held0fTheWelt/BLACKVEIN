"""Contract-style coverage for small world-engine surfaces (audit, metrics, health, fallback).

These tests call production helpers directly with real in-memory payloads — no patched HTTP,
no fake story-runtime managers. They guard operator telemetry and safe-fallback contracts.
"""

from __future__ import annotations

import json
import logging

import pytest

from ai_stack.actor_survival_telemetry import build_actor_survival_telemetry
from app.narrative.fallback_generator import build_safe_fallback_output
from app.narrative.package_models import SceneFallbackBundle
from app.narrative.runtime_health import RuntimeHealthCounters
from app.observability.audit_log import log_story_runtime_failure, log_story_turn_event
from app.observability.runtime_metrics import StoryRuntimeMetrics


@pytest.fixture(autouse=True)
def _reset_wos_audit_logger_handlers() -> None:
    """``audit_log`` attaches a StreamHandler to stderr once; capsys closes that stream between tests."""
    name = "wos.world_engine.audit"
    log = logging.getLogger(name)
    for h in list(log.handlers):
        log.removeHandler(h)
    yield
    for h in list(log.handlers):
        log.removeHandler(h)


def _minimal_turn_state() -> dict:
    return {
        "turn_number": 3,
        "trace_id": "trace-contract",
        "raw_input": "hello from contract test",
        "selected_responder_set": [
            {"actor_id": "annette_reille", "role": "primary_responder", "preferred_reaction_order": 0},
        ],
        "responder_id": "annette_reille",
        "secondary_responder_ids": [],
        "spoken_lines": [{"speaker_id": "annette_reille", "text": "Yes?"}],
        "action_lines": [],
        "initiative_events": [],
        "generation": {
            "metadata": {
                "structured_output": {
                    "spoken_lines": [{"speaker_id": "annette_reille", "text": "Yes?"}],
                    "action_lines": [],
                    "initiative_events": [],
                }
            }
        },
        "visible_output_bundle": {
            "spoken_lines": [{"speaker_id": "annette_reille", "text": "Yes?"}],
            "action_lines": [],
        },
        "pacing_mode": "standard",
        "silence_brevity_decision": {"mode": "normal"},
        "prior_planner_truth": {},
        "quality_class": "standard",
        "degradation_signals": [],
    }


@pytest.mark.contract
def test_log_story_turn_event_emits_structured_json(capsys: pytest.CaptureFixture[str]) -> None:
    survival = build_actor_survival_telemetry(
        _minimal_turn_state(),
        generation_ok=True,
        validation_ok=True,
        commit_applied=True,
        fallback_taken=False,
    )
    vitality = survival["vitality_telemetry_v1"]
    passivity = survival["passivity_diagnosis_v1"]

    log_story_turn_event(
        trace_id="trace-contract",
        story_session_id="sess-1",
        module_id="god_of_carnage",
        turn_number=2,
        player_input="stage whisper",
        outcome="committed",
        quality_class="standard",
        degradation_signals=["thin_edge"],
        vitality_telemetry=vitality,
        passivity_diagnosis=passivity,
        llm_invocation_details={"adapter": "mock"},
        validation_details={"mode": "schema_only"},
        commit_details={"beat_id": "b1"},
        retrieval_details={"hits": 0},
    )
    err = capsys.readouterr().err
    json_lines = [ln for ln in err.strip().splitlines() if ln.strip().startswith("{")]
    assert json_lines, f"expected JSON audit line on stderr, got: {err!r}"
    payload = json.loads(json_lines[-1])
    assert payload["event"] == "story.turn.execute"
    assert payload["story_session_id"] == "sess-1"
    assert payload["player_input_hash"]
    assert payload["vitality_telemetry_v1"]
    assert payload["passivity_diagnosis_v1"]


@pytest.mark.contract
def test_log_story_runtime_failure_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    log_story_runtime_failure(
        trace_id="t-fail",
        story_session_id=None,
        operation="probe",
        message="something went wrong" * 20,
        failure_class="test_failure",
    )
    err = capsys.readouterr().err
    json_lines = [ln for ln in err.strip().splitlines() if ln.strip().startswith("{")]
    assert json_lines, f"expected JSON audit line on stderr, got: {err!r}"
    payload = json.loads(json_lines[-1])
    assert payload["event"] == "story.runtime.failure"
    assert payload["failure_class"] == "test_failure"
    assert len(payload["message"]) <= 500


@pytest.mark.contract
def test_story_runtime_metrics_summary_bounded() -> None:
    m = StoryRuntimeMetrics()
    for i in range(55):
        m.incr("turns", seq=i)
    s = m.summary()
    assert s["counters"]["turns"] == 55
    assert len(s["recent_events"]) == 50
    assert s["recent_events"][-1]["seq"] == 54


@pytest.mark.contract
def test_runtime_health_counters_summary_rates() -> None:
    h = RuntimeHealthCounters()
    assert h.summary()["total_turns"] == 0
    h.record_first_pass_success("m1", "s1")
    h.record_corrective_retry("m1", "s2")
    h.record_safe_fallback("m1", "s3")
    s = h.summary()
    assert s["total_turns"] == 3
    assert s["first_pass_success_rate"] == pytest.approx(1 / 3)
    assert s["corrective_retry_rate"] == pytest.approx(1 / 3)
    assert s["safe_fallback_rate"] == pytest.approx(1 / 3)
    assert len(s["events"]) == 3


@pytest.mark.contract
def test_build_safe_fallback_output_respects_bundle_and_default() -> None:
    bundle = SceneFallbackBundle(generic_safe_line="Quiet beat.")
    out_with = build_safe_fallback_output(fallback_bundle=bundle, reason="blocked_x")
    assert out_with.narrative_response == "Quiet beat."
    assert out_with.blocked_turn_reason == "blocked_x"
    out_default = build_safe_fallback_output(fallback_bundle=None, reason="none")
    assert "tension" in out_default.narrative_response.lower()
    assert out_default.intent_summary == "safe_fallback"
