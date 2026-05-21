"""Governance runtime source segment: route_create_update.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''

    replacement_mock_id = _candidate_mock_model_id(excluding_model_id=model_id)
    impacted_routes = AITaskRoute.query.filter(
        (AITaskRoute.preferred_model_id == model_id)
        | (AITaskRoute.fallback_model_id == model_id)
        | (AITaskRoute.mock_model_id == model_id)
    ).order_by(AITaskRoute.route_id.asc()).all()

    route_changes: list[dict] = []
    for route in impacted_routes:
        before = {
            "preferred_model_id": route.preferred_model_id,
            "fallback_model_id": route.fallback_model_id,
            "mock_model_id": route.mock_model_id,
            "use_mock_when_provider_unavailable": route.use_mock_when_provider_unavailable,
        }
        preferred_id = route.preferred_model_id
        fallback_id = route.fallback_model_id
        mock_id = route.mock_model_id
        use_mock = bool(route.use_mock_when_provider_unavailable)

        if preferred_id == model_id:
            preferred_id = fallback_id if fallback_id != model_id else None
        if fallback_id == model_id:
            fallback_id = preferred_id if preferred_id != model_id else None
        if mock_id == model_id:
            mock_id = replacement_mock_id

        if not preferred_id and not fallback_id:
            if mock_id:
                use_mock = True
            else:
                raise governance_error(
                    "model_delete_would_break_route",
                    "Deleting this model would leave a route without any AI or mock recovery path.",
                    409,
                    {"model_id": model_id, "route_id": route.route_id},
                )
        elif use_mock and not mock_id:
            use_mock = False
        if use_mock and not mock_id:
            raise governance_error(
                "model_delete_requires_mock_replacement",
                "Deleting this model requires a replacement mock model for at least one route.",
                409,
                {"model_id": model_id, "route_id": route.route_id},
            )

        route.preferred_model_id = preferred_id
        route.fallback_model_id = fallback_id
        route.mock_model_id = mock_id
        route.use_mock_when_provider_unavailable = use_mock
        route.updated_at = datetime.now(timezone.utc)
        route_changes.append(
            {
                "route_id": route.route_id,
                "before": before,
                "after": {
                    "preferred_model_id": preferred_id,
                    "fallback_model_id": fallback_id,
                    "mock_model_id": mock_id,
                    "use_mock_when_provider_unavailable": use_mock,
                },
            }
        )

    db.session.delete(model)
    _audit(
        "model_deleted",
        "ai_runtime",
        model_id,
        actor,
'''
