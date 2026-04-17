from __future__ import annotations

from pathlib import Path

from fy_platform.ai.semantic_index.index_manager import SemanticIndex
from fy_platform.ai.workspace import write_json, write_text, workspace_root


class ContextPackService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = workspace_root(root)
        self.index = SemanticIndex(self.root)

    def build_and_write(self, *, suite: str, query: str, suite_scope: list[str], audience: str, out_dir: Path) -> dict:
        pack = self.index.build_context_pack(query, suite_scope=suite_scope, audience=audience)
        json_path = out_dir / f'{suite}_context_pack.json'
        md_path = out_dir / f'{suite}_context_pack.md'
        write_json(json_path, {
            'pack_id': pack.pack_id,
            'query': pack.query,
            'suite_scope': pack.suite_scope,
            'audience': pack.audience,
            'summary': pack.summary,
            'hits': [h.__dict__ for h in pack.hits],
        })
        lines = [f'# Context Pack — {suite}', '', f'Query: `{pack.query}`', '', pack.summary, '']
        for hit in pack.hits:
            lines.extend([f'## {hit.source_path}', '', f'- lexical: {hit.score_lexical}', f'- semantic: {hit.score_semantic}', f'- hybrid: {hit.score_hybrid}', '', hit.excerpt, ''])
        write_text(md_path, '\n'.join(lines).strip() + '\n')
        return {'json_path': str(json_path), 'md_path': str(md_path), 'hit_count': len(pack.hits), 'summary': pack.summary}
