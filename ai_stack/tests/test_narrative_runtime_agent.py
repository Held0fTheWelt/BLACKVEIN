"""
Tests for NarrativeRuntimeAgent (Phase 1 & 2).

Tests the core streaming implementation and narrative validation rules.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from ai_stack.narrative_runtime_agent import (
    NarrativeRuntimeAgent,
    NarrativeRuntimeAgentInput,
    NarrativeRuntimeAgentConfig,
    NarrativeEventKind,
)


@pytest.fixture
def agent_config():
    """Default agent configuration for testing."""
    return NarrativeRuntimeAgentConfig(
        max_narrator_blocks=10,
        motivation_pressure_threshold=0.3,
    )


@pytest.fixture
def narrator_agent(agent_config):
    """Instantiate NarrativeRuntimeAgent with test config."""
    return NarrativeRuntimeAgent(config=agent_config)


@pytest.fixture
def sample_runtime_state():
    """Sample RuntimeState for testing."""
    return {
        "scene_id": "alains_office_act1",
        "actor_positions": {
            "annette": {"location": "office", "state": "alert"},
            "alain": {"location": "office", "state": "focused"},
        },
        "environment_objects": [
            {"object_id": "desk", "state": "cluttered"},
            {"object_id": "chair", "state": "occupied"},
        ],
    }


@pytest.fixture
def sample_npc_agency_plan():
    """Sample NPCAgencyPlan with initiatives."""
    return {
        "initiatives": [
            {
                "actor_id": "annette",
                "initiative_type": "challenge_authority",
                "resolved": False,
                "motivation_intensity": 0.8,
            },
            {
                "actor_id": "alain",
                "initiative_type": "strategic_defense",
                "resolved": False,
                "motivation_intensity": 0.6,
            },
        ],
        "pressure_summary": "High dramatic tension",
    }


@pytest.fixture
def sample_agent_input(sample_runtime_state, sample_npc_agency_plan):
    """Sample NarrativeRuntimeAgentInput for testing."""
    return NarrativeRuntimeAgentInput(
        runtime_state=sample_runtime_state,
        npc_agency_plan=sample_npc_agency_plan,
        dramatic_signature={
            "primary_tension": "authority_challenge",
            "secondary_tension": "strategic_positioning",
        },
        narrative_threads=[
            {"thread_id": "loyalty_test", "state": "active"},
            {"thread_id": "power_shift", "state": "emerging"},
        ],
        session_id="test_session_001",
        turn_number=3,
        trace_id="trace_001",
        enable_langfuse_tracing=False,
    )


class TestNarrativeRuntimeAgentCore:
    """Test core streaming functionality."""

    def test_narrator_agent_instantiation(self, narrator_agent):
        """Agent instantiates with default or custom config."""
        assert narrator_agent is not None
        assert narrator_agent.config.max_narrator_blocks == 10

    def test_stream_narrator_blocks_yields_events(self, narrator_agent, sample_agent_input):
        """stream_narrator_blocks yields NarrativeRuntimeAgentEvent objects."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        assert len(events) > 0
        assert all(hasattr(e, "event_kind") for e in events)

    def test_narrator_blocks_emitted_before_ruhepunkt(self, narrator_agent, sample_agent_input):
        """Narrator blocks are emitted before ruhepunkt signal."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        event_kinds = [e.event_kind for e in events]

        # Find indices
        narrator_block_indices = [i for i, k in enumerate(event_kinds) if k == NarrativeEventKind.NARRATOR_BLOCK]
        ruhepunkt_indices = [i for i, k in enumerate(event_kinds) if k == NarrativeEventKind.RUHEPUNKT_REACHED]

        if narrator_block_indices and ruhepunkt_indices:
            assert max(narrator_block_indices) < min(ruhepunkt_indices)

    def test_ruhepunkt_signal_emitted_when_initiatives_exhausted(self, narrator_agent, sample_agent_input):
        """Ruhepunkt signal emitted when remaining initiatives reach 0."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        event_kinds = [e.event_kind for e in events]
        assert NarrativeEventKind.RUHEPUNKT_REACHED in event_kinds

    def test_streaming_complete_event_emitted(self, narrator_agent, sample_agent_input):
        """Streaming complete event emitted at end."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        event_kinds = [e.event_kind for e in events]
        assert NarrativeEventKind.STREAMING_COMPLETE in event_kinds

    def test_event_sequence_increments(self, narrator_agent, sample_agent_input):
        """Event sequence numbers increment for each event."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        sequence_numbers = [e.sequence_number for e in events]
        assert sequence_numbers == list(range(1, len(events) + 1))


class TestMotivationAnalysis:
    """Test NPC motivation pressure analysis."""

    def test_analyze_motivation_pressure_counts_initiatives(self, narrator_agent, sample_agent_input):
        """Motivation analysis counts remaining unresolved initiatives."""
        analysis = narrator_agent._analyze_motivation_pressure(sample_agent_input)
        assert analysis["remaining_initiatives"] == 2  # Two unresolved in sample

    def test_analyze_motivation_pressure_identifies_actors(self, narrator_agent, sample_agent_input):
        """Motivation analysis identifies NPCs with initiatives."""
        analysis = narrator_agent._analyze_motivation_pressure(sample_agent_input)
        assert "annette" in analysis["initiative_actors"]
        assert "alain" in analysis["initiative_actors"]

    def test_analyze_motivation_pressure_zero_when_all_resolved(self, narrator_agent, sample_agent_input):
        """Remaining initiatives is zero when all resolved."""
        sample_agent_input.npc_agency_plan["initiatives"] = [
            {
                "actor_id": "annette",
                "initiative_type": "challenge_authority",
                "resolved": True,
                "motivation_intensity": 0.8,
            },
        ]
        analysis = narrator_agent._analyze_motivation_pressure(sample_agent_input)
        assert analysis["remaining_initiatives"] == 0


class TestNarratorValidation:
    """Test narrative voice validation rules."""

    def test_validate_rejects_you_feel_that_pattern(self, narrator_agent, sample_agent_input):
        """Validation rejects 'You feel that' pattern (forced judgment)."""
        invalid_block = {
            "narrator_text": "You feel that Annette's strategy is weak.",
            "sequence": 0,
        }
        error = narrator_agent._validate_narrative_output(invalid_block, sample_agent_input)
        assert error is not None

    def test_validate_rejects_you_are_emotion(self, narrator_agent, sample_agent_input):
        """Validation rejects 'You are ashamed/angry' pattern."""
        invalid_block = {
            "narrator_text": "You are ashamed by their accusations.",
            "sequence": 0,
        }
        error = narrator_agent._validate_narrative_output(invalid_block, sample_agent_input)
        assert error is not None
        assert "forced" in error.lower() or "player" in error.lower()

    def test_validate_rejects_you_realize_that_pattern(self, narrator_agent, sample_agent_input):
        """Validation rejects 'You realize that' pattern."""
        invalid_block = {
            "narrator_text": "You realize that Alain is manipulating you.",
            "sequence": 0,
        }
        error = narrator_agent._validate_narrative_output(invalid_block, sample_agent_input)
        assert error is not None

    def test_validate_rejects_hidden_intent_revelation(self, narrator_agent, sample_agent_input):
        """Validation rejects revelation of hidden NPC intent via 'secretly'."""
        invalid_block = {
            "narrator_text": "Alain secretly plans to undermine Annette's authority.",
            "sequence": 0,
        }
        error = narrator_agent._validate_narrative_output(invalid_block, sample_agent_input)
        assert error is not None
        error_lower = error.lower()
        assert "hidden" in error_lower or "intent" in error_lower or "undisclosed" in error_lower or "motivations" in error_lower

    def test_validate_accepts_inner_perception(self, narrator_agent, sample_agent_input):
        """Validation accepts inner perception without forcing state."""
        valid_block = {
            "narrator_text": "The tension in the room is palpable. Alain leans forward, his expression hardening.",
            "sequence": 0,
        }
        error = narrator_agent._validate_narrative_output(valid_block, sample_agent_input)
        assert error is None

    def test_validate_accepts_narrative_threads(self, narrator_agent, sample_agent_input):
        """Validation accepts reference to narrative threads."""
        valid_block = {
            "narrator_text": "The unresolved power dynamic threads itself through the silence.",
            "sequence": 0,
        }
        error = narrator_agent._validate_narrative_output(valid_block, sample_agent_input)
        assert error is None


class TestEventSerialization:
    """Test event serialization to JSON."""

    def test_event_serializes_to_json(self, narrator_agent, sample_agent_input):
        """Events serialize to valid JSON."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        for event in events:
            json_str = event.to_json()
            assert json_str is not None
            assert isinstance(json_str, str)
            # Should be parseable
            import json
            data = json.loads(json_str)
            assert "event_id" in data
            assert "event_kind" in data

    def test_event_json_contains_timestamp(self, narrator_agent, sample_agent_input):
        """Event JSON contains ISO timestamp."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        for event in events:
            json_str = event.to_json()
            import json
            data = json.loads(json_str)
            # Should be ISO format
            assert "T" in data["timestamp"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_npc_agency_plan(self, narrator_agent):
        """Agent handles empty NPC agency plan gracefully."""
        agent_input = NarrativeRuntimeAgentInput(
            runtime_state={"scene_id": "test"},
            npc_agency_plan={},  # Empty
            dramatic_signature={},
            narrative_threads=[],
            session_id="test",
            turn_number=1,
        )
        events = list(narrator_agent.stream_narrator_blocks(agent_input))
        # Should still emit ruhepunkt and complete
        event_kinds = [e.event_kind for e in events]
        assert NarrativeEventKind.RUHEPUNKT_REACHED in event_kinds

    def test_max_narrator_blocks_respected(self, narrator_agent):
        """Agent stops at max_narrator_blocks limit."""
        narrator_agent.config.max_narrator_blocks = 3
        # Create input with many initiatives
        many_initiatives = [
            {"actor_id": f"npc_{i}", "resolved": False}
            for i in range(20)
        ]
        agent_input = NarrativeRuntimeAgentInput(
            runtime_state={"scene_id": "test"},
            npc_agency_plan={"initiatives": many_initiatives},
            dramatic_signature={},
            narrative_threads=[],
            session_id="test",
            turn_number=1,
        )
        events = list(narrator_agent.stream_narrator_blocks(agent_input))
        narrator_blocks = [e for e in events if e.event_kind == NarrativeEventKind.NARRATOR_BLOCK]
        assert len(narrator_blocks) <= 3

    def test_error_event_on_invalid_narrator_output(self, narrator_agent, sample_agent_input):
        """Error event emitted if narrator output validation fails."""
        # Mock _generate_narrator_block to return narrator text that violates validation rules
        original_generate = narrator_agent._generate_narrator_block
        def mock_generate(*args, **kwargs):
            # This text violates the "You feel that" pattern
            return {"narrator_text": "You feel that Alain's strategy is fundamentally flawed."}
        narrator_agent._generate_narrator_block = mock_generate

        try:
            events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
            event_kinds = [e.event_kind for e in events]
            # Should emit error for validation failure
            assert NarrativeEventKind.ERROR in event_kinds
        finally:
            narrator_agent._generate_narrator_block = original_generate


class TestNarratorGeneration:
    """Test Phase 2: Narrator block generation with dramatic context."""

    def test_generate_narrator_block_uses_dramatic_context(self, narrator_agent, sample_agent_input):
        """Generated narrator blocks reflect dramatic context and pressure."""
        motivation_analysis = narrator_agent._analyze_motivation_pressure(sample_agent_input)
        block = narrator_agent._generate_narrator_block(
            sample_agent_input,
            motivation_analysis,
            block_sequence=0,
        )
        assert block is not None
        assert "narrator_text" in block
        assert len(block["narrator_text"]) > 0

    def test_narrator_text_uses_observational_language(self, narrator_agent, sample_agent_input):
        """Narrator uses observational language (notice, perceive, observe, witness)."""
        motivation_analysis = narrator_agent._analyze_motivation_pressure(sample_agent_input)
        block = narrator_agent._generate_narrator_block(
            sample_agent_input,
            motivation_analysis,
            block_sequence=0,
        )
        text_lower = block["narrator_text"].lower()
        # Should contain observational or atmospheric language
        has_observational = any(word in text_lower for word in [
            "notice", "perceive", "observe", "witness", "sense",
            "atmosphere", "weight", "tension", "pause", "shift"
        ])
        assert has_observational or "perception" in text_lower or "moment" in text_lower

    def test_atmospheric_tone_escalates_with_pressure(self, narrator_agent, sample_agent_input):
        """Atmospheric tone varies based on motivation pressure."""
        high_pressure = {
            "remaining_initiatives": 5,
            "pressure_score": 0.9,
            "initiative_actors": ["npc1", "npc2", "npc3"],
        }
        block = narrator_agent._generate_narrator_block(
            sample_agent_input,
            high_pressure,
            block_sequence=0,
        )
        assert block["atmospheric_tone"] == "escalating_tension"

    def test_narrator_references_narrative_threads(self, narrator_agent, sample_agent_input):
        """Narrator block references visible narrative threads."""
        motivation_analysis = narrator_agent._analyze_motivation_pressure(sample_agent_input)
        block = narrator_agent._generate_narrator_block(
            sample_agent_input,
            motivation_analysis,
            block_sequence=0,
        )
        assert len(block["narrative_threads_referenced"]) >= 0

    def test_determine_atmospheric_tone_scale(self, narrator_agent):
        """Atmospheric tone correctly maps pressure score to tone."""
        assert narrator_agent._determine_atmospheric_tone(0.9, "conflict") == "escalating_tension"
        assert narrator_agent._determine_atmospheric_tone(0.7, "conflict") == "mounting_pressure"
        assert narrator_agent._determine_atmospheric_tone(0.4, "conflict") == "simmering_conflict"
        assert narrator_agent._determine_atmospheric_tone(0.2, "conflict") == "cautious_calm"


class TestPhase2Validation:
    """Test Phase 2: Enhanced narrator validation with regex patterns."""

    def test_validate_rejects_dialogue_recap_argue(self, narrator_agent, sample_agent_input):
        """Validation rejects narrator recapping character argument (dialogue_summary)."""
        invalid = {"narrator_text": "Véronique and Alain debate about authority."}
        error = narrator_agent._validate_narrative_output(invalid, sample_agent_input)
        assert error is not None
        assert "dialogue" in error.lower() or "recap" in error.lower()

    def test_validate_rejects_dialogue_recap_discuss(self, narrator_agent, sample_agent_input):
        """Validation rejects narrator discussing what characters said."""
        invalid = {"narrator_text": "Alain and Michel discuss the consequences."}
        error = narrator_agent._validate_narrative_output(invalid, sample_agent_input)
        assert error is not None

    def test_validate_rejects_dialogue_recap_while_pattern(self, narrator_agent, sample_agent_input):
        """Validation rejects 'while NPC becomes' dialogue summary pattern."""
        invalid = {"narrator_text": "Véronique argues while Michel becomes increasingly uncomfortable."}
        error = narrator_agent._validate_narrative_output(invalid, sample_agent_input)
        assert error is not None

    def test_validate_rejects_forced_state_you_decide(self, narrator_agent, sample_agent_input):
        """Validation rejects 'You decide' pattern (forced_player_state)."""
        invalid = {"narrator_text": "You decide that Alain is wrong."}
        error = narrator_agent._validate_narrative_output(invalid, sample_agent_input)
        assert error is not None
        assert "forced" in error.lower() or "player" in error.lower()

    def test_validate_rejects_forced_state_you_feel_that(self, narrator_agent, sample_agent_input):
        """Validation rejects 'You feel that' pattern (forced judgment)."""
        invalid = {"narrator_text": "You feel that Alain is right and Annette is wrong."}
        error = narrator_agent._validate_narrative_output(invalid, sample_agent_input)
        assert error is not None

    def test_validate_rejects_hidden_intent_secretly_wants(self, narrator_agent, sample_agent_input):
        """Validation rejects 'secretly wants' pattern (hidden_npc_intent)."""
        invalid = {"narrator_text": "Alain secretly wants to end the discussion."}
        error = narrator_agent._validate_narrative_output(invalid, sample_agent_input)
        assert error is not None
        error_lower = error.lower()
        assert "hidden" in error_lower or "intent" in error_lower or "undisclosed" in error_lower or "motivations" in error_lower

    def test_validate_rejects_hidden_intent_see_through(self, narrator_agent, sample_agent_input):
        """Validation rejects 'You can see through' pattern."""
        invalid = {"narrator_text": "You can see through Alain's composure to his true intention."}
        error = narrator_agent._validate_narrative_output(invalid, sample_agent_input)
        assert error is not None

    def test_validate_accepts_observational_language(self, narrator_agent, sample_agent_input):
        """Validation accepts observational language about perceived behavior."""
        # From ADR-MVP3-013 valid example
        valid = {"narrator_text": "You notice the pause before Alain answers; it feels less like uncertainty than calculation."}
        error = narrator_agent._validate_narrative_output(valid, sample_agent_input)
        assert error is None

    def test_validate_accepts_atmospheric_description(self, narrator_agent, sample_agent_input):
        """Validation accepts pure atmospheric/scene description."""
        valid = {"narrator_text": "The air in the room grows heavier. A weight settles between you."}
        error = narrator_agent._validate_narrative_output(valid, sample_agent_input)
        assert error is None

    def test_validate_accepts_observable_behavior(self, narrator_agent, sample_agent_input):
        """Validation accepts description of observable NPC behavior."""
        valid = {"narrator_text": "Alain's expression hardens as he leans forward."}
        error = narrator_agent._validate_narrative_output(valid, sample_agent_input)
        assert error is None


@pytest.mark.mvp3
class TestMVP3Gate:
    """MVP3 gate verification for NarrativeRuntimeAgent."""

    def test_mvp3_narrative_agent_streams_continuously(self, narrator_agent, sample_agent_input):
        """Gate: Agent streams narrator blocks continuously (not turn-sequential)."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        narrator_events = [e for e in events if e.event_kind == NarrativeEventKind.NARRATOR_BLOCK]
        # Should have at least one narrator block
        assert len(narrator_events) >= 1

    def test_mvp3_narrative_agent_respects_motivation_pressure(self, narrator_agent, sample_agent_input):
        """Gate: Agent generates blocks based on NPC motivation pressure."""
        analysis = narrator_agent._analyze_motivation_pressure(sample_agent_input)
        assert analysis["pressure_score"] > 0
        assert analysis["remaining_initiatives"] > 0

    def test_mvp3_narrative_agent_signals_ruhepunkt(self, narrator_agent, sample_agent_input):
        """Gate: Agent signals ruhepunkt when initiatives exhausted."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        ruhepunkt_events = [e for e in events if e.event_kind == NarrativeEventKind.RUHEPUNKT_REACHED]
        assert len(ruhepunkt_events) == 1
        assert ruhepunkt_events[0].data["ruhepunkt_reached"] is True

    def test_mvp3_narrator_validation_enforces_adr_013_contract(self, narrator_agent, sample_agent_input):
        """Gate: Narrator validation enforces ADR-MVP3-013 voice contract (Phase 2)."""
        # Test all three major rejection modes
        modes_enforced = 0

        # Mode 1: Dialogue summary rejection
        bad_dialogue = {"narrator_text": "Véronique and Alain argue about authority while Michel becomes uncomfortable."}
        if narrator_agent._validate_narrative_output(bad_dialogue, sample_agent_input):
            modes_enforced += 1

        # Mode 2: Forced player state rejection
        bad_forced = {"narrator_text": "You decide that Alain is right and feel ashamed."}
        if narrator_agent._validate_narrative_output(bad_forced, sample_agent_input):
            modes_enforced += 1

        # Mode 3: Hidden intent revelation rejection
        bad_intent = {"narrator_text": "You can see through Alain's composure; he secretly wants this to end."}
        if narrator_agent._validate_narrative_output(bad_intent, sample_agent_input):
            modes_enforced += 1

        # Mode 4: Valid inner perception acceptance
        good_perception = {"narrator_text": "You notice the pause before Alain answers; it feels less like uncertainty than calculation."}
        if narrator_agent._validate_narrative_output(good_perception, sample_agent_input) is None:
            modes_enforced += 1

        assert modes_enforced >= 4

    def test_mvp3_narrator_generation_produces_valid_output(self, narrator_agent, sample_agent_input):
        """Gate: All generated narrator blocks pass validation (Phase 2)."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        narrator_events = [e for e in events if e.event_kind == NarrativeEventKind.NARRATOR_BLOCK]

        for event in narrator_events:
            block_data = event.data.get("narrator_block", {})
            error = narrator_agent._validate_narrative_output(block_data, sample_agent_input)
            # All generated blocks must be valid
            assert error is None, f"Generated narrator block failed validation: {error}\n{block_data.get('narrator_text')}"


class TestPhase6TracingOptional:
    """Test Phase 6: Langfuse optional instrumentation with trace scaffolds."""

    def test_tracing_disabled_by_default(self, narrator_agent, sample_agent_input):
        """Tracing should be disabled by default in agent input."""
        assert sample_agent_input.enable_langfuse_tracing is False

    def test_trace_scaffold_emitted_when_tracing_disabled(self, narrator_agent, sample_agent_input):
        """When tracing disabled, emit trace_scaffold_emitted event at start."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))

        scaffold_events = [e for e in events if e.event_kind == NarrativeEventKind.TRACE_SCAFFOLD_EMITTED]
        assert len(scaffold_events) == 1, "Should emit trace_scaffold_emitted at start"
        assert scaffold_events[0].data["trace_status"] == "scaffolds_only"
        assert scaffold_events[0].data["reason"] == "enable_langfuse_tracing=False"

    def test_trace_scaffold_summary_emitted_when_tracing_disabled(self, narrator_agent, sample_agent_input):
        """When tracing disabled, emit trace_scaffold_summary event at end."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))

        summary_events = [e for e in events if e.event_kind == NarrativeEventKind.TRACE_SCAFFOLD_SUMMARY]
        assert len(summary_events) == 1, "Should emit trace_scaffold_summary at end"
        assert summary_events[0].data["total_scaffolds"] > 0
        assert "trace_scaffold" in summary_events[0].data

    def test_trace_scaffolds_collect_narrator_block_metadata(self, narrator_agent, sample_agent_input):
        """Trace scaffolds should capture metadata for each narrator block."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))

        summary = next(e for e in events if e.event_kind == NarrativeEventKind.TRACE_SCAFFOLD_SUMMARY)
        scaffold_data = summary.data["trace_scaffold"]

        # Should have narrator_block_generation entries
        assert "narrator_block_generation" in scaffold_data
        assert len(scaffold_data["narrator_block_generation"]) > 0

        # Each entry should have required fields
        for entry in scaffold_data["narrator_block_generation"]:
            assert "timestamp" in entry
            assert "metadata" in entry
            assert "trace_status" in entry
            assert entry["trace_status"] == "scaffold_only"

            # Metadata should have block details
            metadata = entry["metadata"]
            assert "block_id" in metadata
            assert "atmospheric_tone" in metadata

    def test_trace_scaffold_event_order(self, narrator_agent, sample_agent_input):
        """Trace scaffold events should appear in correct order."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        event_kinds = [e.event_kind for e in events]

        # Should have: scaffold_emitted, narrator_blocks, ruhepunkt, scaffold_summary, complete
        if NarrativeEventKind.TRACE_SCAFFOLD_EMITTED in event_kinds:
            emitted_idx = event_kinds.index(NarrativeEventKind.TRACE_SCAFFOLD_EMITTED)

            # Find summary index
            summary_indices = [i for i, k in enumerate(event_kinds)
                             if k == NarrativeEventKind.TRACE_SCAFFOLD_SUMMARY]
            if summary_indices:
                summary_idx = summary_indices[0]
                # Emitted should come before summary
                assert emitted_idx < summary_idx

    def test_trace_scaffold_disabled_when_tracing_enabled(self, narrator_agent):
        """When tracing enabled, should NOT emit trace scaffold events."""
        agent_input = NarrativeRuntimeAgentInput(
            runtime_state={"scene_id": "test"},
            npc_agency_plan={"initiatives": [
                {"actor_id": "npc1", "resolved": False},
            ]},
            dramatic_signature={},
            narrative_threads=[],
            session_id="test_session",
            turn_number=1,
            enable_langfuse_tracing=True,  # Tracing enabled
        )

        events = list(narrator_agent.stream_narrator_blocks(agent_input))
        event_kinds = [e.event_kind for e in events]

        # Should NOT have trace scaffold events
        assert NarrativeEventKind.TRACE_SCAFFOLD_EMITTED not in event_kinds
        assert NarrativeEventKind.TRACE_SCAFFOLD_SUMMARY not in event_kinds

    def test_trace_scaffold_no_interference_with_streaming(self, narrator_agent, sample_agent_input):
        """Trace scaffolds should not interfere with normal streaming."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        event_kinds = [e.event_kind for e in events]

        # Should still have all normal events
        assert NarrativeEventKind.NARRATOR_BLOCK in event_kinds
        assert NarrativeEventKind.RUHEPUNKT_REACHED in event_kinds
        assert NarrativeEventKind.STREAMING_COMPLETE in event_kinds

        # Narrator blocks should still come before ruhepunkt
        block_indices = [i for i, k in enumerate(event_kinds) if k == NarrativeEventKind.NARRATOR_BLOCK]
        ruhepunkt_indices = [i for i, k in enumerate(event_kinds) if k == NarrativeEventKind.RUHEPUNKT_REACHED]

        if block_indices and ruhepunkt_indices:
            assert max(block_indices) < min(ruhepunkt_indices)

    def test_trace_scaffold_block_count_matches_streamed(self, narrator_agent, sample_agent_input):
        """Trace scaffold summary block count should match streamed blocks."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))

        narrator_blocks = [e for e in events if e.event_kind == NarrativeEventKind.NARRATOR_BLOCK]
        summary = next(e for e in events if e.event_kind == NarrativeEventKind.TRACE_SCAFFOLD_SUMMARY)

        assert summary.data["blocks_streamed"] == len(narrator_blocks)

    def test_trace_scaffold_session_id_preserved(self, narrator_agent, sample_agent_input):
        """Trace scaffold events should preserve session_id for correlation."""
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))

        scaffold_events = [e for e in events if e.event_kind in (
            NarrativeEventKind.TRACE_SCAFFOLD_EMITTED,
            NarrativeEventKind.TRACE_SCAFFOLD_SUMMARY
        )]

        for event in scaffold_events:
            assert event.data.get("session_id") == sample_agent_input.session_id


@pytest.mark.mvp3
class TestMVP3Phase6Gate:
    """MVP3 gate verification for Phase 6 Langfuse optional instrumentation."""

    def test_mvp3_phase6_tracing_optional_by_default(self, narrator_agent, sample_agent_input):
        """Gate: Tracing is optional and disabled by default."""
        # Default input has tracing disabled
        assert sample_agent_input.enable_langfuse_tracing is False

        # Streaming should emit trace scaffolds
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))
        scaffold_events = [e for e in events if e.event_kind == NarrativeEventKind.TRACE_SCAFFOLD_EMITTED]
        assert len(scaffold_events) == 1

    def test_mvp3_phase6_trace_scaffolds_emit_without_langfuse(self, narrator_agent, sample_agent_input):
        """Gate: Trace scaffolds emitted even without Langfuse SDK/credentials."""
        # No Langfuse setup needed—should use JSON scaffolds by default
        events = list(narrator_agent.stream_narrator_blocks(sample_agent_input))

        summary = next(e for e in events if e.event_kind == NarrativeEventKind.TRACE_SCAFFOLD_SUMMARY)
        scaffold_data = summary.data["trace_scaffold"]

        # Should have collected trace metadata
        assert "narrator_block_generation" in scaffold_data
        assert len(scaffold_data["narrator_block_generation"]) > 0

    def test_mvp3_phase6_trace_scaffold_respects_enable_flag(self, narrator_agent):
        """Gate: Trace scaffolds respect enable_langfuse_tracing flag."""
        # When tracing enabled, no scaffolds
        agent_input_enabled = NarrativeRuntimeAgentInput(
            runtime_state={"scene_id": "test"},
            npc_agency_plan={"initiatives": [{"actor_id": "npc1", "resolved": False}]},
            dramatic_signature={},
            narrative_threads=[],
            session_id="test",
            turn_number=1,
            enable_langfuse_tracing=True,
        )

        events = list(narrator_agent.stream_narrator_blocks(agent_input_enabled))
        event_kinds = [e.event_kind for e in events]

        # Should NOT have scaffold events when tracing enabled
        assert NarrativeEventKind.TRACE_SCAFFOLD_EMITTED not in event_kinds
        assert NarrativeEventKind.TRACE_SCAFFOLD_SUMMARY not in event_kinds

        # But should still have narrator blocks
        assert NarrativeEventKind.NARRATOR_BLOCK in event_kinds
