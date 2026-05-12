"""JSON persistence for the runtime RAG corpus (DS-003 stage 7)."""

from __future__ import annotations

import errno
import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_stack.rag_constants import INDEX_VERSION

logger = logging.getLogger(__name__)

_ATOMIC_REPLACE_MAX_ATTEMPTS = 6
_ATOMIC_REPLACE_INITIAL_BACKOFF_SECONDS = 0.05
_TRANSIENT_REPLACE_ERRNOS = {
    errno.EACCES,
    errno.EPERM,
    getattr(errno, "EBUSY", 16),
    getattr(errno, "ETXTBSY", 26),
}
_TRANSIENT_REPLACE_WINERRORS = {5, 32, 33}


def _is_transient_atomic_replace_error(exc: OSError) -> bool:
    """Return whether ``os.replace`` likely hit a transient file lock."""
    if isinstance(exc, PermissionError):
        return True
    exc_errno = getattr(exc, "errno", None)
    if exc_errno in _TRANSIENT_REPLACE_ERRNOS:
        return True
    winerror = getattr(exc, "winerror", None)
    return winerror in _TRANSIENT_REPLACE_WINERRORS


def _replace_cache_file_with_retries(source: str, destination: Path) -> bool:
    """Atomically replace a cache file, tolerating transient Windows/WSL locks."""
    delay = _ATOMIC_REPLACE_INITIAL_BACKOFF_SECONDS
    last_error: OSError | None = None
    for attempt in range(1, _ATOMIC_REPLACE_MAX_ATTEMPTS + 1):
        try:
            os.replace(source, destination)
            return True
        except OSError as exc:
            if not _is_transient_atomic_replace_error(exc):
                raise
            last_error = exc
            if attempt >= _ATOMIC_REPLACE_MAX_ATTEMPTS:
                break
            time.sleep(delay)
            delay *= 2
    logger.warning(
        "Runtime RAG corpus cache replace remained locked after %s attempts; "
        "continuing with in-memory corpus and leaving existing cache unchanged: %s",
        _ATOMIC_REPLACE_MAX_ATTEMPTS,
        last_error,
    )
    return False


@dataclass(slots=True)
class PersistentRagStore:
    """``PersistentRagStore`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    storage_path: Path

    def load(self, *, expected_fingerprint: str) -> Any:
        """Describe what ``load`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            expected_fingerprint: ``expected_fingerprint`` (str); meaning follows the type and call sites.
        
        Returns:
            Any:
                Returns a value of type ``Any``; see the function body for structure, error paths, and sentinels.
        """
        if not self.storage_path.exists():
            return None
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        if str(payload.get("index_version", "")) != INDEX_VERSION:
            return None
        if str(payload.get("corpus_fingerprint", "")) != expected_fingerprint:
            return None
        from ai_stack.rag_corpus import InMemoryRetrievalCorpus

        corpus = InMemoryRetrievalCorpus.from_dict(payload)
        corpus.storage_path = str(self.storage_path)
        return corpus

    def save(self, corpus: Any) -> None:
        """Describe what ``save`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            corpus: ``corpus`` (Any); meaning follows the type and call sites.
        """
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = corpus.to_dict()
        payload["storage_path"] = str(self.storage_path)
        serialized = json.dumps(payload, ensure_ascii=True, indent=2)
        tmp_name: str | None = None
        replace_committed = False
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=self.storage_path.parent,
                prefix=".rag_",
                suffix=".json",
            ) as tmp:
                tmp.write(serialized)
                tmp_name = tmp.name
            if tmp_name:
                replace_committed = _replace_cache_file_with_retries(tmp_name, self.storage_path)
        except Exception:
            if tmp_name:
                try:
                    Path(tmp_name).unlink(missing_ok=True)
                except OSError:
                    pass
            raise
        finally:
            if tmp_name and not replace_committed:
                try:
                    Path(tmp_name).unlink(missing_ok=True)
                except OSError:
                    pass
