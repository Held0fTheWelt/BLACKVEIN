"""One-off: build administration-tool/route_registration.py from app.py (DS-015)."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    app_path = root / "administration-tool" / "app.py"
    lines = app_path.read_text(encoding="utf-8").splitlines(keepends=True)

    idx_proxy = next(i for i, ln in enumerate(lines) if ln.startswith("PROXY_ALLOWLIST_PREFIXES"))
    idx_inject = next(i for i, ln in enumerate(lines) if ln.startswith("def inject_config"))
    idx_reg_start = next(i for i, ln in enumerate(lines) if ln.startswith("def _register_routes"))
    idx_create = next(i for i, ln in enumerate(lines) if ln.startswith("def create_app"))

    proxy_block = "".join(lines[idx_proxy:idx_inject])
    reg_inner = "".join(lines[idx_reg_start + 1 : idx_create])

    hdr = '''"""Flask routes, proxy, and security handlers for administration-tool."""

from __future__ import annotations

from typing import Any, Callable

from flask import Flask, request, render_template, Response, redirect, url_for
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


'''
    sig = """def register_routes(
    app: Flask,
    *,
    inject_config: Callable[[], dict[str, Any]],
    backend_origin_fn: Callable[[], str | None],
) -> None:
"""

    body_lines = reg_inner.splitlines(keepends=True)
    # Drop _register_routes docstring (first triple-quoted block)
    i = 0
    while i < len(body_lines) and not body_lines[i].strip():
        i += 1
    if i < len(body_lines) and '"""' in body_lines[i]:
        i += 1
        while i < len(body_lines) and '"""' not in body_lines[i]:
            i += 1
        if i < len(body_lines):
            i += 1
    while i < len(body_lines) and not body_lines[i].strip():
        i += 1

    dedented: list[str] = []
    for ln in body_lines[i:]:
        if ln.startswith("    "):
            dedented.append(ln[4:])
        else:
            dedented.append(ln)

    inner = "".join(dedented)
    inner = inner.replace("return inject_config()", "return inject_config()", 1)
    inner = inner.replace("origin = _backend_origin()", "origin = backend_origin_fn()", 1)

    out = root / "administration-tool" / "route_registration.py"
    out.write_text(hdr + proxy_block + "\n" + sig + inner, encoding="utf-8")
    print("ok", out)


if __name__ == "__main__":
    main()
