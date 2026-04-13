from __future__ import annotations

import base64

import pytest

from app.governance.errors import GovernanceError
from app.services.governance_secret_crypto_service import _load_kek


def test_load_kek_accepts_unpadded_base64(monkeypatch) -> None:
    raw = base64.b64encode(b"a" * 32).decode("utf-8").rstrip("=")
    monkeypatch.setenv("SECRETS_KEK", raw)
    assert _load_kek() == b"a" * 32


def test_load_kek_accepts_urlsafe_base64(monkeypatch) -> None:
    raw = base64.urlsafe_b64encode(b"b" * 32).decode("utf-8").rstrip("=")
    monkeypatch.setenv("SECRETS_KEK", raw)
    assert _load_kek() == b"b" * 32


def test_load_kek_error_message_includes_regeneration_hint(monkeypatch) -> None:
    monkeypatch.setenv("SECRETS_KEK", "not-valid")
    with pytest.raises(GovernanceError) as exc:
        _load_kek()
    assert "init-env --force" in exc.value.message
