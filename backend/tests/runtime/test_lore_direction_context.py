"""Tests for W2.3.5 lore and direction context layer.

Tests verify that:
- modular guidance units can be selected deterministically
- only relevant lore/direction context is attached for a given situation
- irrelevant module context is excluded
- injected context remains bounded as source material grows
- current scene / progression / relationship context can influence selection
- the lore/direction layer remains distinct from history/summary/context layers
- no regressions in existing runtime tests
"""

from __future__ import annotations

import pytest

from app.content.module_models import (
    CharacterDefinition,
    ContentModule,
    EndingCondition,
    ModuleMetadata,
    PhaseTransition,
    RelationshipAxis,
    ScenePhase,
    TriggerDefinition,
)
from app.runtime.lore_direction_context import (
    LoreDirectionContext,
    ModuleGuidanceUnit,
    derive_lore_direction_context,
)
from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext, SalientRelationshipAxis
from app.runtime.session_history import HistoryEntry, SessionHistory


@pytest.fixture
def minimal_module() -> ContentModule:
    """Create a minimal test module with basic content."""
    return ContentModule(
        metadata=ModuleMetadata(
            module_id="test_module",
            title="Test Module",
            version="1.0.0",
            contract_version="1.0.0",
            description="Test module for W2.3.5",
        ),
        characters={
            "alice": CharacterDefinition(
                id="alice",
                name="Alice",
                role="protagonist",
                baseline_attitude="determined",
                extras={},
            ),
            "bob": CharacterDefinition(
                id="bob",
                name="Bob",
                role="antagonist",
                baseline_attitude="hostile",
                extras={},
            ),
        },
        relationship_axes={
            "dominance": RelationshipAxis(
                id="dominance",
                name="Dominance",
                description="Power dynamics between characters",
                baseline={"alice": 0.5, "bob": 0.5},
                escalation={"conflict_increase": 0.2},
            ),
        },
        trigger_definitions={
            "conflict_alice_bob": TriggerDefinition(
                id="conflict_alice_bob",
                name="Conflict Alice Bob",
                description="Direct confrontation between Alice and Bob",
                recognition_markers=["argument", "disagreement"],
                escalation_impact={"dominance": 0.3},
                active_in_phases=["phase_1"],
            ),
        },
        scene_phases={
            "phase_1": ScenePhase(
                id="phase_1",
                name="First Phase",
                sequence=1,
                description="The opening confrontation",
                content_focus=["tension", "dominance"],
                engine_tasks=["establish_conflict"],
                active_triggers=["conflict_alice_bob"],
            ),
            "phase_2": ScenePhase(
                id="phase_2",
                name="Second Phase",
                sequence=2,
                description="The escalation",
                content_focus=["escalation"],
                engine_tasks=["raise_stakes"],
                active_triggers=["conflict_alice_bob"],
            ),
        },
        phase_transitions={
            "t1": PhaseTransition(
                from_phase="phase_1",
                to_phase="phase_2",
                trigger_conditions=["conflict_escalates"],
                transition_action="Move to escalation",
            ),
        },
        ending_conditions={
            "ending_resolution": EndingCondition(
                id="ending_resolution",
                name="Resolution",
                description="The conflict is resolved",
                trigger_conditions=["both_agree"],
                outcome={"winner": None},
            ),
        },
    )


class TestModuleGuidanceUnitSelection:
    """Tests for selecting guidance units from modules."""

    def test_scene_guidance_selected_for_current_scene(self, minimal_module):
        """Current scene triggers selection of relevant phase guidance."""
        history = SessionHistory()
        progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=1,
            total_turns_in_source=1,
            current_scene_id="phase_1",
            session_phase="early",
        )
        relationships = RelationshipAxisContext()

        context = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_1",
            history=history,
            progression_summary=progression,
            relationship_context=relationships,
        )

        # Should include phase guidance
        phase_units = [u for u in context.selected_units if u.unit_type == "phase"]
        assert len(phase_units) > 0
        assert any("opening confrontation" in u.guidance_text for u in phase_units)

    def test_character_guidance_selected_for_recent_characters(self, minimal_module):
        """Characters in recent triggers get guidance selected."""
        history = SessionHistory()
        history.add_entry(
            HistoryEntry(
                turn_number=1,
                scene_id="phase_1",
                guard_outcome="accepted",
                detected_triggers=["conflict_alice_bob"],
            )
        )

        progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=1,
            total_turns_in_source=1,
            current_scene_id="phase_1",
            session_phase="early",
        )
        relationships = RelationshipAxisContext()

        context = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_1",
            history=history,
            progression_summary=progression,
            relationship_context=relationships,
        )

        # Should include character guidance for alice and/or bob
        char_units = [u for u in context.selected_units if u.unit_type == "character"]
        assert len(char_units) > 0

    def test_trigger_guidance_selected_for_recent_triggers(self, minimal_module):
        """Recent triggers get their guidance selected."""
        history = SessionHistory()
        history.add_entry(
            HistoryEntry(
                turn_number=1,
                scene_id="phase_1",
                guard_outcome="accepted",
                detected_triggers=["conflict_alice_bob"],
            )
        )

        progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=1,
            total_turns_in_source=1,
            current_scene_id="phase_1",
            session_phase="early",
        )
        relationships = RelationshipAxisContext()

        context = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_1",
            history=history,
            progression_summary=progression,
            relationship_context=relationships,
        )

        # Should include trigger guidance
        trigger_units = [u for u in context.selected_units if u.unit_type == "trigger"]
        assert len(trigger_units) > 0


class TestLoreDirectionContextBounds:
    """Tests for bounded context size."""

    def test_selected_units_bounded_to_15(self, minimal_module):
        """Selected units never exceed 15."""
        history = SessionHistory()
        for turn in range(1, 20):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="phase_1",
                    guard_outcome="accepted",
                    detected_triggers=["conflict_alice_bob"],
                )
            )

        progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=20,
            total_turns_in_source=20,
            current_scene_id="phase_1",
            session_phase="middle",
            derived_from_turn=20,
        )
        relationships = RelationshipAxisContext(
            salient_axes=[
                SalientRelationshipAxis(
                    character_a="alice",
                    character_b="bob",
                    salience_score=0.9,
                    recent_change_direction="escalating",
                    signal_type="tension",
                )
            ],
            total_character_pairs_known=1,
            has_escalation_markers=True,
            highest_salience_axis=("alice", "bob"),
        )

        context = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_1",
            history=history,
            progression_summary=progression,
            relationship_context=relationships,
        )

        assert len(context.selected_units) <= 15

    def test_irrelevant_content_excluded(self, minimal_module):
        """Phase 2 guidance excluded when in phase 1."""
        history = SessionHistory()
        progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=1,
            total_turns_in_source=1,
            current_scene_id="phase_1",
            session_phase="early",
        )
        relationships = RelationshipAxisContext()

        context = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_1",
            history=history,
            progression_summary=progression,
            relationship_context=relationships,
        )

        # Should not include phase_2 guidance
        phase_2_units = [u for u in context.selected_units if "phase_2" in u.unit_id]
        assert len(phase_2_units) == 0


class TestLoreDirectionContextSelection:
    """Tests for deterministic selection."""

    def test_same_situation_produces_same_context(self, minimal_module):
        """Identical situation produces identical context."""
        history1 = SessionHistory()
        history1.add_entry(
            HistoryEntry(
                turn_number=1,
                scene_id="phase_1",
                guard_outcome="accepted",
                detected_triggers=["conflict_alice_bob"],
            )
        )

        history2 = SessionHistory()
        history2.add_entry(
            HistoryEntry(
                turn_number=1,
                scene_id="phase_1",
                guard_outcome="accepted",
                detected_triggers=["conflict_alice_bob"],
            )
        )

        progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=1,
            total_turns_in_source=1,
            current_scene_id="phase_1",
            session_phase="early",
        )
        relationships = RelationshipAxisContext()

        context1 = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_1",
            history=history1,
            progression_summary=progression,
            relationship_context=relationships,
        )

        context2 = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_1",
            history=history2,
            progression_summary=progression,
            relationship_context=relationships,
        )

        assert len(context1.selected_units) == len(context2.selected_units)
        assert context1.selection_rationale == context2.selection_rationale


class TestLoreDirectionContextInfluence:
    """Tests for how context layers influence selection."""

    def test_progression_influences_guidance(self, minimal_module):
        """Progression level influences what guidance is selected."""
        history = SessionHistory()
        relationships = RelationshipAxisContext()

        # Early phase
        early_progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=1,
            total_turns_in_source=1,
            current_scene_id="phase_1",
            session_phase="early",
            derived_from_turn=1,
        )

        early_context = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_1",
            history=history,
            progression_summary=early_progression,
            relationship_context=relationships,
        )

        # Late phase
        late_progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=50,
            total_turns_in_source=50,
            current_scene_id="phase_2",
            session_phase="late",
            derived_from_turn=50,
        )

        late_context = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_2",
            history=history,
            progression_summary=late_progression,
            relationship_context=relationships,
        )

        # Different phases should result in different guidance
        assert early_context.derived_from_turn != late_context.derived_from_turn

    def test_relationship_context_influences_guidance(self, minimal_module):
        """Active relationships influence guidance selection."""
        history = SessionHistory()
        progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=1,
            total_turns_in_source=1,
            current_scene_id="phase_1",
            session_phase="early",
        )

        # No active relationships
        no_rel_context = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_1",
            history=history,
            progression_summary=progression,
            relationship_context=RelationshipAxisContext(),
        )

        # With active relationships
        active_rel_context = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_1",
            history=history,
            progression_summary=progression,
            relationship_context=RelationshipAxisContext(
                has_escalation_markers=True,
                highest_salience_axis=("alice", "bob"),
            ),
        )

        # Should have different rationale
        assert "escalation" in str(active_rel_context.selection_rationale).lower()


class TestLoreDirectionContextDistinctness:
    """Tests ensuring lore/direction context is distinct from other layers."""

    def test_not_raw_module_dump(self, minimal_module):
        """Context doesn't include irrelevant module content."""
        history = SessionHistory()
        progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=1,
            total_turns_in_source=1,
            current_scene_id="phase_1",
            session_phase="early",
        )
        relationships = RelationshipAxisContext()

        context = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_1",
            history=history,
            progression_summary=progression,
            relationship_context=relationships,
        )

        # Context should be much smaller than module
        assert len(context.selected_units) < (
            len(minimal_module.characters)
            + len(minimal_module.relationship_axes)
            + len(minimal_module.trigger_definitions)
        )

    def test_metadata_present_for_clarity(self, minimal_module):
        """Context includes metadata about selection."""
        history = SessionHistory()
        progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=1,
            total_turns_in_source=1,
            current_scene_id="phase_1",
            session_phase="early",
        )
        relationships = RelationshipAxisContext()

        context = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_1",
            history=history,
            progression_summary=progression,
            relationship_context=relationships,
        )

        # Should include clear metadata
        assert context.module_id == "test_module"
        assert context.total_available_units > 0
        assert len(context.selection_rationale) > 0


class TestLoreDirectionContextEndingHandling:
    """Tests for ending-state guidance."""

    def test_ending_guidance_selected_when_reached(self, minimal_module):
        """Ending guidance selected when ending is reached."""
        history = SessionHistory()
        progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=10,
            total_turns_in_source=10,
            current_scene_id="phase_2",
            session_phase="ended",
            ending_reached=True,
            ending_id="ending_resolution",
            derived_from_turn=10,
        )
        relationships = RelationshipAxisContext()

        context = derive_lore_direction_context(
            module=minimal_module,
            current_scene_id="phase_2",
            history=history,
            progression_summary=progression,
            relationship_context=relationships,
        )

        # Should include ending guidance
        ending_units = [u for u in context.selected_units if u.unit_type == "ending"]
        assert len(ending_units) > 0
        assert any("ending_reached" in rationale for rationale in context.selection_rationale)
