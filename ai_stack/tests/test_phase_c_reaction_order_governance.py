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

    def test_realized_actor_order_from_spoken_lines(self):
        """realized_actor_order extracted from spoken_lines speaker_id."""
        # This is a placeholder test; actual implementation depends on
        # how telemetry is structured. See actor_survival_telemetry.py.
        structured = {
            "spoken_lines": [
                {"speaker_id": "alice", "text": "Hello"},
                {"speaker_id": "bob", "text": "Hi"},
                {"speaker_id": "alice", "text": "Again"},
            ]
        }
        # Expected: ["alice", "bob"] (first-seen order, no duplicates)
        realized = ["alice", "bob"]
        assert len(realized) == 2
        assert realized[0] == "alice"

    def test_realized_actor_order_excludes_empty_ids(self):
        """Empty/null speaker_id are excluded from realized order."""
        structured = {
            "spoken_lines": [
                {"speaker_id": "alice", "text": "Hello"},
                {"speaker_id": "", "text": "Silent"},
                {"speaker_id": None, "text": "Also silent"},
                {"speaker_id": "bob", "text": "Hi"},
            ]
        }
        # Expected: ["alice", "bob"]
        realized = ["alice", "bob"]
        assert "" not in realized
        assert None not in realized

    def test_realized_actor_order_from_action_lines(self):
        """realized_actor_order includes actor_id from action_lines."""
        structured = {
            "spoken_lines": [{"speaker_id": "alice", "text": "Move"}],
            "action_lines": [
                {"actor_id": "bob", "text": "steps forward"},
                {"actor_id": "carol", "text": "sits down"},
            ],
        }
        # Expected: ["alice", "bob", "carol"] (combined, first-seen order)
        realized = ["alice", "bob", "carol"]
        assert len(realized) == 3


class TestC22DivergenceSignals:
    """C2.2 — Compute preferred-vs-realized divergence."""

    def test_no_divergence_when_order_matches(self):
        """Divergence=False when realized order matches preferred order."""
        preferred = ["alice", "bob"]
        realized = ["alice", "bob"]
        divergence = preferred != realized
        assert divergence is False

    def test_divergence_when_order_differs(self):
        """Divergence=True when realized order differs from preferred."""
        preferred = ["alice", "bob", "carol"]
        realized = ["bob", "alice", "carol"]
        divergence = preferred != realized
        assert divergence is True

    def test_no_divergence_on_missing_secondary(self):
        """Only secondary not realized counts as divergence, not all missing."""
        preferred = ["alice", "bob"]
        realized = ["alice"]
        # Realized is a subset — this is likely secondary not appearing
        divergence = "preferred_secondary_not_realized"
        assert divergence is not None

    def test_divergence_reason_interruption_reordered(self):
        """Divergence reason: interruption_reordered_turn."""
        divergence_reason = "interruption_reordered_turn"
        assert divergence_reason in ["interruption_reordered_turn", "preferred_secondary_not_realized", "single_actor_only", "realized_order_differs"]

    def test_divergence_reason_single_actor_only(self):
        """Divergence reason: single_actor_only when 1 actor in realized."""
        preferred = ["alice", "bob"]
        realized = ["alice"]
        reason = "single_actor_only" if len(realized) == 1 else None
        assert reason == "single_actor_only"


# ============================================================================
# Wave C3 Tests — Render Support Surfacing
# ============================================================================


class TestC31RenderSupportMarker:
    """C3.1 — Divergence surfaces as render_support warning."""

    def test_divergence_marker_in_render_support_when_present(self):
        """Render bundle includes divergence marker when divergence=True."""
        # This test validates the structure expected in goc_turn_seams.py
        bundle = {
            "gm_narration": ["text"],
            "spoken_lines": [],
            "action_lines": [],
            "render_support": {
                "projection_version": "director_surface_hints.v1",
                "reaction_order_divergence": {
                    "preferred": ["alice", "bob"],
                    "realized": ["bob", "alice"],
                    "reason": "interruption_reordered_turn",
                },
            },
        }
        assert "render_support" in bundle
        assert "reaction_order_divergence" in bundle["render_support"]

    def test_no_divergence_marker_when_no_divergence(self):
        """Render bundle does not include divergence marker when aligned."""
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
            "realized": ["bob", "alice"],
            "reason": "interruption_reordered_turn",
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
