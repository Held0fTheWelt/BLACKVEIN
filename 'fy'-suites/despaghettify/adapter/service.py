from __future__ import annotations

import ast
from pathlib import Path

from fy_platform.ai.base_adapter import BaseSuiteAdapter


class DespaghettifyAdapter(BaseSuiteAdapter):
    __test__ = False
    FILE_SPIKE_LINES = 350
    FUNC_SPIKE_LINES = 80

    def __init__(self, root: Path | None = None) -> None:
        super().__init__('despaghettify', root)

    def _scan(self, target: Path) -> dict:
        file_spikes = []
        function_spikes = []
        total_files = 0
        for path in target.rglob('*.py'):
            parts = set(path.parts)
            if 'tests' in parts or '__pycache__' in parts or '.venv' in parts:
                continue
            total_files += 1
            rel = path.relative_to(target).as_posix()
            text = path.read_text(encoding='utf-8', errors='replace')
            lines = text.splitlines()
            if len(lines) >= self.FILE_SPIKE_LINES:
                file_spikes.append({'path': rel, 'line_count': len(lines), 'category': 'local_spike_file_length'})
            try:
                module = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(module):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and hasattr(node, 'end_lineno'):
                    span = int(node.end_lineno or node.lineno) - int(node.lineno) + 1
                    if span >= self.FUNC_SPIKE_LINES:
                        function_spikes.append({'path': rel, 'name': node.name, 'line_span': span, 'category': 'local_spike_function_length'})
        return {
            'total_python_files': total_files,
            'file_spikes': file_spikes,
            'function_spikes': function_spikes,
            'global_category': 'low' if total_files < 50 else 'medium',
            'local_spike_count': len(file_spikes) + len(function_spikes),
        }

    def audit(self, target_repo_root: str) -> dict:
        target = Path(target_repo_root).resolve()
        run_id, run_dir, tgt_id = self._start_run('audit', target)
        try:
            payload = self._scan(target)
            md_lines = ['# Despaghettify Audit', '', f"- global_category: {payload['global_category']}", f"- local_spike_count: {payload['local_spike_count']}", '']
            for spike in payload['file_spikes'][:10]:
                md_lines.append(f"- file spike: `{spike['path']}` ({spike['line_count']} lines)")
            for spike in payload['function_spikes'][:10]:
                md_lines.append(f"- function spike: `{spike['path']}::{spike['name']}` ({spike['line_span']} lines)")
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md='\n'.join(md_lines) + '\n', role_prefix='despaghettify_audit')
            self._finish_run(run_id, 'ok', {'local_spike_count': payload['local_spike_count'], 'target_repo_id': tgt_id})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'local_spike_count': payload['local_spike_count'], **paths}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}

    def prepare_fix(self, finding_ids: list[str]) -> dict:
        out = super().prepare_fix(finding_ids)
        out['suggested_actions'] = [
            'split longest files along domain seams',
            'extract oversized functions into helpers or services',
            'rerun despaghettify to confirm local spike closure',
        ]
        return out
