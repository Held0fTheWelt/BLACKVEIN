"""Smoke test: MCP stdio launcher works with alien cwd and without PYTHONPATH."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LAUNCHER = REPO / "scripts" / "wos_mcp_stdio_launcher.py"


def main() -> int:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    payload = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
    r = subprocess.run(
        [sys.executable, str(LAUNCHER)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=90,
        cwd=tempfile.gettempdir(),
        env=env,
    )
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        print("FAIL rc=", r.returncode, file=sys.stderr)
        print(r.stderr, file=sys.stderr)
        return 1
    if '"result"' not in out and "protocolVersion" not in out:
        print("FAIL unexpected stdout:", out[:800], file=sys.stderr)
        print("stderr:", r.stderr[-800:], file=sys.stderr)
        return 2
    print("OK:", out[:240])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
