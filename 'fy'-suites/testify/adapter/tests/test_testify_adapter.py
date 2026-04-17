from fy_platform.tests.fixtures_autark import create_target_repo
from testify.adapter.service import TestifyAdapter


def test_testify_adapter_audit_and_compare(tmp_path, monkeypatch):
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = TestifyAdapter()
    first = adapter.audit(str(repo))
    second = adapter.audit(str(repo))
    assert first['ok'] and second['ok']
    diff = adapter.compare_runs(first['run_id'], second['run_id'])
    assert diff['ok'] is True
