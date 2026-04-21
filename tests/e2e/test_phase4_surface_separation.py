"""Phase 4: Operator/Player Surface Separation Tests

Validates that player-facing surfaces only show appropriate data,
while operator surfaces have access to diagnostics.
"""

import pytest


class TestPlayerSurfaceIsolation:
    """Verify player-visible surface only shows player-appropriate fields."""

    def test_runtime_view_excludes_diagnostic_fields(self):
        """Verify runtime_view excludes all diagnostic/operator fields."""
        from frontend.app.routes_play import _build_play_shell_runtime_view

        # Complete backend response with diagnostic fields
        payload = {
            "trace_id": "trace_123",
            "world_engine_story_session_id": "wes_456",
            "turn": {
                "turn_number": 1,
                "turn_kind": "player",
                "raw_input": "I look around.",
                "interpreted_input": {"kind": "action"},
                "visible_output_bundle": {
                    "gm_narration": ["You see a room."],
                    "spoken_lines": ["Hello."],
                },
                "validation_outcome": {"status": "approved"},
                "narrative_commit": {
                    "committed_scene_id": "scene_1",
                    "committed_consequences": ["You feel calm."],
                },
                "graph": {"errors": []},
            },
            "state": {
                "committed_state": {"current_scene_id": "scene_1"},
                "current_scene_id": "scene_1",
            },
        }

        view = _build_play_shell_runtime_view(payload)

        # Fields that SHOULD be in player view
        assert "turn_number" in view
        assert "player_line" in view
        assert "narration_text" in view
        assert "spoken_lines" in view
        assert "committed_consequences" in view

        # Operator/diagnostic fields should NOT be in player view
        assert "trace_id" not in view
        assert "world_engine_story_session_id" not in view
        assert "validation_status" not in view
        assert "graph_error_count" not in view
        assert "current_scene_id" not in view
        assert "committed_scene_id" not in view

    def test_player_cannot_see_validation_errors(self):
        """Verify validation status and errors hidden from players."""
        from frontend.app.routes_play import _build_play_shell_runtime_view

        payload = {
            "turn": {
                "turn_number": 1,
                "interpreted_input": {"kind": "action"},
                "visible_output_bundle": {"gm_narration": ["Text"]},
                "validation_outcome": {"status": "approved", "reason": "passed"},
                "narrative_commit": {},
                "graph": {"errors": ["error1", "error2"]},
            },
            "state": {"committed_state": {}},
        }

        view = _build_play_shell_runtime_view(payload)

        # Validation and error details should be hidden
        assert view.get("validation_status") is None
        assert view.get("graph_error_count") is None

