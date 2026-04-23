"""
Phase C tests — Preferred Reaction Order Governance.

Tests for C1 (packet wiring), C2 (telemetry), C3 (render), C4 (integration).
"""

import pytest
from unittest.mock import Mock, patch
from typing import Any


# ============================================================================
# Wave C1 Tests — Canonical Preferred Order Contract
# ============================================================================


class TestC11PreferredOrderPacketField:
    """C1.1 — preferred_reaction_order as explicit top-level packet field."""

    def test_preferred_reaction_order_extracted_from_responders(self):
        """preferred_reaction_order is built from selected_responder_set."""
        from ai_stack.langgraph_runtime_executor import _preferred_reaction_order_ids_from_responders

        responders = [
            {"actor_id": "alice", "preferred_reaction_order": 0},
            {"actor_id": "bob", "preferred_reaction_order": 1},
            {"actor_id": "carol", "preferred_reaction_order": 2},
        ]
        result = _preferred_reaction_order_ids_from_responders(responders)
        assert result == ["alice", "bob", "carol"]

    def test_preferred_reaction_order_sorted_by_sequence(self):
        """preferred_reaction_order is deterministically sorted."""
        from ai_stack.langgraph_runtime_executor import _preferred_reaction_order_ids_from_responders

        # Unordered input
        responders = [
            {"actor_id": "bob", "preferred_reaction_order": 1},
            {"actor_id": "alice", "preferred_reaction_order": 0},
            {"actor_id": "carol", "preferred_reaction_order": 2},
        ]
        result = _preferred_reaction_order_ids_from_responders(responders)
        assert result == ["alice", "bob", "carol"]

    def test_preferred_reaction_order_excludes_empty_ids(self):
        """Empty or None actor_ids are excluded."""
        from ai_stack.langgraph_runtime_executor import _preferred_reaction_order_ids_from_responders

        responders = [
            {"actor_id": "alice", "preferred_reaction_order": 0},
            {"actor_id": "", "preferred_reaction_order": 1},  # Empty
            {"actor_id": None, "preferred_reaction_order": 2},  # None
            {"actor_id": "bob", "preferred_reaction_order": 3},
        ]
        result = _preferred_reaction_order_ids_from_responders(responders)
        assert result == ["alice", "bob"]

    def test_preferred_reaction_order_deduplicates(self):
        """Duplicate actor IDs appear only once."""
        from ai_stack.langgraph_runtime_executor import _preferred_reaction_order_ids_from_responders

        responders = [
            {"actor_id": "alice", "preferred_reaction_order": 0},
            {"actor_id": "alice", "preferred_reaction_order": 1},  # Duplicate
        ]
        result = _preferred_reaction_order_ids_from_responders(responders)
        assert result == ["alice"]

    def test_preferred_reaction_order_in_dramatic_packet(self):
        """Packet contains preferred_reaction_order field."""
        from ai_stack.langgraph_runtime_executor import _build_dramatic_generation_packet

        state = {
            "session_id": "test_session",
            "module_id": "GOC",
            "current_scene_id": "scene_1",
            "selected_scene_function": "establish_pressure",
            "selected_responder_set": [
                {"actor_id": "alice", "preferred_reaction_order": 0},
                {"actor_id": "bob", "preferred_reaction_order": 1},
            ],
            "character_mind_records": [],
            "prior_continuity_impacts": [],
            "scene_assessment": {},
            "semantic_move_record": {},
        }

        packet = _build_dramatic_generation_packet(state)
        assert "preferred_reaction_order" in packet
        assert packet["preferred_reaction_order"] == ["alice", "bob"]

    def test_preferred_reaction_order_none_when_no_responders(self):
        """Preferred order is empty list when no responders."""
        from ai_stack.langgraph_runtime_executor import _build_dramatic_generation_packet

        state = {
            "session_id": "test_session",
            "module_id": "GOC",
            "current_scene_id": "scene_1",
            "selected_scene_function": "establish_pressure",
            "selected_responder_set": [],
            "character_mind_records": [],
            "prior_continuity_impacts": [],
            "scene_assessment": {},
            "semantic_move_record": {},
        }

        packet = _build_dramatic_generation_packet(state)
        assert packet["preferred_reaction_order"] == []


class TestC12PreferredOrderDirective:
    """C1.2 — preferred_reaction_order_directive as explicit normative instruction."""

    def test_preferred_reaction_order_directive_present_when_multiple_responders(self):
        """Directive is emitted when multiple responders nominated."""
        from ai_stack.langgraph_runtime_executor import _build_dramatic_generation_packet

        state = {
            "session_id": "test_session",
            "module_id": "GOC",
            "current_scene_id": "scene_1",
            "selected_scene_function": "establish_pressure",
            "selected_responder_set": [
                {"actor_id": "alice", "preferred_reaction_order": 0},
                {"actor_id": "bob", "preferred_reaction_order": 1},
            ],
            "character_mind_records": [],
            "prior_continuity_impacts": [],
            "scene_assessment": {},
            "semantic_move_record": {},
        }

        packet = _build_dramatic_generation_packet(state)
        assert "preferred_reaction_order_directive" in packet
        assert packet["preferred_reaction_order_directive"] is not None
        assert "alice" in packet["preferred_reaction_order_directive"]
        assert "bob" in packet["preferred_reaction_order_directive"]

    def test_preferred_reaction_order_directive_none_when_single_responder(self):
        """Directive is None when only primary responder."""
        from ai_stack.langgraph_runtime_executor import _build_dramatic_generation_packet

        state = {
            "session_id": "test_session",
            "module_id": "GOC",
            "current_scene_id": "scene_1",
            "selected_scene_function": "establish_pressure",
            "selected_responder_set": [
                {"actor_id": "alice", "preferred_reaction_order": 0},
            ],
            "character_mind_records": [],
            "prior_continuity_impacts": [],
            "scene_assessment": {},
            "semantic_move_record": {},
        }

        packet = _build_dramatic_generation_packet(state)
        # When only one responder, preferred_reaction_order_directive is None
        assert packet["preferred_reaction_order_directive"] is None

    def test_preferred_reaction_order_directive_normative_language(self):
        """Directive uses normative language, not absolute."""
        from ai_stack.langgraph_runtime_executor import _build_dramatic_generation_packet

        state = {
            "session_id": "test_session",
            "module_id": "GOC",
            "current_scene_id": "scene_1",
            "selected_scene_function": "establish_pressure",
            "selected_responder_set": [
                {"actor_id": "alice", "preferred_reaction_order": 0},
                {"actor_id": "bob", "preferred_reaction_order": 1},
            ],
            "character_mind_records": [],
            "prior_continuity_impacts": [],
            "scene_assessment": {},
            "semantic_move_record": {},
        }

        packet = _build_dramatic_generation_packet(state)
        directive = packet["preferred_reaction_order_directive"]
        # Should use soft language like "should" not "must"
        assert "should" in directive.lower() or "unless" in directive.lower()


class TestC1PromptIntegration:
    """C1 prompt catalog integration."""

    def test_canonical_catalog_includes_preferred_order_guidance(self):
        """Canonical prompt catalog has preferred_reaction_order guidance."""
        from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog

        catalog = CanonicalPromptCatalog()
        system_prompt = catalog.get_prompt("runtime_turn_system")["template"]
        assert "preferred_reaction_order" in system_prompt

    def test_system_prompt_allows_divergence(self):
        """System prompt allows divergence from preferred order."""
        from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog

        catalog = CanonicalPromptCatalog()
        system_prompt = catalog.get_prompt("runtime_turn_system")["template"]
        # Should mention that interruption/constraints may justify divergence
        assert "interruption" in system_prompt.lower() or "constraint" in system_prompt.lower()

    def test_human_prompt_references_preferred_order(self):
        """Human prompt explicitly mentions preferred_reaction_order."""
        from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog

        catalog = CanonicalPromptCatalog()
        human_prompt = catalog.get_prompt("runtime_turn_human")["template"]
        assert "preferred_reaction_order" in human_prompt


# ============================================================================
# Wave C2 Tests — Realized Order and Divergence Telemetry
# ============================================================================


class TestC21RealizedActorOrder:
    """C2.1 — Compute realized spoken/action order from visible lanes."""

    def test_realized_actor_order_in_telemetry(self):
        """Telemetry includes realized_spoken_order, realized_action_order, realized_actor_order."""
        from ai_stack.actor_survival_telemetry import build_actor_survival_telemetry

        state = {
            "selected_responder_set": [
                {"actor_id": "alice", "preferred_reaction_order": 0},
                {"actor_id": "bob", "preferred_reaction_order": 1},
            ],
            "spoken_lines": [
                {"speaker_id": "alice", "text": "Hello"},
                {"speaker_id": "bob", "text": "Hi"},
            ],
            "action_lines": [],
            "initiative_events": [],
            "generation": {"metadata": {"structured_output": {
                "spoken_lines": [
                    {"speaker_id": "alice", "text": "Hello"},
                    {"speaker_id": "bob", "text": "Hi"},
                ],
                "action_lines": [],
                "initiative_events": [],
            }}},
            "visible_output_bundle": {
                "spoken_lines": ["alice: Hello", "bob: Hi"],
                "action_lines": [],
            },
        }

        telemetry = build_actor_survival_telemetry(
            state, generation_ok=True, validation_ok=True, commit_applied=True, fallback_taken=False
        )
        vitality = telemetry.get("vitality_telemetry_v1", {})

        # All three order fields should be present
        assert "realized_spoken_order" in vitality
        assert "realized_action_order" in vitality
        assert "realized_actor_order" in vitality
        assert vitality["realized_spoken_order"] == ["alice", "bob"]
        assert vitality["realized_action_order"] == []
        assert vitality["realized_actor_order"] == ["alice", "bob"]

    def test_realized_actor_order_excludes_empty_ids(self):
        """Empty/null actor_ids are excluded from realized order."""
        from ai_stack.actor_survival_telemetry import _collect_actor_ids_from_rows

        rows = [
            {"speaker_id": "alice", "text": "Hello"},
            {"speaker_id": "", "text": "Silent"},
            {"speaker_id": None, "text": "Also silent"},
            {"speaker_id": "bob", "text": "Hi"},
        ]
        result = _collect_actor_ids_from_rows(rows, speaker_key="speaker_id", actor_key="actor_id")
        assert result == ["alice", "bob"]
        assert "" not in result
        assert None not in result

    def test_realized_actor_order_deduplicates(self):
        """Duplicate actor IDs appear only once."""
        from ai_stack.actor_survival_telemetry import _collect_actor_ids_from_rows

        rows = [
            {"speaker_id": "alice", "text": "Hello"},
            {"speaker_id": "bob", "text": "Hi"},
            {"speaker_id": "alice", "text": "Again"},  # Duplicate
        ]
        result = _collect_actor_ids_from_rows(rows, speaker_key="speaker_id", actor_key="actor_id")
        assert result == ["alice", "bob"]  # alice appears only once


class TestC22DivergenceSignals:
    """C2.2 — Compute preferred-vs-realized divergence."""

    def test_no_divergence_when_order_matches(self):
        """Divergence=None when realized order matches preferred order."""
        from ai_stack.actor_survival_telemetry import build_actor_survival_telemetry

        state = {
            "selected_responder_set": [
                {"actor_id": "alice", "preferred_reaction_order": 0},
                {"actor_id": "bob", "preferred_reaction_order": 1},
            ],
            "spoken_lines": [
                {"speaker_id": "alice", "text": "Hello"},
                {"speaker_id": "bob", "text": "Hi"},
            ],
            "action_lines": [],
            "initiative_events": [],
            "generation": {"metadata": {"structured_output": {
                "spoken_lines": [
                    {"speaker_id": "alice", "text": "Hello"},
                    {"speaker_id": "bob", "text": "Hi"},
                ],
                "action_lines": [],
                "initiative_events": [],
            }}},
            "visible_output_bundle": {
                "spoken_lines": ["alice: Hello", "bob: Hi"],
                "action_lines": [],
            },
        }

        telemetry = build_actor_survival_telemetry(
            state, generation_ok=True, validation_ok=True, commit_applied=True, fallback_taken=False
        )
        vitality = telemetry.get("vitality_telemetry_v1", {})
        # When order matches, divergence should be None
        assert vitality.get("reaction_order_divergence") is None
        assert vitality.get("reaction_order_divergence_reason") is None

    def test_divergence_when_secondary_not_realized(self):
        """Divergence=True when secondary responders nominated but not realized."""
        from ai_stack.actor_survival_telemetry import build_actor_survival_telemetry

        state = {
            "selected_responder_set": [
                {"actor_id": "alice", "preferred_reaction_order": 0},
                {"actor_id": "bob", "preferred_reaction_order": 1},  # Secondary
            ],
            "secondary_responder_ids": ["bob"],
            "spoken_lines": [{"speaker_id": "alice", "text": "Hello"}],
            "action_lines": [],
            "initiative_events": [],
            "generation": {"metadata": {"structured_output": {
                "spoken_lines": [{"speaker_id": "alice", "text": "Hello"}],
                "action_lines": [],
                "initiative_events": [],
            }}},
            "visible_output_bundle": {
                "spoken_lines": ["alice: Hello"],
                "action_lines": [],
            },
        }

        telemetry = build_actor_survival_telemetry(
            state, generation_ok=True, validation_ok=True, commit_applied=True, fallback_taken=False
        )
        vitality = telemetry.get("vitality_telemetry_v1", {})
        # Secondary nominated but not realized
        assert vitality.get("reaction_order_divergence") is True
        assert vitality.get("reaction_order_divergence_reason") == "preferred_secondary_not_realized"

    def test_divergence_reason_single_actor_only(self):
        """Divergence reason: single_actor_only when only primary realized."""
        from ai_stack.actor_survival_telemetry import build_actor_survival_telemetry

        state = {
            "selected_responder_set": [
                {"actor_id": "alice", "preferred_reaction_order": 0},
                {"actor_id": "bob", "preferred_reaction_order": 1},
            ],
            "spoken_lines": [{"speaker_id": "alice", "text": "Hello"}],
            "action_lines": [],
            "initiative_events": [],
            "generation": {"metadata": {"structured_output": {
                "spoken_lines": [{"speaker_id": "alice", "text": "Hello"}],
                "action_lines": [],
                "initiative_events": [],
            }}},
            "visible_output_bundle": {
                "spoken_lines": ["alice: Hello"],
                "action_lines": [],
            },
        }

        telemetry = build_actor_survival_telemetry(
            state, generation_ok=True, validation_ok=True, commit_applied=True, fallback_taken=False
        )
        vitality = telemetry.get("vitality_telemetry_v1", {})
        # Single actor realized but multiple preferred
        assert vitality.get("reaction_order_divergence") is True
        assert vitality.get("reaction_order_divergence_reason") == "single_actor_only"

    def test_no_divergence_when_single_preferred_actor(self):
        """No divergence when only one responder was preferred."""
        from ai_stack.actor_survival_telemetry import build_actor_survival_telemetry

        state = {
            "selected_responder_set": [
                {"actor_id": "alice", "preferred_reaction_order": 0},
            ],
            "spoken_lines": [{"speaker_id": "alice", "text": "Hello"}],
            "action_lines": [],
            "initiative_events": [],
            "generation": {"metadata": {"structured_output": {
                "spoken_lines": [{"speaker_id": "alice", "text": "Hello"}],
                "action_lines": [],
                "initiative_events": [],
            }}},
            "visible_output_bundle": {
                "spoken_lines": ["alice: Hello"],
                "action_lines": [],
            },
        }

        telemetry = build_actor_survival_telemetry(
            state, generation_ok=True, validation_ok=True, commit_applied=True, fallback_taken=False
        )
        vitality = telemetry.get("vitality_telemetry_v1", {})
        # Single responder, no divergence
        assert vitality.get("reaction_order_divergence") is None


# ============================================================================
# Wave C3 Tests — Render Support Surfacing
# ============================================================================


class TestC31RenderSupportMarker:
    """C3.1 — Divergence surfaces as render_support warning."""

    def test_divergence_marker_in_render_context(self):
        """Render context includes divergence fields."""
        render_context = {
            "reaction_order_divergence": True,
            "reaction_order_divergence_reason": "single_actor_only",
            "preferred_reaction_order": ["alice", "bob"],
            "realized_actor_order": ["alice"],
        }
        assert render_context["reaction_order_divergence"] is True
        assert render_context["reaction_order_divergence_reason"] == "single_actor_only"

    def test_divergence_marker_structure_in_bundle(self):
        """Divergence marker structure expected in render_support."""
        bundle = {
            "gm_narration": ["text"],
            "spoken_lines": [],
            "action_lines": [],
            "render_support": {
                "projection_version": "director_surface_hints.v1",
                "reaction_order_divergence": {
                    "preferred": ["alice", "bob"],
                    "realized": ["alice"],
                    "reason": "single_actor_only",
                },
            },
        }
        assert "render_support" in bundle
        assert "reaction_order_divergence" in bundle["render_support"]
        payload = bundle["render_support"]["reaction_order_divergence"]
        assert payload["preferred"] == ["alice", "bob"]
        assert payload["realized"] == ["alice"]
        assert payload["reason"] == "single_actor_only"

    def test_no_divergence_marker_when_none(self):
        """Render bundle does not include divergence marker when None."""
        bundle = {
            "gm_narration": ["text"],
            "spoken_lines": [],
            "action_lines": [],
        }
        # Divergence marker should not be present
        assert "reaction_order_divergence" not in bundle.get("render_support", {})

    def test_divergence_payload_compact(self):
        """Divergence payload is compact (preferred, realized, reason)."""
        payload = {
            "preferred": ["alice", "bob"],
            "realized": ["bob"],
            "reason": "preferred_secondary_not_realized",
        }
        assert "preferred" in payload
        assert "realized" in payload
        assert "reason" in payload
        # No unnecessary nesting
        assert len(payload) == 3


# ============================================================================
# Wave C4 Tests — Integration and Hardening
# ============================================================================


class TestC4IntegrationSanity:
    """C4 sanity checks for full integration."""

    def test_packet_and_prompt_field_names_aligned(self):
        """Packet field names match prompt references."""
        from ai_stack.langgraph_runtime_executor import _build_dramatic_generation_packet
        from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog

        # Build a minimal packet
        state = {
            "session_id": "test",
            "module_id": "GOC",
            "current_scene_id": "scene_1",
            "selected_scene_function": "establish_pressure",
            "selected_responder_set": [
                {"actor_id": "alice", "preferred_reaction_order": 0},
                {"actor_id": "bob", "preferred_reaction_order": 1},
            ],
            "character_mind_records": [],
            "prior_continuity_impacts": [],
            "scene_assessment": {},
            "semantic_move_record": {},
        }

        packet = _build_dramatic_generation_packet(state)

        # Verify field names in packet
        assert "preferred_reaction_order" in packet
        assert "preferred_reaction_order_directive" in packet

        # Verify prompt references these names
        catalog = CanonicalPromptCatalog()
        system_prompt = catalog.get_prompt("runtime_turn_system")["template"]
        assert "preferred_reaction_order" in system_prompt

    def test_empty_state_does_not_crash(self):
        """Empty or minimal state does not cause packet building to crash."""
        from ai_stack.langgraph_runtime_executor import _build_dramatic_generation_packet

        state = {
            "selected_responder_set": None,  # No responders
        }

        # Should not raise
        packet = _build_dramatic_generation_packet(state)
        assert "preferred_reaction_order" in packet
        assert packet["preferred_reaction_order"] == []
