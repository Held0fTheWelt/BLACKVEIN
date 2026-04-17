from fy_platform.tests.fixtures_autark import create_target_repo
from docify.adapter.service import DocifyAdapter


def test_docify_adapter_finds_missing_docstrings(tmp_path, monkeypatch):
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = DocifyAdapter()
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
    assert audit['finding_count'] >= 1
