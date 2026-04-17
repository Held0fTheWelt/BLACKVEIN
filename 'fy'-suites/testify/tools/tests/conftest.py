from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest


def build_minimal_testify_repo(tmp_path: Path) -> Path:
    root = tmp_path / 'repo'
    (root / "'fy'-suites" / 'testify' / 'reports').mkdir(parents=True, exist_ok=True)
    (root / '.github' / 'workflows').mkdir(parents=True, exist_ok=True)
    (root / 'tests').mkdir(parents=True, exist_ok=True)
    for rel in ('backend/pyproject.toml', 'frontend/pyproject.toml', 'administration-tool/pyproject.toml', 'world-engine/pyproject.toml', 'ai_stack/pyproject.toml', 'story_runtime_core/pyproject.toml'):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('[project]\nname="fixture"\n', encoding='utf-8')
    (root / 'pyproject.toml').write_text(
        '[project]\nname="fixture"\n\n[project.scripts]\n'
        'despag-check = "despaghettify.tools.hub_cli:main"\n'
        'wos-despag = "despaghettify.tools.hub_cli:main"\n'
        'postmanify = "postmanify.tools.cli:main"\n'
        'docify = "docify.tools.hub_cli:main"\n'
        'contractify = "contractify.tools.hub_cli:main"\n'
        'fy-platform = "fy_platform.tools.cli:main"\n'
        'dockerify = "dockerify.tools.hub_cli:main"\n'
        'testify = "testify.tools.hub_cli:main"\n'
        'documentify = "documentify.tools.hub_cli:main"\n\n'
        '[tool.setuptools.packages.find]\nwhere = ["\'fy\'-suites"]\n',
        encoding='utf-8',
    )
    (root / 'tests' / 'run_tests.py').write_text(
        'SUITE_DISPLAY_NAMES = {"backend": "Backend", "ai_stack": "AI"}\n'
        'SUITE_PYTEST_TARGETS = {"backend": ("backend", "tests"), "ai_stack": (".", "ai_stack/tests")}\n'
        'ALL_SUITE_SEQUENCE = ("backend", "ai_stack")\n',
        encoding='utf-8',
    )
    required = ['backend-tests.yml','admin-tests.yml','engine-tests.yml','ai-stack-tests.yml','quality-gate.yml','pre-deployment.yml','compose-smoke.yml']
    for name in required:
        (root / '.github' / 'workflows' / name).write_text('name: x\non:\n  push: {}\njobs:\n  test:\n    runs-on: ubuntu-latest\n', encoding='utf-8')
    return root


@pytest.fixture(autouse=True)
def _patch_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    fake = build_minimal_testify_repo(tmp_path)
    monkeypatch.setenv('TESTIFY_REPO_ROOT', str(fake))
    monkeypatch.setattr('testify.tools.repo_paths.repo_root', lambda start=None: fake)
    monkeypatch.setattr('testify.tools.hub_cli.repo_root', lambda start=None: fake)
    yield
