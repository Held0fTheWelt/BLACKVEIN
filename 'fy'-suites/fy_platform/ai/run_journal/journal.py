from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now, workspace_root


class RunJournal:
    def __init__(self, root: Path | None = None) -> None:
        self.root = workspace_root(root)

    def path_for(self, suite: str, run_id: str) -> Path:
        path = self.root / '.fydata' / 'journal' / suite / f'{run_id}.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def append(self, suite: str, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        line = {'ts': utc_now(), 'event_type': event_type, 'payload': payload}
        path = self.path_for(suite, run_id)
        with path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + '\n')

    def read(self, suite: str, run_id: str) -> list[dict[str, Any]]:
        path = self.path_for(suite, run_id)
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
