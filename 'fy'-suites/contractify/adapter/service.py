from __future__ import annotations

from pathlib import Path

from contractify.tools.audit_pipeline import build_discover_payload, run_audit
from fy_platform.ai.base_adapter import BaseSuiteAdapter


class ContractifyAdapter(BaseSuiteAdapter):
    __test__ = False
    def __init__(self, root: Path | None = None) -> None:
        super().__init__('contractify', root)

    def audit(self, target_repo_root: str) -> dict:
        target = Path(target_repo_root).resolve()
        run_id, run_dir, tgt_id = self._start_run('audit', target)
        try:
            try:
                payload = run_audit(target, max_contracts=30)
            except Exception as exc:
                payload = {
                    'stats': {'contracts': 0, 'drift_findings': 0, 'conflicts': 0},
                    'drift_findings': [],
                    'conflicts': [],
                    'fallback_note': f'contractify fallback summary used: {exc}',
                    'discovery_preview': build_discover_payload(target, max_contracts=30) if target.exists() else {},
                }
            findings = len(payload.get('drift_findings', [])) + len(payload.get('conflicts', []))
            md = "# Contractify Audit\n\n" + f"- target: `{target}`\n- findings: {findings}\n"
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md=md, role_prefix='contractify_audit')
            self._finish_run(run_id, 'ok', {'finding_count': findings, 'target_repo_id': tgt_id})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'finding_count': findings, **paths}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}

    def triage(self, query: str | None = None) -> dict:
        base = super().triage(query)
        latest = self.registry.latest_run(self.suite)
        if latest:
            artifacts = self.registry.artifacts_for_run(latest['run_id'])
            base['latest_artifact_count'] = len(artifacts)
        return base

    def prepare_fix(self, finding_ids: list[str]) -> dict:
        out = super().prepare_fix(finding_ids)
        out['suggested_actions'] = [
            're-anchor affected contracts to a single owner vocabulary',
            'refresh projection/back-reference links',
            'regenerate audit and compare against accepted run',
        ]
        return out
