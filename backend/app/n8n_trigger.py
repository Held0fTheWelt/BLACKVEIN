"""Trigger n8n webhook for translation jobs. Payload is signed with N8N_WEBHOOK_SECRET when set."""
import hashlib
import hmac
import json
import logging
import urllib.request

from flask import current_app

logger = logging.getLogger(__name__)


def trigger_webhook(event: str, payload: dict) -> bool:
    """
    POST event + payload to N8N_WEBHOOK_URL. If N8N_WEBHOOK_SECRET is set, add X-Webhook-Signature (HMAC-SHA256).
    Returns True if request was sent (no guarantee n8n processed it). Returns False if URL not configured.
    """
    url = current_app.config.get("N8N_WEBHOOK_URL") if current_app else None
    if not url:
        return False
    body = {"event": event, **payload}
    body_bytes = json.dumps(body, sort_keys=True).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    secret = current_app.config.get("N8N_WEBHOOK_SECRET") if current_app else None
    if secret:
        sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={sig}"
    try:
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 400:
                logger.warning("n8n webhook returned %s for event %s", resp.status, event)
    except Exception as e:
        logger.warning("n8n webhook request failed for event %s: %s", event, e)
        return False
    return True
