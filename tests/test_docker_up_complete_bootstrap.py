"""
Integration tests for ADR-0030: docker-up.py Complete Bootstrap Implementation

Tests verify that docker-up.py:
1. Creates admin user on first run (idempotent)
2. Returns correct exit codes for all error scenarios
3. Does NOT silently fail on configured features (e.g., Langfuse)
4. Provides actionable error messages

These are INTEGRATION tests that actually start docker-compose and verify real behavior.
No mocks—real exit codes, real database state, real backend responses.

Run via: python tests/run_tests.py --suite docker-up
Or standalone: pytest tests/test_docker_up_complete_bootstrap.py -v
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKER_UP_SCRIPT = REPO_ROOT / "docker-up.py"
ENV_FILE = REPO_ROOT / ".env"
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def run_docker_up(args: list[str] = None) -> tuple[int, str, str]:
    """Run docker-up.py and capture exit code + stderr.

    Returns:
        (exit_code, stdout, stderr)
    """
    if args is None:
        args = ["up"]

    cmd = ["python", str(DOCKER_UP_SCRIPT)] + args
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def backend_is_healthy(timeout: int = 30) -> bool:
    """Check if backend /api/v1/health is responding."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = Request("http://localhost:8000/api/v1/health")
            with urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except URLError:
            time.sleep(0.5)
    return False


def get_bootstrap_status() -> dict:
    """Fetch /api/v1/bootstrap/public-status from backend."""
    try:
        req = Request("http://localhost:8000/api/v1/bootstrap/public-status")
        with urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Could not fetch bootstrap status: {e}")


class TestDockerUpBootstrapFirstRun:
    """Test first-run initialization (clean environment)."""

    @pytest.mark.skipif(
        not DOCKER_UP_SCRIPT.exists(),
        reason="docker-up.py not found"
    )
    def test_init_env_creates_secrets(self):
        """
        Test: python docker-up.py init-env creates .env with all required secrets.

        Acceptance: .env exists, contains SECRET_KEY, JWT_SECRET_KEY, etc.
        """
        # Clean environment
        if ENV_FILE.exists():
            ENV_FILE.unlink()

        # Run init-env
        exit_code, stdout, stderr = run_docker_up(["init-env"])

        # Verify
        assert exit_code == 0, f"init-env failed: {stderr}"
        assert ENV_FILE.exists(), ".env was not created"
        env_content = ENV_FILE.read_text()
        assert "SECRET_KEY=" in env_content
        assert "JWT_SECRET_KEY=" in env_content
        assert "PLAY_SERVICE_SHARED_SECRET=" in env_content

    @pytest.mark.skipif(
        not DOCKER_UP_SCRIPT.exists(),
        reason="docker-up.py not found"
    )
    @pytest.mark.integration
    @pytest.mark.slow  # ~2 min (compose build + startup)
    def test_first_run_creates_admin_user_exit_0(self):
        """
        Test: python docker-up.py up (first run) creates admin user, exits 0.

        Acceptance:
        - Exit code is 0
        - Admin user created (checked via backend)
        - No "error" in stderr
        """
        # Ensure .env exists
        if not ENV_FILE.exists():
            run_docker_up(["init-env"])

        # Clean containers for fresh start
        subprocess.run(
            ["docker", "compose", "down", "-v"],
            cwd=REPO_ROOT,
            capture_output=True
        )

        # Run docker-up.py up
        exit_code, stdout, stderr = run_docker_up(["up"])

        # Verify exit code
        assert exit_code == 0, f"docker-up.py up failed with exit {exit_code}: {stderr}"

        # Verify admin user was created (backend is healthy)
        assert backend_is_healthy(timeout=30), "Backend did not become healthy"
        status = get_bootstrap_status()
        assert status.get("ok"), f"Bootstrap status check failed: {status}"

        # Verify no "error" in stderr
        assert "ERROR" not in stderr, f"Unexpected error in stderr: {stderr}"


class TestDockerUpBootstrapIdempotency:
    """Test idempotency (running docker-up.py twice)."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_second_run_idempotent_exit_0(self):
        """
        Test: python docker-up.py up (second run) succeeds, no "user already exists" error.

        Setup: First run already passed.
        Acceptance:
        - Exit code is 0
        - No error about user existing
        - Admin login still works
        """
        # Assuming first-run test passed, admin user exists

        # Run docker-up.py up again
        exit_code, stdout, stderr = run_docker_up(["up"])

        # Verify exit code
        assert exit_code == 0, f"Second run failed with exit {exit_code}: {stderr}"

        # Verify no "error" in stderr (idempotent)
        assert "ERROR" not in stderr, f"Second run produced error: {stderr}"

        # Verify admin can still log in
        assert backend_is_healthy(timeout=10)
        try:
            req = Request(
                "http://localhost:8000/api/v1/auth/login",
                data=json.dumps({"username": "admin", "password": "Admin123"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                assert data.get("access_token"), f"Login failed: {data}"
        except Exception as e:
            pytest.fail(f"Admin login failed: {e}")


class TestDockerUpBootstrapErrorHandling:
    """Test error scenarios and exit codes."""

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Database manipulation requires unix shell"
    )
    @pytest.mark.integration
    @pytest.mark.slow
    def test_migration_failure_exit_2(self):
        """
        Test: If migrations incomplete (users table not found), exit code is 2.

        Setup: Break migrations by removing DB or corrupting schema.
        Acceptance: Exit code is 2, error message mentions "migrations" or "table"
        """
        # Ensure backend is running from prior test
        assert backend_is_healthy(timeout=10)

        # Break migrations: delete users table via docker exec
        subprocess.run(
            [
                "docker", "exec", "worldofshadows-backend-1",
                "sqlite3", "/app/instance/wos.db", "DROP TABLE IF EXISTS users;"
            ],
            cwd=REPO_ROOT,
            capture_output=True
        )

        # Run docker-up.py up
        exit_code, stdout, stderr = run_docker_up(["up"])

        # Verify exit code is 2 (migrations failed)
        assert exit_code == 2, f"Expected exit 2 for migration failure, got {exit_code}: {stderr}"

        # Verify error message mentions migrations or database
        assert "migration" in stderr.lower() or "database" in stderr.lower() or "table" in stderr.lower(), \
            f"Error message should mention migrations/database: {stderr}"

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Requires docker exec capability"
    )
    @pytest.mark.integration
    @pytest.mark.slow
    def test_langfuse_enabled_but_fails_exit_4(self):
        """
        Test: If LANGFUSE_ENABLED=true but initialization fails, exit code is 4 (NOT silent).

        Setup: Set LANGFUSE_ENABLED=true with invalid credentials.
        Acceptance: Exit code is 4, error message mentions "langfuse"
        """
        # Update .env to enable Langfuse with bad credentials
        env_lines = ENV_FILE.read_text().split("\n")
        # Add Langfuse settings
        langfuse_lines = [
            "LANGFUSE_ENABLED=true",
            "LANGFUSE_SECRET_KEY=invalid_key_12345",
            "LANGFUSE_PUBLIC_KEY=invalid_pk"
        ]
        env_content = "\n".join(env_lines + langfuse_lines)
        ENV_FILE.write_text(env_content)

        # Run docker-up.py up
        exit_code, stdout, stderr = run_docker_up(["up"])

        # Verify exit code is 4 (Langfuse failed, not silent)
        assert exit_code == 4, f"Expected exit 4 for Langfuse failure, got {exit_code}: {stderr}"

        # Verify error message mentions Langfuse
        assert "langfuse" in stderr.lower(), f"Error message should mention Langfuse: {stderr}"

        # Restore .env (remove Langfuse settings)
        subprocess.run(
            ["git", "checkout", "HEAD", ".env"],
            cwd=REPO_ROOT,
            capture_output=True
        )


class TestDockerUpBootstrapExitCodes:
    """Verify all exit codes are documented and distinct."""

    def test_exit_codes_documented(self):
        """
        Test: All exit codes (0-6) are documented in docker-up.py docstring.

        Acceptance: grep docker-up.py for exit code documentation
        """
        docker_up_content = DOCKER_UP_SCRIPT.read_text()

        # Verify exit codes are documented (format: "exit {code}", "Exit {code}", or "{code} =")
        for code in range(0, 7):
            patterns = [f"exit {code}", f"Exit {code}", f"{code} ="]
            found = any(pattern in docker_up_content for pattern in patterns)
            assert found, f"Exit code {code} not documented in docker-up.py"


# Markers for test organization
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
