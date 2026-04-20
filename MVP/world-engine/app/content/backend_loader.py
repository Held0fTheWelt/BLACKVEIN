from __future__ import annotations

from typing import Any

import httpx

from app.content.models import ExperienceTemplate


class BackendContentLoadError(RuntimeError):
    pass



def load_published_templates(source_url: str, timeout: float = 10.0) -> dict[str, ExperienceTemplate]:
    if not source_url.strip():
        return {}
    try:
        response = httpx.get(source_url, timeout=timeout)
        response.raise_for_status()
        payload: Any = response.json()
    except Exception as exc:  # pragma: no cover - network/path failures are surfaced to caller
        raise BackendContentLoadError(f"Unable to load backend content feed: {exc}") from exc

    templates_payload = payload.get("templates") if isinstance(payload, dict) else None
    if not isinstance(templates_payload, list):
        raise BackendContentLoadError("Backend content feed returned an invalid templates payload.")

    templates: dict[str, ExperienceTemplate] = {}
    for item in templates_payload:
        try:
            template = ExperienceTemplate.model_validate(item)
        except Exception as exc:  # pragma: no cover - invalid payload should fail loudly
            raise BackendContentLoadError(f"Invalid backend template payload: {exc}") from exc
        templates[template.id] = template
    return templates
