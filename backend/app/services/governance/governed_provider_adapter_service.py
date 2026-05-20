"""Backend model adapters backed by governed provider credentials.

Provider API keys are intentionally not read from Compose/runtime environment
slots. Backend-owned bounded model calls should use the same encrypted
AI Runtime Governance credential store that world-engine consumes through the
internal provider-credential endpoint.
"""

from __future__ import annotations

import logging

from flask import has_app_context

from story_runtime_core.adapters import (
    BaseModelAdapter,
    MockModelAdapter,
    OllamaAdapter,
    OpenAIChatAdapter,
)

from app.models.governance_core import AIProviderConfig

logger = logging.getLogger(__name__)


def build_governed_provider_adapters() -> dict[str, BaseModelAdapter]:
    """Return adapters keyed by governed provider_id, with secrets from governance storage only."""
    adapters: dict[str, BaseModelAdapter] = {"mock": MockModelAdapter()}
    if not has_app_context():
        return adapters

    try:
        from app.services.governance.governance_runtime_service import get_provider_credential_for_runtime

        providers = AIProviderConfig.query.filter_by(is_enabled=True).all()
    except Exception as exc:  # noqa: BLE001 - callers can still use mock fallback
        logger.debug("Could not load governed provider configs: %s", type(exc).__name__, exc_info=True)
        return adapters

    for provider in providers:
        provider_id = str(provider.provider_id or "").strip()
        provider_type = str(provider.provider_type or "").strip().lower()
        if not provider_id:
            continue

        base_url = str(provider.base_url or "").strip() or None
        api_key: str | None = None
        if bool(provider.credential_configured):
            api_key = get_provider_credential_for_runtime(provider_id)

        adapter = _adapter_for_provider(
            provider_type=provider_type,
            base_url=base_url,
            api_key=api_key,
        )
        if adapter is not None:
            adapters[provider_id] = adapter

    return adapters


def _adapter_for_provider(
    *,
    provider_type: str,
    base_url: str | None,
    api_key: str | None,
) -> BaseModelAdapter | None:
    """Map governed provider metadata to a concrete adapter without env-key fallback."""
    if provider_type == "mock":
        return MockModelAdapter()
    if provider_type == "ollama":
        return OllamaAdapter(base_url=base_url)
    if provider_type in {"openai", "openrouter"}:
        if not api_key:
            return None
        return OpenAIChatAdapter(base_url=base_url, api_key=api_key)
    return None
