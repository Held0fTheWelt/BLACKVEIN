"""Index manager for fy_platform.ai.semantic_index.

"""
from __future__ import annotations

import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from fy_platform.ai.persistence_state import ensure_schema_state
from fy_platform.ai.policy.indexing_policy import MAX_TEXT_BYTES, is_indexable_path, should_exclude_dir, should_exclude_file
from fy_platform.ai.schemas.common import ContextPack, RetrievalHit
from fy_platform.ai.workspace import read_text_safe, utc_now, workspace_root
from fy_platform.ai.semantic_index.context_pack_summary import next_steps as summary_next_steps, pack_confidence, pack_uncertainty, priorities as summary_priorities, summarize_hits
from fy_platform.ai.semantic_index.scoring import confidence as scoring_confidence, lexical_score, passes_noise_gate, rationale as scoring_rationale, recency_score, scope_score, semantic_score, suite_affinity_score, tokens

class SemanticIndex:
    """Coordinate semantic index behavior.
    """
    def __init__(self, root: Path | None = None) -> None:
        """Initialize SemanticIndex.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        self.root = workspace_root(root)
        self.db_path = self.root / '.fydata' / 'index' / 'semantic_index.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        ensure_schema_state(self.root)

    def _connect(self) -> sqlite3.Connection:
        """Connect the requested operation.

        Returns:
            sqlite3.Connection:
                Value produced by this callable as
                ``sqlite3.Connection``.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Init db.

        Exceptions are normalized inside the implementation before
        control returns to callers. Control flow branches on the parsed
        state rather than relying on one linear path.
        """
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
                    scope TEXT NOT NULL,
                    created_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_suite ON chunks(suite);
                CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_path);
                CREATE INDEX IF NOT EXISTS idx_chunks_scope ON chunks(scope);
                """
            )
            cols = {row['name'] for row in conn.execute('PRAGMA table_info(chunks)').fetchall()}
            if 'created_at' not in cols:
                conn.execute('ALTER TABLE chunks ADD COLUMN created_at TEXT')
            conn.commit()
        finally:
            conn.close()

    def clear_scope(self, suite: str, scope: str, target_repo_id: str | None = None) -> None:
        """Clear scope.

        Exceptions are normalized inside the implementation before
        control returns to callers. Control flow branches on the parsed
        state rather than relying on one linear path.

        Args:
            suite: Primary suite used by this step.
            scope: Primary scope used by this step.
            target_repo_id: Identifier used to select an existing run or
                record.
        """
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
        """Add chunk.

        Exceptions are normalized inside the implementation before
        control returns to callers.

        Args:
            suite: Primary suite used by this step.
            source_path: Filesystem path to the file or directory being
                processed.
            chunk_type: Primary chunk type used by this step.
            text: Text content to inspect or rewrite.
            scope: Primary scope used by this step.
            run_id: Identifier used to select an existing run or record.
            target_repo_id: Identifier used to select an existing run or
                record.

        Returns:
            str:
                Rendered text produced for downstream
                callers or writers.
        """
        chunk_id = uuid.uuid4().hex
        conn = self._connect()
        try:
            conn.execute(
                'INSERT INTO chunks(chunk_id, suite, source_path, chunk_type, text, token_count, run_id, target_repo_id, scope, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (chunk_id, suite, source_path, chunk_type, text, len(tokens(text)), run_id, target_repo_id, scope, utc_now()),
            )
            conn.commit()
        finally:
            conn.close()
        return chunk_id

    def index_texts(self, *, suite: str, items: Iterable[tuple[str, str]], scope: str, run_id: str | None = None, target_repo_id: str | None = None) -> int:
        """Index texts.

        The implementation iterates over intermediate items before it
        returns.

        Args:
            suite: Primary suite used by this step.
            items: Primary items used by this step.
            scope: Primary scope used by this step.
            run_id: Identifier used to select an existing run or record.
            target_repo_id: Identifier used to select an existing run or
                record.

        Returns:
            int:
                Value produced by this callable as
                ``int``.
        """
        count = 0
        for source_path, text in items:
            for i, chunk in enumerate(self._chunk_text(text)):
                self.add_chunk(suite=suite, source_path=f'{source_path}#chunk-{i+1}', chunk_type='text', text=chunk, scope=scope, run_id=run_id, target_repo_id=target_repo_id)
                count += 1
        return count

    def index_directory(self, *, suite: str, directory: Path, scope: str, run_id: str | None = None, target_repo_id: str | None = None) -> int:
        """Index directory.

        The implementation iterates over intermediate items before it
        returns. Exceptions are normalized inside the implementation
        before control returns to callers.

        Args:
            suite: Primary suite used by this step.
            directory: Primary directory used by this step.
            scope: Primary scope used by this step.
            run_id: Identifier used to select an existing run or record.
            target_repo_id: Identifier used to select an existing run or
                record.

        Returns:
            int:
                Value produced by this callable as
                ``int``.
        """
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
        """Chunk text.

        The implementation iterates over intermediate items before it
        returns. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            text: Text content to inspect or rewrite.
            max_chars: Primary max chars used by this step.

        Returns:
            list[str]:
                Collection produced from the parsed or
                accumulated input data.
        """
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
        """Tokens the requested operation.

        Args:
            text: Text content to inspect or rewrite.

        Returns:
            list[str]:
                Collection produced from the parsed or
                accumulated input data.
        """
        return tokens(text)

    def search(self, query: str, *, suite_scope: list[str] | None = None, limit: int = 8) -> list[RetrievalHit]:
        """Search the requested operation.

        The implementation iterates over intermediate items before it
        returns. Exceptions are normalized inside the implementation
        before control returns to callers.

        Args:
            query: Free-text input that shapes this operation.
            suite_scope: Primary suite scope used by this step.
            limit: Primary limit used by this step.

        Returns:
            list[RetrievalHit]:
                Collection produced from the parsed or
                accumulated input data.
        """
        query_tokens = self._tokens(query)
        q_counter = Counter(query_tokens)
        conn = self._connect()
        try:
            rows = conn.execute('SELECT rowid, * FROM chunks').fetchall()
        finally:
            conn.close()
        if not rows:
            return []
        newest_rowid = max(int(row['rowid']) for row in rows)
        hits = []
        emitted_by_source: dict[str, int] = {}
        for row in rows:
            if suite_scope and row['suite'] not in suite_scope:
                continue
            text = row['text']
            doc_tokens = tokens(text)
            if not doc_tokens:
                continue
            lexical = lexical_score(query_tokens, doc_tokens)
            semantic = semantic_score(q_counter, Counter(doc_tokens))
            matched_terms = sorted({token for token in query_tokens if token in doc_tokens})[:8]
            recency = recency_score(int(row['rowid']), newest_rowid)
            scope_value = scope_score(row['scope'])
            suite_affinity = suite_affinity_score(query_tokens, row['suite'], row['source_path'])
            hybrid = 0.45 * lexical + 0.25 * semantic + 0.15 * recency + 0.10 * scope_value + 0.05 * suite_affinity
            if not passes_noise_gate(lexical, semantic, matched_terms):
                continue
            source_key = row['source_path'].split('#chunk-')[0]
            if emitted_by_source.get(source_key, 0) >= 2:
                continue
            emitted_by_source[source_key] = emitted_by_source.get(source_key, 0) + 1
            confidence = scoring_confidence(lexical, semantic, hybrid, matched_terms)
            excerpt = text[:280].replace('\n', ' ')
            rationale = scoring_rationale(matched_terms, recency, suite_affinity, scope_value)
            hits.append(RetrievalHit(
                chunk_id=row['chunk_id'],
                suite=row['suite'],
                score_lexical=round(lexical, 4),
                score_semantic=round(semantic, 4),
                score_hybrid=round(hybrid, 4),
                source_path=row['source_path'],
                excerpt=excerpt,
                scope=row['scope'],
                target_repo_id=row['target_repo_id'],
                score_recency=round(recency, 4),
                score_scope=round(scope_value, 4),
                score_suite_affinity=round(suite_affinity, 4),
                matched_terms=matched_terms,
                confidence=confidence,
                rationale=rationale,
            ))
        hits.sort(key=lambda h: (h.score_hybrid, h.score_lexical, h.score_semantic), reverse=True)
        return hits[:limit]

    def build_context_pack(self, query: str, *, suite_scope: list[str] | None = None, audience: str = 'developer', limit: int = 8) -> ContextPack:
        """Build context pack.

        Args:
            query: Free-text input that shapes this operation.
            suite_scope: Primary suite scope used by this step.
            audience: Free-text input that shapes this operation.
            limit: Primary limit used by this step.

        Returns:
            ContextPack:
                Value produced by this callable as
                ``ContextPack``.
        """
        hits = self.search(query, suite_scope=suite_scope, limit=limit)
        summary = summarize_hits(query, hits, audience=audience)
        artifact_paths = sorted({hit.source_path for hit in hits})
        related_suites = sorted({hit.suite for hit in hits if hit.suite not in (suite_scope or [])})
        evidence_confidence = pack_confidence(hits)
        priorities = summary_priorities(query, hits)
        next_steps = summary_next_steps(hits, audience)
        uncertainty = pack_uncertainty(hits)
        return ContextPack(
            pack_id=uuid.uuid4().hex,
            query=query,
            suite_scope=suite_scope or [],
            audience=audience,
            hits=hits,
            summary=summary,
            artifact_paths=artifact_paths,
            related_suites=related_suites,
            evidence_confidence=evidence_confidence,
            priorities=priorities,
            next_steps=next_steps,
            uncertainty=uncertainty,
        )


