import json
import shutil

from documentify.tools.document_builder import generate_documentation
from documentify.tools.hub_cli import main
from documentify.tools.repo_paths import repo_root


def test_generate_documentation_materializes_expected_views() -> None:
    root = repo_root()
    out_dir = root / "'fy'-suites" / 'documentify' / 'generated'
    summary = generate_documentation(root, out_dir)
    assert summary['generated_count'] >= 7
    assert (out_dir / 'simple' / 'PLATFORM_OVERVIEW.md').is_file()
    assert (out_dir / 'roles' / 'developer' / 'README.md').is_file()


def test_cli_writes_reports() -> None:
    root = repo_root()
    out = root / "'fy'-suites" / 'documentify' / 'reports' / '_pytest_documentify_audit.json'
    md = root / "'fy'-suites" / 'documentify' / 'reports' / '_pytest_documentify_audit.md'
    gen = root / "'fy'-suites" / 'documentify' / '_pytest_generated'
    try:
        code = main(['generate', '--out-dir', gen.relative_to(root).as_posix(), '--out', out.relative_to(root).as_posix(), '--md-out', md.relative_to(root).as_posix(), '--quiet'])
        assert code == 0
        data = json.loads(out.read_text(encoding='utf-8'))
        assert data['suite'] == 'documentify'
        assert md.is_file()
    finally:
        if out.is_file():
            out.unlink()
        if md.is_file():
            md.unlink()
        if gen.exists():
            shutil.rmtree(gen)
