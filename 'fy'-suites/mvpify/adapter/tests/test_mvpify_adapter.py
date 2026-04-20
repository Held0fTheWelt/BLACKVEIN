"""Tests for mvpify adapter.

"""
from __future__ import annotations

import zipfile
from pathlib import Path

from fy_platform.tests.fixtures_autark import create_target_repo
from mvpify.adapter.service import MVPifyAdapter
from mvpify.tools.hub_cli import run


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
    (src / 'bundle' / 'docs' / 'ADR').mkdir(parents=True)
    (src / 'bundle' / 'docs' / 'platform').mkdir(parents=True)
    (src / 'bundle' / 'contractify' / 'reports').mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'bundle' / 'README.md').write_text('# Imported MVP\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'bundle' / 'docs' / 'ADR' / 'ADR-0001.md').write_text('# ADR 1\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'bundle' / 'docs' / 'platform' / 'MVP.md').write_text('# MVP\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'bundle' / 'contractify' / 'reports' / 'contract_audit.json').write_text('{"ok": true}\n', encoding='utf-8')
    z = tmp_path / 'bundle.zip'
    # Enter a managed resource scope for this phase and rely on the context manager to
    # clean up when _build_mvp_zip leaves it.
    with zipfile.ZipFile(z, 'w') as zf:
        # Process path one item at a time so _build_mvp_zip applies the same rule across
        # the full collection.
        for path in src.rglob('*'):
            # Branch on path.is_file() so _build_mvp_zip only continues along the
            # matching state path.
            if path.is_file():
                zf.write(path, path.relative_to(src))
    return z


def _prepare_workspace(tmp_path: Path) -> None:
    """Prepare workspace.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'fy_governance_enforcement.yaml').write_text('mode: test\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'README.md').write_text('# test\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'pyproject.toml').write_text('[project]\nname="x"\nversion="0"\n', encoding='utf-8')
    for req in ['requirements.txt', 'requirements-dev.txt', 'requirements-test.txt']:
        (tmp_path / req).write_text('\n', encoding='utf-8')
    (tmp_path / 'mvpify' / 'adapter').mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'mvpify' / 'adapter' / 'service.py').write_text('', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'mvpify' / 'adapter' / 'cli.py').write_text('', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'mvpify' / 'README.md').write_text('# mvpify\n', encoding='utf-8')
    (tmp_path / 'mvpify' / 'reports').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'mvpify' / 'state').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'mvpify' / 'tools').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'mvpify' / 'templates').mkdir(parents=True, exist_ok=True)


def test_mvpify_audit_and_mirror_docs(tmp_path, monkeypatch):
    """Verify that mvpify audit and mirror docs works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    create_target_repo(tmp_path)
    _prepare_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    z = _build_mvp_zip(tmp_path)
    adapter = MVPifyAdapter(tmp_path)
    result = adapter.audit(str(tmp_path))
    assert result['ok'] is True

    payload = run(tmp_path, mvp_zip=str(z))
    inventory = payload['import_inventory']
    assert inventory['mirrored_docs_root'].startswith('docs/MVPs/imports/')
    mirrored_root = tmp_path / inventory['mirrored_docs_root']
    assert (mirrored_root / 'ADR' / 'ADR-0001.md').exists()
    assert (mirrored_root / 'mvpify_reference_manifest.json').exists()
