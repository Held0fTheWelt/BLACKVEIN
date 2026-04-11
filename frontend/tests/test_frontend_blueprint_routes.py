"""Regression net: every player blueprint rule stays registered (split across routes*.py)."""

from __future__ import annotations

from app.frontend_blueprint import frontend_bp


def _rule_paths(app):
    return sorted(
        {r.rule for r in app.url_map.iter_rules() if r.endpoint.startswith("frontend.")}
    )


def test_frontend_blueprint_registers_expected_routes(app):
    paths = _rule_paths(app)
    assert "/" in paths
    assert "/login" in paths
    assert "/play" in paths
    assert "/play/<session_id>" in paths
    assert "/play/<session_id>/execute" in paths
    assert "/api/v1/<path:subpath>" in paths
    # Split module still attaches to the same blueprint object
    assert frontend_bp.name == "frontend"
