"""Fail CI when docs/api/openapi.yaml drifts from registered Flask /api/v1 routes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "generate_openapi_spec.py"


@pytest.mark.skipif(not SCRIPT.is_file(), reason="openapi generator script missing")
def test_openapi_yaml_matches_flask_routes():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=str(REPO_ROOT / "backend"),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        proc.stderr or proc.stdout or "openapi drift"
    ) + "\nRegenerate: python backend/scripts/generate_openapi_spec.py --write"


def test_backend_info_serves_openapi_and_explorer():
    from app import create_app
    from app.config import TestingConfig

    app = create_app(TestingConfig)
    with app.test_client() as client:
        spec = client.get("/backend/openapi.yaml")
        assert spec.status_code == 200
        assert b"openapi:" in spec.data
        page = client.get("/backend/api-explorer")
        assert page.status_code == 200
        assert b"redoc-container" in page.data
