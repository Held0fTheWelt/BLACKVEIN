from __future__ import annotations

from pathlib import Path

from testify.tools.test_governance import audit_test_governance, render_markdown
from fy_platform.ai.base_adapter import BaseSuiteAdapter


class TestifyAdapter(BaseSuiteAdapter):
    __test__ = False
    def __init__(self, root: Path | None = None) -> None:
        super().__init__('testify', root)

    def audit(self, target_repo_root: str) -> dict:
        target = Path(target_repo_root).resolve()
        run_id, run_dir, tgt_id = self._start_run('audit', target)
        try:
            try:
                payload = audit_test_governance(target)
                md = render_markdown(payload)
            except Exception as exc:
                checks = []
                checks.append({'name': 'tests_run_script', 'ok': (target / 'tests' / 'run_tests.py').is_file()})
                checks.append({'name': 'github_workflow', 'ok': any((target / '.github' / 'workflows').glob('*.y*ml')) if (target / '.github' / 'workflows').is_dir() else False})
                payload = {'fallback_note': f'testify fallback used: {exc}', 'checks': checks, 'findings': [c for c in checks if not c['ok']]}
                md = '# Testify Audit\n\n' + '\n'.join(f"- {c['name']}: {'ok' if c['ok'] else 'missing'}" for c in checks) + '\n'
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md=md, role_prefix='testify_audit')
            failures = len(payload.get('findings', [])) if isinstance(payload, dict) else 0
            self._finish_run(run_id, 'ok', {'finding_count': failures, 'target_repo_id': tgt_id})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'finding_count': failures, **paths}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}

    def prepare_fix(self, finding_ids: list[str]) -> dict:
        out = super().prepare_fix(finding_ids)
        out['suggested_actions'] = [
            'align tests/run_tests.py with workflow entries',
            'ensure CI workflow covers required suite targets',
            'refresh testify audit after changes',
        ]
        return out
