"""Phase 4: Operator/Player Surface Separation Tests

Validates that player-facing surfaces only show appropriate data,
while operator surfaces have access to diagnostics.
"""

import pytest


class TestPlayerSurfaceIsolation:
    """Verify player-visible surface only shows player-appropriate fields."""

    def test_runtime_view_excludes_diagnostic_fields(self):
        """Verify normalized rows exclude trace/session diagnostics."""
        from frontend.app.routes_play import (
            _normalize_story_entries_for_shell,
            _runtime_status_view_from_story_entries,
        )

        view = _normalize_story_entries_for_shell(
            [
                {
                    "trace_id": "trace_123",
                    "world_engine_story_session_id": "wes_456",
                    "role": "runtime",
                    "turn_number": 1,
                    "text": "You see a room.",
                    "spoken_lines": ["Hello."],
                    "committed_consequences": ["You feel calm."],
                    "validation_status": "approved",
                    "graph_error_count": 2,
                }
            ],
            shell_state_view={},
            diagnostics_deep=False,
        )[0]

        assert "turn_number" in view
        assert "text" in view
        assert "spoken_lines" in view
        assert "committed_consequences" in view

        # Player runtime status surface should exclude trace/session diagnostics.
        status_view = _runtime_status_view_from_story_entries([view], shell_state_view={})
        assert "trace_id" not in status_view
        assert "world_engine_story_session_id" not in status_view

    def test_player_cannot_see_validation_errors(self):
        """Verify runtime_status_view omits raw graph error counts."""
        from frontend.app.routes_play import (
            _normalize_story_entries_for_shell,
            _runtime_status_view_from_story_entries,
        )

        normalized = _normalize_story_entries_for_shell(
            [
                {
                    "role": "runtime",
                    "turn_number": 1,
                    "text": "Text",
                    "validation_status": "approved",
                    "graph_error_count": 2,
                }
            ],
            shell_state_view={},
            diagnostics_deep=False,
        )
        status_view = _runtime_status_view_from_story_entries(normalized, shell_state_view={})
        assert status_view.get("validation_status") == "approved"
        assert status_view.get("graph_error_count") is None

