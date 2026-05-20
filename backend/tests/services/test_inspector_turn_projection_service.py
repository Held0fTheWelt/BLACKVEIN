"""Unit tests for inspector_turn_projection_service.py - Helper functions."""

from unittest.mock import MagicMock, patch
import pytest

from app.services.inspector.inspector_turn_projection_service import (
    _LAST_TURN_PLANNER_KEYS,
    _last_turn_from_bundle,
    _planner_fields_from_last_turn,
    _projectable_state,
    build_inspector_turn_projection,
)


class TestLastTurnFromBundle:
    """Tests for _last_turn_from_bundle function."""

    def test_last_turn_from_bundle_valid(self):
        """Test extracting last turn from valid bundle."""
        bundle = {
            "world_engine_diagnostics": {
                "diagnostics": [
                    {"turn_number": 1},
                    {"turn_number": 2, "trace_id": "trace-2"},
                ]
            }
        }
        result = _last_turn_from_bundle(bundle)
        assert result == {"turn_number": 2, "trace_id": "trace-2"}

    def test_last_turn_from_bundle_single_turn(self):
        """Test with single turn in diagnostics."""
        bundle = {
            "world_engine_diagnostics": {
                "diagnostics": [{"turn_number": 1}]
            }
        }
        result = _last_turn_from_bundle(bundle)
        assert result == {"turn_number": 1}

    def test_last_turn_from_bundle_no_diagnostics_dict(self):
        """Test when diagnostics key is missing."""
        bundle = {"world_engine_diagnostics": {}}
        result = _last_turn_from_bundle(bundle)
        assert result is None

    def test_last_turn_from_bundle_diagnostics_not_dict(self):
        """Test when world_engine_diagnostics is not a dict."""
        bundle = {"world_engine_diagnostics": None}
        result = _last_turn_from_bundle(bundle)
        assert result is None

    def test_last_turn_from_bundle_diagnostics_not_list(self):
        """Test when diagnostics is not a list."""
        bundle = {"world_engine_diagnostics": {"diagnostics": "not_a_list"}}
        result = _last_turn_from_bundle(bundle)
        assert result is None

    def test_last_turn_from_bundle_empty_diagnostics(self):
        """Test with empty diagnostics list."""
        bundle = {"world_engine_diagnostics": {"diagnostics": []}}
        result = _last_turn_from_bundle(bundle)
        assert result is None

    def test_last_turn_from_bundle_tail_not_dict(self):
        """Test when last item in diagnostics is not a dict."""
        bundle = {
            "world_engine_diagnostics": {
                "diagnostics": [
                    {"turn_number": 1},
                    "not_a_dict",
                ]
            }
        }
        result = _last_turn_from_bundle(bundle)
        assert result is None

    def test_last_turn_from_bundle_missing_world_engine_diagnostics(self):
        """Test when world_engine_diagnostics key is missing."""
        bundle = {}
        result = _last_turn_from_bundle(bundle)
        assert result is None


class TestPlannerFieldsFromLastTurn:
    """Tests for _planner_fields_from_last_turn function."""

    def test_planner_fields_all_present_at_top_level(self):
        """Test extracting all planner fields from top-level keys."""
        last_turn = {
            "semantic_move_record": {"move": "attack"},
            "social_state_record": {"allies": 2},
            "character_mind_records": {"mind": 1},
            "scene_plan_record": {"scene": "battle"},
            "interpreted_move": {"signal": "fight"},
            "turn_id": "turn-1",
            "turn_timestamp_iso": "2026-04-13T00:00:00Z",
        }
        result = _planner_fields_from_last_turn(last_turn)
        assert result["semantic_move_record"] == {"move": "attack"}
        assert result["social_state_record"] == {"allies": 2}
        assert result["turn_id"] == "turn-1"
        assert result["turn_timestamp_iso"] == "2026-04-13T00:00:00Z"

    def test_planner_fields_fallback_to_graph_planner_state(self):
        """Test fallback to graph.planner_state_projection when top-level missing."""
        last_turn = {
            "graph": {
                "planner_state_projection": {
                    "semantic_move_record": {"graph_move": "defend"},
                    "social_state_record": {"allies": 1},
                }
            },
            "turn_id": "turn-1",
        }
        result = _planner_fields_from_last_turn(last_turn)
        assert result["semantic_move_record"] == {"graph_move": "defend"}
        assert result["turn_id"] == "turn-1"

    def test_planner_fields_top_level_takes_precedence(self):
        """Test that top-level fields take precedence over graph fields."""
        last_turn = {
            "semantic_move_record": {"top": "level"},
            "graph": {
                "planner_state_projection": {
                    "semantic_move_record": {"graph": "level"},
                    "character_mind_records": {"from": "graph"},
                }
            },
        }
        result = _planner_fields_from_last_turn(last_turn)
        assert result["semantic_move_record"] == {"top": "level"}
        assert result["character_mind_records"] == {"from": "graph"}

    def test_planner_fields_interpreted_input_fallback(self):
        """Test interpreted_move falls back to interpreted_input."""
        last_turn = {
            "interpreted_input": {"signals": ["attack"]},
            "turn_id": "turn-1",
        }
        result = _planner_fields_from_last_turn(last_turn)
        assert result["interpreted_input"] == {"signals": ["attack"]}
        assert result["interpreted_move"] == {"signals": ["attack"]}
        assert result["turn_id"] == "turn-1"

    def test_planner_fields_interpreted_move_takes_precedence(self):
        """Test interpreted_move takes precedence over interpreted_input."""
        last_turn = {
            "interpreted_move": {"move": "direct"},
            "interpreted_input": {"signals": ["indirect"]},
        }
        result = _planner_fields_from_last_turn(last_turn)
        assert result["interpreted_input"] == {"signals": ["indirect"]}
        assert result["interpreted_move"] == {"move": "direct"}

    def test_planner_keys_include_interpreted_input(self) -> None:
        assert "interpreted_input" in _LAST_TURN_PLANNER_KEYS

    def test_planner_fields_empty_last_turn(self):
        """Test with empty last_turn dict."""
        result = _planner_fields_from_last_turn({})
        assert result == {}

    def test_planner_fields_graph_not_dict(self):
        """Test when graph is not a dict."""
        last_turn = {
            "semantic_move_record": {"move": "attack"},
            "graph": "not_a_dict",
        }
        result = _planner_fields_from_last_turn(last_turn)
        assert result["semantic_move_record"] == {"move": "attack"}

    def test_planner_fields_planner_state_projection_not_dict(self):
        """Test when planner_state_projection is not a dict."""
        last_turn = {
            "graph": {
                "planner_state_projection": "not_a_dict",
            },
        }
        result = _planner_fields_from_last_turn(last_turn)
        assert result == {}

    def test_planner_fields_none_values_skipped(self):
        """Test that None values are skipped."""
        last_turn = {
            "semantic_move_record": None,
            "social_state_record": {"allies": 2},
            "turn_id": "turn-1",
        }
        result = _planner_fields_from_last_turn(last_turn)
        assert "semantic_move_record" not in result
        assert result["social_state_record"] == {"allies": 2}
        assert result["turn_id"] == "turn-1"

    def test_planner_fields_interpreted_input_not_dict(self):
        """Test when interpreted_input is not a dict."""
        last_turn = {
            "interpreted_input": "not_a_dict",
        }
        result = _planner_fields_from_last_turn(last_turn)
        assert "interpreted_move" not in result


class TestProjectableState:
    """Tests for _projectable_state function."""

    def test_projectable_state_with_valid_bundle(self):
        """Test building projectable state with valid bundle."""
        bundle = {
            "module_id": "god_of_carnage",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid-1",
        }
        last_turn = {
            "turn_number": 2,
            "trace_id": "trace-2",
            "retrieval": {"status": "ok"},
            "model_route": {"generation": {"success": True}},
            "graph": {"nodes": ["node1"]},
            "visible_output_bundle": {"text": "output"},
        }
        state = _projectable_state(bundle=bundle, last_turn=last_turn)

        assert state["session_id"] == "we-sid-1"
        assert state["module_id"] == "god_of_carnage"
        assert state["current_scene_id"] == "scene-1"
        assert state["turn_number"] == 2
        assert state["trace_id"] == "trace-2"
        assert state["retrieval"] == {"status": "ok"}
        assert state["generation"] == {"success": True}

    def test_projectable_state_missing_model_route(self):
        """Test when model_route is missing."""
        bundle = {
            "module_id": "test",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid",
        }
        last_turn = {
            "turn_number": 1,
            "trace_id": "trace-1",
        }
        state = _projectable_state(bundle=bundle, last_turn=last_turn)

        assert state["routing"] == {}
        assert state["generation"] == {}

    def test_projectable_state_model_route_not_dict(self):
        """Test when model_route is not a dict."""
        bundle = {
            "module_id": "test",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid",
        }
        last_turn = {
            "turn_number": 1,
            "trace_id": "trace-1",
            "model_route": "not_a_dict",
        }
        state = _projectable_state(bundle=bundle, last_turn=last_turn)

        assert state["routing"] == {}
        assert state["generation"] == {}

    def test_projectable_state_generation_not_dict(self):
        """Test when generation in model_route is not a dict."""
        bundle = {
            "module_id": "test",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid",
        }
        last_turn = {
            "turn_number": 1,
            "trace_id": "trace-1",
            "model_route": {
                "generation": "not_a_dict",
                "routing_mode": "primary",
            },
        }
        state = _projectable_state(bundle=bundle, last_turn=last_turn)

        assert state["generation"] == {}
        assert state["routing"] == {"routing_mode": "primary"}

    def test_projectable_state_turn_number_not_int(self):
        """Test when turn_number is not an integer."""
        bundle = {
            "module_id": "test",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid",
        }
        last_turn = {
            "turn_number": "two",
            "trace_id": "trace-1",
        }
        state = _projectable_state(bundle=bundle, last_turn=last_turn)

        assert state["turn_number"] is None

    def test_projectable_state_retrieval_not_dict(self):
        """Test when retrieval is not a dict."""
        bundle = {
            "module_id": "test",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid",
        }
        last_turn = {
            "turn_number": 1,
            "trace_id": "trace-1",
            "retrieval": "not_a_dict",
        }
        state = _projectable_state(bundle=bundle, last_turn=last_turn)

        assert state["retrieval"] == {}

    def test_projectable_state_graph_not_dict(self):
        """Test when graph is not a dict."""
        bundle = {
            "module_id": "test",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid",
        }
        last_turn = {
            "turn_number": 1,
            "trace_id": "trace-1",
            "graph": "not_a_dict",
        }
        state = _projectable_state(bundle=bundle, last_turn=last_turn)

        assert state["graph_diagnostics"] == {}

    def test_projectable_state_validation_outcome_not_dict(self):
        """Test when validation_outcome is not a dict."""
        bundle = {
            "module_id": "test",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid",
        }
        last_turn = {
            "turn_number": 1,
            "trace_id": "trace-1",
            "validation_outcome": "not_a_dict",
        }
        state = _projectable_state(bundle=bundle, last_turn=last_turn)

        assert state["validation_outcome"] == {}

    def test_projectable_state_committed_result_not_dict(self):
        """Test when committed_result is not a dict."""
        bundle = {
            "module_id": "test",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid",
        }
        last_turn = {
            "turn_number": 1,
            "trace_id": "trace-1",
            "committed_result": ["item"],
        }
        state = _projectable_state(bundle=bundle, last_turn=last_turn)

        assert state["committed_result"] == {}

    def test_projectable_state_includes_planner_fields(self):
        """Test that planner fields are included in state."""
        bundle = {
            "module_id": "test",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid",
        }
        last_turn = {
            "turn_number": 1,
            "trace_id": "trace-1",
            "semantic_move_record": {"move": "attack"},
            "turn_id": "turn-1",
        }
        state = _projectable_state(bundle=bundle, last_turn=last_turn)

        assert state["semantic_move_record"] == {"move": "attack"}
        assert state["turn_id"] == "turn-1"


class TestBuildInspectorTurnProjection:
    """Tests for build_inspector_turn_projection function."""

    def test_build_inspector_turn_projection_session_not_found(self):
        """Test when session is not found."""
        with patch(
            "app.services.inspector.inspector_turn_projection_service.build_session_evidence_bundle"
        ) as mock_bundle:
            mock_bundle.return_value = {"error": "world_engine_story_session_not_found"}

            result = build_inspector_turn_projection(
                session_id="nonexistent",
                trace_id="trace-1"
            )

            assert result["error"] == "world_engine_story_session_not_found"

    def test_build_inspector_turn_projection_canonical_mode(self):
        """Test canonical mode (default)."""
        bundle = {
            "trace_id": "trace-1",
            "backend_session_id": "backend-1",
            "module_id": "god_of_carnage",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid-1",
            "world_engine_diagnostics": {
                "diagnostics": [
                    {
                        "turn_number": 1,
                        "trace_id": "trace-1",
                        "model_route": {},
                    }
                ]
            },
            "degraded_path_signals": [],
        }

        with patch(
            "app.services.inspector.inspector_turn_projection_service.build_session_evidence_bundle"
        ) as mock_bundle:
            with patch(
                "app.services.inspector.inspector_turn_projection_service.build_operator_canonical_turn_record"
            ) as mock_canonical:
                with patch(
                    "app.services.inspector.inspector_turn_projection_service.build_inspector_projection_sections"
                ) as mock_sections:
                    mock_bundle.return_value = bundle
                    mock_canonical.return_value = {"canonical": "record"}
                    mock_sections.return_value = {}

                    result = build_inspector_turn_projection(
                        session_id="backend-1",
                        trace_id="trace-1",
                        mode="canonical"
                    )

                    assert result["projection_status"] == "ok"
                    assert "raw_evidence" not in result
                    assert result["raw_evidence_refs"]["mode"] == "canonical"

    def test_build_inspector_turn_projection_raw_mode(self):
        """Test raw mode includes evidence."""
        bundle = {
            "trace_id": "trace-1",
            "backend_session_id": "backend-1",
            "module_id": "god_of_carnage",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid-1",
            "world_engine_diagnostics": {
                "diagnostics": [
                    {
                        "turn_number": 1,
                        "trace_id": "trace-1",
                        "model_route": {},
                    }
                ]
            },
            "world_engine_state": {"session_id": "we-sid-1"},
            "execution_truth": {"health": "ok"},
            "cross_layer_classifiers": {"mode": "primary"},
            "bridge_errors": [],
            "degraded_path_signals": [],
        }

        with patch(
            "app.services.inspector.inspector_turn_projection_service.build_session_evidence_bundle"
        ) as mock_bundle:
            with patch(
                "app.services.inspector.inspector_turn_projection_service.build_operator_canonical_turn_record"
            ) as mock_canonical:
                with patch(
                    "app.services.inspector.inspector_turn_projection_service.build_inspector_projection_sections"
                ) as mock_sections:
                    mock_bundle.return_value = bundle
                    mock_canonical.return_value = {"canonical": "record"}
                    mock_sections.return_value = {}

                    result = build_inspector_turn_projection(
                        session_id="backend-1",
                        trace_id="trace-1",
                        mode="raw"
                    )

                    assert result["projection_status"] == "ok"
                    assert "raw_evidence" in result
                    assert result["raw_evidence"]["world_engine_state"] == {"session_id": "we-sid-1"}

    def test_build_inspector_turn_projection_no_last_turn(self):
        """Test when no last turn is available."""
        bundle = {
            "trace_id": "trace-1",
            "backend_session_id": "backend-1",
            "module_id": "god_of_carnage",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid-1",
            "world_engine_diagnostics": {"diagnostics": []},
            "degraded_path_signals": [],
        }

        with patch(
            "app.services.inspector.inspector_turn_projection_service.build_session_evidence_bundle"
        ) as mock_bundle:
            with patch(
                "app.services.inspector.inspector_turn_projection_service.build_inspector_projection_sections"
            ) as mock_sections:
                mock_bundle.return_value = bundle
                mock_sections.return_value = {}

                result = build_inspector_turn_projection(
                    session_id="backend-1",
                    trace_id="trace-1"
                )

                assert result["projection_status"] == "partial"

    def test_build_inspector_turn_projection_missing_world_engine_session_id(self):
        """Test when world_engine_story_session_id is missing."""
        bundle = {
            "trace_id": "trace-1",
            "backend_session_id": "backend-1",
            "module_id": "god_of_carnage",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": None,
            "world_engine_diagnostics": {
                "diagnostics": [
                    {
                        "turn_number": 1,
                        "trace_id": "trace-1",
                        "model_route": {},
                    }
                ]
            },
            "degraded_path_signals": [],
        }

        with patch(
            "app.services.inspector.inspector_turn_projection_service.build_session_evidence_bundle"
        ) as mock_bundle:
            with patch(
                "app.services.inspector.inspector_turn_projection_service.build_inspector_projection_sections"
            ) as mock_sections:
                mock_bundle.return_value = bundle
                mock_sections.return_value = {}

                result = build_inspector_turn_projection(
                    session_id="backend-1",
                    trace_id="trace-1"
                )

                assert result["projection_status"] == "partial"

    def test_build_inspector_turn_projection_empty_world_engine_session_id(self):
        """Test when world_engine_story_session_id is empty string."""
        bundle = {
            "trace_id": "trace-1",
            "backend_session_id": "backend-1",
            "module_id": "god_of_carnage",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "",
            "world_engine_diagnostics": {
                "diagnostics": [
                    {
                        "turn_number": 1,
                        "trace_id": "trace-1",
                        "model_route": {},
                    }
                ]
            },
            "degraded_path_signals": [],
        }

        with patch(
            "app.services.inspector.inspector_turn_projection_service.build_session_evidence_bundle"
        ) as mock_bundle:
            with patch(
                "app.services.inspector.inspector_turn_projection_service.build_inspector_projection_sections"
            ) as mock_sections:
                mock_bundle.return_value = bundle
                mock_sections.return_value = {}

                result = build_inspector_turn_projection(
                    session_id="backend-1",
                    trace_id="trace-1"
                )

                assert result["projection_status"] == "partial"

    def test_build_inspector_turn_projection_includes_degraded_signals(self):
        """Test that degraded_path_signals are included as warnings."""
        bundle = {
            "trace_id": "trace-1",
            "backend_session_id": "backend-1",
            "module_id": "god_of_carnage",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid-1",
            "world_engine_diagnostics": {
                "diagnostics": [
                    {
                        "turn_number": 1,
                        "trace_id": "trace-1",
                        "model_route": {},
                    }
                ]
            },
            "degraded_path_signals": ["signal_1", "signal_2"],
        }

        with patch(
            "app.services.inspector.inspector_turn_projection_service.build_session_evidence_bundle"
        ) as mock_bundle:
            with patch(
                "app.services.inspector.inspector_turn_projection_service.build_inspector_projection_sections"
            ) as mock_sections:
                mock_bundle.return_value = bundle
                mock_sections.return_value = {}

                result = build_inspector_turn_projection(
                    session_id="backend-1",
                    trace_id="trace-1"
                )

                assert result["warnings"] == ["signal_1", "signal_2"]

    def test_build_inspector_turn_projection_no_degraded_signals(self):
        """Test when degraded_path_signals is None."""
        bundle = {
            "trace_id": "trace-1",
            "backend_session_id": "backend-1",
            "module_id": "god_of_carnage",
            "current_scene_id": "scene-1",
            "world_engine_story_session_id": "we-sid-1",
            "world_engine_diagnostics": {
                "diagnostics": [
                    {
                        "turn_number": 1,
                        "trace_id": "trace-1",
                        "model_route": {},
                    }
                ]
            },
            "degraded_path_signals": None,
        }

        with patch(
            "app.services.inspector.inspector_turn_projection_service.build_session_evidence_bundle"
        ) as mock_bundle:
            with patch(
                "app.services.inspector.inspector_turn_projection_service.build_inspector_projection_sections"
            ) as mock_sections:
                mock_bundle.return_value = bundle
                mock_sections.return_value = {}

                result = build_inspector_turn_projection(
                    session_id="backend-1",
                    trace_id="trace-1"
                )

                assert result["warnings"] == []
