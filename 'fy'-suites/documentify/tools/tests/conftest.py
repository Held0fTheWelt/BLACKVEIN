from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest


def build_minimal_documentify_repo(tmp_path: Path) -> Path:
    root = tmp_path / 'repo'
    (root / "'fy'-suites" / 'documentify' / 'reports').mkdir(parents=True, exist_ok=True)
    (root / '.github' / 'workflows').mkdir(parents=True, exist_ok=True)
    (root / 'docs' / 'start-here').mkdir(parents=True, exist_ok=True)
    (root / 'docs' / 'technical').mkdir(parents=True, exist_ok=True)
    (root / 'docs' / 'testing').mkdir(parents=True, exist_ok=True)
    (root / 'docs' / 'operations').mkdir(parents=True, exist_ok=True)
    for svc in ('frontend', 'administration-tool', 'backend', 'world-engine', 'ai_stack', 'story_runtime_core', 'writers-room'):
        (root / svc).mkdir(parents=True, exist_ok=True)
    (root / 'pyproject.toml').write_text('[project]\nname="fixture"\n', encoding='utf-8')
    (root / 'README.md').write_text('# Fixture\n', encoding='utf-8')
    (root / 'docs' / 'start-here' / 'README.md').write_text('# Start\n', encoding='utf-8')
    (root / 'docs' / 'technical' / 'README.md').write_text('# Technical\n', encoding='utf-8')
    (root / 'docs' / 'testing' / 'README.md').write_text('# Testing\n', encoding='utf-8')
    (root / 'docs' / 'operations' / 'RUNBOOK.md').write_text('# Runbook\n', encoding='utf-8')
    (root / '.github' / 'workflows' / 'backend-tests.yml').write_text('name: x\n', encoding='utf-8')
    (root / 'docker-up.py').write_text('print()\n', encoding='utf-8')
    (root / 'docker-compose.yml').write_text('services: {}\n', encoding='utf-8')
    (root / 'tests').mkdir(parents=True, exist_ok=True)
    (root / 'tests' / 'TESTING.md').write_text('# Testing\n', encoding='utf-8')
    (root / 'tests' / 'run_tests.py').write_text('print()\n', encoding='utf-8')
    return root


@pytest.fixture(autouse=True)
def _patch_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    fake = build_minimal_documentify_repo(tmp_path)
    monkeypatch.setenv('DOCUMENTIFY_REPO_ROOT', str(fake))
    monkeypatch.setattr('documentify.tools.repo_paths.repo_root', lambda start=None: fake)
    monkeypatch.setattr('documentify.tools.hub_cli.repo_root', lambda start=None: fake)
    yield
