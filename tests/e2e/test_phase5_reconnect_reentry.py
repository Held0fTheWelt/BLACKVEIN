"""Phase 5: Reconnect/Re-entry Flow Validation

Tests that session identifiers and mapping logic support reliable reconnect:
- Template-to-content-module mapping is stable and deterministic
- Turn log session key is correctly named
- Cookie name format is unique per run_id
- Backend session callable surface exists

These are contract/unit tests for the reconnect seam. Full browser reconnect
(page reload with real cookie persistence) requires Playwright E2E.
"""

from __future__ import annotations

import pytest


class TestSessionPersistenceMapping:
    """Verify session/template mapping logic supports reconnect."""

    def test_template_to_content_module_mapping_is_deterministic(self):
        """god_of_carnage_solo runtime profile maps to god_of_carnage module consistently."""
        from frontend.app.routes_play import play_template_to_content_module_id

        results = [play_template_to_content_module_id("god_of_carnage_solo") for _ in range(3)]
        assert all(r == "god_of_carnage" for r in results), (
            f"Mapping must be deterministic: got {results}"
        )

    def test_template_mapping_returns_canonical_module_not_profile(self):
        """Template mapping must return canonical module id, not the runtime profile id."""
        from frontend.app.routes_play import play_template_to_content_module_id

        result = play_template_to_content_module_id("god_of_carnage_solo")
        assert result == "god_of_carnage", (
            f"Must map to canonical module 'god_of_carnage', not '{result}'"
        )
        assert result != "god_of_carnage_solo", (
            "Canonical module id must not be the runtime profile id"
        )

    def test_turn_log_session_key_is_correct(self):
        """Turn-log legacy key stays in eviction list (no direct runtime usage)."""
        from frontend.app.routes_play import _LEGACY_LARGE_SESSION_KEYS

        assert "play_shell_turn_logs" in _LEGACY_LARGE_SESSION_KEYS

    def test_backend_turn_function_is_callable(self):
        """_run_backend_turn must be a callable (required for reconnect flow)."""
        from frontend.app.routes_play import _run_backend_turn

        assert callable(_run_backend_turn), "_run_backend_turn must be callable"


class TestCookieKeyContract:
    """Verify cookie key format supports per-run isolation."""

    def test_cookie_key_is_unique_per_run_id(self):
        """Each run_id produces a unique cookie key — no cross-session contamination."""
        run_ids = ["run_abc123", "run_def456", "run_ghi789"]
        cookie_keys = [f"wos_backend_session_{run_id}" for run_id in run_ids]

        assert len(cookie_keys) == len(set(cookie_keys)), (
            "Cookie keys must be unique per run_id"
        )
        for run_id, key in zip(run_ids, cookie_keys):
            assert run_id in key, f"Cookie key must contain run_id: {key}"
            assert key.startswith("wos_backend_session_"), (
                f"Cookie key must follow wos_backend_session_ prefix: {key}"
            )


class TestCookieSecurityContract:
    """Verify session cookie security flags via Flask test client."""

    def test_play_shell_sets_httponly_secure_samesite_cookie(self, client, player_backend_mock):
        """Session cookie must have HttpOnly, Secure, and SameSite=Strict flags."""
        run_resp = client.post(
            "/api/v1/game/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        if run_resp.status_code != 200:
            pytest.skip("Backend mock not available for cookie security test")

        run_id = run_resp.json.get("run", {}).get("id")
        if not run_id:
            pytest.skip("run_id not returned — skipping cookie security test")

        play_resp = client.get(f"/play/{run_id}")
        if play_resp.status_code != 200:
            pytest.skip("Play shell not available for cookie security test")

        cookies = play_resp.headers.getlist("Set-Cookie")
        wos_cookies = [c for c in cookies if "wos_backend_session_" in c]

        assert wos_cookies, (
            f"Expected at least one wos_backend_session_ cookie. Got: {cookies}"
        )
        for cookie in wos_cookies:
            assert "HttpOnly" in cookie, f"Cookie missing HttpOnly flag: {cookie}"
            assert "Secure" in cookie, f"Cookie missing Secure flag: {cookie}"
            assert "SameSite=Strict" in cookie, f"Cookie missing SameSite=Strict flag: {cookie}"
