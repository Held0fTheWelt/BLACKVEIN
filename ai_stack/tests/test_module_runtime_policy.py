from __future__ import annotations

from pathlib import Path

from ai_stack.beat_lifecycle_contracts import phase_beat_candidates, select_beat_candidate
from ai_stack.callback_web_contracts import CALLBACK_WEB_POLICY_SCHEMA_VERSION
from ai_stack.consequence_cascade_contracts import CONSEQUENCE_CASCADE_POLICY_SCHEMA_VERSION
from ai_stack.expectation_variation_contracts import EXPECTATION_VARIATION_POLICY_VERSION
from ai_stack.genre_awareness_contracts import GENRE_AWARENESS_POLICY_VERSION
from ai_stack.improvisational_coherence_contracts import (
    IMPROVISATIONAL_COHERENCE_POLICY_VERSION,
)
from ai_stack.meta_narrative_awareness_contracts import (
    META_NARRATIVE_AWARENESS_POLICY_VERSION_V2,
)
from ai_stack.narrative_momentum_contracts import NARRATIVE_MOMENTUM_POLICY_VERSION
from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.pacing_rhythm_contracts import PACING_RHYTHM_POLICY_VERSION
from ai_stack.relationship_state_contracts import RELATIONSHIP_STATE_POLICY_VERSION
from ai_stack.sensory_context_contracts import SENSORY_CONTEXT_POLICY_VERSION
from ai_stack.social_pressure_contracts import SOCIAL_PRESSURE_POLICY_VERSION
from ai_stack.symbolic_object_resonance_contracts import (
    SYMBOLIC_OBJECT_RESONANCE_POLICY_VERSION,
)
from ai_stack.temporal_control_contracts import TEMPORAL_CONTROL_POLICY_VERSION
from ai_stack.tonal_consistency_contracts import TONAL_CONSISTENCY_POLICY_VERSION
from ai_stack.runtime_aspect_ledger import (
    ASPECT_BEAT,
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_COMMIT,
    ASPECT_HIERARCHICAL_MEMORY,
    ASPECT_NARRATOR_AUTHORITY,
    initialize_runtime_aspect_ledger,
    make_aspect_record,
    set_aspect_record,
)


MODULE_ID = "god_of_carnage"


def test_module_runtime_policy_loads_goc_without_runtime_hardcoding() -> None:
    policy = load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()

    assert policy["module_id"] == MODULE_ID
    assert policy["runtime_profile_id"] == "solo_test"
    assert policy["actor_roster"]
    assert policy["playable_roles"]
    assert policy["location_model"]["locations"]
    assert policy["phase_policy"]["phases"]
    assert policy["narrative_aspect_policy"]["aspects"]
    assert policy["information_disclosure_policy"]["enabled"] is True
    assert policy["information_disclosure_policy"]["units"]
    assert policy["memory_policy"]["enabled"] is True
    assert policy["dramatic_irony_policy"]["enabled"] is True
    assert policy["dramatic_irony_policy"]["direct_reveal_allowed"] is False
    assert policy["dramatic_irony_policy"]["model_context_visibility"] == "bounded_surface_only"
    assert policy["dramatic_irony_policy"]["require_structured_realization"] is True
    assert policy["runtime_governance_policy"]["dramatic_irony"]["enabled"] is True
    assert policy["runtime_governance_policy"]["dramatic_irony"]["hidden_fact_echo_check"] is True
    assert policy["runtime_governance_policy"]["callback_web"]["schema_version"] == CALLBACK_WEB_POLICY_SCHEMA_VERSION
    assert policy["runtime_governance_policy"]["callback_web"]["enabled"] is True
    assert policy["runtime_governance_policy"]["callback_web"]["max_graph_edges"] == 4
    assert policy["runtime_governance_policy"]["callback_web"]["allowed_continuity_classes"]
    assert (
        policy["runtime_governance_policy"]["consequence_cascade"]["schema_version"]
        == CONSEQUENCE_CASCADE_POLICY_SCHEMA_VERSION
    )
    assert policy["runtime_governance_policy"]["consequence_cascade"]["enabled"] is True
    assert policy["runtime_governance_policy"]["consequence_cascade"]["max_graph_items"] == 5
    assert policy["runtime_governance_policy"]["consequence_cascade"]["allowed_continuity_classes"]
    assert policy["runtime_governance_policy"]["pacing_rhythm"]["schema_version"] == PACING_RHYTHM_POLICY_VERSION
    assert policy["runtime_governance_policy"]["pacing_rhythm"]["enabled"] is True
    assert policy["runtime_governance_policy"]["pacing_rhythm"]["cadence_profiles"]
    assert (
        policy["runtime_governance_policy"]["temporal_control"]["schema_version"]
        == TEMPORAL_CONTROL_POLICY_VERSION
    )
    assert policy["runtime_governance_policy"]["temporal_control"]["enabled"] is True
    assert "recall_committed_past" in policy["runtime_governance_policy"]["temporal_control"]["allowed_operations"]
    assert policy["runtime_governance_policy"]["sensory_context"]["schema_version"] == SENSORY_CONTEXT_POLICY_VERSION
    assert policy["runtime_governance_policy"]["sensory_context"]["enabled"] is True
    assert policy["runtime_governance_policy"]["sensory_context"]["require_structured_events"] is True
    assert (
        policy["runtime_governance_policy"]["symbolic_object_resonance"]["schema_version"]
        == SYMBOLIC_OBJECT_RESONANCE_POLICY_VERSION
    )
    assert policy["runtime_governance_policy"]["symbolic_object_resonance"]["enabled"] is True
    assert policy["runtime_governance_policy"]["symbolic_object_resonance"]["max_symbols_per_turn"] == 2
    assert policy["runtime_governance_policy"]["symbolic_object_resonance"]["allowed_resonance_roles"]
    assert policy["symbolic_object_resonance_policy"]["enabled"] is True
    assert (
        policy["runtime_governance_policy"]["tonal_consistency"]["schema_version"]
        == TONAL_CONSISTENCY_POLICY_VERSION
    )
    assert policy["runtime_governance_policy"]["tonal_consistency"]["enabled"] is True
    assert policy["runtime_governance_policy"]["tonal_consistency"]["tone_profiles"]
    assert policy["tonal_consistency_policy"]["enabled"] is True
    assert (
        policy["runtime_governance_policy"]["genre_awareness"]["schema_version"]
        == GENRE_AWARENESS_POLICY_VERSION
    )
    assert policy["runtime_governance_policy"]["genre_awareness"]["enabled"] is True
    assert (
        policy["runtime_governance_policy"]["genre_awareness"]["genre_profile_id"]
        == "bourgeois_social_drama"
    )
    assert policy["runtime_governance_policy"]["genre_awareness"]["required_conventions"]
    assert policy["runtime_governance_policy"]["genre_awareness"]["require_structured_events"] is True
    assert policy["genre_awareness_policy"]["enabled"] is True
    assert (
        policy["runtime_governance_policy"]["improvisational_coherence"]["schema_version"]
        == IMPROVISATIONAL_COHERENCE_POLICY_VERSION
    )
    assert policy["runtime_governance_policy"]["improvisational_coherence"]["enabled"] is True
    assert policy["runtime_governance_policy"]["improvisational_coherence"]["min_anchor_refs"] >= 1
    assert (
        policy["runtime_governance_policy"]["expectation_variation"]["schema_version"]
        == EXPECTATION_VARIATION_POLICY_VERSION
    )
    assert policy["runtime_governance_policy"]["expectation_variation"]["enabled"] is True
    assert policy["runtime_governance_policy"]["expectation_variation"]["max_variation_units_per_turn"] == 1
    assert policy["runtime_governance_policy"]["expectation_variation"]["allowed_variation_types"]
    assert (
        policy["runtime_governance_policy"]["narrative_momentum"]["schema_version"]
        == NARRATIVE_MOMENTUM_POLICY_VERSION
    )
    assert policy["runtime_governance_policy"]["narrative_momentum"]["enabled"] is True
    assert policy["runtime_governance_policy"]["narrative_momentum"]["allowed_transitions"]
    assert policy["runtime_governance_policy"]["narrative_momentum"]["source_weights"]["scene_energy_transition"]
    assert policy["runtime_governance_policy"]["narrative_momentum"]["require_structured_events"] is True
    assert policy["narrative_momentum_policy"]["enabled"] is True
    assert (
        policy["runtime_governance_policy"]["meta_narrative_awareness"]["schema_version"]
        == META_NARRATIVE_AWARENESS_POLICY_VERSION_V2
    )
    assert policy["runtime_governance_policy"]["meta_narrative_awareness"]["enabled"] is True
    assert "full_fourth_wall" in policy["runtime_governance_policy"]["meta_narrative_awareness"]["allowed_intensities"]
    assert "full" in policy["runtime_governance_policy"]["meta_narrative_awareness"]["allowed_awareness_tiers"]
    assert policy["runtime_governance_policy"]["meta_narrative_awareness"]["allow_direct_player_address"] is True
    assert policy["runtime_governance_policy"]["meta_narrative_awareness"]["allow_cross_session_memory"] is True
    assert policy["runtime_governance_policy"]["meta_narrative_awareness"]["characters_with_awareness"]
    assert policy["runtime_governance_policy"]["social_pressure"]["schema_version"] == SOCIAL_PRESSURE_POLICY_VERSION
    assert policy["runtime_governance_policy"]["social_pressure"]["enabled"] is True
    assert policy["runtime_governance_policy"]["social_pressure"]["source_scores"]["social_risk_band"]
    assert (
        policy["runtime_governance_policy"]["relationship_state_machine"]["schema_version"]
        == RELATIONSHIP_STATE_POLICY_VERSION
    )
    assert policy["runtime_governance_policy"]["relationship_state_machine"]["enabled"] is True
    assert policy["runtime_governance_policy"]["relationship_state_machine"]["transition_weights"]
    assert policy["runtime_governance_policy"]["action_resolution_short_path"]["enabled"] is True
    assert policy["runtime_governance_policy"]["visible_projection"]["hard_failure_behavior"] == "recover"
    assert "character_documents" in policy["content_sources"]
    assert "actor_pressure_profiles" in policy["content_sources"]
    assert "narrative_aspect_policy" in policy["content_sources"]
    assert "information_disclosure_policy" in policy["content_sources"]
    assert "memory_policy" in policy["content_sources"]
    assert "dramatic_irony_policy" in policy["content_sources"]
    assert "expectation_variation_policy" in policy["content_sources"]
    assert "narrative_momentum_policy" in policy["content_sources"]
    assert "symbolic_object_resonance_policy" in policy["content_sources"]
    assert "genre_awareness_policy" in policy["content_sources"]
    assert "meta_narrative_awareness_policy" in policy["content_sources"]
    assert "tonal_consistency_policy" in policy["content_sources"]
    assert "runtime_intelligence" in policy["content_sources"]


def test_runtime_aspect_ledger_schema_is_module_neutral() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="story-1",
        module_id="example_module",
        runtime_profile_id="example_profile",
        turn_number=3,
        turn_kind="player",
        raw_player_input="Look around.",
        turn_id="story-1:turn:3",
    )

    assert ledger["schema_version"] == "turn_aspect_ledger.v1"
    assert ledger["module_id"] == "example_module"
    assert ledger["runtime_profile_id"] == "example_profile"
    assert ledger["canonical_turn_id"] == "story-1:turn:3"
    assert "god_of_carnage" not in str(ledger)


def test_runtime_aspect_ledger_exposes_design_model_projection() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="story-2",
        module_id="example_module",
        runtime_profile_id="example_profile",
        turn_number=4,
        turn_kind="player",
        raw_player_input="Go north.",
        turn_id="story-2:turn:4",
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_BEAT,
        make_aspect_record(
            applicable=True,
            status="passed",
            expected={"candidate_beats": ["beat_a"], "expected_realization": ["narrator.location_transition.describe"]},
            selected={"selected_beat_id": "beat_a", "selection_source": "module_policy"},
            actual={"realized": True},
            source="runtime",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_CAPABILITY_SELECTION,
        make_aspect_record(
            applicable=True,
            status="passed",
            expected={"required_capabilities": ["narrator.location_transition.describe"]},
            selected={"selected_capabilities": ["player.movement.request", "narrator.location_transition.describe"]},
            actual={"realized_capabilities": ["player.movement.request", "narrator.location_transition.describe"]},
            source="runtime",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_NARRATOR_AUTHORITY,
        make_aspect_record(
            applicable=True,
            status="passed",
            expected={"required": True},
            actual={"narrator_block_present": True},
            source="runtime",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_COMMIT,
        make_aspect_record(
            applicable=True,
            status="passed",
            actual={"commit_applied": True, "quality_class": "healthy"},
            source="runtime",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_HIERARCHICAL_MEMORY,
        make_aspect_record(
            applicable=True,
            status="passed",
            expected={"policy_present": True, "policy_enabled": True},
            selected={"selected_tiers": ["turn"], "source_canonical_turn_id": "story-2:turn:4"},
            actual={
                "write_allowed": True,
                "written_item_count": 1,
                "memory_present": True,
                "context_item_count": 1,
                "context_bounded": True,
            },
            source="commit",
        ),
    )

    projection = ledger["runtime_intelligence_projection"]
    assert projection["schema_version"] == "turn_aspect_ledger.v1"
    assert projection["beat"]["selected_beat"]["id"] == "beat_a"
    assert projection["beat"]["realized"] is True
    assert projection["authority"]["narrator"]["required"] is True
    assert "player.movement.request" in projection["capability"]["selected_capabilities"]
    assert projection["hierarchical_memory"]["written_item_count"] == 1
    assert projection["hierarchical_memory"]["context_bounded"] is True
    assert projection["commit"]["committed"] is True


def test_authority_and_capability_policy_come_from_module_policy() -> None:
    policy = load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()

    forbidden = policy["capability_policy"]["forbidden"]
    assert "npc.execute_player_action.forbidden" in forbidden
    assert "npc.narrate_player_perception.forbidden" in forbidden
    assert policy["authority_policy"]["hard_forbidden_policy"]


def test_narrative_aspect_policy_loads_from_generic_module_content(tmp_path: Path) -> None:
    module_dir = tmp_path / "module_alpha"
    module_dir.mkdir()
    (module_dir / "narrative_aspect_policy.yaml").write_text(
        """
narrative_aspect_policy:
  schema_version: narrative_aspect_policy.v1
  aspects:
    - id: aspect_alpha
      enabled: true
      activation:
        always: true
      evidence:
        - id: state_alpha
          kind: state_path_present
          path: signals.alpha
          required: true
""".strip(),
        encoding="utf-8",
    )

    policy = load_module_runtime_policy(
        "module_alpha",
        "profile_alpha",
        content_modules_root=tmp_path,
    ).to_dict()

    aspect_policy = policy["narrative_aspect_policy"]
    assert policy["module_id"] == "module_alpha"
    assert aspect_policy["aspects"][0]["id"] == "aspect_alpha"
    assert aspect_policy["aspects"][0]["evidence"][0]["kind"] == "state_path_present"
    assert "narrative_aspect_policy" in policy["content_sources"]


def test_memory_policy_loads_from_generic_module_content(tmp_path: Path) -> None:
    module_dir = tmp_path / "module_alpha"
    module_dir.mkdir()
    (module_dir / "memory_policy.yaml").write_text(
        """
memory_policy:
  schema_version: hierarchical_memory_policy.v1
  enabled: true
  write_requires_committed_turn: true
  tiers:
    - id: turn
      enabled: true
      max_items: 3
      max_context_items: 2
""".strip(),
        encoding="utf-8",
    )

    policy = load_module_runtime_policy(
        "module_alpha",
        "profile_alpha",
        content_modules_root=tmp_path,
    ).to_dict()

    memory_policy = policy["memory_policy"]
    assert memory_policy["enabled"] is True
    assert memory_policy["tiers"][0]["id"] == "turn"
    assert memory_policy["tiers"][0]["max_items"] == 3
    assert "memory_policy" in policy["content_sources"]


def test_information_disclosure_policy_loads_from_generic_module_content(tmp_path: Path) -> None:
    module_dir = tmp_path / "module_alpha"
    module_dir.mkdir()
    (module_dir / "information_disclosure_policy.yaml").write_text(
        """
information_disclosure_policy:
  schema_version: information_disclosure_policy.v1
  enabled: true
  max_visible_units_per_turn: 1
  units:
    - id: unit_alpha
      stage: hint
      allowed_modes:
        - visible_hint
      unlock_conditions:
        always: true
""".strip(),
        encoding="utf-8",
    )

    policy = load_module_runtime_policy(
        "module_alpha",
        "profile_alpha",
        content_modules_root=tmp_path,
    ).to_dict()

    disclosure_policy = policy["information_disclosure_policy"]
    assert disclosure_policy["enabled"] is True
    assert disclosure_policy["units"][0]["id"] == "unit_alpha"
    assert disclosure_policy["units"][0]["stage"] == "hint"
    assert "information_disclosure_policy" in policy["content_sources"]


def test_beat_candidates_come_from_phase_policy_data() -> None:
    policy = load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()
    phase_id = next(iter(policy["phase_policy"]["phases"].keys()))

    candidates = phase_beat_candidates(
        module_policy=policy,
        phase_id=phase_id,
        expected_visible_functions=["narrator.scene_context.establish"],
    )
    selection = select_beat_candidate(candidates, selection_source="module_policy")

    assert candidates
    assert selection.selected_beat_id
    assert selection.selection_source == "module_policy"
    assert "narrator.scene_context.establish" in selection.expected_visible_functions


def test_generic_runtime_intelligence_modules_do_not_embed_goc_literals() -> None:
    repo = Path(__file__).resolve().parents[2]
    generic_files = [
        repo / "ai_stack" / "beat_lifecycle_contracts.py",
        repo / "ai_stack" / "authority_contracts.py",
        repo / "ai_stack" / "dramatic_capability_contracts.py",
        repo / "ai_stack" / "visible_origin_contracts.py",
        repo / "ai_stack" / "module_runtime_policy.py",
        repo / "ai_stack" / "expectation_variation_contracts.py",
        repo / "ai_stack" / "expectation_variation_engine.py",
        repo / "ai_stack" / "information_disclosure_contracts.py",
        repo / "ai_stack" / "information_disclosure_engine.py",
        repo / "ai_stack" / "improvisational_coherence_contracts.py",
        repo / "ai_stack" / "improvisational_coherence_engine.py",
        repo / "ai_stack" / "narrative_aspect_contracts.py",
        repo / "ai_stack" / "hierarchical_memory_contracts.py",
        repo / "ai_stack" / "runtime_aspect_ledger.py",
        repo / "ai_stack" / "runtime_dramatic_capabilities.py",
        repo / "ai_stack" / "langgraph_runtime_executor.py",
        repo / "world-engine" / "app" / "story_runtime" / "manager.py",
        repo / "tools" / "mcp_server" / "tools_registry_handlers_langfuse_verify.py",
    ]
    forbidden = (
        "Annette",
        "Alain",
        "Veronique",
        "Véronique",
        "Michel",
        "bathroom",
        "living_room",
        "vallon_living_room",
        "phase_1",
        "ritual_civility",
        "god_of_carnage",
    )
    for path in generic_files:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{token!r} leaked into {path}"
