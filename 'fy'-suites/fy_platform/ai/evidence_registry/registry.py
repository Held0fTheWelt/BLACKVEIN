"""Registry for fy_platform.ai.evidence_registry.

"""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from fy_platform.ai.persistence_state import ensure_schema_state, record_migration_event
from fy_platform.ai.policy.review_policy import validate_transition
from fy_platform.ai.schemas.common import ArtifactRecord, CompareRunsDelta, EvidenceRecord, SuiteRunRecord, to_jsonable
from fy_platform.ai.workspace import ensure_workspace_layout, utc_now, workspace_root
from fy_platform.ai.evidence_registry.compare_runs import build_compare_runs_delta


class EvidenceRegistry:
    """Registry for evidence records.
    """
    def __init__(self, root: Path | None = None) -> None:
        """Initialize EvidenceRegistry.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        self.root = workspace_root(root)
        ensure_workspace_layout(self.root)
        self.db_path = self.root / '.fydata' / 'registry' / 'registry.db'
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
        control returns to callers.
        """
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
                    status TEXT NOT NULL,
                    strategy_profile TEXT DEFAULT '',
                    run_metadata_json TEXT DEFAULT '{}'
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
            columns = {row['name'] for row in conn.execute('PRAGMA table_info(suite_runs)').fetchall()}
            if 'strategy_profile' not in columns:
                conn.execute("ALTER TABLE suite_runs ADD COLUMN strategy_profile TEXT DEFAULT ''")
                record_migration_event(self.root, component='registry', from_version=2, to_version=3, action='add_strategy_profile_column')
            if 'run_metadata_json' not in columns:
                conn.execute("ALTER TABLE suite_runs ADD COLUMN run_metadata_json TEXT DEFAULT '{}'")
                record_migration_event(self.root, component='registry', from_version=2, to_version=3, action='add_run_metadata_column')
            conn.commit()
        finally:
            conn.close()

    def start_run(self, *, suite: str, mode: str, target_repo_root: str | None, target_repo_id: str | None, strategy_profile: str = '', run_metadata: dict[str, Any] | None = None) -> SuiteRunRecord:
        """Start run.

        Exceptions are normalized inside the implementation before
        control returns to callers.

        Args:
            suite: Primary suite used by this step.
            mode: Named mode for this operation.
            target_repo_root: Root directory used to resolve
                repository-local paths.
            target_repo_id: Identifier used to select an existing run or
                record.

        Returns:
            SuiteRunRecord:
                Value produced by this callable as
                ``SuiteRunRecord``.
        """
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
            strategy_profile=strategy_profile,
            run_metadata=dict(run_metadata or {}),
        )
        conn = self._connect()
        try:
            conn.execute(
                'INSERT INTO suite_runs(run_id, suite, mode, started_at, ended_at, workspace_root, target_repo_root, target_repo_id, status, strategy_profile, run_metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (record.run_id, record.suite, record.mode, record.started_at, record.ended_at, record.workspace_root, record.target_repo_root, record.target_repo_id, record.status, record.strategy_profile, json.dumps(to_jsonable(record.run_metadata))),
            )
            conn.commit()
        finally:
            conn.close()
        return record

    def finish_run(self, run_id: str, *, status: str = 'ok') -> None:
        """Finish run.

        Exceptions are normalized inside the implementation before
        control returns to callers.

        Args:
            run_id: Identifier used to select an existing run or record.
            status: Named status for this operation.
        """
        conn = self._connect()
        try:
            conn.execute('UPDATE suite_runs SET ended_at = ?, status = ? WHERE run_id = ?', (utc_now(), status, run_id))
            conn.commit()
        finally:
            conn.close()

    def record_artifact(self, *, suite: str, run_id: str, format: str, role: str, path: str, payload: Any | None = None) -> ArtifactRecord:
        """Record artifact.

        Exceptions are normalized inside the implementation before
        control returns to callers.

        Args:
            suite: Primary suite used by this step.
            run_id: Identifier used to select an existing run or record.
            format: Primary format used by this step.
            role: Primary role used by this step.
            path: Filesystem path to the file or directory being
                processed.
            payload: Structured data carried through this workflow.

        Returns:
            ArtifactRecord:
                Value produced by this callable as
                ``ArtifactRecord``.
        """
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
        """Record evidence.

        Exceptions are normalized inside the implementation before
        control returns to callers.

        Args:
            suite: Primary suite used by this step.
            run_id: Identifier used to select an existing run or record.
            kind: Primary kind used by this step.
            source_uri: Primary source uri used by this step.
            ownership_zone: Primary ownership zone used by this step.
            content_hash: Primary content hash used by this step.
            mime_type: Primary mime type used by this step.
            deterministic: Whether to enable this optional behavior.
            review_state: Primary review state used by this step.
            excerpt: Primary excerpt used by this step.

        Returns:
            EvidenceRecord:
                Value produced by this callable as
                ``EvidenceRecord``.
        """
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

    def update_evidence_review_state(self, evidence_id: str, new_state: str) -> dict[str, Any]:
        """Update evidence review state.

        Exceptions are normalized inside the implementation before
        control returns to callers. Control flow branches on the parsed
        state rather than relying on one linear path.

        Args:
            evidence_id: Identifier used to select an existing run or
                record.
            new_state: Primary new state used by this step.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        conn = self._connect()
        try:
            row = conn.execute('SELECT review_state FROM evidence WHERE evidence_id = ?', (evidence_id,)).fetchone()
            if not row:
                return {'ok': False, 'reason': 'evidence_not_found', 'evidence_id': evidence_id}
            current = row['review_state']
            result = validate_transition(current, new_state)
            if not result.ok:
                return {'ok': False, 'reason': result.reason, 'evidence_id': evidence_id, 'current_state': current, 'new_state': new_state}
            conn.execute('UPDATE evidence SET review_state = ? WHERE evidence_id = ?', (new_state, evidence_id))
            conn.commit()
            return {'ok': True, 'evidence_id': evidence_id, 'current_state': current, 'new_state': new_state}
        finally:
            conn.close()

    def list_evidence(self, suite: str | None = None, review_state: str | None = None) -> list[dict[str, Any]]:
        """List evidence.

        Exceptions are normalized inside the implementation before
        control returns to callers. Control flow branches on the parsed
        state rather than relying on one linear path.

        Args:
            suite: Primary suite used by this step.
            review_state: Primary review state used by this step.

        Returns:
            list[dict[str, Any]]:
                Structured payload describing the
                outcome of the operation.
        """
        conn = self._connect()
        try:
            query = 'SELECT * FROM evidence WHERE 1=1'
            params: list[Any] = []
            if suite:
                query += ' AND suite = ?'
                params.append(suite)
            if review_state:
                query += ' AND review_state = ?'
                params.append(review_state)
            query += ' ORDER BY created_at DESC'
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def evidence_for_run(self, run_id: str) -> list[dict[str, Any]]:
        """Evidence for run.

        Exceptions are normalized inside the implementation before
        control returns to callers.

        Args:
            run_id: Identifier used to select an existing run or record.

        Returns:
            list[dict[str, Any]]:
                Structured payload describing the
                outcome of the operation.
        """
        conn = self._connect()
        try:
            rows = conn.execute('SELECT * FROM evidence WHERE run_id = ? ORDER BY created_at ASC', (run_id,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def link(self, src_id: str, dst_id: str, relation: str) -> None:
        """Link the requested operation.

        Exceptions are normalized inside the implementation before
        control returns to callers.

        Args:
            src_id: Identifier used to select an existing run or record.
            dst_id: Identifier used to select an existing run or record.
            relation: Primary relation used by this step.
        """
        conn = self._connect()
        try:
            conn.execute('INSERT INTO links(src_id, dst_id, relation) VALUES (?, ?, ?)', (src_id, dst_id, relation))
            conn.commit()
        finally:
            conn.close()

    def _decode_run_row(self, row) -> dict[str, Any] | None:
        """Decode a suite run row into a JSON-ready dictionary."""
        if not row:
            return None
        payload = dict(row)
        raw = payload.get('run_metadata_json')
        if raw:
            try:
                payload['run_metadata'] = json.loads(raw)
            except json.JSONDecodeError:
                payload['run_metadata'] = {}
        else:
            payload['run_metadata'] = {}
        return payload

    def latest_run(self, suite: str) -> dict[str, Any] | None:
        """Latest run.

        Exceptions are normalized inside the implementation before
        control returns to callers.

        Args:
            suite: Primary suite used by this step.

        Returns:
            dict[str, Any] | None:
                Structured payload describing the
                outcome of the operation.
        """
        conn = self._connect()
        try:
            row = conn.execute('SELECT * FROM suite_runs WHERE suite = ? ORDER BY started_at DESC LIMIT 1', (suite,)).fetchone()
            return self._decode_run_row(row)
        finally:
            conn.close()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Get run.

        Exceptions are normalized inside the implementation before
        control returns to callers.

        Args:
            run_id: Identifier used to select an existing run or record.

        Returns:
            dict[str, Any] | None:
                Structured payload describing the
                outcome of the operation.
        """
        conn = self._connect()
        try:
            row = conn.execute('SELECT * FROM suite_runs WHERE run_id = ?', (run_id,)).fetchone()
            return self._decode_run_row(row)
        finally:
            conn.close()

    def list_runs(self, suite: str) -> list[dict[str, Any]]:
        """List runs.

        Exceptions are normalized inside the implementation before
        control returns to callers.

        Args:
            suite: Primary suite used by this step.

        Returns:
            list[dict[str, Any]]:
                Structured payload describing the
                outcome of the operation.
        """
        conn = self._connect()
        try:
            rows = conn.execute('SELECT * FROM suite_runs WHERE suite = ? ORDER BY started_at DESC', (suite,)).fetchall()
            return [item for item in (self._decode_run_row(r) for r in rows) if item]
        finally:
            conn.close()

    def artifacts_for_run(self, run_id: str) -> list[dict[str, Any]]:
        """Artifacts for run.

        Exceptions are normalized inside the implementation before
        control returns to callers.

        Args:
            run_id: Identifier used to select an existing run or record.

        Returns:
            list[dict[str, Any]]:
                Structured payload describing the
                outcome of the operation.
        """
        conn = self._connect()
        try:
            rows = conn.execute('SELECT * FROM artifacts WHERE run_id = ? ORDER BY created_at ASC', (run_id,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def artifact_payload(self, artifact_id: str) -> Any | None:
        """Artifact payload.

        Exceptions are normalized inside the implementation before
        control returns to callers. Control flow branches on the parsed
        state rather than relying on one linear path.

        Args:
            artifact_id: Identifier used to select an existing run or
                record.

        Returns:
            Any | None:
                Value produced by this callable as ``Any
                | None``.
        """
        conn = self._connect()
        try:
            row = conn.execute('SELECT payload_json FROM artifacts WHERE artifact_id = ?', (artifact_id,)).fetchone()
            if not row or not row['payload_json']:
                return None
            return json.loads(row['payload_json'])
        finally:
            conn.close()

    def compare_runs(self, left_run_id: str, right_run_id: str) -> CompareRunsDelta | None:
        """Compare runs.

        Args:
            left_run_id: Identifier used to select an existing run or
                record.
            right_run_id: Identifier used to select an existing run or
                record.

        Returns:
            CompareRunsDelta | None:
                Value produced by this callable as
                ``CompareRunsDelta | None``.
        """
        return build_compare_runs_delta(self, left_run_id, right_run_id)
