from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.config import PLAY_SERVICE_SECRET


class TicketError(Exception):
    pass


class TicketManager:
    def __init__(self, secret: str | None = None) -> None:
        # SECURITY: Validate secret upfront before any encode() operations
        # Fail fast and explicitly if secret is missing or blank
        if secret is not None:
            # Explicit secret provided: validate it
            if not secret or (isinstance(secret, str) and not secret.strip()):
                raise TicketError("Secret cannot be None or blank")
            effective_secret = secret
        else:
            # No explicit secret: use global PLAY_SERVICE_SECRET
            if not PLAY_SERVICE_SECRET or (isinstance(PLAY_SERVICE_SECRET, str) and not PLAY_SERVICE_SECRET.strip()):
                raise TicketError(
                    "PLAY_SERVICE_SECRET is required and cannot be empty. "
                    "Set PLAY_SERVICE_SECRET environment variable."
                )
            effective_secret = PLAY_SERVICE_SECRET

        # Now that we've validated the secret exists and is non-blank, encode it
        self.secret = effective_secret.encode("utf-8")

    def issue(self, payload: dict[str, Any], ttl_seconds: int = 3600) -> str:
        body = {
            **payload,
            "iat": int(time.time()),
            "exp": int(time.time()) + ttl_seconds,
        }
        raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
        sig = hmac.new(self.secret, raw, hashlib.sha256).hexdigest().encode("ascii")
        return base64.urlsafe_b64encode(raw + b"." + sig).decode("ascii")

    def verify(self, token: str) -> dict[str, Any]:
        try:
            decoded = base64.urlsafe_b64decode(token.encode("ascii"))
            raw, provided_sig = decoded.rsplit(b".", 1)
        except Exception as exc:
            raise TicketError("Malformed ticket") from exc

        expected_sig = hmac.new(self.secret, raw, hashlib.sha256).hexdigest().encode("ascii")
        if not hmac.compare_digest(expected_sig, provided_sig):
            raise TicketError("Invalid signature")

        payload = json.loads(raw.decode("utf-8"))
        if int(payload["exp"]) < int(time.time()):
            raise TicketError("Expired ticket")
        return payload
