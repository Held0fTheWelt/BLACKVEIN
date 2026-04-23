"""Wave 1 Actor Contract Hardening — Closure verification tests.

Verify that all Wave 1 acceptance criteria are met:
1. Runtime generation contract is unambiguously actor-first
2. Prose narration is clearly secondary
3. Schema semantics clearly communicate actor-lane expectations
4. Validation/rewrite feedback aligns with those expectations
5. Render-stage actor-lane rejection is explicit, not silent
6. Telemetry uses correct actor attribution fields
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from pydantic import BaseModel

from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog
from ai_stack.langchain_integration.bridges import RuntimeTurnStructuredOutput
from ai_stack.goc_turn_seams import run_visible_render
from ai_stack.actor_survival_telemetry import build_actor_survival_telemetry


class TestWave1ActorFirstPromptContract:
    """Verify prompt contract is unambiguously actor-first."""

    def test_system_prompt_lists_actor_requirements_first(self):
        """System prompt must list actor lanes before prose formatting."""
        catalog = CanonicalPromptCatalog()
        system_prompt = catalog.get_prompt("runtime_turn_system")["template"]

        # Find positions of PRIMARY TASK and SECONDARY OUTPUT
        primary_task_pos = system_prompt.find("PRIMARY TASK")
        secondary_pos = system_prompt.find("SECONDARY OUTPUT")

        assert primary_task_pos != -1, "PRIMARY TASK section not found in system prompt"
        assert secondary_pos != -1, "SECONDARY OUTPUT section not found in system prompt"
        assert (
            primary_task_pos < secondary_pos
        ), "Actor realization (PRIMARY) should come before prose (SECONDARY)"

    def test_system_prompt_explicitly_defines_actor_lanes(self):
        """System prompt must explicitly define what goes in each actor lane."""
        catalog = CanonicalPromptCatalog()
        system_prompt = catalog.get_prompt("runtime_turn_system")["template"]

        # Check for primary task definition with actor lanes
        required_terms = [
            "Who responds in this turn",
            "What they say",
            "What they do",
            "speaker_id",
            "actor_id",
            "initiative_events",
            "state_effects",
        ]
        for term in required_terms:
            assert (
                term in system_prompt
            ), f"System prompt missing explicit reference to {term}"

    def test_human_prompt_lists_actor_steps_first(self):
        """Human prompt must list actor-level JSON requirements before prose structure."""
        catalog = CanonicalPromptCatalog()
        human_prompt = catalog.get_prompt("runtime_turn_human")["template"]

        # Check for ACTOR REALIZATION TASK section comes before PROSE PROJECTION
        actor_task_pos = human_prompt.find("ACTOR REALIZATION TASK")
        prose_projection_pos = human_prompt.find("PROSE PROJECTION")

        assert actor_task_pos != -1, "ACTOR REALIZATION TASK section not found"
        assert prose_projection_pos != -1, "PROSE PROJECTION section not found"
        assert actor_task_pos < prose_projection_pos, "Actor realization should come before prose projection"

        # Check for key actor lane terms
        assert "spoken_lines" in human_prompt
        assert "action_lines" in human_prompt
        assert "speaker_id" in human_prompt

    def test_prompt_narrative_response_is_explicitly_copy_only(self):
        """Prompts must explicitly state narrative_response is a copy, not original."""
        catalog = CanonicalPromptCatalog()
        system_prompt = catalog.get_prompt("runtime_turn_system")["template"]
        human_prompt = catalog.get_prompt("runtime_turn_human")["template"]

        combined = system_prompt + human_prompt
        assert (
            "copy" in combined.lower()
        ), "Prompt must explicitly reference copying narration_summary to narrative_response"

        # Also check that narrative_response is not described as a primary output
        assert (
            "SECONDARY OUTPUT" in system_prompt or "prose projection" in human_prompt.lower()
        ), "Prompts must indicate narration is secondary, not primary"


class TestWave1SchemaSemanticsSharpness:
    """Verify schema semantics clearly mark actor lanes as required."""

    def test_primary_responder_id_is_marked_required(self):
        """primary_responder_id must be explicitly marked as Required."""
        schema = RuntimeTurnStructuredOutput.model_json_schema()
        props = schema.get("properties", {})
        primary_responder = props.get("primary_responder_id", {})

        # Check field description in schema
        assert "Required" in primary_responder.get("description", ""), \
            "primary_responder_id must have 'Required' in its description"

    def test_spoken_lines_is_marked_required_when_actors_speak(self):
        """spoken_lines must be explicitly marked as required for actor-bearing turns."""
        schema = RuntimeTurnStructuredOutput.model_json_schema()
        props = schema.get("properties", {})
        spoken_lines = props.get("spoken_lines", {})

        description = spoken_lines.get("description", "")
        assert "Required when actors speak" in description or \
               "speaker_id" in description, \
            "spoken_lines must document that it's required when actors speak"

    def test_action_lines_must_have_actor_id(self):
        """action_lines must require actor_id on each entry."""
        schema = RuntimeTurnStructuredOutput.model_json_schema()
        props = schema.get("properties", {})
        action_lines = props.get("action_lines", {})

        description = action_lines.get("description", "")
        assert "actor_id" in description, \
            "action_lines description must mention actor_id requirement"

    def test_spoken_line_structure_uses_speaker_id_not_responder_id(self):
        """RuntimeSpokenLine must use speaker_id, not responder_id."""
        struct = RuntimeTurnStructuredOutput.RuntimeSpokenLine
        fields = struct.model_fields

        assert "speaker_id" in fields, "RuntimeSpokenLine must have speaker_id field"
        assert "responder_id" not in fields, "RuntimeSpokenLine must not have responder_id (use speaker_id)"

    def test_action_line_structure_uses_actor_id(self):
        """RuntimeActionLine must use actor_id."""
        struct = RuntimeTurnStructuredOutput.RuntimeActionLine
        fields = struct.model_fields

        assert "actor_id" in fields, "RuntimeActionLine must have actor_id field"

    def test_initiative_event_structure_uses_actor_id(self):
        """RuntimeInitiativeEvent must use actor_id."""
        struct = RuntimeTurnStructuredOutput.RuntimeInitiativeEvent
        fields = struct.model_fields

        assert "actor_id" in fields, "RuntimeInitiativeEvent must have actor_id field"


class TestWave1RenderGuardedDowngrade:
    """Verify render-stage actor-lane clearing is explicit, not silent."""

    def test_actor_lanes_gated_marker_added_when_validation_rejected(self):
        """When actor-lane validation is rejected, markers must include actor_lanes_validation_gated."""
        validation_outcome = {
            "status": "rejected",
            "reason": "actor_lane_invalid_initiative_type",
            "actor_lane_validation": {
                "status": "rejected",
                "reason": "actor_lane_invalid_initiative_type",
                "checked_fields": ["initiative_events"],
            },
        }
        generation = {
            "content": "The scene shifts.",
            "metadata": {
                "structured_output": {
                    "primary_responder_id": "actor1",
                    "spoken_lines": [{"speaker_id": "actor1", "text": "Hello"}],
                    "action_lines": [{"actor_id": "actor1", "text": "waves hand"}],
                }
            },
        }

        bundle, markers = run_visible_render(
            module_id="goc",
            committed_result={"commit_applied": False},
            validation_outcome=validation_outcome,
            generation=generation,
            transition_pattern="soft",
            live_player_truth_surface=False,
            render_context={},
        )

        assert "actor_lanes_validation_gated" in markers, \
            "Markers must include 'actor_lanes_validation_gated' when actor lanes are rejected"

    def test_render_downgrade_metadata_present_when_actor_lanes_rejected(self):
        """When actor lanes are rejected, bundle must include render_downgrade metadata."""
        validation_outcome = {
            "status": "rejected",
            "reason": "actor_lane_illegal_actor",
            "actor_lane_validation": {
                "status": "rejected",
                "reason": "actor_lane_illegal_actor",
                "checked_fields": ["spoken_lines"],
            },
        }
        generation = {
            "content": "The exchange shifts.",
            "metadata": {
                "structured_output": {
                    "primary_responder_id": "actor1",
                    "spoken_lines": [{"speaker_id": "illegal_actor", "text": "Hello"}],
                }
            },
        }

        bundle, _ = run_visible_render(
            module_id="goc",
            committed_result={"commit_applied": False},
            validation_outcome=validation_outcome,
            generation=generation,
            transition_pattern="soft",
            live_player_truth_surface=False,
            render_context={},
        )

        assert "render_downgrade" in bundle, \
            "Bundle must contain 'render_downgrade' key when actor lanes are gated"
        assert bundle["render_downgrade"]["actor_lanes"] == "validation_rejected", \
            "render_downgrade must document that actor_lanes were validation_rejected"

    def test_actor_lanes_cleared_when_validation_rejected(self):
        """Actor lanes must be empty (cleared) when validation rejects them."""
        validation_outcome = {
            "status": "rejected",
            "reason": "actor_lane_invalid_initiative_type",
            "actor_lane_validation": {
                "status": "rejected",
                "reason": "actor_lane_invalid_initiative_type",
            },
        }
        generation = {
            "content": "The scene shifts.",
            "metadata": {
                "structured_output": {
                    "primary_responder_id": "actor1",
                    "spoken_lines": [{"speaker_id": "actor1", "text": "Hello"}],
                    "action_lines": [{"actor_id": "actor1", "text": "gestures"}],
                }
            },
        }

        bundle, _ = run_visible_render(
            module_id="goc",
            committed_result={"commit_applied": False},
            validation_outcome=validation_outcome,
            generation=generation,
            transition_pattern="soft",
            live_player_truth_surface=False,
            render_context={},
        )

        assert bundle["spoken_lines"] == [], "spoken_lines must be empty when validation rejected"
        assert bundle["action_lines"] == [], "action_lines must be empty when validation rejected"


class TestWave1TelemetryConsistency:
    """Verify telemetry uses correct schema field names."""

    def test_telemetry_reads_speaker_id_not_responder_id(self):
        """Telemetry must check speaker_id, not responder_id, for spoken line attribution."""
        state = {
            "selected_responder_set": [{"actor_id": "actor1"}],
            "selected_scene_function": "establish_pressure",
            "generation": {
                "metadata": {
                    "structured_output": {
                        "spoken_lines": [
                            {"speaker_id": "actor1", "text": "What happened?", "tone": "confused"},
                        ],
                        "action_lines": [],
                    }
                }
            },
            "validation_outcome": {"status": "approved", "reason": ""},
            "committed_result": {"commit_applied": True, "committed_effects": []},
            "visible_output_bundle": {
                "gm_narration": ["Actor1 responds."],
                "spoken_lines": ["Actor1: What happened?"],
            },
            "failure_markers": [],
        }

        telemetry = build_actor_survival_telemetry(
            state,
            generation_ok=True,
            validation_ok=True,
            commit_applied=True,
            fallback_taken=False,
        )

        # Verify that telemetry correctly detects speaker attribution
        assert telemetry["actor_survival"]["generation_phase"]["responder_attribution_present"] is True, \
            "Telemetry must correctly detect speaker_id attribution in spoken lines"

    def test_telemetry_detects_no_attribution_when_no_speaker_id(self):
        """Telemetry must report no attribution when spoken_lines lack speaker_id."""
        state = {
            "selected_responder_set": [{"actor_id": "actor1"}],
            "selected_scene_function": "establish_pressure",
            "generation": {
                "metadata": {
                    "structured_output": {
                        "spoken_lines": [
                            {"text": "What happened?", "tone": "confused"},  # No speaker_id
                        ],
                        "action_lines": [],
                    }
                }
            },
            "validation_outcome": {"status": "approved", "reason": ""},
            "committed_result": {"commit_applied": True, "committed_effects": []},
            "visible_output_bundle": {
                "gm_narration": ["The character responds."],
                "spoken_lines": ["What happened?"],
            },
            "failure_markers": [],
        }

        telemetry = build_actor_survival_telemetry(
            state,
            generation_ok=True,
            validation_ok=True,
            commit_applied=True,
            fallback_taken=False,
        )

        # Telemetry should report no speaker attribution
        assert telemetry["actor_survival"]["generation_phase"]["responder_attribution_present"] is False, \
            "Telemetry must correctly report missing speaker_id attribution"


class TestWave1ActorBeforeNarration:
    """Verify actor realization is primary, narration is projection."""

    def test_schema_field_ordering_actor_first(self):
        """Schema field ordering must place actor fields before narrative_response."""
        schema = RuntimeTurnStructuredOutput.model_json_schema()
        props = schema.get("properties", {})

        # Get field names in order they appear in schema
        field_order = list(props.keys())

        # Find positions
        narration_summary_idx = field_order.index("narration_summary") if "narration_summary" in field_order else -1
        primary_responder_idx = field_order.index("primary_responder_id") if "primary_responder_id" in field_order else -1
        spoken_lines_idx = field_order.index("spoken_lines") if "spoken_lines" in field_order else -1
        narrative_response_idx = field_order.index("narrative_response") if "narrative_response" in field_order else -1

        # narration_summary should come before narrative_response
        assert narration_summary_idx < narrative_response_idx, \
            "narration_summary should be listed before narrative_response in schema"

        # primary_responder_id and spoken_lines should come before narrative_response
        assert primary_responder_idx < narrative_response_idx, \
            "primary_responder_id should come before narrative_response"
        assert spoken_lines_idx < narrative_response_idx, \
            "spoken_lines should come before narrative_response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
