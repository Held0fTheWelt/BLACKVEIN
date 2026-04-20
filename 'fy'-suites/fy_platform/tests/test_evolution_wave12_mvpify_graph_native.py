"""Tests for evolution wave12 mvpify graph native.

"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from fy_platform.ai.workspace import workspace_root
from fy_platform.tools.cli import main


def _workspace() -> Path:
    """Workspace the requested operation.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return workspace_root(Path(__file__))


def _build_import_zip(tmp_path: Path) -> Path:
    """Build import zip.

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
    src = tmp_path / 'bundle'
    (src / 'docs' / 'ADR').mkdir(parents=True)
    (src / 'docs' / 'platform').mkdir(parents=True)
    (src / "'fy'-suites" / 'contractify').mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'README.md').write_text('# Imported MVP\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'docs' / 'ADR' / 'ADR-0001.md').write_text('# ADR 1\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'docs' / 'platform' / 'MVP.md').write_text('# MVP\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / "'fy'-suites" / 'contractify' / 'README.md').write_text('# contractify\n', encoding='utf-8')
    z = tmp_path / 'import.zip'
    # Enter a managed resource scope for this phase and rely on the context manager to
    # clean up when _build_import_zip leaves it.
    with zipfile.ZipFile(z, 'w') as zf:
        # Process path one item at a time so _build_import_zip applies the same rule
        # across the full collection.
        for path in src.rglob('*'):
            # Branch on path.is_file() so _build_import_zip only continues along the
            # matching state path.
            if path.is_file():
                zf.write(path, path.relative_to(src))
    return z


def test_import_surface_emits_mvpify_canonical_graph(tmp_path: Path, capsys) -> None:
    """Verify that import surface emits mvpify canonical graph works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace()
    bundle = _build_import_zip(tmp_path)
    assert main(['import', '--mode', 'mvp', '--project-root', str(workspace), '--bundle', str(bundle)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['canonical_graph']['unit_count'] >= 2
    export_dir = workspace / payload['canonical_graph']['export_dir']
    manifest = json.loads((export_dir / 'import_manifest.json').read_text(encoding='utf-8'))
    assert manifest['import_id']


def test_documentify_reads_mvpify_graph_input(tmp_path: Path, capsys) -> None:
    """Verify that documentify reads mvpify graph input works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace()
    bundle = _build_import_zip(tmp_path)
    assert main(['import', '--mode', 'mvp', '--project-root', str(workspace), '--bundle', str(bundle)]) == 0
    _ = capsys.readouterr().out
    assert main(['analyze', '--mode', 'docs', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    docs = json.loads(capsys.readouterr().out)
    assert docs['graph_inputs']['mvpify']['available'] is True
    generated_dir = Path(docs['generated_dir'])
    ops = (generated_dir / 'status' / 'OPERATIONS_AND_RISK_SUMMARY.md').read_text(encoding='utf-8')
    assert 'latest_import_id' in ops
