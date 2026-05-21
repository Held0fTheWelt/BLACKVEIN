"""Game routes implementation concern: runtime profile merge and compile.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''


def _merge_runtime_profile_handoff(
    runtime_projection: dict[str, Any],
    *,
    module_id: str,
    handoff: dict[str, Any],
) -> dict[str, Any]:
    if not handoff:
        return runtime_projection

    content_module_id = str(handoff.get("content_module_id") or "").strip()
    if content_module_id != module_id:
        raise GameServiceError(
            f"Runtime profile content_module_id {content_module_id!r} does not match compiled module {module_id!r}.",
            status_code=502,
        )

    enriched = dict(runtime_projection)
    for key in _RUNTIME_HANDOFF_FIELDS:
        if key in handoff:
            enriched[key] = handoff[key]
    return enriched


def _compile_player_module(
    template_id: str,
    *,
    runtime_profile_handoff: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    module_id = resolve_canonical_module_id_for_template(template_id)
    try:
        compiled = compile_module(module_id)
    except ModuleLoadError as exc:
        raise GameContentValidationError(f"canonical module not found for template_id {template_id!r}") from exc
    runtime_projection = compiled.runtime_projection.model_dump(mode="json")
    runtime_projection = _merge_runtime_profile_handoff(
        runtime_projection,
        module_id=module_id,
        handoff=runtime_profile_handoff or {},
    )

    provenance = {
        "template_id": template_id,
        "module_id": module_id,
        "canonical_content_authority": f"content/modules/{module_id}/",
        "runtime_projection_module_id": runtime_projection.get("module_id"),
        "runtime_projection_module_version": runtime_projection.get("module_version"),
        "publication_gate": "game_content_published",
    }
    if runtime_profile_handoff:
        provenance["runtime_profile_handoff"] = {
            key: runtime_profile_handoff[key]
            for key in _RUNTIME_HANDOFF_FIELDS
            if key in runtime_profile_handoff
        }
    return module_id, runtime_projection, provenance
'''
