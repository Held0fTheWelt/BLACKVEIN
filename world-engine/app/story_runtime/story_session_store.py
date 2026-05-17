"""Durable JSON persistence payloads for authored story sessions (audit F-H1).

Stores plain JSON dicts on disk (one file per session id). Serialization of
``StorySession`` lives in ``manager.py`` to avoid circular imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.runtime.json_at_rest import JsonAtRestCodec, associated_data


class JsonStorySessionStore:
    """Atomic JSON file per session id (same pattern as ``JsonRunStore``)."""

    backend_name = "json"

    def __init__(self, root: Path, *, codec: JsonAtRestCodec | None = None) -> None:
        self.root = root
        self.codec = codec or JsonAtRestCodec.plain()
        self.backend_name = self.codec.backend_name("json")
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, session_id: str) -> Path:
        return self.codec.path_for(self.root, session_id)

    def _aad(self, session_id: str) -> bytes:
        return associated_data("story-session", session_id)

    def save(self, session_id: str, payload: dict[str, Any]) -> None:
        destination = self.path_for(session_id)
        temp_path = destination.with_suffix(destination.suffix + ".tmp")
        temp_path.write_text(self.codec.dumps(payload, aad=self._aad(session_id)), encoding="utf-8")
        temp_path.replace(destination)

    def load_all_raw(self) -> dict[str, dict[str, Any]]:
        """Load every ``*.json`` snapshot in root (skips corrupt files)."""
        out: dict[str, dict[str, Any]] = {}
        for path in sorted(self.root.glob(f"*{self.codec.extension}")):
            try:
                session_id = path.name.removesuffix(self.codec.extension)
                data = self.codec.loads(path.read_text(encoding="utf-8"), aad=self._aad(session_id))
                if isinstance(data, dict) and isinstance(data.get("session_id"), str):
                    out[data["session_id"]] = data
            except Exception:
                continue
        return out

    def delete(self, session_id: str) -> None:
        for suffix in (".json", ".json.enc"):
            path = self.root / f"{session_id}{suffix}"
            if path.exists():
                path.unlink()

    def describe(self) -> dict[str, str]:
        return {
            "backend": self.backend_name,
            "root": str(self.root),
            "encrypted_at_rest": "yes" if self.codec.encrypted else "no",
        }
