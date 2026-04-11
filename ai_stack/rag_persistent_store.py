"""JSON persistence for the runtime RAG corpus (DS-003 stage 7)."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_stack.rag_constants import INDEX_VERSION


@dataclass(slots=True)
class PersistentRagStore:
    storage_path: Path

    def load(self, *, expected_fingerprint: str) -> Any:
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
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = corpus.to_dict()
        payload["storage_path"] = str(self.storage_path)
        serialized = json.dumps(payload, ensure_ascii=True, indent=2)
        tmp_name: str | None = None
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
                os.replace(tmp_name, self.storage_path)
        except Exception:
            if tmp_name:
                try:
                    Path(tmp_name).unlink(missing_ok=True)
                except OSError:
                    pass
            raise
