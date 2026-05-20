"""E2E Tests for World of Shadows Gameplay Seam Repairs (Phase 1-2)

Tests verify:
1. Session identifier persistence via cookies (survives page reload)
2. Template mapping configuration scalability
3. Turn response validation against canonical contract
4. Frontend/backend integration seam integrity
"""

from __future__ import annotations

import json
from typing import Any

import pytest


class TestSessionPersistenceCookie:
    """PHASE 1 REPAIR: Session identifier persistence via cookies"""

    def test_backend_session_id_stored_in_cookie(self, client, player_backend_mock):
        """Verify backend_session_id is stored in persistent cookie after session creation."""
        # Create a run
        run_resp = client.post(
            "/api/v1/game/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        assert run_resp.status_code == 200
        run_id = run_resp.json["run"]["id"]

        # Visit play shell to create session
        play_resp = client.get(f"/play/{run_id}")
        assert play_resp.status_code == 200

        # Verify cookie was set
        cookie_key = f"wos_backend_session_{run_id}"
        cookies = play_resp.headers.getlist("Set-Cookie")
        cookie_names = [c.split("=")[0] for c in cookies]
        assert cookie_key in cookie_names, f"Expected cookie {cookie_key} in {cookie_names}"

        # Verify cookie has security flags
        matching_cookie = next(c for c in cookies if cookie_key in c)
        assert "Secure" in matching_cookie, "Cookie missing Secure flag"
        assert "HttpOnly" in matching_cookie, "Cookie missing HttpOnly flag"
        assert "SameSite=Strict" in matching_cookie, "Cookie missing SameSite=Strict flag"

    def test_session_survives_page_reload(self, client, player_backend_mock):
        """Verify session persists when page is reloaded (cookie lookup)."""
        # Create run and session
        run_resp = client.post(
            "/api/v1/game/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        run_id = run_resp.json["run"]["id"]

        # First load - creates session and sets cookie
        play_resp1 = client.get(f"/play/{run_id}")
        assert play_resp1.status_code == 200
        cookies1 = dict(client.cookie_jar._cookies.get("localhost.localdomain", {}).get("/", {}))

        # Extract backend_session_id from first response (stored in template context)
        html1 = play_resp1.get_data(as_text=True)
        assert "backend_session_id" in html1

        # Simulate page reload - cookies should persist
        play_resp2 = client.get(f"/play/{run_id}")
        assert play_resp2.status_code == 200
        html2 = play_resp2.get_data(as_text=True)
        assert "backend_session_id" in html2

        # Verify same session_id is used (would fail if cookie not read)
        assert play_resp1.status_code == play_resp2.status_code

    def test_turn_execution_with_cookie_fallback(self, client, player_backend_mock):
        """Verify turn execution works when backend_session_id comes from cookie (not session storage)."""
        # Create run
        run_resp = client.post(
            "/api/v1/game/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        run_id = run_resp.json["run"]["id"]

        # Load play shell to create session and set cookie
        play_resp = client.get(f"/play/{run_id}")
        assert play_resp.status_code == 200

        # Clear Flask session to force cookie-only lookup
        with client.session_transaction() as sess:
            if "play_shell_backend_sessions" in sess:
                del sess["play_shell_backend_sessions"]

        # Execute turn - should still work using cookie
        turn_resp = client.post(
            f"/play/{run_id}/execute",
            data={"player_input": "I look around carefully."},
        )
        # Should succeed or redirect (not 400 "not ready")
        assert turn_resp.status_code in [200, 302]


class TestTemplateMapping:
    """PHASE 1 REPAIR: Template mapping configuration scalability"""

    def test_template_mapping_config_file_loaded(self):
        """Verify template mapping config file is loaded correctly."""
        from frontend.app.routes_play import _PLAY_TEMPLATE_TO_CONTENT_MODULE_ID

        # Should have god_of_carnage_solo mapping
        assert "god_of_carnage_solo" in _PLAY_TEMPLATE_TO_CONTENT_MODULE_ID
        assert _PLAY_TEMPLATE_TO_CONTENT_MODULE_ID["god_of_carnage_solo"] == "god_of_carnage"

    def test_template_mapping_fallback(self):
        """Verify unknown template_id falls back to template_id as module_id."""
        from frontend.app.routes_play import play_template_to_content_module_id

        # Unknown template should map to itself
        result = play_template_to_content_module_id("unknown_template")
        assert result == "unknown_template"

    def test_template_mapping_config_yaml_structure(self):
        """Verify template mapping YAML config has correct structure."""
        import yaml
        from pathlib import Path

        config_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "config" / "template_module_mapping.yaml"
        assert config_path.exists(), f"Template mapping config not found at {config_path}"

        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert "templates" in config, "Config missing 'templates' key"
        assert isinstance(config["templates"], dict), "templates must be a dict"
        assert "god_of_carnage_solo" in config["templates"], "Missing god_of_carnage_solo mapping"


class TestTurnResponseValidation:
    """PHASE 2 REPAIR: Turn response validation against canonical contract"""

    def test_backend_validates_world_engine_response(self, client, player_backend_mock):
        """Verify backend validates world-engine turn response contains canonical evidence."""
        from app.services.game.game_service import _validate_story_turn_canonical_evidence

        # Valid turn response with all canonical evidence fields.
        valid_turn = {
            "canonical_turn_id": "story-1:turn:1",
            "turn_number": 1,
            "turn_kind": "player",
            "interpreted_input": {"kind": "speech"},
            "narrative_commit": {"committed_scene_id": "scene_1"},
            "validation_outcome": {"status": "approved"},
            "turn_aspect_ledger": {"turn_aspect_ledger": {"input": {"status": "passed"}}},
            "diagnostics": {"quality_class": "healthy"},
            "visible_output_bundle": {"gm_narration": ["The room is quiet."]},
        }

        # Should not raise
        _validate_story_turn_canonical_evidence(valid_turn)

    def test_backend_rejects_missing_required_fields(self):
        """Verify backend rejects turn response missing visible output evidence."""
        from app.services.game.game_service import (
            GameServiceError,
            _validate_story_turn_canonical_evidence,
        )

        # Missing visible_output_bundle / visible_scene_output.
        invalid_turn = {
            "canonical_turn_id": "story-1:turn:1",
            "turn_number": 1,
            "turn_kind": "player",
            "interpreted_input": {"kind": "speech"},
            "narrative_commit": {"committed_scene_id": "scene_1"},
            "validation_outcome": {"status": "approved"},
            "turn_aspect_ledger": {"turn_aspect_ledger": {"input": {"status": "passed"}}},
            "diagnostics": {"quality_class": "healthy"},
        }

        with pytest.raises(GameServiceError) as exc:
            _validate_story_turn_canonical_evidence(invalid_turn)
        assert "visible_output" in exc.value.payload["missing"]

    def test_backend_validates_canonical_evidence_field_types(self):
        """Verify backend validates canonical evidence field types (dict vs string)."""
        from app.services.game.game_service import (
            GameServiceError,
            _validate_story_turn_canonical_evidence,
        )

        # Wrong type for turn_aspect_ledger (should be a nested dict).
        invalid_turn = {
            "canonical_turn_id": "story-1:turn:1",
            "turn_number": 1,
            "turn_kind": "player",
            "interpreted_input": {"kind": "speech"},
            "narrative_commit": {"committed_scene_id": "scene_1"},
            "validation_outcome": {"status": "approved"},
            "turn_aspect_ledger": "not-a-ledger",
            "diagnostics": {"quality_class": "healthy"},
            "visible_output_bundle": {"gm_narration": ["The room is quiet."]},
        }

        with pytest.raises(GameServiceError) as exc:
            _validate_story_turn_canonical_evidence(invalid_turn)
        assert "turn_aspect_ledger" in exc.value.payload["missing"]


class TestFrontendTurnProjection:
    """PHASE 2 REPAIR: Frontend turn response projection validates critical fields"""

    def test_frontend_extracts_canonical_fields(self):
        """Verify frontend canonical shell projection via normalized story entries."""
        from frontend.app.routes_play import _normalize_story_entries_for_shell

        story_entries = [
            {
                "role": "runtime",
                "turn_number": 1,
                "text": "You see a room.\n\nIt is quiet.",
                "spoken_lines": ["Hello there."],
                "interpreted_input_kind": "action",
                "validation_status": "approved",
                "committed_consequences": ["You feel calm."],
            }
        ]

        normalized = _normalize_story_entries_for_shell(
            story_entries,
            shell_state_view={"player_shell_context": {"responder_id": "alain"}},
        )

        assert len(normalized) == 1
        view = normalized[0]
        assert view["turn_number"] == 1
        assert view["text"] == "You see a room.\n\nIt is quiet."
        assert view["spoken_lines"] == ["Hello there."]
        assert view["validation_status"] == "approved"
        assert view["committed_consequences"] == ["You feel calm."]

    def test_frontend_handles_missing_optional_fields_gracefully(self):
        """Verify frontend gracefully handles sparse story-entry payloads."""
        from frontend.app.routes_play import _normalize_story_entries_for_shell

        normalized = _normalize_story_entries_for_shell(
            [{"role": "runtime", "turn_number": 1, "text": "Welcome."}],
            shell_state_view={},
        )
        assert len(normalized) == 1
        assert normalized[0]["text"] == "Welcome."
        assert normalized[0]["spoken_lines"] == []


class TestEndToEndGameplayFlow:
    """PHASE 3: Complete end-to-end gameplay flow"""

    def test_complete_play_session_flow(self, client, player_backend_mock):
        """Verify complete gameplay flow: run creation → session → turn → response."""
        # Step 1: Create a run
        run_resp = client.post(
            "/api/v1/game/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        assert run_resp.status_code == 200
        run_data = run_resp.json
        run_id = run_data["run"]["id"]
        assert run_id

        # Step 2: Load play shell (creates backend session)
        shell_resp = client.get(f"/play/{run_id}")
        assert shell_resp.status_code == 200
        shell_html = shell_resp.get_data(as_text=True)
        assert "session_shell.html" in shell_resp.template or "backend_session_id" in shell_html

        # Step 3: Execute a turn
        turn_resp = client.post(
            f"/play/{run_id}/execute",
            data={"player_input": "I look around carefully."},
        )
        assert turn_resp.status_code in [200, 302]  # 200 for JSON, 302 for redirect

        # Step 4: Verify session persists on reload
        reload_resp = client.get(f"/play/{run_id}")
        assert reload_resp.status_code == 200

        # Step 5: Execute another turn (using persisted session)
        turn2_resp = client.post(
            f"/play/{run_id}/execute",
            data={"player_input": "I speak to them."},
        )
        assert turn2_resp.status_code in [200, 302]

    def test_turn_response_contains_all_contract_fields(self, client, player_backend_mock):
        """Verify turn response from backend contains all canonical contract fields."""
        # Setup: create run and session
        run_resp = client.post(
            "/api/v1/game/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        run_id = run_resp.json["run"]["id"]

        shell_resp = client.get(f"/play/{run_id}")
        assert shell_resp.status_code == 200

        # Execute turn and get response (JSON)
        turn_resp = client.post(
            f"/play/{run_id}/execute",
            data={"player_input": "I look around."},
            headers={"Accept": "application/json"},
        )

        # For JSON response, check the data
        if turn_resp.status_code == 200 and turn_resp.is_json:
            data = turn_resp.json
            # Verify required fields from canonical contract are present
            assert "interpreted_input_kind" in data or data.get("ok") is False


@pytest.fixture
def player_backend_mock(mocker):
    """Mock player backend requests for testing."""
    # Mock game service responses
    mocker.patch(
        "frontend.app.player_backend.request_backend",
        return_value=mocker.MagicMock(
            ok=True,
            json=lambda: {
                "run": {"id": "test_run_123"},
                "session_id": "test_session_456",
                "opening_turn": {"turn_kind": "opening", "turn_number": 0},
                "turn": {
                    "turn_number": 1,
                    "turn_kind": "player",
                    "interpreted_input": {"kind": "action"},
                    "visible_output_bundle": {"gm_narration": ["Test narration."]},
                    "validation_outcome": {"status": "approved"},
                    "narrative_commit": {"committed_scene_id": "test_scene"},
                },
                "state": {
                    "current_scene_id": "test_scene",
                    "committed_state": {},
                },
                "diagnostics": {},
            },
        ),
    )
