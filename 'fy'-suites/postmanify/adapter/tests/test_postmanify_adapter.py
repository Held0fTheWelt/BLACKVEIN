from fy_platform.tests.fixtures_autark import create_target_repo
from postmanify.adapter.service import PostmanifyAdapter


def test_postmanify_adapter_generates_collections(tmp_path, monkeypatch):
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = PostmanifyAdapter()
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
    assert audit['sub_suite_count'] >= 1
