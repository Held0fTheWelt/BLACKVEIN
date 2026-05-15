"""Durable JSON persistence for callback-web records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonCallbackWebStore:
    """Atomic JSON file per callback web id."""

    backend_name = "json"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, callback_web_id: str) -> Path:
        return self.root / f"{callback_web_id}.json"

    def save(self, callback_web_id: str, payload: dict[str, Any]) -> None:
        destination = self.path_for(callback_web_id)
        temp_path = destination.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(destination)

    def load(self, callback_web_id: str) -> dict[str, Any]:
        path = self.path_for(callback_web_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("callback_web_payload_not_object")
        return data

    def load_all_raw(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for path in sorted(self.root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("callback_web_id"), str):
                    out[data["callback_web_id"]] = data
            except Exception:
                continue
        return out

    def load_for_session(self, session_id: str) -> list[dict[str, Any]]:
        rows = [
            payload
            for payload in self.load_all_raw().values()
            if isinstance(payload, dict) and payload.get("story_session_id") == session_id
        ]
        rows.sort(key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), reverse=True)
        return rows

    def delete(self, callback_web_id: str) -> None:
        path = self.path_for(callback_web_id)
        if path.exists():
            path.unlink()

    def describe(self) -> dict[str, str]:
        return {"backend": self.backend_name, "root": str(self.root)}
