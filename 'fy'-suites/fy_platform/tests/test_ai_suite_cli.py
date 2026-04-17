from fy_platform.tests.fixtures_autark import create_target_repo
from pathlib import Path
from fy_platform.tools.ai_suite_cli import main


def test_generic_ai_suite_cli(tmp_path, monkeypatch, capsys):
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(Path(r"/mnt/data/fy_complete_mvp/'fy'-suites"))
    rc = main(['docify', 'audit', '--target-repo', str(repo)])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"ok": true' in out.lower()
