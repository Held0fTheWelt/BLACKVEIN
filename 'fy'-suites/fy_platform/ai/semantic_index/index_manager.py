from __future__ import annotations

import math
import re
import sqlite3
import uuid
from collections import Counter
from pathlib import Path
from typing import Iterable

from fy_platform.ai.policy.indexing_policy import MAX_TEXT_BYTES, is_indexable_path, should_exclude_dir, should_exclude_file
from fy_platform.ai.schemas.common import ContextPack, RetrievalHit
from fy_platform.ai.workspace import read_text_safe, workspace_root

TOKEN_RE = re.compile(r"[A-Za-z0-9_\-/]{2,}")


class SemanticIndex:
    def __init__(self, root: Path | None = None) -> None:
        self.root = workspace_root(root)
        self.db_path = self.root / '.fydata' / 'index' / 'semantic_index.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    suite TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    chunk_type TEXT NOT NULL,
                    text TEXT NOT NULL,
                    token_count INTEGER NOT NULL,
                    run_id TEXT,
                    target_repo_id TEXT,
                    scope TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_suite ON chunks(suite);
                CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_path);
                """
            )
            conn.commit()
        finally:
            conn.close()

    def clear_scope(self, suite: str, scope: str, target_repo_id: str | None = None) -> None:
        conn = self._connect()
        try:
            if target_repo_id:
                conn.execute('DELETE FROM chunks WHERE suite = ? AND scope = ? AND target_repo_id = ?', (suite, scope, target_repo_id))
            else:
                conn.execute('DELETE FROM chunks WHERE suite = ? AND scope = ?', (suite, scope))
            conn.commit()
        finally:
            conn.close()

    def add_chunk(self, *, suite: str, source_path: str, chunk_type: str, text: str, scope: str, run_id: str | None = None, target_repo_id: str | None = None) -> str:
        chunk_id = uuid.uuid4().hex
        conn = self._connect()
        try:
            conn.execute(
                'INSERT INTO chunks(chunk_id, suite, source_path, chunk_type, text, token_count, run_id, target_repo_id, scope) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (chunk_id, suite, source_path, chunk_type, text, len(self._tokens(text)), run_id, target_repo_id, scope),
            )
            conn.commit()
        finally:
            conn.close()
        return chunk_id

    def index_texts(self, *, suite: str, items: Iterable[tuple[str, str]], scope: str, run_id: str | None = None, target_repo_id: str | None = None) -> int:
        count = 0
        for source_path, text in items:
            for i, chunk in enumerate(self._chunk_text(text)):
                self.add_chunk(suite=suite, source_path=f'{source_path}#chunk-{i+1}', chunk_type='text', text=chunk, scope=scope, run_id=run_id, target_repo_id=target_repo_id)
                count += 1
        return count

    def index_directory(self, *, suite: str, directory: Path, scope: str, run_id: str | None = None, target_repo_id: str | None = None) -> int:
        items = []
        for path in directory.rglob('*'):
            if path.is_dir() and should_exclude_dir(path.name):
                continue
            if not path.is_file() or should_exclude_file(path.name) or not is_indexable_path(path):
                continue
            try:
                if path.stat().st_size > MAX_TEXT_BYTES:
                    continue
            except OSError:
                continue
            rel = path.relative_to(directory).as_posix()
            items.append((rel, read_text_safe(path)))
        return self.index_texts(suite=suite, items=items, scope=scope, run_id=run_id, target_repo_id=target_repo_id)

    def _chunk_text(self, text: str, max_chars: int = 1200) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= max_chars:
            return [text]
        chunks = []
        current = []
        current_len = 0
        for para in text.split('\n\n'):
            para = para.strip()
            if not para:
                continue
            if current_len + len(para) + 2 > max_chars and current:
                chunks.append('\n\n'.join(current))
                current = [para]
                current_len = len(para)
            else:
                current.append(para)
                current_len += len(para) + 2
        if current:
            chunks.append('\n\n'.join(current))
        return chunks

    def _tokens(self, text: str) -> list[str]:
        return [t.lower() for t in TOKEN_RE.findall(text)]

    def search(self, query: str, *, suite_scope: list[str] | None = None, limit: int = 8) -> list[RetrievalHit]:
        query_tokens = self._tokens(query)
        q_counter = Counter(query_tokens)
        conn = self._connect()
        try:
            rows = conn.execute('SELECT * FROM chunks').fetchall()
        finally:
            conn.close()
        hits = []
        for row in rows:
            if suite_scope and row['suite'] not in suite_scope:
                continue
            text = row['text']
            tokens = self._tokens(text)
            if not tokens:
                continue
            lexical = self._lexical_score(query_tokens, tokens)
            semantic = self._semantic_score(q_counter, Counter(tokens))
            hybrid = 0.6 * lexical + 0.4 * semantic
            if hybrid <= 0:
                continue
            excerpt = text[:280].replace('\n', ' ')
            hits.append(RetrievalHit(
                chunk_id=row['chunk_id'],
                score_lexical=round(lexical, 4),
                score_semantic=round(semantic, 4),
                score_hybrid=round(hybrid, 4),
                source_path=row['source_path'],
                excerpt=excerpt,
            ))
        hits.sort(key=lambda h: h.score_hybrid, reverse=True)
        return hits[:limit]

    def build_context_pack(self, query: str, *, suite_scope: list[str] | None = None, audience: str = 'developer', limit: int = 8) -> ContextPack:
        hits = self.search(query, suite_scope=suite_scope, limit=limit)
        summary = self._summarize_hits(query, hits)
        return ContextPack(pack_id=uuid.uuid4().hex, query=query, suite_scope=suite_scope or [], audience=audience, hits=hits, summary=summary)

    def _lexical_score(self, query_tokens: list[str], doc_tokens: list[str]) -> float:
        if not query_tokens or not doc_tokens:
            return 0.0
        q = Counter(query_tokens)
        d = Counter(doc_tokens)
        inter = sum(min(q[t], d.get(t, 0)) for t in q)
        return inter / max(len(query_tokens), 1)

    def _semantic_score(self, q: Counter, d: Counter) -> float:
        if not q or not d:
            return 0.0
        dot = sum(q[k] * d.get(k, 0) for k in q)
        nq = math.sqrt(sum(v * v for v in q.values()))
        nd = math.sqrt(sum(v * v for v in d.values()))
        if nq == 0 or nd == 0:
            return 0.0
        return dot / (nq * nd)

    def _summarize_hits(self, query: str, hits: list[RetrievalHit]) -> str:
        if not hits:
            return f'No indexed evidence matched query: {query}'
        top = hits[0]
        return f'Found {len(hits)} indexed evidence hits for query "{query}". Strongest source: {top.source_path}.'
