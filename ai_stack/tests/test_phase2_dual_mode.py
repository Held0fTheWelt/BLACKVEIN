"""Phase 2 Stage B — Dual Mode Block Stream tests.

Validates:
* bundle output is unchanged when dual mode is active
* block_stream_events are emitted in parallel
* each event references the same tick_id
* one event = one block payload (dict, not list)
* parity diagnostics: aligned / mismatch / event_missing / not_applicable
* feature flag default is off
* typewriter compatibility shim
* no Pi/Π runtime keys in dual-mode output
* no Commit/Readiness or validation_outcome change
* no fixed speaker queue concepts
"""

from __future__ import annotations

import os
import re
import uuid
from typing import Any
from unittest import mock

import pytest

from ai_stack.block_stream_dual_mode import (
    PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED,
    augment_envelope_with_block_stream,
    block_stream_event_to_block_shape,
    bundle_blocks_to_stream_events,
    compute_parity_diagnostics,
    is_dual_mode_enabled,
)
from ai_stack.contracts.director_pulse_contracts import (
    LANE_PLAYER_HINT,
    LANE_VISIBLE_SCENE_OUTPUT,
    SCHEMA_BLOCK_STREAM_EVENT,
    SCHEMA_DIRECTOR_TICK_DECISION,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tid() -> str:
    return str(uuid.uuid4())


def _block(block_type: str = "narrator", text: str = "Hello.") -> dict[str, Any]:
    return {
        "id": _tid(),
        "block_type": block_type,
        "text": text,
        "speaker_label": "",
        "actor_id": None,
        "delivery": {"mode": "typewriter", "characters_per_second": 44},
    }


def _envelope(
    blocks: list[dict[str, Any]] | None = None,
    npc_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Minimal scene_turn_envelope.v2 dict for testing augmentation."""
    return {
        "contract": "scene_turn_envelope.v2",
        "content_module_id": "god_of_carnage",
        "runtime_profile_id": "god_of_carnage_solo",
        "runtime_module_id": "solo_story_runtime",
        "selected_player_role": "annette",
        "human_actor_id": "annette",
        "npc_actor_ids": list(npc_ids or ["michel", "veronique"]),
        "npc_agency_plan": None,
        "visible_scene_output": {
            "contract": "visible_scene_output.blocks.v1",
            "blocks": list(blocks or []),
        },
        "diagnostics": {
            "live_dramatic_scene_simulator": {"status": "approved", "invoked": True},
            "npc_agency": {"primary_responder_id": "michel"},
        },
    }


# ── Feature flag ──────────────────────────────────────────────────────────────

class TestFeatureFlag:

    def test_default_is_off(self):
        """PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED is False by default."""
        with mock.patch.dict(os.environ, {PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED: "false"}):
            assert is_dual_mode_enabled() is False

    def test_enable_via_env_true(self):
        with mock.patch.dict(os.environ, {PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED: "true"}):
            assert is_dual_mode_enabled() is True

    def test_enable_via_env_1(self):
        with mock.patch.dict(os.environ, {PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED: "1"}):
            assert is_dual_mode_enabled() is True

    def test_enable_via_env_yes(self):
        with mock.patch.dict(os.environ, {PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED: "yes"}):
            assert is_dual_mode_enabled() is True

    def test_flag_off_leaves_env_unset(self):
        env_without_flag = {k: v for k, v in os.environ.items() if k != PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED}
        with mock.patch.dict(os.environ, env_without_flag, clear=True):
            assert is_dual_mode_enabled() is False

    def test_flag_constant_is_string(self):
        assert isinstance(PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED, str)
        assert "PHASE2" in PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED


# ── bundle_blocks_to_stream_events ────────────────────────────────────────────

class TestBundleBlocksToStreamEvents:

    def test_one_event_per_bundle_block(self):
        blocks = [_block("narrator"), _block("actor_line"), _block("actor_action")]
        events = bundle_blocks_to_stream_events(blocks, tick_id=_tid())
        assert len(events) == 3

    def test_empty_bundle_returns_empty_events(self):
        assert bundle_blocks_to_stream_events([], tick_id=_tid()) == []

    def test_each_event_references_same_tick_id(self):
        tid = _tid()
        blocks = [_block(), _block()]
        events = bundle_blocks_to_stream_events(blocks, tick_id=tid)
        for event in events:
            assert event["tick_id"] == tid

    def test_event_schema_version(self):
        events = bundle_blocks_to_stream_events([_block()], tick_id=_tid())
        assert events[0]["schema_version"] == SCHEMA_BLOCK_STREAM_EVENT

    def test_block_payload_is_dict_not_list(self):
        events = bundle_blocks_to_stream_events([_block()], tick_id=_tid())
        payload = events[0]["block_payload"]
        assert isinstance(payload, dict)
        assert not isinstance(payload, list)

    def test_block_payload_preserves_original_block(self):
        block = _block("actor_line", "Bonjour!")
        events = bundle_blocks_to_stream_events([block], tick_id=_tid())
        payload = events[0]["block_payload"]
        assert payload["text"] == "Bonjour!"
        assert payload["block_type"] == "actor_line"

    def test_actor_line_goes_to_visible_scene_output_lane(self):
        events = bundle_blocks_to_stream_events([_block("actor_line")], tick_id=_tid())
        assert events[0]["lane"] == LANE_VISIBLE_SCENE_OUTPUT

    def test_souffleuse_goes_to_player_hint_lane(self):
        events = bundle_blocks_to_stream_events([_block("souffleuse")], tick_id=_tid())
        assert events[0]["lane"] == LANE_PLAYER_HINT

    def test_narrator_goes_to_visible_scene_output_lane(self):
        events = bundle_blocks_to_stream_events([_block("narrator")], tick_id=_tid())
        assert events[0]["lane"] == LANE_VISIBLE_SCENE_OUTPUT

    def test_unknown_block_type_normalises_to_narrator(self):
        events = bundle_blocks_to_stream_events([_block("some_unknown_type")], tick_id=_tid())
        assert events[0]["block_type"] == "narrator"

    def test_system_boot_normalises_to_narrator(self):
        events = bundle_blocks_to_stream_events([_block("system_boot")], tick_id=_tid())
        assert events[0]["block_type"] == "narrator"

    def test_each_event_has_unique_event_id(self):
        blocks = [_block(), _block(), _block()]
        events = bundle_blocks_to_stream_events(blocks, tick_id=_tid())
        ids = [e["event_id"] for e in events]
        assert len(ids) == len(set(ids))

    def test_original_blocks_not_mutated(self):
        block = _block("narrator", "original text")
        original_text = block["text"]
        bundle_blocks_to_stream_events([block], tick_id=_tid())
        assert block["text"] == original_text

    def test_no_pi_keys_in_events(self):
        events = bundle_blocks_to_stream_events([_block(), _block("actor_line")], tick_id=_tid())
        pi_pattern = re.compile(r"\bPi?\d+\b|capability_\d+", re.IGNORECASE)
        for event in events:
            for key in event:
                assert not pi_pattern.search(key), f"Pi/Π key found in event: {key!r}"


# ── Parity diagnostics ────────────────────────────────────────────────────────

class TestParityDiagnostics:

    def _make_event(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_BLOCK_STREAM_EVENT,
            "event_id": _tid(),
            "tick_id": _tid(),
            "block_type": "narrator",
            "block_payload": {"id": _tid(), "text": "x"},
            "cut_in_state": "uninterrupted",
            "lane": LANE_VISIBLE_SCENE_OUTPUT,
            "source": "director",
        }

    def test_aligned_when_counts_and_types_match(self):
        blocks = [_block("narrator"), _block("actor_line")]
        events = [
            {**self._make_event(), "block_type": "narrator"},
            {**self._make_event(), "block_type": "actor_line"},
        ]
        parity = compute_parity_diagnostics(blocks, events)
        assert parity["parity_status"] == "aligned"
        assert parity["parity_warnings"] == []

    def test_count_mismatch_when_different_counts(self):
        blocks = [_block(), _block(), _block()]
        events = [self._make_event()]
        parity = compute_parity_diagnostics(blocks, events)
        assert parity["parity_status"] == "count_mismatch"
        assert len(parity["parity_warnings"]) >= 1

    def test_event_missing_when_stream_empty_bundle_nonempty(self):
        parity = compute_parity_diagnostics([_block()], [])
        assert parity["parity_status"] == "event_missing"

    def test_bundle_missing_when_bundle_empty_stream_nonempty(self):
        parity = compute_parity_diagnostics([], [self._make_event()])
        assert parity["parity_status"] == "bundle_missing"

    def test_not_applicable_when_both_empty(self):
        parity = compute_parity_diagnostics([], [])
        assert parity["parity_status"] == "not_applicable"

    def test_type_mismatch_when_types_differ(self):
        blocks = [_block("narrator"), _block("actor_line")]
        events = [
            {**self._make_event(), "block_type": "actor_action"},
            {**self._make_event(), "block_type": "narrator"},
        ]
        parity = compute_parity_diagnostics(blocks, events)
        assert parity["parity_status"] == "type_mismatch"

    def test_bundle_block_count_field(self):
        parity = compute_parity_diagnostics([_block(), _block()], [])
        assert parity["bundle_block_count"] == 2

    def test_event_count_field(self):
        events = [self._make_event(), self._make_event()]
        parity = compute_parity_diagnostics([], events)
        assert parity["event_count"] == 2

    def test_event_stream_shadow_only_always_true(self):
        parity = compute_parity_diagnostics([], [])
        assert parity["event_stream_shadow_only"] is True

    def test_fallback_bundle_available_true_when_bundle_nonempty(self):
        parity = compute_parity_diagnostics([_block()], [])
        assert parity["fallback_bundle_available"] is True

    def test_fallback_bundle_available_false_when_bundle_empty(self):
        parity = compute_parity_diagnostics([], [self._make_event()])
        assert parity["fallback_bundle_available"] is False


# ── Typewriter compatibility shim ─────────────────────────────────────────────

class TestTypewriterCompatShim:

    def _event(self, block_type: str = "narrator") -> dict[str, Any]:
        block = _block(block_type)
        return {
            "schema_version": SCHEMA_BLOCK_STREAM_EVENT,
            "event_id": "ev-1",
            "tick_id": "tick-1",
            "block_type": block_type,
            "block_payload": block,
            "cut_in_state": "uninterrupted",
            "lane": LANE_VISIBLE_SCENE_OUTPUT,
            "source": "director",
        }

    def test_returns_dict(self):
        shape = block_stream_event_to_block_shape(self._event())
        assert isinstance(shape, dict)

    def test_preserves_block_content(self):
        shape = block_stream_event_to_block_shape(self._event("actor_line"))
        assert shape["block_type"] == "actor_line"

    def test_adds_stream_event_id(self):
        shape = block_stream_event_to_block_shape(self._event())
        assert "_stream_event_id" in shape
        assert shape["_stream_event_id"] == "ev-1"

    def test_adds_tick_id(self):
        shape = block_stream_event_to_block_shape(self._event())
        assert "_tick_id" in shape
        assert shape["_tick_id"] == "tick-1"

    def test_adds_lane(self):
        shape = block_stream_event_to_block_shape(self._event())
        assert "_lane" in shape

    def test_malformed_event_returns_empty_dict(self):
        assert block_stream_event_to_block_shape({}) == {}
        assert block_stream_event_to_block_shape(None) == {}  # type: ignore

    def test_original_event_not_mutated(self):
        event = self._event()
        original_keys = set(event.keys())
        block_stream_event_to_block_shape(event)
        assert set(event.keys()) == original_keys


# ── augment_envelope_with_block_stream ────────────────────────────────────────

class TestAugmentEnvelope:

    def test_bundle_blocks_unchanged_after_augmentation(self):
        blocks = [_block("narrator", "Scene text."), _block("actor_line", "A line.")]
        env = _envelope(blocks=blocks)
        result = augment_envelope_with_block_stream(env)
        assert result["visible_scene_output"]["blocks"] == env["visible_scene_output"]["blocks"]

    def test_visible_scene_output_contract_unchanged(self):
        env = _envelope(blocks=[_block()])
        result = augment_envelope_with_block_stream(env)
        assert result["visible_scene_output"]["contract"] == "visible_scene_output.blocks.v1"

    def test_block_stream_events_added_to_visible_scene_output(self):
        env = _envelope(blocks=[_block(), _block("actor_line")])
        result = augment_envelope_with_block_stream(env)
        assert "block_stream_events" in result["visible_scene_output"]

    def test_block_stream_events_is_list(self):
        env = _envelope(blocks=[_block()])
        result = augment_envelope_with_block_stream(env)
        assert isinstance(result["visible_scene_output"]["block_stream_events"], list)

    def test_one_stream_event_per_bundle_block(self):
        blocks = [_block(), _block("actor_line"), _block("actor_action")]
        env = _envelope(blocks=blocks)
        result = augment_envelope_with_block_stream(env)
        events = result["visible_scene_output"]["block_stream_events"]
        assert len(events) == 3

    def test_all_events_share_same_tick_id(self):
        env = _envelope(blocks=[_block(), _block()])
        result = augment_envelope_with_block_stream(env)
        events = result["visible_scene_output"]["block_stream_events"]
        tick_ids = {e["tick_id"] for e in events}
        assert len(tick_ids) == 1

    def test_director_pulse_added_to_diagnostics(self):
        env = _envelope(blocks=[_block()])
        result = augment_envelope_with_block_stream(env)
        assert "director_pulse" in result["diagnostics"]

    def test_director_pulse_has_required_keys(self):
        env = _envelope(blocks=[_block()])
        result = augment_envelope_with_block_stream(env)
        pulse = result["diagnostics"]["director_pulse"]
        assert "director_tick_decision" in pulse
        assert "npc_motivation_scores" in pulse
        assert "parity" in pulse
        assert "shadow_only" in pulse
        assert "dual_mode_enabled" in pulse

    def test_shadow_only_is_always_true(self):
        env = _envelope(blocks=[_block()])
        result = augment_envelope_with_block_stream(env)
        assert result["diagnostics"]["director_pulse"]["shadow_only"] is True

    def test_dual_mode_enabled_is_true_in_pulse(self):
        env = _envelope(blocks=[_block()])
        result = augment_envelope_with_block_stream(env)
        assert result["diagnostics"]["director_pulse"]["dual_mode_enabled"] is True

    def test_existing_diagnostics_preserved(self):
        env = _envelope(blocks=[_block()])
        result = augment_envelope_with_block_stream(env)
        assert "live_dramatic_scene_simulator" in result["diagnostics"]
        assert "npc_agency" in result["diagnostics"]

    def test_tick_decision_schema_version(self):
        env = _envelope(blocks=[_block()])
        result = augment_envelope_with_block_stream(env)
        tick_dec = result["diagnostics"]["director_pulse"]["director_tick_decision"]
        assert tick_dec["schema_version"] == SCHEMA_DIRECTOR_TICK_DECISION

    def test_npc_motivation_scores_count_matches_npc_actor_ids(self):
        env = _envelope(blocks=[_block()], npc_ids=["michel", "alain"])
        result = augment_envelope_with_block_stream(env)
        scores = result["diagnostics"]["director_pulse"]["npc_motivation_scores"]
        assert len(scores) == 2

    def test_malformed_envelope_returned_unchanged(self):
        result = augment_envelope_with_block_stream("not_a_dict")  # type: ignore
        assert result == "not_a_dict"

    def test_empty_blocks_produces_empty_stream_events(self):
        env = _envelope(blocks=[])
        result = augment_envelope_with_block_stream(env)
        events = result["visible_scene_output"]["block_stream_events"]
        assert events == []

    def test_original_envelope_not_mutated(self):
        env = _envelope(blocks=[_block()])
        original_vso = dict(env["visible_scene_output"])
        augment_envelope_with_block_stream(env)
        # Original visible_scene_output should not have gained block_stream_events
        assert "block_stream_events" not in env["visible_scene_output"]

    def test_parity_status_aligned_for_simple_case(self):
        blocks = [_block("narrator"), _block("actor_line")]
        env = _envelope(blocks=blocks)
        result = augment_envelope_with_block_stream(env)
        parity = result["diagnostics"]["director_pulse"]["parity"]
        assert parity["parity_status"] == "aligned"

    def test_parity_not_applicable_for_empty_bundle(self):
        env = _envelope(blocks=[])
        result = augment_envelope_with_block_stream(env)
        parity = result["diagnostics"]["director_pulse"]["parity"]
        assert parity["parity_status"] == "not_applicable"

    def test_fallback_bundle_available_true_when_blocks_present(self):
        env = _envelope(blocks=[_block()])
        result = augment_envelope_with_block_stream(env)
        parity = result["diagnostics"]["director_pulse"]["parity"]
        assert parity["fallback_bundle_available"] is True

    def test_no_pi_keys_in_augmented_output(self):
        env = _envelope(blocks=[_block(), _block("actor_line")])
        result = augment_envelope_with_block_stream(env)
        import json
        serialised = json.dumps(result)
        pi_pattern = re.compile(r"\bPi?\d+\b|capability_\d+", re.IGNORECASE)
        assert not pi_pattern.search(serialised), "Pi/Π key found in augmented envelope"

    def test_no_fixed_speaker_queue_concepts_in_output(self):
        env = _envelope(blocks=[_block()])
        result = augment_envelope_with_block_stream(env)
        import json
        serialised = json.dumps(result).lower()
        for term in ("speaker_queue", "fixed_roster", "turn_order"):
            assert term not in serialised, f"Forbidden queue concept found: {term!r}"

    def test_no_hardcoded_npc_id_dependence(self):
        # Envelope with completely different NPC IDs must still work
        env = _envelope(blocks=[_block()], npc_ids=["npc_x", "npc_y"])
        result = augment_envelope_with_block_stream(env)
        scores = result["diagnostics"]["director_pulse"]["npc_motivation_scores"]
        npc_ids_in_scores = {s["npc_id"] for s in scores}
        assert npc_ids_in_scores == {"npc_x", "npc_y"}

    def test_npc_ids_inferred_from_envelope_when_not_supplied(self):
        env = _envelope(blocks=[_block()], npc_ids=["npc_a", "npc_b"])
        result = augment_envelope_with_block_stream(env)
        scores = result["diagnostics"]["director_pulse"]["npc_motivation_scores"]
        assert len(scores) == 2


# ── ADR-0039 Guardrails ───────────────────────────────────────────────────────

class TestDualModeADR0039Guardrails:

    def _source(self, module_name: str) -> str:
        import importlib, inspect
        mod = importlib.import_module(module_name)
        return inspect.getsource(mod)

    def test_no_pi_keys_in_dual_mode_module(self):
        source = self._source("ai_stack.block_stream_dual_mode")
        pi_pattern = re.compile(r"\bPi?\d+\b|capability_\d+", re.IGNORECASE)
        assert not pi_pattern.search(source), "Pi/Π key found in block_stream_dual_mode"

    def test_no_hardcoded_npc_ids_in_dual_mode_module(self):
        source = self._source("ai_stack.block_stream_dual_mode").lower()
        for name in ("veronique", "michel", "annette", "alain"):
            assert name not in source, f"Hardcoded NPC ID found: {name!r}"

    def test_no_speaker_queue_in_dual_mode_module(self):
        source = self._source("ai_stack.block_stream_dual_mode").lower()
        for term in ("speaker_queue", "fixed_roster"):
            assert term not in source, f"Forbidden speaker-queue concept: {term!r}"

    def test_commit_readiness_not_modified(self):
        """Dual-mode augmentation must not touch commit or validation_outcome."""
        env = _envelope(blocks=[_block()])
        env["commit_applied"] = True
        env["validation_outcome"] = "accepted"
        result = augment_envelope_with_block_stream(env)
        assert result.get("commit_applied") is True
        assert result.get("validation_outcome") == "accepted"
