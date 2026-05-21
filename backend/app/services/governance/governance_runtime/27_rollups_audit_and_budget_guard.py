"""Governance runtime source segment: rollups_audit_and_budget_guard.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
    model = db.session.get(AIModelConfig, model_id)
    if model is None or not model.is_enabled:
        raise governance_error("route_invalid_model_reference", "Route references missing or disabled model.", 409, {"model_id": model_id})
    if route_field in {"preferred_model_id", "fallback_model_id"}:
        if _route_expects_embedding_model(task_kind=task_kind, route_id=route_id):
            if not _is_embedding_model(model):
                raise governance_error(
                    "route_invalid_model_role",
                    "Retrieval embedding route preferred/fallback models must use model_role embedding_role.",
                    409,
                    {"model_id": model_id, "route_field": route_field, "model_role": model.model_role, "task_kind": task_kind, "route_id": route_id},
                )
        elif not _is_generation_model(model):
            raise governance_error(
                "route_invalid_model_role",
                "Preferred and fallback route models must be generation models (llm/slm), not mock or embedding_role.",
                409,
                {"model_id": model_id, "route_field": route_field, "model_role": model.model_role, "task_kind": task_kind, "route_id": route_id},
            )
    if route_field == "mock_model_id" and model.model_role != "mock":
        raise governance_error(
            "route_invalid_model_role",
            "Mock fallback must reference a model whose model_role is mock.",
            409,
            {"model_id": model_id, "route_field": route_field, "model_role": model.model_role},
        )


def create_route(payload: dict, actor: str) -> AITaskRoute:
    route_id = _slug(payload.get("route_id") or f"{payload.get('task_kind','task')}_{payload.get('workflow_scope','global')}")
    task_kind = (payload.get("task_kind") or "").strip()
    for field in ("preferred_model_id", "fallback_model_id", "mock_model_id"):
        _ensure_model_exists(payload.get(field), route_field=field, task_kind=task_kind, route_id=route_id)
    route = db.session.get(AITaskRoute, route_id)
    if route:
        return route
    route = AITaskRoute(
        route_id=route_id,
        task_kind=(payload.get("task_kind") or "").strip(),
        workflow_scope=(payload.get("workflow_scope") or "global").strip(),
        preferred_model_id=payload.get("preferred_model_id"),
        fallback_model_id=payload.get("fallback_model_id"),
        mock_model_id=payload.get("mock_model_id"),
        is_enabled=bool(payload.get("is_enabled", True)),
        use_mock_when_provider_unavailable=bool(payload.get("use_mock_when_provider_unavailable", True)),
    )
    db.session.add(route)
    _audit("route_created", "ai_runtime", route_id, actor, "Route created.", {})
    db.session.commit()
    return route


def update_route(route_id: str, payload: dict, actor: str) -> AITaskRoute:
    route = db.session.get(AITaskRoute, route_id)
    if route is None:
        raise governance_error("route_not_found", f"Route '{route_id}' not found.", 404, {"route_id": route_id})
    task_kind = (payload.get("task_kind", route.task_kind) or "").strip()
    for field in ("preferred_model_id", "fallback_model_id", "mock_model_id"):
        model_id = payload.get(field, getattr(route, field))
        _ensure_model_exists(model_id, route_field=field, task_kind=task_kind, route_id=route_id)
    for field in ("preferred_model_id", "fallback_model_id", "mock_model_id"):
        if field in payload:
            setattr(route, field, payload.get(field))
    for field in ("task_kind", "workflow_scope", "is_enabled", "use_mock_when_provider_unavailable"):
        if field in payload:
            setattr(route, field, payload.get(field))
    route.updated_at = datetime.now(timezone.utc)
    _audit("route_updated", "ai_runtime", route_id, actor, "Route updated.", {})
    db.session.commit()

    _attempt_runtime_rebind()

'''
