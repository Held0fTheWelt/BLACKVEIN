"""Ad-hoc MCP probe: speak JSON-RPC to the stdio launcher and dump tool schemas.

Used once-off to verify that opening-quality / judge / projection tools are
registered and to inspect their input schemas before calling them.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LAUNCHER = REPO / "scripts" / "wos_mcp_stdio_launcher.py"

TARGET_TOOLS = {
    "run_projection_tests",
    "summarize_live_opening_matrix",
    "summarize_opening_judge_scores",
    "fetch_langfuse_trace_scores",
    "build_opening_quality_context",
}


def main() -> int:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    payload_lines = [
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
    ]
    payload = "\n".join(payload_lines) + "\n"
    r = subprocess.run(
        [sys.executable, str(LAUNCHER)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=tempfile.gettempdir(),
        env=env,
    )
    if r.returncode != 0:
        print("FAIL rc=", r.returncode, file=sys.stderr)
        print(r.stderr[-2000:], file=sys.stderr)
        return 1

    found: dict[str, dict] = {}
    for raw in r.stdout.splitlines():
        s = raw.strip()
        if not s:
            continue
        try:
            msg = json.loads(s)
        except json.JSONDecodeError:
            continue
        if msg.get("id") != 2:
            continue
        for tool in msg.get("result", {}).get("tools", []):
            name = tool.get("name")
            if name in TARGET_TOOLS:
                found[name] = tool

    for name in sorted(TARGET_TOOLS):
        tool = found.get(name)
        if not tool:
            print(f"MISSING: {name}")
            continue
        schema = tool.get("inputSchema") or tool.get("input_schema") or {}
        required = schema.get("required") or []
        props = list((schema.get("properties") or {}).keys())
        print(f"OK     : {name}  required={required} props={props}")
    return 0 if len(found) == len(TARGET_TOOLS) else 2


if __name__ == "__main__":
    raise SystemExit(main())
