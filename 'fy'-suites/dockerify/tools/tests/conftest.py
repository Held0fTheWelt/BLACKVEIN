from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest


def build_minimal_dockerify_repo(tmp_path: Path) -> Path:
    root = tmp_path / 'repo'
    (root / "'fy'-suites" / 'dockerify' / 'reports').mkdir(parents=True, exist_ok=True)
    (root / 'backend' / 'migrations').mkdir(parents=True, exist_ok=True)
    (root / 'database' / 'tests').mkdir(parents=True, exist_ok=True)
    (root / 'tests' / 'smoke').mkdir(parents=True, exist_ok=True)
    (root / 'pyproject.toml').write_text('[project]\nname="fixture"\n', encoding='utf-8')
    (root / 'docker-compose.yml').write_text(
        'services:\n'
        '  backend:\n'
        '    depends_on:\n'
        '      play-service:\n'
        '        condition: service_healthy\n'
        '  frontend: {}\n'
        '  administration-tool: {}\n'
        '  play-service:\n'
        '    healthcheck:\n'
        '      test: ["CMD", "true"]\n',
        encoding='utf-8',
    )
    (root / 'docker-up.py').write_text('init-env ensure-env up build restart stop down reset health .env', encoding='utf-8')
    (root / '.env.example').write_text('SECRET_KEY=\n', encoding='utf-8')
    for rel in ('backend/Dockerfile', 'world-engine/Dockerfile', 'frontend/Dockerfile', 'administration-tool/Dockerfile'):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('FROM scratch\n', encoding='utf-8')
    (root / 'backend' / 'docker-entrypoint.sh').write_text('flask db upgrade\n', encoding='utf-8')
    (root / 'database' / 'tests' / 'test_database_migrations_and_files.py').write_text('def test_ok():\n    assert True\n', encoding='utf-8')
    (root / 'database' / 'tests' / 'test_database_upgrades.py').write_text('def test_ok():\n    assert True\n', encoding='utf-8')
    for rel in ('test_backend_startup.py', 'test_admin_startup.py', 'test_engine_startup.py'):
        (root / 'tests' / 'smoke' / rel).write_text('def test_ok():\n    assert True\n', encoding='utf-8')
    return root


@pytest.fixture(autouse=True)
def _patch_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    fake = build_minimal_dockerify_repo(tmp_path)
    monkeypatch.setenv('DOCKERIFY_REPO_ROOT', str(fake))
    monkeypatch.setattr('dockerify.tools.repo_paths.repo_root', lambda start=None: fake)
    monkeypatch.setattr('dockerify.tools.hub_cli.repo_root', lambda start=None: fake)
    yield
