from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from fy_platform.ai.schemas.common import ArtifactRecord, EvidenceRecord, SuiteRunRecord, to_jsonable
from fy_platform.ai.workspace import ensure_workspace_layout, utc_now, workspace_root


class EvidenceRegistry:
    def __init__(self, root: Path | None = None) -> None:
        self.root = workspace_root(root)
        ensure_workspace_layout(self.root)
        self.db_path = self.root / '.fydata' / 'registry' / 'registry.db'
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
                CREATE TABLE IF NOT EXISTS suite_runs (
                    run_id TEXT PRIMARY KEY,
                    suite TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    workspace_root TEXT NOT NULL,
                    target_repo_root TEXT,
                    target_repo_id TEXT,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    suite TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    format TEXT NOT NULL,
                    role TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT,
                    FOREIGN KEY(run_id) REFERENCES suite_runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    suite TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    source_uri TEXT NOT NULL,
                    ownership_zone TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    deterministic INTEGER NOT NULL,
                    review_state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    excerpt TEXT DEFAULT '',
                    FOREIGN KEY(run_id) REFERENCES suite_runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS links (
                    src_id TEXT NOT NULL,
                    dst_id TEXT NOT NULL,
                    relation TEXT NOT NULL
                );
                """
            )
            conn.commit()
        finally:
            conn.close()

    def start_run(self, *, suite: str, mode: str, target_repo_root: str | None, target_repo_id: str | None) -> SuiteRunRecord:
        record = SuiteRunRecord(
            run_id=f'{suite}-{uuid.uuid4().hex[:12]}',
            suite=suite,
            mode=mode,
            started_at=utc_now(),
            ended_at=None,
            workspace_root=str(self.root),
            target_repo_root=target_repo_root,
            target_repo_id=target_repo_id,
            status='running',
        )
        conn = self._connect()
        try:
            conn.execute(
                'INSERT INTO suite_runs(run_id, suite, mode, started_at, ended_at, workspace_root, target_repo_root, target_repo_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (record.run_id, record.suite, record.mode, record.started_at, record.ended_at, record.workspace_root, record.target_repo_root, record.target_repo_id, record.status),
            )
            conn.commit()
        finally:
            conn.close()
        return record

    def finish_run(self, run_id: str, *, status: str = 'ok') -> None:
        conn = self._connect()
        try:
            conn.execute('UPDATE suite_runs SET ended_at = ?, status = ? WHERE run_id = ?', (utc_now(), status, run_id))
            conn.commit()
        finally:
            conn.close()

    def record_artifact(self, *, suite: str, run_id: str, format: str, role: str, path: str, payload: Any | None = None) -> ArtifactRecord:
        rec = ArtifactRecord(artifact_id=uuid.uuid4().hex, suite=suite, run_id=run_id, format=format, role=role, path=path, created_at=utc_now())
        conn = self._connect()
        try:
            conn.execute(
                'INSERT INTO artifacts(artifact_id, suite, run_id, format, role, path, created_at, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (rec.artifact_id, rec.suite, rec.run_id, rec.format, rec.role, rec.path, rec.created_at, json.dumps(to_jsonable(payload)) if payload is not None else None),
            )
            conn.commit()
        finally:
            conn.close()
        return rec

    def record_evidence(self, *, suite: str, run_id: str, kind: str, source_uri: str, ownership_zone: str, content_hash: str, mime_type: str, deterministic: bool, review_state: str = 'raw', excerpt: str = '') -> EvidenceRecord:
        rec = EvidenceRecord(
            evidence_id=uuid.uuid4().hex,
            suite=suite,
            run_id=run_id,
            kind=kind,
            source_uri=source_uri,
            ownership_zone=ownership_zone,
            content_hash=content_hash,
            mime_type=mime_type,
            deterministic=deterministic,
            review_state=review_state,
            created_at=utc_now(),
        )
        conn = self._connect()
        try:
            conn.execute(
                'INSERT INTO evidence(evidence_id, suite, run_id, kind, source_uri, ownership_zone, content_hash, mime_type, deterministic, review_state, created_at, excerpt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (rec.evidence_id, rec.suite, rec.run_id, rec.kind, rec.source_uri, rec.ownership_zone, rec.content_hash, rec.mime_type, int(rec.deterministic), rec.review_state, rec.created_at, excerpt),
            )
            conn.commit()
        finally:
            conn.close()
        return rec

    def link(self, src_id: str, dst_id: str, relation: str) -> None:
        conn = self._connect()
        try:
            conn.execute('INSERT INTO links(src_id, dst_id, relation) VALUES (?, ?, ?)', (src_id, dst_id, relation))
            conn.commit()
        finally:
            conn.close()

    def latest_run(self, suite: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute('SELECT * FROM suite_runs WHERE suite = ? ORDER BY started_at DESC LIMIT 1', (suite,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute('SELECT * FROM suite_runs WHERE run_id = ?', (run_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_runs(self, suite: str) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute('SELECT * FROM suite_runs WHERE suite = ? ORDER BY started_at DESC', (suite,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def artifacts_for_run(self, run_id: str) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute('SELECT * FROM artifacts WHERE run_id = ? ORDER BY created_at ASC', (run_id,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def artifact_payload(self, artifact_id: str) -> Any | None:
        conn = self._connect()
        try:
            row = conn.execute('SELECT payload_json FROM artifacts WHERE artifact_id = ?', (artifact_id,)).fetchone()
            if not row or not row['payload_json']:
                return None
            return json.loads(row['payload_json'])
        finally:
            conn.close()
