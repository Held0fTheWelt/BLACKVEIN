from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from app.runtime.models import RuntimeInstance


class RunStore(ABC):
    @abstractmethod
    def load_all(self) -> list[RuntimeInstance]:
        raise NotImplementedError

    @abstractmethod
    def save(self, instance: RuntimeInstance) -> None:
        raise NotImplementedError


class JsonRunStore(RunStore):
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, run_id: str) -> Path:
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
