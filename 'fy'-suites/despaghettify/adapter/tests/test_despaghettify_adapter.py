from fy_platform.tests.fixtures_autark import create_target_repo
from despaghettify.adapter.service import DespaghettifyAdapter


def test_despaghettify_adapter_detects_spikes_and_reset(tmp_path, monkeypatch):
    repo = create_target_repo(tmp_path)
    # create a local spike file
    spike = repo / 'src' / 'spike.py'
    spike.write_text('\n'.join(['x = 1'] * 400), encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    adapter = DespaghettifyAdapter()
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
    assert audit['local_spike_count'] >= 1
    reset = adapter.reset('reindex-reset')
    assert reset['ok'] is True
