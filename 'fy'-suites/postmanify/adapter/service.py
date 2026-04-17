from __future__ import annotations

from pathlib import Path

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.workspace import write_json
from postmanify.tools.openapi_postman import build_collections, load_openapi_dict


class PostmanifyAdapter(BaseSuiteAdapter):
    __test__ = False
    def __init__(self, root: Path | None = None) -> None:
        super().__init__('postmanify', root)

    def audit(self, target_repo_root: str) -> dict:
        target = Path(target_repo_root).resolve()
        run_id, run_dir, tgt_id = self._start_run('audit', target)
        try:
            openapi = target / 'docs' / 'api' / 'openapi.yaml'
            if not openapi.is_file():
                raise FileNotFoundError(f'Missing OpenAPI file: {openapi}')
            spec = load_openapi_dict(openapi)
            master, subs = build_collections(spec, backend_api_prefix='/api/v1')
            generated_dir = self.hub_dir / 'generated' / tgt_id / run_id / 'postman'
            generated_dir.mkdir(parents=True, exist_ok=True)
            master_path = generated_dir / 'master_collection.json'
            write_json(master_path, master)
            sub_paths = []
            for slug, coll in subs.items():
                path = generated_dir / f'{slug}.postman_collection.json'
                write_json(path, coll)
                sub_paths.append(str(path.relative_to(self.root)))
            payload = {'openapi': str(openapi), 'sub_suite_count': len(subs), 'master_path': str(master_path.relative_to(self.root)), 'sub_paths': sub_paths}
            md = '# Postmanify Audit\n\n' + f'- openapi: `{openapi}`\n- sub_suite_count: {len(subs)}\n'
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md=md, role_prefix='postmanify_audit')
            self._finish_run(run_id, 'ok', {'sub_suite_count': len(subs), 'target_repo_id': tgt_id})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'sub_suite_count': len(subs), **paths, 'generated_dir': str(generated_dir)}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}
