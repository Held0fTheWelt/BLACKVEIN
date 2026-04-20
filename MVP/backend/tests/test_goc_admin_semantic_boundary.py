"""Admin / governance API must not expose semantic authoring shortcuts (gate G6)."""

from __future__ import annotations


def test_ai_stack_governance_routes_reject_non_get_methods(client, moderator_headers) -> None:
    """Governance evidence routes are read-only; POST must not succeed as a mutation path."""
    r_post = client.post(
        "/api/v1/admin/ai-stack/session-evidence/test-session",
        json={"semantic_patch": {"forbidden": True}},
        headers=moderator_headers,
    )
    assert r_post.status_code in {405, 404}

    r_put = client.put(
        "/api/v1/admin/ai-stack/improvement-packages",
        json={},
        headers=moderator_headers,
    )
    assert r_put.status_code in {405, 404}


def test_no_canonical_module_write_route_registered(client, moderator_headers) -> None:
    """Sanity: hypothetical canonical-module writer is not mounted under admin AI-stack."""
    r = client.post(
        "/api/v1/admin/ai-stack/canonical-module/god_of_carnage/semantic-overwrite",
        json={"labels": ["forked_truth"]},
        headers=moderator_headers,
    )
    assert r.status_code == 404


def test_admin_ai_stack_release_readiness_rejects_post(client, moderator_headers) -> None:
    r = client.post(
        "/api/v1/admin/ai-stack/release-readiness",
        json={"semantic_patch": True},
        headers=moderator_headers,
    )
    assert r.status_code in {405, 404}


def test_admin_ai_stack_closure_cockpit_rejects_post(client, moderator_headers) -> None:
    r = client.post(
        "/api/v1/admin/ai-stack/closure-cockpit",
        json={"semantic_patch": True},
        headers=moderator_headers,
    )
    assert r.status_code in {405, 404}


def test_admin_ai_stack_inspector_extended_routes_reject_post(client, moderator_headers) -> None:
    for path in (
        "/api/v1/admin/ai-stack/inspector/timeline/test-session",
        "/api/v1/admin/ai-stack/inspector/comparison/test-session",
        "/api/v1/admin/ai-stack/inspector/coverage-health/test-session",
        "/api/v1/admin/ai-stack/inspector/provenance-raw/test-session",
    ):
        r = client.post(path, json={"semantic_patch": True}, headers=moderator_headers)
        assert r.status_code in {405, 404}


def test_game_admin_no_hypothetical_semantic_registry_write_route(client, moderator_headers) -> None:
    """Control-plane routes exist; semantic registry mutation is not an admin POST surface."""
    r = client.post(
        "/api/v1/game-admin/runtime/model-routing-registry",
        json={"task_kind": "injected_meaning"},
        headers=moderator_headers,
    )
    assert r.status_code == 404
