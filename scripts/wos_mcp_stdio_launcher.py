"""WoS MCP stdio entrypoint for Cursor and other MCP hosts.

Cursor often starts MCP without a reliable workspace cwd or PYTHONPATH, which breaks
``python -m tools.mcp_server.server`` (``No module named 'tools'``). This script
resolves the repository root from its own path and prepends it to ``sys.path`` so
imports work regardless of cwd or environment.

It also forces ``sys.stdin`` / ``sys.stdout`` into line-buffered mode with
write-through. On Windows, Python defaults to block-buffered stdout when stdout
is a pipe (~8 KB buffer). MCP hosts like Cursor send a request, then wait for a
newline-delimited JSON response *immediately*; if the response sits in the
in-process buffer, Cursor hits its 60-second request timeout and aborts the
connection. Server code itself also calls ``sys.stdout.flush()`` after each
response, but reconfiguring here is a belt-and-suspenders guarantee that holds
even if a future entrypoint forgets the explicit flush.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_REPO = str(_ROOT)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)
os.environ.setdefault("REPO_ROOT", _REPO)

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", line_buffering=True, write_through=True)
    except (AttributeError, ValueError, OSError):
        pass

runpy.run_module("tools.mcp_server.server", run_name="__main__")
