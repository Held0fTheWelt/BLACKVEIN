"""Game routes implementation concern: template catalog helpers.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
def _parse_optional_int(raw_value: Any, *, field_name: str) -> int | None:
    if raw_value in (None, "", "null"):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a valid integer.") from exc


def _serialize_template_catalog(templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: list[dict[str, Any]] = []
    for template in templates:
        kind = template.get("kind") or "unknown"
        grouped.append(
            {
                "id": template.get("id"),
                "title": template.get("title") or template.get("id") or "Untitled",
                "kind": kind,
                "kind_label": {
                    "solo_story": "Solo Story",
                    "group_story": "Group Story",
                    "open_world": "Open World",
                }.get(kind, kind.replace("_", " ").title()),
            }
        )
    return grouped



def _builtin_play_template_dicts() -> list[dict[str, Any]]:
    """Fallback catalog for the play launcher when the world-engine list is empty or play is not configured."""
    from app.content.builtins import load_builtin_templates

    out: list[dict[str, Any]] = []
    for tmpl in load_builtin_templates().values():
        d = tmpl.model_dump(mode="json")
        out.append({"id": d["id"], "title": d["title"], "kind": d["kind"]})
    return out


def _template_catalog_from_runtime_or_fallback(*, play_service_configured: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return play templates plus diagnostic catalog-source metadata."""
    diagnostic: dict[str, Any] = {
        "source": "builtin_fallback",
        "degraded": not play_service_configured,
        "runtime_error": None,
    }
    templates: list[dict[str, Any]] = []
    if play_service_configured:
        try:
            templates = list_play_templates()
            diagnostic["source"] = "play_service"
            diagnostic["degraded"] = False
        except GameServiceError as exc:
            diagnostic.update(
                {
                    "source": "builtin_fallback",
                    "degraded": True,
                    "runtime_error": str(exc),
                    "runtime_status_code": exc.status_code,
                }
            )
    if not templates:
        templates = _builtin_play_template_dicts()
    return templates, diagnostic


'''
