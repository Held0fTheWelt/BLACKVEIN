"""Tests for wiki API: GET and PUT /api/v1/wiki (moderator/admin only)."""
import pytest


def test_wiki_get_without_auth_returns_401(client):
    """GET /api/v1/wiki without Authorization returns 401."""
    response = client.get("/api/v1/wiki")
    assert response.status_code == 401


def test_wiki_get_with_user_role_returns_403(client, auth_headers):
    """GET /api/v1/wiki with JWT for plain user returns 403."""
    response = client.get("/api/v1/wiki", headers=auth_headers)
    assert response.status_code == 403


def test_wiki_get_with_moderator_returns_200(client, moderator_headers, tmp_path, monkeypatch):
    """GET /api/v1/wiki with moderator JWT returns 200 and content/html."""
    wiki_file = tmp_path / "wiki.md"
    wiki_file.write_text("# Hello\n\nWiki content.", encoding="utf-8")

    from app.api.v1 import wiki_routes
    def fake_path():
        return wiki_file
    monkeypatch.setattr(wiki_routes, "_wiki_path", fake_path)

    response = client.get("/api/v1/wiki", headers=moderator_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "content" in data
    assert data["content"] == "# Hello\n\nWiki content."
    assert "html" in data
    assert "Hello" in (data["html"] or "")


def test_wiki_get_missing_file_returns_empty_content(client, moderator_headers, tmp_path, monkeypatch):
    """GET /api/v1/wiki when file does not exist returns 200 with empty content."""
    wiki_file = tmp_path / "wiki.md"
    assert not wiki_file.exists()

    from app.api.v1 import wiki_routes
    def fake_path():
        return wiki_file
    monkeypatch.setattr(wiki_routes, "_wiki_path", fake_path)

    response = client.get("/api/v1/wiki", headers=moderator_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("content") == ""
    assert data.get("html") is None


def test_wiki_put_without_auth_returns_401(client):
    """PUT /api/v1/wiki without Authorization returns 401."""
    response = client.put(
        "/api/v1/wiki",
        json={"content": "# Updated"},
        content_type="application/json",
    )
    assert response.status_code == 401


def test_wiki_put_with_moderator_writes_file(client, moderator_headers, tmp_path, monkeypatch):
    """PUT /api/v1/wiki with moderator JWT writes content and returns 200."""
    wiki_file = tmp_path / "wiki.md"
    wiki_file.parent.mkdir(parents=True, exist_ok=True)
    wiki_file.write_text("old", encoding="utf-8")

    from app.api.v1 import wiki_routes
    def fake_path():
        return wiki_file
    monkeypatch.setattr(wiki_routes, "_wiki_path", fake_path)

    response = client.put(
        "/api/v1/wiki",
        json={"content": "# New content\n\nUpdated."},
        content_type="application/json",
        headers=moderator_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("message") == "Updated"
    assert data.get("content") == "# New content\n\nUpdated."
    assert wiki_file.read_text(encoding="utf-8") == "# New content\n\nUpdated."


def test_wiki_put_without_body_returns_400(client, moderator_headers, tmp_path, monkeypatch):
    """PUT /api/v1/wiki without JSON body returns 400."""
    wiki_file = tmp_path / "wiki.md"
    from app.api.v1 import wiki_routes
    monkeypatch.setattr(wiki_routes, "_wiki_path", lambda: wiki_file)

    response = client.put("/api/v1/wiki", headers=moderator_headers)
    assert response.status_code == 400
    assert response.get_json().get("error")


def test_wiki_put_without_content_key_returns_400(client, moderator_headers, tmp_path, monkeypatch):
    """PUT /api/v1/wiki with body missing 'content' returns 400."""
    wiki_file = tmp_path / "wiki.md"
    from app.api.v1 import wiki_routes
    monkeypatch.setattr(wiki_routes, "_wiki_path", lambda: wiki_file)

    response = client.put(
        "/api/v1/wiki",
        json={},
        content_type="application/json",
        headers=moderator_headers,
    )
    assert response.status_code == 400
    assert "content" in (response.get_json().get("error") or "").lower()
