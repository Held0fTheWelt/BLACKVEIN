"""Phase 2 Stage B→C/C Stream Readiness tests.

Validates:
* capability outputs extracted correctly from graph_state
* motivation score sources classified as real vs default
* cut-in readiness is diagnostic-only (live_interruption_supported=False)
* stream readiness proof levels: none, local_only, candidate, primary_ready
* blockers reported accurately
* bundle path unchanged (readiness does not mutate envelope)
* parity aligned → candidate readiness; parity mismatch → blocks primary
* motivation scorer uses real graph outputs when present
* motivation scorer reports default when graph_state absent
* compute_primary_selection: correct decision fields for all combinations
* is_primary_enabled flag default off and explicit enable
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from unittest import mock

from ai_stack.block_stream_dual_mode import (
    PHASE2_BLOCK_STREAM_PRIMARY_ENABLED,
    is_primary_enabled,
)
from ai_stack.director.director_pulse_contracts import (
    CUT_KIND_EM_DASH,
    CUT_KIND_NO_ACTIVE_BLOCK,
    CUT_KIND_SKIP_TO_END,
)
from ai_stack.stream_readiness import (
    PROOF_LEVEL_CANDIDATE,
    PROOF_LEVEL_LOCAL_ONLY,
    PROOF_LEVEL_NONE,
    PROOF_LEVEL_PRIMARY_READY,
    SCORE_SOURCE_DEFAULT,
    SCORE_SOURCE_REAL,
    classify_motivation_score_sources,
    compute_cut_in_readiness,
    compute_primary_selection,
    compute_stream_readiness,
    extract_capability_outputs_from_graph_state,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tid() -> str:
    return str(uuid.uuid4())


def _minimal_block(block_type: str = "narrator") -> dict[str, Any]:
    return {"id": _tid(), "block_type": block_type, "text": "Hello."}


def _stream_event(block: dict[str, Any], tick_id: str | None = None) -> dict[str, Any]:
    return {
        "schema": "block_stream_event.v1",
        "event_id": _tid(),
        "tick_id": tick_id or _tid(),
        "block_type": block.get("block_type", "narrator"),
        "block_payload": dict(block),
        "cut_in_state": "uninterrupted",
        "lane": "visible_scene_output",
        "source": "director",
    }


def _minimal_envelope(
    *,
    bundle_blocks: list[dict] | None = None,
    stream_events: list[dict] | None = None,
    parity_status: str = "aligned",
    parity_warnings: list[str] | None = None,
) -> dict[str, Any]:
    blocks = bundle_blocks or []
    events = stream_events or []
    return {
        "visible_scene_output": {
            "blocks": blocks,
            "block_stream_events": events,
        },
        "diagnostics": {
            "director_pulse": {
                "parity": {
                    "parity_status": parity_status,
                    "parity_warnings": parity_warnings or [],
                    "bundle_block_count": len(blocks),
                    "event_count": len(events),
                    "event_stream_shadow_only": True,
                    "fallback_bundle_available": len(blocks) > 0,
                },
            },
        },
    }


# ── extract_capability_outputs_from_graph_state ───────────────────────────────

class TestExtractCapabilityOutputs:
    def test_none_graph_state_returns_all_none(self):
        out = extract_capability_outputs_from_graph_state(None)
        assert out["scene_energy_output"] is None
        assert out["social_pressure_output"] is None
        assert out["relationship_state_output"] is None
        assert out["narrative_momentum_output"] is None

    def test_empty_dict_returns_all_none(self):
        out = extract_capability_outputs_from_graph_state({})
        assert all(v is None for v in out.values())

    def test_scene_energy_transition_extracted(self):
        gs = {"scene_energy_transition": {"energy_level": 0.7}}
        out = extract_capability_outputs_from_graph_state(gs)
        assert out["scene_energy_output"] == {"energy_level": 0.7}

    def test_social_pressure_state_extracted(self):
        gs = {"social_pressure_state": {"band": "high"}}
        out = extract_capability_outputs_from_graph_state(gs)
        assert out["social_pressure_output"] == {"band": "high"}

    def test_relationship_state_record_preferred_over_relationship_state(self):
        gs = {
            "relationship_state_record": {"pair_states": {}},
            "relationship_state": {"pair_states": {"other": True}},
        }
        out = extract_capability_outputs_from_graph_state(gs)
        assert out["relationship_state_output"] == {"pair_states": {}}

    def test_relationship_state_fallback(self):
        gs = {"relationship_state": {"pair_states": {"x": True}}}
        out = extract_capability_outputs_from_graph_state(gs)
        assert out["relationship_state_output"] == {"pair_states": {"x": True}}

    def test_narrative_momentum_state_extracted(self):
        gs = {"narrative_momentum_state": {"state": "building"}}
        out = extract_capability_outputs_from_graph_state(gs)
        assert out["narrative_momentum_output"] == {"state": "building"}

    def test_non_dict_values_ignored(self):
        gs = {
            "scene_energy_transition": "not-a-dict",
            "social_pressure_state": 42,
            "narrative_momentum_state": None,
        }
        out = extract_capability_outputs_from_graph_state(gs)
        assert out["scene_energy_output"] is None
        assert out["social_pressure_output"] is None
        assert out["narrative_momentum_output"] is None

    def test_all_four_present(self):
        gs = {
            "scene_energy_transition": {"energy_level": 0.5},
            "social_pressure_state": {"band": "medium"},
            "relationship_state_record": {"pair_states": {}},
            "narrative_momentum_state": {"state": "plateau"},
        }
        out = extract_capability_outputs_from_graph_state(gs)
        assert out["scene_energy_output"] is not None
        assert out["social_pressure_output"] is not None
        assert out["relationship_state_output"] is not None
        assert out["narrative_momentum_output"] is not None


# ── classify_motivation_score_sources ────────────────────────────────────────

class TestClassifyMotivationScoreSources:
    def test_no_graph_state_all_default(self):
        src = classify_motivation_score_sources(None)
        assert src["scene_energy"] == SCORE_SOURCE_DEFAULT
        assert src["social_pressure"] == SCORE_SOURCE_DEFAULT
        assert src["relationship_axis_pressure"] == SCORE_SOURCE_DEFAULT
        assert src["narrative_momentum"] == SCORE_SOURCE_DEFAULT

    def test_all_real_when_all_present(self):
        gs = {
            "scene_energy_transition": {"energy_level": 0.5},
            "social_pressure_state": {"band": "medium"},
            "relationship_state_record": {"pair_states": {}},
            "narrative_momentum_state": {"state": "plateau"},
        }
        src = classify_motivation_score_sources(gs)
        assert src["scene_energy"] == SCORE_SOURCE_REAL
        assert src["social_pressure"] == SCORE_SOURCE_REAL
        assert src["relationship_axis_pressure"] == SCORE_SOURCE_REAL
        assert src["narrative_momentum"] == SCORE_SOURCE_REAL

    def test_partial_graph_state_mixed_sources(self):
        gs = {
            "scene_energy_transition": {"energy_level": 0.6},
            # social_pressure_state absent
            "narrative_momentum_state": {"state": "building"},
        }
        src = classify_motivation_score_sources(gs)
        assert src["scene_energy"] == SCORE_SOURCE_REAL
        assert src["social_pressure"] == SCORE_SOURCE_DEFAULT
        assert src["narrative_momentum"] == SCORE_SOURCE_REAL

    def test_returns_all_four_keys(self):
        src = classify_motivation_score_sources({})
        assert set(src.keys()) == {"scene_energy", "social_pressure", "relationship_axis_pressure", "narrative_momentum"}


# ── compute_cut_in_readiness ──────────────────────────────────────────────────

class TestComputeCutInReadiness:
    def test_default_call_no_active_block(self):
        result = compute_cut_in_readiness()
        assert result["computed_cut_kind"] == CUT_KIND_NO_ACTIVE_BLOCK
        assert result["live_interruption_supported"] is False
        assert result["diagnostic_only"] is True

    def test_no_ws_loop_blocked(self):
        result = compute_cut_in_readiness(
            active_block_id="b1",
            active_block_type="actor_line",
            ws_session_loop_supported=False,
        )
        assert result["live_interruption_supported"] is False
        assert result["blocker"] == "ws_session_loop_not_ready"

    def test_ws_loop_ready_but_no_active_block(self):
        result = compute_cut_in_readiness(
            ws_session_loop_supported=True,
            active_block_id=None,
        )
        assert result["live_interruption_supported"] is False
        assert result["blocker"] == "no_active_block"

    def test_ws_loop_ready_and_active_block_no_blocker(self):
        result = compute_cut_in_readiness(
            active_block_id="b1",
            active_block_type="actor_line",
            ws_session_loop_supported=True,
        )
        assert result["live_interruption_supported"] is True
        assert result["blocker"] is None

    def test_actor_line_yields_em_dash(self):
        result = compute_cut_in_readiness(
            active_block_id="b1",
            active_block_type="actor_line",
            ws_session_loop_supported=True,
        )
        assert result["computed_cut_kind"] == CUT_KIND_EM_DASH

    def test_narrator_yields_skip_to_end(self):
        result = compute_cut_in_readiness(
            active_block_id="b1",
            active_block_type="narrator",
            ws_session_loop_supported=True,
        )
        assert result["computed_cut_kind"] == CUT_KIND_SKIP_TO_END

    def test_none_block_type_yields_no_active_block(self):
        result = compute_cut_in_readiness(
            active_block_id=None,
            active_block_type=None,
        )
        assert result["computed_cut_kind"] == CUT_KIND_NO_ACTIVE_BLOCK

    def test_player_input_present_recorded(self):
        result = compute_cut_in_readiness(player_input_present=True)
        assert result["player_input_present"] is True

    def test_diagnostic_only_always_true(self):
        for ws in (True, False):
            result = compute_cut_in_readiness(ws_session_loop_supported=ws)
            assert result["diagnostic_only"] is True


# ── compute_stream_readiness ──────────────────────────────────────────────────

class TestComputeStreamReadiness:
    def test_invalid_envelope_returns_none_proof_level(self):
        result = compute_stream_readiness(None)
        assert result["proof_level"] == PROOF_LEVEL_NONE
        assert result["event_stream_present"] is False
        assert "envelope_invalid" in result["blockers"]

    def test_empty_envelope_dict_proof_none(self):
        result = compute_stream_readiness({})
        assert result["proof_level"] == PROOF_LEVEL_NONE

    def test_aligned_stream_with_frontend_adapter_is_candidate(self):
        block = _minimal_block()
        event = _stream_event(block)
        envelope = _minimal_envelope(
            bundle_blocks=[block],
            stream_events=[event],
            parity_status="aligned",
        )
        result = compute_stream_readiness(
            envelope,
            frontend_event_adapter_deployed=True,
            ws_session_loop_supported=False,
        )
        assert result["proof_level"] == PROOF_LEVEL_CANDIDATE
        assert result["event_stream_present"] is True
        assert result["bundle_fallback_available"] is True

    def test_aligned_stream_no_frontend_adapter_is_local_only(self):
        block = _minimal_block()
        event = _stream_event(block)
        envelope = _minimal_envelope(
            bundle_blocks=[block],
            stream_events=[event],
            parity_status="aligned",
        )
        result = compute_stream_readiness(
            envelope,
            frontend_event_adapter_deployed=False,
            ws_session_loop_supported=False,
        )
        assert result["proof_level"] == PROOF_LEVEL_LOCAL_ONLY

    def test_aligned_stream_ws_ready_and_frontend_adapter_is_primary_ready(self):
        block = _minimal_block()
        event = _stream_event(block)
        envelope = _minimal_envelope(
            bundle_blocks=[block],
            stream_events=[event],
            parity_status="aligned",
        )
        result = compute_stream_readiness(
            envelope,
            frontend_event_adapter_deployed=True,
            ws_session_loop_supported=True,
        )
        assert result["proof_level"] == PROOF_LEVEL_PRIMARY_READY

    def test_parity_mismatch_blocks_primary_readiness(self):
        block = _minimal_block()
        event = _stream_event(block)
        envelope = _minimal_envelope(
            bundle_blocks=[block],
            stream_events=[event],
            parity_status="count_mismatch",
        )
        result = compute_stream_readiness(
            envelope,
            frontend_event_adapter_deployed=True,
            ws_session_loop_supported=True,
        )
        assert result["proof_level"] == PROOF_LEVEL_NONE
        assert any("parity_not_aligned" in b for b in result["blockers"])

    def test_event_stream_empty_reports_blocker(self):
        block = _minimal_block()
        envelope = _minimal_envelope(
            bundle_blocks=[block],
            stream_events=[],
            parity_status="event_missing",
        )
        result = compute_stream_readiness(
            envelope,
            frontend_event_adapter_deployed=True,
            ws_session_loop_supported=False,
        )
        assert result["event_stream_present"] is False
        assert any("event_stream_empty" in b for b in result["blockers"])

    def test_ws_session_loop_not_ready_is_blocker(self):
        block = _minimal_block()
        event = _stream_event(block)
        envelope = _minimal_envelope(
            bundle_blocks=[block],
            stream_events=[event],
            parity_status="aligned",
        )
        result = compute_stream_readiness(
            envelope,
            frontend_event_adapter_deployed=True,
            ws_session_loop_supported=False,
        )
        assert "ws_session_loop_not_ready" in result["blockers"]

    def test_bundle_not_mutated(self):
        block = _minimal_block()
        event = _stream_event(block)
        envelope = _minimal_envelope(bundle_blocks=[block], stream_events=[event])
        original_blocks = list(envelope["visible_scene_output"]["blocks"])
        compute_stream_readiness(envelope)
        assert envelope["visible_scene_output"]["blocks"] == original_blocks

    def test_motivation_sources_from_graph_state(self):
        block = _minimal_block()
        event = _stream_event(block)
        envelope = _minimal_envelope(bundle_blocks=[block], stream_events=[event])
        gs = {
            "scene_energy_transition": {"energy_level": 0.5},
            "social_pressure_state": {"band": "medium"},
        }
        result = compute_stream_readiness(envelope, graph_state=gs)
        assert result["motivation_score_sources"]["scene_energy"] == SCORE_SOURCE_REAL
        assert result["motivation_score_sources"]["social_pressure"] == SCORE_SOURCE_REAL
        assert result["motivation_score_sources"]["relationship_axis_pressure"] == SCORE_SOURCE_DEFAULT
        assert result["motivation_score_sources"]["narrative_momentum"] == SCORE_SOURCE_DEFAULT

    def test_motivation_defaults_when_no_graph_state(self):
        block = _minimal_block()
        event = _stream_event(block)
        envelope = _minimal_envelope(bundle_blocks=[block], stream_events=[event])
        result = compute_stream_readiness(envelope, graph_state=None)
        src = result["motivation_score_sources"]
        assert all(v == SCORE_SOURCE_DEFAULT for v in src.values())

    def test_cut_in_readiness_in_result(self):
        envelope = _minimal_envelope()
        result = compute_stream_readiness(envelope)
        assert "cut_in_readiness" in result
        assert result["cut_in_readiness"]["diagnostic_only"] is True

    def test_ws_session_loop_supported_passed_through(self):
        envelope = _minimal_envelope()
        result = compute_stream_readiness(envelope, ws_session_loop_supported=True)
        assert result["ws_session_loop_supported"] is True

    def test_frontend_event_adapter_not_deployed_is_blocker(self):
        block = _minimal_block()
        event = _stream_event(block)
        envelope = _minimal_envelope(
            bundle_blocks=[block],
            stream_events=[event],
            parity_status="aligned",
        )
        result = compute_stream_readiness(envelope, frontend_event_adapter_deployed=False)
        assert "frontend_event_adapter_not_deployed" in result["blockers"]

    def test_no_blockers_when_all_conditions_met_except_ws(self):
        # candidate level: parity aligned, events present, frontend adapter deployed
        # ws not ready is still a blocker, but that's expected at Stage B→C
        block = _minimal_block()
        event = _stream_event(block)
        envelope = _minimal_envelope(
            bundle_blocks=[block],
            stream_events=[event],
            parity_status="aligned",
        )
        result = compute_stream_readiness(
            envelope,
            graph_state={
                "scene_energy_transition": {"energy_level": 0.5},
                "social_pressure_state": {"band": "low"},
                "relationship_state_record": {"pair_states": {}},
                "narrative_momentum_state": {"state": "plateau"},
            },
            frontend_event_adapter_deployed=True,
            ws_session_loop_supported=False,
        )
        # Only ws blocker remains when all other conditions are met
        assert result["blockers"] == ["ws_session_loop_not_ready"]
        assert result["proof_level"] == PROOF_LEVEL_CANDIDATE

    def test_can_be_primary_candidate_true_when_parity_aligned_and_events_present(self):
        block = _minimal_block()
        event = _stream_event(block)
        envelope = _minimal_envelope(
            bundle_blocks=[block],
            stream_events=[event],
            parity_status="aligned",
        )
        result = compute_stream_readiness(
            envelope,
            frontend_event_adapter_deployed=True,
            ws_session_loop_supported=False,
        )
        assert result["can_be_primary_candidate"] is True

    def test_can_be_primary_candidate_false_when_parity_misaligned(self):
        block = _minimal_block()
        event = _stream_event(block)
        envelope = _minimal_envelope(
            bundle_blocks=[block, _minimal_block()],  # 2 blocks
            stream_events=[event],                     # 1 event
            parity_status="count_mismatch",
        )
        result = compute_stream_readiness(envelope, frontend_event_adapter_deployed=True)
        assert result["can_be_primary_candidate"] is False


# ── compute_primary_selection ─────────────────────────────────────────────────

class TestComputePrimarySelection:
    def _candidate_readiness(self, parity_status: str = "aligned") -> dict:
        block = _minimal_block()
        event = _stream_event(block)
        return {
            "can_be_primary_candidate": True,
            "event_stream_present": True,
            "parity_status": parity_status,
            "bundle_fallback_available": True,
            "blockers": [],
        }

    def _non_candidate_readiness(self, reason: str = "not_aligned") -> dict:
        return {
            "can_be_primary_candidate": False,
            "event_stream_present": True,
            "parity_status": reason,
            "bundle_fallback_available": True,
            "blockers": [f"parity_not_aligned:{reason}"],
        }

    def test_primary_used_when_candidate_and_event_present(self):
        result = compute_primary_selection(self._candidate_readiness())
        assert result["event_stream_primary_attempted"] is True
        assert result["event_stream_primary_used"] is True
        assert result["event_stream_fallback_used"] is False
        assert result["event_stream_fallback_reason"] is None

    def test_parity_status_forwarded(self):
        result = compute_primary_selection(self._candidate_readiness("aligned"))
        assert result["parity_status"] == "aligned"

    def test_bundle_fallback_available_forwarded(self):
        result = compute_primary_selection(self._candidate_readiness())
        assert result["bundle_fallback_available"] is True

    def test_fallback_when_not_candidate(self):
        result = compute_primary_selection(self._non_candidate_readiness("count_mismatch"))
        assert result["event_stream_primary_used"] is False
        assert result["event_stream_fallback_used"] is True
        assert result["event_stream_fallback_reason"] == "readiness_not_candidate"

    def test_fallback_when_event_stream_missing(self):
        readiness = {
            "can_be_primary_candidate": False,
            "event_stream_present": False,
            "parity_status": "event_missing",
            "bundle_fallback_available": True,
        }
        result = compute_primary_selection(readiness)
        assert result["event_stream_fallback_reason"] == "event_stream_missing"

    def test_invalid_readiness_returns_safe_fallback(self):
        result = compute_primary_selection(None)
        assert result["event_stream_primary_used"] is False
        assert result["event_stream_fallback_used"] is True
        assert result["event_stream_fallback_reason"] == "readiness_invalid"

    def test_invalid_readiness_dict_empty_is_safe(self):
        result = compute_primary_selection({})
        assert result["event_stream_primary_used"] is False
        assert result["event_stream_fallback_reason"] == "event_stream_missing"

    def test_all_required_keys_present(self):
        result = compute_primary_selection(self._candidate_readiness())
        for key in (
            "event_stream_primary_attempted",
            "event_stream_primary_used",
            "event_stream_fallback_used",
            "event_stream_fallback_reason",
            "parity_status",
            "bundle_fallback_available",
        ):
            assert key in result, f"missing key: {key}"


# ── is_primary_enabled flag ───────────────────────────────────────────────────

class TestIsPrimaryEnabled:
    def test_default_off(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            os_env_backup = __import__("os").environ.pop(PHASE2_BLOCK_STREAM_PRIMARY_ENABLED, None)
            try:
                assert is_primary_enabled() is False
            finally:
                if os_env_backup is not None:
                    __import__("os").environ[PHASE2_BLOCK_STREAM_PRIMARY_ENABLED] = os_env_backup

    def test_true_enables(self):
        with mock.patch.dict("os.environ", {PHASE2_BLOCK_STREAM_PRIMARY_ENABLED: "true"}):
            assert is_primary_enabled() is True

    def test_yes_enables(self):
        with mock.patch.dict("os.environ", {PHASE2_BLOCK_STREAM_PRIMARY_ENABLED: "yes"}):
            assert is_primary_enabled() is True

    def test_one_enables(self):
        with mock.patch.dict("os.environ", {PHASE2_BLOCK_STREAM_PRIMARY_ENABLED: "1"}):
            assert is_primary_enabled() is True

    def test_false_disables(self):
        with mock.patch.dict("os.environ", {PHASE2_BLOCK_STREAM_PRIMARY_ENABLED: "false"}):
            assert is_primary_enabled() is False

    def test_invalid_value_fails_closed(self):
        with mock.patch.dict("os.environ", {PHASE2_BLOCK_STREAM_PRIMARY_ENABLED: "maybe"}):
            assert is_primary_enabled() is False

    def test_empty_string_fails_closed(self):
        with mock.patch.dict("os.environ", {PHASE2_BLOCK_STREAM_PRIMARY_ENABLED: ""}):
            assert is_primary_enabled() is False

    def test_uppercase_true_enables(self):
        with mock.patch.dict("os.environ", {PHASE2_BLOCK_STREAM_PRIMARY_ENABLED: "TRUE"}):
            assert is_primary_enabled() is True
