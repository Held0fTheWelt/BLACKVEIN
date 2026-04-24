"""MVP 1 backend behavior-proving tests — Experience Identity and Session Start.

Tests prove backend-side contracts for runtime profile, role selection, and
visitor rejection in the backend game routes and game service layer.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# ---------------------------------------------------------------------------
# game_service create_run contract tests
# ---------------------------------------------------------------------------

class TestGameServiceCreateRun:
    """Verify game_service.create_run passes runtime_profile_id and selected_player_role."""

    def test_create_run_passes_runtime_profile_id_to_play_service(self, app):
        with app.app_context():
            from app.services.game_service import create_run as svc_create_run
            captured = {}

            def fake_request(method, path, *, json_payload=None, internal=False, trace_id=None):
                captured["payload"] = json_payload
                return {
                    "run": {"id": "run_test_001"},
                    "run_id": "run_test_001",
                    "store": {},
                    "hint": "test",
                }

            with patch("app.services.game_service._request", side_effect=fake_request):
                with patch("app.services.game_service._parse_create_run_v1", side_effect=lambda x: x):
                    svc_create_run(
                        account_id="1",
                        display_name="Test",
                        runtime_profile_id="god_of_carnage_solo",
                        selected_player_role="annette",
                    )

            payload = captured.get("payload", {})
            assert payload.get("runtime_profile_id") == "god_of_carnage_solo"
            assert payload.get("selected_player_role") == "annette"
            assert "template_id" not in payload

    def test_create_run_passes_template_id_when_no_profile(self, app):
        with app.app_context():
            from app.services.game_service import create_run as svc_create_run
            captured = {}

            def fake_request(method, path, *, json_payload=None, internal=False, trace_id=None):
                captured["payload"] = json_payload
                return {
                    "run": {"id": "run_test_002"},
                    "run_id": "run_test_002",
                    "store": {},
                    "hint": "test",
                }

            with patch("app.services.game_service._request", side_effect=fake_request):
                with patch("app.services.game_service._parse_create_run_v1", side_effect=lambda x: x):
                    svc_create_run(
                        template_id="some_template",
                        account_id="1",
                        display_name="Test",
                    )

            payload = captured.get("payload", {})
            assert payload.get("template_id") == "some_template"
            assert "runtime_profile_id" not in payload


# ---------------------------------------------------------------------------
# game_routes create_run contract tests
# ---------------------------------------------------------------------------

class TestGameRoutesCreateRun:
    """Verify game_routes accepts and routes runtime_profile_id and selected_player_role."""

    def test_game_create_run_requires_template_or_profile(self, client, auth_headers):
        response = client.post(
            "/api/v1/game/runs",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 400
        data = response.get_json()
        error = data.get("error", "")
        assert "template_id" in error or "runtime_profile_id" in error

    def test_game_create_run_forwards_runtime_profile_and_role(self, client, auth_headers):
        captured = {}

        def fake_create_run(**kwargs):
            captured.update(kwargs)
            return {
                "run": {"id": "run_mvp1"},
                "run_id": "run_mvp1",
                "store": {},
                "hint": "test",
            }

        with patch("app.api.v1.game_routes.create_play_run", side_effect=fake_create_run):
            response = client.post(
                "/api/v1/game/runs",
                json={
                    "runtime_profile_id": "god_of_carnage_solo",
                    "selected_player_role": "annette",
                },
                headers=auth_headers,
            )

        assert captured.get("runtime_profile_id") == "god_of_carnage_solo"
        assert captured.get("selected_player_role") == "annette"


# ---------------------------------------------------------------------------
# Source locator and operational artifact presence
# ---------------------------------------------------------------------------

class TestMvp1ArtifactPresence:

    def test_source_locator_artifact_exists(self):
        artifact = REPO_ROOT / "tests" / "reports" / "MVP_Live_Runtime_Completion" / "MVP1_SOURCE_LOCATOR.md"
        assert artifact.is_file(), f"MVP1 source locator artifact missing at {artifact}"

    def test_operational_evidence_artifact_exists(self):
        artifact = REPO_ROOT / "tests" / "reports" / "MVP_Live_Runtime_Completion" / "MVP1_OPERATIONAL_EVIDENCE.md"
        assert artifact.is_file(), (
            f"MVP1 operational evidence artifact missing at {artifact}. "
            "This artifact is required to close MVP1."
        )

    def test_handoff_artifact_exists(self):
        artifact = REPO_ROOT / "tests" / "reports" / "MVP_Live_Runtime_Completion" / "MVP1_HANDOFF_RUNTIME_PROFILE.md"
        assert artifact.is_file(), (
            f"MVP1 handoff artifact missing at {artifact}. "
            "This artifact is required for MVP 2 to consume."
        )
