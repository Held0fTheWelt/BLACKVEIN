from fy_platform.tests.fixtures_autark import create_target_repo
from documentify.adapter.service import DocumentifyAdapter


def test_documentify_adapter_generates_docs(tmp_path, monkeypatch):
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = DocumentifyAdapter()
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
    assert audit['doc_count'] >= 1
    assert 'generated_dir' in audit
