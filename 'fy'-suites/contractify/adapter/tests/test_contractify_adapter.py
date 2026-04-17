from fy_platform.tests.fixtures_autark import create_target_repo
from contractify.adapter.service import ContractifyAdapter


def test_contractify_adapter_full_cycle(tmp_path, monkeypatch):
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = ContractifyAdapter()
    init = adapter.init(str(repo))
    assert init['ok'] is True
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
    explain = adapter.explain()
    assert explain['ok'] is True
    pack = adapter.prepare_context_pack('openapi health')
    assert pack['hit_count'] >= 1
