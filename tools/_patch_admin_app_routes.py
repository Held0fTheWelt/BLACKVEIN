"""Replace administration-tool/app.py _register_routes with lazy sibling import."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    p = root / "administration-tool" / "app.py"
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    s = next(i for i, ln in enumerate(lines) if ln.startswith("def _register_routes"))
    e = next(i for i, ln in enumerate(lines) if ln.startswith("def create_app"))
    new_block = '''_route_registration_module = None


def _get_route_registration():
    global _route_registration_module
    if _route_registration_module is None:
        import importlib.util
        from pathlib import Path as _Path

        _rp = _Path(__file__).resolve().parent / "route_registration.py"
        spec = importlib.util.spec_from_file_location(
            "administration_tool_route_registration", _rp
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("route_registration.py missing")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _route_registration_module = mod
    return _route_registration_module


def _register_routes(app):
    """Register routes via sibling module (DS-015 split)."""
    _get_route_registration().register_routes(
        app,
        inject_config=inject_config,
        backend_origin_fn=_backend_origin,
    )


'''
    out = lines[:s] + [new_block] + lines[e:]
    p.write_text("".join(out), encoding="utf-8")
    print("ok", s, e)


if __name__ == "__main__":
    main()
