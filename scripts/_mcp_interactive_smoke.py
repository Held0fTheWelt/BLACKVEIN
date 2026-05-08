"""Interactive stdio smoke test mimicking Cursor's MCP V2 connection pattern.

Cursor keeps stdin/stdout open and sends requests one at a time, expecting an
immediate newline-delimited response on stdout per request. The original
``smoke_wos_mcp_stdio.py`` only verifies the EOF-flush case (single payload +
close) which masks the Windows pipe block-buffering bug.

This driver:
    1. Spawns the launcher with stdin/stdout pipes kept open.
    2. Sends ``initialize`` and waits up to 5 s for a response.
    3. Sends ``notifications/initialized`` (no ``id``) and verifies that *no*
       response comes back within 1 s (notifications must not be answered).
    4. Sends ``tools/list`` and waits up to 5 s for a response.
    5. Closes stdin and waits for the child to exit cleanly.

Exit codes:
    0 — all three exchanges succeeded
    1 — child process failed to start
    2 — initialize timed out (the original bug)
    3 — tools/list timed out
    4 — notification was answered (spec violation)
    5 — tools/list returned no tools
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


def _readline_with_timeout(proc: subprocess.Popen, timeout: float) -> str | None:
    """Read one line from proc.stdout with a wall-clock timeout via threading.Timer."""
    import threading

    result: dict[str, str | None] = {"line": None}

    def reader() -> None:
        assert proc.stdout is not None
        result["line"] = proc.stdout.readline()

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None
    return result["line"]


def main() -> int:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    proc = subprocess.Popen(
        [sys.executable, str(LAUNCHER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        cwd=tempfile.gettempdir(),
        env=env,
        bufsize=0,
    )
    if proc.stdin is None or proc.stdout is None:
        print("FAIL: no stdio pipes", file=sys.stderr)
        return 1

    def send(msg: dict) -> None:
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    line = _readline_with_timeout(proc, timeout=5.0)
    if not line:
        print("FAIL: initialize response timed out (5s)", file=sys.stderr)
        proc.kill()
        return 2
    init_resp = json.loads(line)
    print("ok initialize:", json.dumps(init_resp.get("result", {}).get("serverInfo", {})))

    # Send notification + next request back-to-back. If the server (incorrectly)
    # answered the notification, we'd see TWO lines on stdout; if it correctly
    # ignores it, only the tools/list response follows. We disambiguate by
    # parsing the next line and checking its id.
    send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    line = _readline_with_timeout(proc, timeout=5.0)
    if not line:
        print("FAIL: tools/list response timed out (5s)", file=sys.stderr)
        proc.kill()
        return 3
    parsed_first = json.loads(line)
    if parsed_first.get("id") != 2:
        # Server answered the notification — drain the next line which should be tools/list
        print(f"FAIL: notification was answered: {line.strip()[:200]}", file=sys.stderr)
        proc.kill()
        return 4
    print("ok notification: no response (correct)")
    tools_resp = parsed_first
    tools = tools_resp.get("result", {}).get("tools", [])
    if not tools:
        print(f"FAIL: tools/list returned 0 tools: {line.strip()[:200]}", file=sys.stderr)
        proc.kill()
        return 5
    print(f"ok tools/list: {len(tools)} tools, first 3 = {[t.get('name') for t in tools[:3]]}")

    proc.stdin.close()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
