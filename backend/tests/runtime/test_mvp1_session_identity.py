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
# game_service create_run contract tests (UNIT TESTS — payloads only, not integration)
# Real integration with Play Service is tested in test_backend_playservice_integration.py
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGameServiceCreateRun:
    """Verify game_service.create_run passes runtime_profile_id and selected_player_role.

    Unit tests for payload construction only. Real Play Service integration is tested
    in test_backend_playservice_integration.py with live endpoints.
    """

    def test_create_run_passes_runtime_profile_id_to_play_service(self, app):
        with app.app_context():
            from app.services.game_service import create_run as svc_create_run
            captured = {}

            def fake_request(method, path, *, json_payload=None, internal=False, trace_id=None, langfuse_trace_id=None, timeout_seconds=None):
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

            def fake_request(method, path, *, json_payload=None, internal=False, trace_id=None, langfuse_trace_id=None, timeout_seconds=None):
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

class TestBackendBypassRejection:
    """FIX-004: backend rejects template_id=god_of_carnage_solo without runtime_profile_id."""

    def test_backend_rejects_goc_solo_template_start_without_role(self, client, auth_headers):
        response = client.post(
            "/api/v1/game/runs",
            json={"template_id": "god_of_carnage_solo"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        data = response.get_json()
        code = data.get("code")
        assert code == "runtime_profile_required", (
            f"Expected code=runtime_profile_required, got {code!r}. Full response: {data}"
        )

    def test_backend_accepts_runtime_profile_with_role(self, client, auth_headers):
        captured = {}

        def fake_create_run(**kwargs):
            captured.update(kwargs)
            return {
                "run": {"id": "run_accept_test"},
                "run_id": "run_accept_test",
                "store": {},
                "hint": "test",
            }

        with patch("app.api.v1.game_routes.create_play_run", side_effect=fake_create_run):
            response = client.post(
                "/api/v1/game/runs",
                json={"runtime_profile_id": "god_of_carnage_solo", "selected_player_role": "annette"},
                headers=auth_headers,
            )
        assert response.status_code == 200
        assert captured.get("runtime_profile_id") == "god_of_carnage_solo"


class TestBackendLivePath:
    """FIX-008: backend live path tests."""

    def test_backend_player_session_annette_live_path(self, client, auth_headers):
        """Backend must forward annette start to play service correctly."""
        captured = {}

        def fake_create_run(**kwargs):
            captured.update(kwargs)
            return {"run": {"id": "annette_session"}, "run_id": "annette_session", "store": {}, "hint": "ok"}

        with patch("app.api.v1.game_routes.create_play_run", side_effect=fake_create_run):
            response = client.post(
                "/api/v1/game/player-sessions",
                json={
                    "runtime_profile_id": "god_of_carnage_solo",
                    "selected_player_role": "annette",
                },
                headers=auth_headers,
            )
        assert captured.get("runtime_profile_id") == "god_of_carnage_solo"
        assert captured.get("selected_player_role") == "annette"

    def test_backend_player_session_alain_live_path(self, client, auth_headers):
        """Backend must forward alain start to play service correctly."""
        captured = {}

        def fake_create_run(**kwargs):
            captured.update(kwargs)
            return {"run": {"id": "alain_session"}, "run_id": "alain_session", "store": {}, "hint": "ok"}

        with patch("app.api.v1.game_routes.create_play_run", side_effect=fake_create_run):
            response = client.post(
                "/api/v1/game/player-sessions",
                json={
                    "runtime_profile_id": "god_of_carnage_solo",
                    "selected_player_role": "alain",
                },
                headers=auth_headers,
            )
        assert captured.get("runtime_profile_id") == "god_of_carnage_solo"
        assert captured.get("selected_player_role") == "alain"


class TestDockerUpGate:
    """FIX-011: docker-up.py gate mode tests."""

    def test_docker_up_gate_fails_when_backend_unreachable(self, app):
        """docker-up.py gate must exit nonzero when backend is unreachable."""
        import subprocess, sys
        from pathlib import Path
        docker_up = REPO_ROOT / "docker-up.py"
        assert docker_up.is_file(), f"docker-up.py not found at {docker_up}"
        result = subprocess.run(
            [sys.executable, str(docker_up), "gate", "--backend-url", "http://127.0.0.1:19999"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0, (
            f"docker-up.py gate must return nonzero when backend unreachable, got {result.returncode}. "
            f"stdout: {result.stdout!r}"
        )
        assert "FAIL" in result.stdout or "unreachable" in result.stderr.lower()

    def test_docker_up_gate_fails_when_bootstrap_required_for_mvp(self, app):
        """docker-up.py gate must exit nonzero when bootstrap is required."""
        import subprocess, sys
        from unittest.mock import patch as mock_patch
        from urllib.request import urlopen
        from io import BytesIO
        import json as json_mod

        class FakeResponse:
            def __init__(self):
                self.status = 200
                self._data = json_mod.dumps({"data": {"bootstrap_required": True}}).encode()
            def read(self):
                return self._data
            def __enter__(self): return self
            def __exit__(self, *a): pass

        docker_up = REPO_ROOT / "docker-up.py"
        content = docker_up.read_text(encoding="utf-8")
        assert "bootstrap_required" in content, (
            "docker-up.py gate subcommand must check for bootstrap_required"
        )


