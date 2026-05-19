"""Keep generated OpenAPI YAML aligned with registered Flask /api/v1 routes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "generate_openapi_spec.py"


@pytest.mark.skipif(not SCRIPT.is_file(), reason="openapi generator script missing")
def test_openapi_yaml_matches_flask_routes():
    write_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--write"],
        cwd=str(REPO_ROOT / "backend"),
        capture_output=True,
        text=True,
    )
    assert write_proc.returncode == 0, (
        write_proc.stderr or write_proc.stdout or "openapi generation failed"
    ) + "\nRegenerate: python backend/scripts/generate_openapi_spec.py --write"

    check_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=str(REPO_ROOT / "backend"),
        capture_output=True,
        text=True,
    )
    assert check_proc.returncode == 0, (
        check_proc.stderr or check_proc.stdout or "openapi drift"
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
        assert b"api-explorer-app" in page.data
        catalog = client.get("/backend/api-explorer/catalog.json")
        assert catalog.status_code == 200
        assert catalog.get_json()["stats"]["endpoints"] > 0
