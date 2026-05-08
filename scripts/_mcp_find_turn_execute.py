"""One-shot probe: list recent Langfuse traces via the MCP server and pick
the most recent ``world-engine.turn.execute`` and ``world-engine.session.create``
trace_ids. Used by the opening-quality assessment to cover both Turn 0
(opening) and Turn 1+ (continuation) expectations.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LAUNCHER = REPO / "scripts" / "wos_mcp_stdio_launcher.py"


def _env() -> dict[str, str]:
    e = os.environ.copy()
    e.setdefault("PYTHONIOENCODING", "utf-8")
    e.setdefault("BACKEND_BASE_URL", "http://127.0.0.1:8000")
    e.setdefault("WOS_MCP_OPERATING_PROFILE", "healthy")
    e.setdefault("LANGFUSE_MCP_ENABLED", "1")
    return e


def main() -> int:
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "query_langfuse_traces",
                "arguments": {"limit": 100},
            },
        },
    ]
    inp = "".join(json.dumps(r) + "\n" for r in reqs)
    proc = subprocess.run(
        [sys.executable, "-u", str(LAUNCHER)],
        input=inp,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env(),
        timeout=90,
    )
    payload: dict | None = None
    for raw in proc.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            resp = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if resp.get("id") == 2:
            content = (resp.get("result") or {}).get("content")
            if isinstance(content, list) and content:
                first = content[0]
                if isinstance(first, dict):
                    text = first.get("text")
                    if isinstance(text, str):
                        try:
                            payload = json.loads(text)
                        except json.JSONDecodeError:
                            print("response.text not JSON:", text[:200])
                            return 1
            break
    if not isinstance(payload, dict):
        print("no payload found in stdout")
        print("STDOUT:")
        print(proc.stdout[:2000])
        print("STDERR:")
        print(proc.stderr[:2000])
        return 1
    print("payload top-level keys:", sorted(payload.keys()))
    traces = (
        payload.get("traces")
        or payload.get("rows")
        or payload.get("items")
        or payload.get("data")
        or []
    )
    print(f"total trace rows: {len(traces)}")
    if traces:
        sample = traces[0]
        if isinstance(sample, dict):
            print("first row keys:", sorted(sample.keys()))
            print("first row preview:", json.dumps({k: sample.get(k) for k in list(sample.keys())[:8]}, ensure_ascii=False)[:500])

    def _id(item: dict) -> str | None:
        for k in ("id", "trace_id", "traceId"):
            v = item.get(k)
            if isinstance(v, str) and v:
                return v
        return None

    turn_execute = [t for t in traces if isinstance(t, dict) and "turn.execute" in str(t.get("name", "")).lower()]
    session_create = [t for t in traces if isinstance(t, dict) and "session.create" in str(t.get("name", "")).lower()]
    print(f"turn.execute candidates: {len(turn_execute)}")
    print(f"session.create candidates: {len(session_create)}")
    if turn_execute:
        for t in turn_execute[:3]:
            print(" turn.execute:", _id(t), "@", t.get("createdAt") or t.get("timestamp") or t.get("start_time"))
    if session_create:
        for t in session_create[:3]:
            print(" session.create:", _id(t), "@", t.get("createdAt") or t.get("timestamp") or t.get("start_time"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
