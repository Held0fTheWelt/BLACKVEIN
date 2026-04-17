from fy_platform.tests.fixtures_autark import create_target_repo
from dockerify.adapter.service import DockerifyAdapter


def test_dockerify_adapter_audit(tmp_path, monkeypatch):
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = DockerifyAdapter()
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
