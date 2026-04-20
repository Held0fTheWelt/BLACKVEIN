"""Transitional: persistence backends for in-process ``RuntimeManager`` (tests / local runs).

These stores back the **deprecated** backend-local experience runtime, not the World
Engine authoritative store.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol

from sqlalchemy import Boolean, Column, DateTime, MetaData, String, Table, Text, create_engine, delete, insert, select
from sqlalchemy.engine import Engine

from app.runtime.models import RuntimeInstance


class RunStore(Protocol):
    backend_name: str

    def save(self, instance: RuntimeInstance) -> None: ...

    def load_all(self) -> list[RuntimeInstance]: ...

    def describe(self) -> dict[str, str]: ...


class JsonRunStore:
    backend_name = "json"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, run_id: str) -> Path:
        # Validate and sanitize the run_id to prevent path traversal
        if not re.match(r'^[a-zA-Z0-9_-]+$', run_id):
            raise ValueError("Invalid run_id")
        return self.root / f"{run_id}.json"

    def save(self, instance: RuntimeInstance) -> None:
        destination = self.path_for(instance.id)
        temp_path = destination.with_suffix(".json.tmp")
        temp_path.write_text(instance.model_dump_json(indent=2), encoding="utf-8")
        temp_path.replace(destination)

    def load_all(self) -> list[RuntimeInstance]:
        instances: list[RuntimeInstance] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                instances.append(RuntimeInstance.model_validate(data))
            except Exception:
                continue
        return instances

    def describe(self) -> dict[str, str]:
        return {"backend": self.backend_name, "root": str(self.root)}


class SqlAlchemyRunStore:
    backend_name = "sqlalchemy"

    def __init__(self, url: str) -> None:
        self.url = url
        self.engine: Engine = create_engine(url, future=True)
        self.metadata = MetaData()
        self.runs = Table(
            "runtime_runs",
            self.metadata,
            Column("run_id", String(64), primary_key=True),
            Column("template_id", String(120), nullable=False),
            Column("kind", String(40), nullable=False),
            Column("join_policy", String(40), nullable=False),
            Column("status", String(40), nullable=False),
            Column("persistent", Boolean, nullable=False, default=False),
            Column("owner_account_id", String(120), nullable=True),
            Column("created_at", DateTime(timezone=True), nullable=False),
            Column("updated_at", DateTime(timezone=True), nullable=False),
            Column("payload_json", Text, nullable=False),
        )
        self.metadata.create_all(self.engine)

    def save(self, instance: RuntimeInstance) -> None:
        payload_json = instance.model_dump_json()
        with self.engine.begin() as conn:
            conn.execute(delete(self.runs).where(self.runs.c.run_id == instance.id))
            conn.execute(
                insert(self.runs).values(
                    run_id=instance.id,
                    template_id=instance.template_id,
                    kind=instance.kind.value,
                    join_policy=instance.join_policy.value,
                    status=instance.status.value,
                    persistent=instance.persistent,
                    owner_account_id=instance.owner_account_id,
                    created_at=instance.created_at,
                    updated_at=instance.updated_at,
                    payload_json=payload_json,
                )
            )

    def load_all(self) -> list[RuntimeInstance]:
        instances: list[RuntimeInstance] = []
        with self.engine.begin() as conn:
            rows = conn.execute(select(self.runs.c.payload_json).order_by(self.runs.c.updated_at.asc())).fetchall()
        for row in rows:
            try:
                instances.append(RuntimeInstance.model_validate(json.loads(row.payload_json)))
            except Exception:
                continue
        return instances

    def describe(self) -> dict[str, str]:
        return {"backend": self.backend_name, "url": self.url}


def build_run_store(*, root: Path, backend: str, url: str | None = None) -> RunStore:
    backend_name = backend.strip().lower()
    if backend_name == "json":
        return JsonRunStore(root)
    if backend_name in {"sqlalchemy", "postgres", "postgresql"}:
        if not url:
            raise ValueError("RUN_STORE_URL is required when using SQL-backed runtime persistence.")
        return SqlAlchemyRunStore(url)
    raise ValueError(f"Unsupported run store backend: {backend}")
