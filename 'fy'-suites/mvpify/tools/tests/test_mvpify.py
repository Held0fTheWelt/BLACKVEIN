"""Tests for mvpify.

"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from mvpify.tools.hub_cli import run
from mvpify.tools.importer import inspect_source, materialize_import
from mvpify.tools.planner import build_plan


def _build_repo(tmp_path: Path) -> Path:
    """Build repo.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    (tmp_path / 'mvpify' / 'reports').mkdir(parents=True)
    (tmp_path / 'mvpify' / 'state').mkdir(parents=True)
    (tmp_path / 'docs' / 'MVPs' / 'imports').mkdir(parents=True, exist_ok=True)
    return tmp_path


def _build_mvp_zip(tmp_path: Path) -> Path:
    """Build mvp zip.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    src = tmp_path / 'src'
    (src / 'base' / "'fy'-suites" / 'contractify').mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'base' / "'fy'-suites" / 'contractify' / 'README.md').write_text('# contractify', encoding='utf-8')
    (src / 'base' / 'docs' / 'ADR').mkdir(parents=True)
    (src / 'base' / 'docs' / 'platform').mkdir(parents=True)
    (src / 'base' / 'tests').mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'base' / 'README.md').write_text('hello', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'base' / 'docker-compose.yml').write_text('services: {}', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'base' / 'docker-up.py').write_text('print(1)', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'base' / 'tests' / 'run_tests.py').write_text('print(1)', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'base' / 'docs' / 'ADR' / 'adr-0001.md').write_text('# ADR', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'base' / 'docs' / 'platform' / 'MVP.md').write_text('# MVP', encoding='utf-8')
    z = tmp_path / 'sample.zip'
    with zipfile.ZipFile(z, 'w') as zf:
        for path in src.rglob('*'):
            if path.is_file():
                zf.write(path, path.relative_to(src))
    return z


def test_importer_scans_zip(tmp_path: Path) -> None:
    """Verify that importer scans zip works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    z = _build_mvp_zip(tmp_path)
    payload = inspect_source(mvp_zip=str(z))
    assert payload['source_mode'] == 'zip'
    assert payload['artifact_count'] >= 5
    suites = {item['name']: item for item in payload['suite_signals']}
    assert suites['contractify']['present'] is True


def test_materialize_import_mirrors_docs(tmp_path: Path) -> None:
    """Verify that materialize import mirrors docs works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    repo = _build_repo(tmp_path / 'repo')
    z = _build_mvp_zip(tmp_path)
    payload = materialize_import(repo_root=repo, mvp_zip=str(z))
    mirrored = repo / payload['mirrored_docs_root']
    assert mirrored.exists()
    assert (mirrored / 'ADR' / 'adr-0001.md').exists()
    assert (mirrored / 'mvpify_reference_manifest.json').exists()


def test_planner_includes_governance_and_verification(tmp_path: Path) -> None:
    """Verify that planner includes governance and verification works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    z = _build_mvp_zip(tmp_path)
    payload = inspect_source(mvp_zip=str(z))
    plan = build_plan(payload, str(tmp_path))
    suites = [item['suite'] for item in plan['steps']]
    assert 'mvpify' in suites
    assert 'contractify' in suites
    assert 'testify' in suites
    assert plan['highest_value_next_step']['suite'] in {'contractify', 'mvpify'}


def test_full_run_writes_reports(tmp_path: Path) -> None:
    """Verify that full run writes reports works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    repo_root = _build_repo(tmp_path / 'repo')
    z = _build_mvp_zip(tmp_path)
    result = run(repo_root, mvp_zip=str(z))
    reports = repo_root / 'mvpify' / 'reports'
    assert (reports / 'mvpify_import_inventory.json').exists()
    assert (reports / 'mvpify_orchestration_plan.json').exists()
    assert (reports / 'mvpify_implementation_task.md').exists()
    payload = json.loads((reports / 'mvpify_orchestration_plan.json').read_text(encoding='utf-8'))
    assert payload['ok'] is True
