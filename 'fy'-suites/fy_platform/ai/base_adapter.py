from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from fy_platform.ai.context_packs.service import ContextPackService
from fy_platform.ai.evidence_registry.registry import EvidenceRegistry
from fy_platform.ai.model_router.router import ModelRouter
from fy_platform.ai.run_journal.journal import RunJournal
from fy_platform.ai.semantic_index.index_manager import SemanticIndex
from fy_platform.ai.workspace import (
    binding_path,
    ensure_workspace_layout,
    internal_run_dir,
    suite_hub_dir,
    target_repo_id,
    utc_now,
    workspace_root,
    write_json,
    write_text,
)


class BaseSuiteAdapter(ABC):
    def __init__(self, suite: str, root: Path | None = None) -> None:
        self.suite = suite
        self.root = workspace_root(root)
        ensure_workspace_layout(self.root)
        self.registry = EvidenceRegistry(self.root)
        self.journal = RunJournal(self.root)
        self.index = SemanticIndex(self.root)
        self.context_packs = ContextPackService(self.root)
        self.router = ModelRouter()
        self.hub_dir = suite_hub_dir(self.root, suite)
        self.hub_dir.mkdir(parents=True, exist_ok=True)
        (self.hub_dir / 'reports').mkdir(parents=True, exist_ok=True)
        (self.hub_dir / 'state').mkdir(parents=True, exist_ok=True)
        (self.hub_dir / 'generated').mkdir(parents=True, exist_ok=True)

    def init(self, target_repo_root: str | None = None) -> dict[str, Any]:
        ensure_workspace_layout(self.root)
        target = Path(target_repo_root).resolve() if target_repo_root else None
        binding = {
            'suite': self.suite,
            'workspace_root': str(self.root),
            'target_repo_root': str(target) if target else None,
            'bound_at': utc_now(),
        }
        write_json(binding_path(self.root, self.suite), binding)
        return {'ok': True, 'suite': self.suite, 'binding': binding}

    def inspect(self, query: str | None = None) -> dict[str, Any]:
        latest = self.registry.latest_run(self.suite)
        if query:
            pack = self.index.build_context_pack(query, suite_scope=[self.suite])
            return {'ok': True, 'suite': self.suite, 'latest_run': latest, 'query': query, 'hit_count': len(pack.hits), 'summary': pack.summary}
        return {'ok': True, 'suite': self.suite, 'latest_run': latest}

    @abstractmethod
    def audit(self, target_repo_root: str) -> dict[str, Any]:
        raise NotImplementedError

    def explain(self, audience: str = 'developer') -> dict[str, Any]:
        latest = self.registry.latest_run(self.suite)
        if not latest:
            return {'ok': False, 'reason': 'no_runs', 'suite': self.suite}
        artifacts = self.registry.artifacts_for_run(latest['run_id'])
        summary = f"Suite {self.suite} last ran in mode {latest['mode']} with status {latest['status']}."
        if artifacts:
            summary += f" Produced {len(artifacts)} artifacts."
        if audience == 'manager':
            summary = summary.replace('Produced', 'Generated')
        return {'ok': True, 'suite': self.suite, 'run_id': latest['run_id'], 'summary': summary, 'artifacts': artifacts}

    def prepare_context_pack(self, query: str, audience: str = 'developer') -> dict[str, Any]:
        latest = self.registry.latest_run(self.suite)
        if latest and latest.get('target_repo_root'):
            target = Path(latest['target_repo_root'])
            if target.is_dir():
                self.index.clear_scope(self.suite, 'target', latest.get('target_repo_id'))
                self.index.index_directory(suite=self.suite, directory=target, scope='target', target_repo_id=latest.get('target_repo_id'))
        self.index.clear_scope(self.suite, 'suite')
        self.index.index_directory(suite=self.suite, directory=self.hub_dir, scope='suite')
        out_dir = self.hub_dir / 'generated' / 'context_packs'
        out_dir.mkdir(parents=True, exist_ok=True)
        return self.context_packs.build_and_write(suite=self.suite, query=query, suite_scope=[self.suite], audience=audience, out_dir=out_dir)

    def compare_runs(self, left_run_id: str, right_run_id: str) -> dict[str, Any]:
        left = self.registry.get_run(left_run_id)
        right = self.registry.get_run(right_run_id)
        if not left or not right:
            return {'ok': False, 'reason': 'run_not_found', 'suite': self.suite}
        left_art = self.registry.artifacts_for_run(left_run_id)
        right_art = self.registry.artifacts_for_run(right_run_id)
        return {
            'ok': True,
            'suite': self.suite,
            'left_run_id': left_run_id,
            'right_run_id': right_run_id,
            'left_status': left['status'],
            'right_status': right['status'],
            'artifact_delta': len(right_art) - len(left_art),
        }

    def clean(self, mode: str = 'standard') -> dict[str, Any]:
        removed = []
        cache_dir = self.root / '.fydata' / 'cache'
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            removed.append(str(cache_dir.relative_to(self.root)))
        if mode == 'aggressive':
            run_dir = self.root / '.fydata' / 'runs' / self.suite
            if run_dir.is_dir():
                shutil.rmtree(run_dir)
                run_dir.mkdir(parents=True, exist_ok=True)
                removed.append(str(run_dir.relative_to(self.root)))
        return {'ok': True, 'suite': self.suite, 'mode': mode, 'removed': removed}

    def reset(self, mode: str = 'soft') -> dict[str, Any]:
        removed = []
        if mode in {'soft', 'hard'}:
            state_dir = self.hub_dir / 'state'
            if state_dir.is_dir():
                shutil.rmtree(state_dir)
                state_dir.mkdir(parents=True, exist_ok=True)
                removed.append(str(state_dir.relative_to(self.root)))
        if mode in {'hard', 'reindex-reset'}:
            index_db = self.root / '.fydata' / 'index' / 'semantic_index.db'
            if index_db.exists():
                index_db.unlink()
                removed.append(str(index_db.relative_to(self.root)))
                self.index = SemanticIndex(self.root)
        return {'ok': True, 'suite': self.suite, 'mode': mode, 'removed': removed}

    def triage(self, query: str | None = None) -> dict[str, Any]:
        route = self.router.route('triage')
        return {'ok': True, 'suite': self.suite, 'route': route.__dict__, 'query': query or ''}

    def prepare_fix(self, finding_ids: list[str]) -> dict[str, Any]:
        route = self.router.route('prepare_fix')
        return {'ok': True, 'suite': self.suite, 'route': route.__dict__, 'finding_ids': finding_ids, 'advisory_only': True}

    def _start_run(self, mode: str, target_repo_root: Path) -> tuple[str, Path, str]:
        tgt_id = target_repo_id(target_repo_root)
        run = self.registry.start_run(suite=self.suite, mode=mode, target_repo_root=str(target_repo_root), target_repo_id=tgt_id)
        run_dir = internal_run_dir(self.root, self.suite, run.run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        self.journal.append(self.suite, run.run_id, 'run_started', {'mode': mode, 'target_repo_root': str(target_repo_root), 'target_repo_id': tgt_id})
        return run.run_id, run_dir, tgt_id

    def _finish_run(self, run_id: str, status: str, summary: dict[str, Any]) -> None:
        self.journal.append(self.suite, run_id, 'run_finished', {'status': status, 'summary': summary})
        self.registry.finish_run(run_id, status=status)

    def _write_payload_bundle(self, *, run_id: str, run_dir: Path, payload: dict[str, Any], summary_md: str, role_prefix: str) -> dict[str, str]:
        json_path = run_dir / f'{role_prefix}.json'
        md_path = run_dir / f'{role_prefix}.md'
        write_json(json_path, payload)
        write_text(md_path, summary_md)
        self.registry.record_artifact(suite=self.suite, run_id=run_id, format='json', role=f'{role_prefix}_json', path=str(json_path.relative_to(self.root)), payload=payload)
        self.registry.record_artifact(suite=self.suite, run_id=run_id, format='md', role=f'{role_prefix}_md', path=str(md_path.relative_to(self.root)), payload={'markdown_preview': summary_md[:500]})
        return {'json_path': str(json_path), 'md_path': str(md_path)}
