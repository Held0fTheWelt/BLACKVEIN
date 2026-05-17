from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ModuleNotFoundError:  # pragma: no cover - dependency is present in full runtime envs
    AESGCM = None


AEAD_JSON_FORMAT = "wos.aead-json.v1"
AEAD_JSON_ALGORITHM = "AES-256-GCM"
AEAD_KEY_ENV_NAMES = ("WORLD_ENGINE_JSON_AEAD_KEY", "RUN_STORE_JSON_AEAD_KEY")
PLACEHOLDER_VALUES = {
    "__auto_generated_do_not_edit__",
    "change-me",
    "changeme",
    "change_me",
    "replace-me",
    "replaceme",
}


def generate_aead_key() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")


def decode_aead_key(raw: str) -> bytes:
    value = (raw or "").strip()
    if not value:
        raise ValueError("WORLD_ENGINE_JSON_AEAD_KEY must not be empty")
    if len(value) == 64:
        try:
            key = bytes.fromhex(value)
        except ValueError:
            key = b""
        if len(key) == 32:
            return key
    padded = value + ("=" * (-len(value) % 4))
    try:
        key = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception as exc:
        raise ValueError("WORLD_ENGINE_JSON_AEAD_KEY must be base64url or 64-character hex") from exc
    if len(key) != 32:
        raise ValueError("WORLD_ENGINE_JSON_AEAD_KEY must decode to exactly 32 bytes")
    return key


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def associated_data(kind: str, item_id: str) -> bytes:
    return f"world-engine:{kind}:{item_id}".encode("utf-8")


class JsonAtRestCodec:
    def __init__(self, key: bytes | None = None) -> None:
        self.key = key
        if key is None:
            self._aead = None
            return
        if len(key) != 32:
            raise ValueError("AEAD JSON key must be exactly 32 bytes")
        if AESGCM is None:
            raise RuntimeError("cryptography is required for AEAD JSON persistence")
        self._aead = AESGCM(key)

    @classmethod
    def plain(cls) -> "JsonAtRestCodec":
        return cls()

    @classmethod
    def from_key_string(cls, raw: str) -> "JsonAtRestCodec":
        return cls(decode_aead_key(raw))

    @classmethod
    def from_env(cls, *, required: bool = False) -> "JsonAtRestCodec":
        for name in AEAD_KEY_ENV_NAMES:
            raw = os.getenv(name)
            value = (raw or "").strip()
            if value and value.lower() not in PLACEHOLDER_VALUES:
                return cls.from_key_string(value)
        if required:
            names = " or ".join(AEAD_KEY_ENV_NAMES)
            raise ValueError(f"{names} is required for AEAD JSON persistence")
        return cls.plain()

    @property
    def encrypted(self) -> bool:
        return self._aead is not None

    @property
    def extension(self) -> str:
        return ".json.enc" if self.encrypted else ".json"

    def backend_name(self, base: str = "json") -> str:
        return f"{base}_aead" if self.encrypted else base

    def path_for(self, root: Path, item_id: str) -> Path:
        return root / f"{item_id}{self.extension}"

    def dumps(self, payload: dict[str, Any], *, aad: bytes) -> str:
        if not self.encrypted:
            return json.dumps(payload, indent=2, ensure_ascii=False)
        assert self._aead is not None
        nonce = os.urandom(12)
        plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ciphertext = self._aead.encrypt(nonce, plaintext, aad)
        envelope = {
            "format": AEAD_JSON_FORMAT,
            "algorithm": AEAD_JSON_ALGORITHM,
            "nonce": _encode(nonce),
            "ciphertext": _encode(ciphertext),
        }
        return json.dumps(envelope, sort_keys=True, separators=(",", ":"))

    def loads(self, raw: str, *, aad: bytes) -> dict[str, Any]:
        data = json.loads(raw)
        if not self.encrypted:
            if not isinstance(data, dict):
                raise ValueError("json_payload_not_object")
            return data
        if not isinstance(data, dict) or data.get("format") != AEAD_JSON_FORMAT:
            raise ValueError("aead_json_payload_required")
        if data.get("algorithm") != AEAD_JSON_ALGORITHM:
            raise ValueError("unsupported_aead_json_algorithm")
        assert self._aead is not None
        plaintext = self._aead.decrypt(_decode(str(data["nonce"])), _decode(str(data["ciphertext"])), aad)
        payload = json.loads(plaintext.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("aead_json_plaintext_not_object")
        return payload
