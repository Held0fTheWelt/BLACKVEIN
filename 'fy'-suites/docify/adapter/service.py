from __future__ import annotations

import ast
from pathlib import Path

from fy_platform.ai.base_adapter import BaseSuiteAdapter


class DocifyAdapter(BaseSuiteAdapter):
    __test__ = False
    def __init__(self, root: Path | None = None) -> None:
        super().__init__('docify', root)

    def _scan_python(self, target: Path) -> dict:
        findings = []
        scanned = 0
        for path in target.rglob('*.py'):
            parts = set(path.parts)
            if 'tests' in parts or '__pycache__' in parts or '.venv' in parts:
                continue
            scanned += 1
            rel = path.relative_to(target).as_posix()
            try:
                module = ast.parse(path.read_text(encoding='utf-8', errors='replace'))
            except SyntaxError:
                findings.append({'path': rel, 'line': 1, 'kind': 'module', 'name': '<module>', 'code': 'SYNTAX_ERROR'})
                continue
            if not ast.get_docstring(module):
                findings.append({'path': rel, 'line': 1, 'kind': 'module', 'name': '<module>', 'code': 'MISSING_MODULE_DOCSTRING'})
            for node in ast.walk(module):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name.startswith('_') and not (node.name.startswith('__') and node.name.endswith('__')):
                        continue
                    if not ast.get_docstring(node):
                        findings.append({'path': rel, 'line': int(getattr(node, 'lineno', 1)), 'kind': type(node).__name__.lower(), 'name': node.name, 'code': 'MISSING_DOCSTRING'})
        return {'scanned_python_files': scanned, 'findings': findings, 'finding_count': len(findings)}

    def audit(self, target_repo_root: str) -> dict:
        target = Path(target_repo_root).resolve()
        run_id, run_dir, tgt_id = self._start_run('audit', target)
        try:
            payload = self._scan_python(target)
            md_lines = ['# Docify Audit', '', f"- scanned_python_files: {payload['scanned_python_files']}", f"- finding_count: {payload['finding_count']}", '']
            for finding in payload['findings'][:25]:
                md_lines.append(f"- `{finding['path']}:{finding['line']}` {finding['code']} — {finding['name']}")
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md='\n'.join(md_lines) + '\n', role_prefix='docify_audit')
            self._finish_run(run_id, 'ok', {'finding_count': payload['finding_count'], 'target_repo_id': tgt_id})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'finding_count': payload['finding_count'], **paths}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}

    def prepare_fix(self, finding_ids: list[str]) -> dict:
        out = super().prepare_fix(finding_ids)
        out['suggested_actions'] = [
            'add module/class/function docstrings for the highest-count files first',
            'prefer public API surfaces before private helpers',
            'rerun docify audit to verify reduction',
        ]
        return out
