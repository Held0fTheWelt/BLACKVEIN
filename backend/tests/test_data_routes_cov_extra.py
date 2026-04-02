"""Extra coverage for app.api.v1.data_routes."""
import pytest

from app.services import data_import_service


def test_get_user_id_for_rate_limit_jwt_raises(app, monkeypatch):
    from app.api.v1 import data_routes

    def boom():
        raise RuntimeError("jwt down")

    monkeypatch.setattr(data_routes, "get_jwt_identity", boom)
    with app.test_request_context("/", environ_base={"REMOTE_ADDR": "192.168.1.9"}):
        assert data_routes._get_user_id_for_rate_limit() == "192.168.1.9"


def test_get_user_id_for_rate_limit_uses_identity(app, monkeypatch):
    from app.api.v1 import data_routes

    monkeypatch.setattr(data_routes, "get_jwt_identity", lambda: 42)
    with app.test_request_context("/"):
        assert data_routes._get_user_id_for_rate_limit() == "42"


def test_get_user_id_for_rate_limit_falsy_identity_uses_remote_addr(app, monkeypatch):
    from app.api.v1 import data_routes

    monkeypatch.setattr(data_routes, "get_jwt_identity", lambda: None)
    with app.test_request_context("/", environ_base={"REMOTE_ADDR": "10.11.12.13"}):
        assert data_routes._get_user_id_for_rate_limit() == "10.11.12.13"


def test_export_encrypt_value_error(client, admin_headers, monkeypatch):
    from app.api.v1 import data_routes

    def bad_encrypt(payload, password):
        raise ValueError("bad")

    monkeypatch.setattr(data_routes.data_export_service, "export_full", lambda: {"metadata": {}, "data": {}})
    monkeypatch.setattr(data_routes.data_export_service, "encrypt_export", bad_encrypt)
    resp = client.post(
        "/api/v1/data/export",
        json={"scope": "full", "encrypt": True, "password": "secret"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_decrypt_type_error(client, admin_headers, monkeypatch):
    from app.api.v1 import data_routes

    def bad_decrypt(payload, password):
        raise TypeError("bad")

    monkeypatch.setattr(data_routes.data_export_service, "decrypt_export", bad_decrypt)
    body = {
        "password": "p",
        "encrypted_data": "x",
        "iv": "y",
        "salt": "z",
    }
    resp = client.post(
        "/api/v1/data/export/decrypt",
        json=body,
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_import_execute_import_error(client, super_admin_headers, monkeypatch):
    from app.api.v1 import data_routes

    class DummyPre:
        ok = True
        issues = []
        metadata = {}

    monkeypatch.setattr(
        data_routes.data_import_service,
        "preflight_validate_payload",
        lambda payload: DummyPre(),
    )

    def boom(payload):
        raise data_import_service.ImportError("fail")

    monkeypatch.setattr(data_routes.data_import_service, "execute_import", boom)
    payload = {"metadata": {"format_version": 1, "schema_revision": "x"}, "data": {"tables": {}}}
    resp = client.post(
        "/api/v1/data/import/execute",
        json=payload,
        headers=super_admin_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["ok"] is False


def test_export_data_forbidden_non_admin(client, auth_headers):
    resp = client.post("/api/v1/data/export", json={"scope": "full"}, headers=auth_headers)
    assert resp.status_code == 403


def test_decrypt_export_forbidden_non_admin(client, auth_headers):
    resp = client.post(
        "/api/v1/data/export/decrypt",
        json={"password": "p", "encrypted_data": "x", "iv": "y", "salt": "z"},
        headers=auth_headers,
    )
    assert resp.status_code == 403


def test_import_preflight_forbidden_non_admin(client, auth_headers):
    resp = client.post(
        "/api/v1/data/import/preflight",
        json={"metadata": {"format_version": 1}, "data": {}},
        headers=auth_headers,
    )
    assert resp.status_code == 403


def test_import_execute_success(client, super_admin_headers, monkeypatch):
    from app.api.v1 import data_routes

    class Issue:
        code = "OK"
        message = "done"
        table = None

    class Result:
        issues = [Issue()]
        metadata = {"imported": True}

    class DummyPre:
        ok = True
        issues = []
        metadata = {}

    monkeypatch.setattr(
        data_routes.data_import_service,
        "preflight_validate_payload",
        lambda _p: DummyPre(),
    )
    monkeypatch.setattr(
        data_routes.data_import_service,
        "execute_import",
        lambda _p: Result(),
    )
    payload = {"metadata": {"format_version": 1, "schema_revision": "test"}, "data": {"tables": {}}}
    resp = client.post(
        "/api/v1/data/import/execute",
        json=payload,
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["issues"][0]["code"] == "OK"
    assert body["metadata"]["imported"] is True
