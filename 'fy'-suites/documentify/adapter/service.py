from __future__ import annotations

from pathlib import Path

from documentify.tools.document_builder import collect_repository_context, _role_doc, _simple_overview, _technical_reference, ROLE_MAP
from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.workspace import write_text


class DocumentifyAdapter(BaseSuiteAdapter):
    __test__ = False
    def __init__(self, root: Path | None = None) -> None:
        super().__init__('documentify', root)

    def audit(self, target_repo_root: str) -> dict:
        target = Path(target_repo_root).resolve()
        run_id, run_dir, tgt_id = self._start_run('audit', target)
        try:
            generated_dir = self.hub_dir / 'generated' / tgt_id / run_id
            generated_dir.mkdir(parents=True, exist_ok=True)
            context = collect_repository_context(target)
            generated_files: list[str] = []

            simple = generated_dir / 'simple' / 'PLATFORM_OVERVIEW.md'
            technical = generated_dir / 'technical' / 'SYSTEM_REFERENCE.md'
            simple.parent.mkdir(parents=True, exist_ok=True)
            technical.parent.mkdir(parents=True, exist_ok=True)
            write_text(simple, _simple_overview(context))
            write_text(technical, _technical_reference(context))
            generated_files.extend([str(simple.relative_to(self.root)), str(technical.relative_to(self.root))])

            roles_root = generated_dir / 'roles'
            for role in ROLE_MAP:
                role_path = roles_root / role / 'README.md'
                role_path.parent.mkdir(parents=True, exist_ok=True)
                write_text(role_path, _role_doc(role, target))
                generated_files.append(str(role_path.relative_to(self.root)))

            summary = {
                'suite': self.suite,
                'generated_count': len(generated_files),
                'services': context['services'],
                'docs_dirs': context['docs_dirs'],
                'workflows': context['workflows'],
                'generated_files': generated_files,
            }
            md = '# Documentify Generation\n\n' + f"- generated_count: {summary.get('generated_count', 0)}\n- generated_dir: `{generated_dir.relative_to(self.root)}`\n"
            payload = {'summary': summary, 'generated_dir': str(generated_dir.relative_to(self.root))}
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md=md, role_prefix='documentify_generation')
            self._finish_run(run_id, 'ok', {'doc_count': len(summary.get('generated_files', [])), 'target_repo_id': tgt_id})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'doc_count': len(summary.get('generated_files', [])), **paths, 'generated_dir': str(generated_dir)}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}

    def inspect(self, query: str | None = None) -> dict:
        out = super().inspect(query)
        out['tracks'] = ['easy', 'technical', 'role-bound', 'ai-read']
        return out

    def prepare_fix(self, finding_ids: list[str]) -> dict:
        out = super().prepare_fix(finding_ids)
        out['suggested_actions'] = [
            'grow document templates one maturity step upward',
            'cross-link generated documents to evidence sources',
            'export updated ai-read bundle for shared retrieval',
        ]
        return out
