from __future__ import annotations

import httpx

from app.content.models import ExperienceTemplate


class RemoteContentError(RuntimeError):
    pass


def load_remote_templates(source_url: str) -> dict[str, ExperienceTemplate]:
    url = (source_url or '').strip().rstrip('/')
    if not url:
        return {}
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
    except httpx.RequestError as exc:
        raise RemoteContentError(f'Failed to fetch remote templates: {exc}') from exc
    if response.status_code >= 400:
        raise RemoteContentError(f'Remote content source returned HTTP {response.status_code}')
    data = response.json()
    items = data.get('items') if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise RemoteContentError('Remote content source returned an unexpected payload')
    templates: dict[str, ExperienceTemplate] = {}
    for row in items:
        if not isinstance(row, dict):
            continue
        payload = row.get('payload') if 'payload' in row else row
        if not isinstance(payload, dict):
            continue
        template = ExperienceTemplate.model_validate(payload)
        templates[template.id] = template
    return templates
