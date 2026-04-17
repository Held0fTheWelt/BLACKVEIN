from __future__ import annotations

from pathlib import Path

from dockerify.tools.docker_audit import audit_docker_surface, render_markdown
from fy_platform.ai.base_adapter import BaseSuiteAdapter


class DockerifyAdapter(BaseSuiteAdapter):
    __test__ = False
    def __init__(self, root: Path | None = None) -> None:
        super().__init__('dockerify', root)

    def audit(self, target_repo_root: str) -> dict:
        target = Path(target_repo_root).resolve()
        run_id, run_dir, tgt_id = self._start_run('audit', target)
        try:
            payload = audit_docker_surface(target)
            md = render_markdown(payload)
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md=md, role_prefix='dockerify_audit')
            findings = len(payload.get('findings', [])) if isinstance(payload, dict) else 0
            self._finish_run(run_id, 'ok', {'finding_count': findings, 'target_repo_id': tgt_id})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'finding_count': findings, **paths}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}
