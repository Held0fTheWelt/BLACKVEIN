"""Governance runtime source segment: default_provider_seed.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
    blockers: list[dict] = []
    if not enabled_non_mock_provider:
        blockers.append(
            {
                "code": "enabled_non_mock_provider_missing",
                "entity_type": "provider",
                "entity_id": None,
                "message": "No enabled non-mock provider is currently eligible for runtime assignment.",
                "suggested_action": _readiness_suggested_action(code="enabled_non_mock_provider_missing", entity_id=None),
            }
        )
    if not enabled_non_mock_model:
        blockers.append(
            {
                "code": "enabled_non_mock_model_missing",
                "entity_type": "model",
                "entity_id": None,
                "message": "No enabled model is attached to an eligible non-mock provider.",
                "suggested_action": _readiness_suggested_action(code="enabled_non_mock_model_missing", entity_id=None),
            }
        )
    if not enabled_ai_route:
        blockers.append(
            {
                "code": "enabled_ai_route_missing",
                "entity_type": "route",
                "entity_id": None,
                "message": "No enabled route currently resolves to an eligible preferred or fallback non-mock model.",
                "suggested_action": _readiness_suggested_action(code="enabled_ai_route_missing", entity_id=None),
            }
        )

    suppress_disabled_provider_blockers = _has_enabled_non_mock_provider(provider_rows)
    task_routes_green = _task_routes_operator_green(route_rows)

    for provider in provider_rows:
        if not provider.get("is_enabled") and suppress_disabled_provider_blockers:
            # Operator has at least one live non-mock path; ignore dormant provider inventory noise.
            continue
        for limitation in provider.get("limitations") or []:
            if limitation == "no_enabled_models" and task_routes_green:
                continue
            code = f"provider_{limitation}"
            blockers.append(
                {
                    "code": code,
                    "entity_type": "provider",
                    "entity_id": provider["provider_id"],
                    "message": f"Provider '{provider['provider_id']}' is not ready for AI routes: {limitation}.",
                    "suggested_action": _readiness_suggested_action(
                        code=code, entity_id=provider["provider_id"], limitation=limitation
                    ),
                }
            )
    for route in route_rows:
        for route_blocker in route.get("readiness_blockers") or []:
            code = f"route_{route_blocker}"
            blockers.append(
                {
                    "code": code,
                    "entity_type": "route",
                    "entity_id": route["route_id"],
                    "message": f"Route '{route['route_id']}' cannot run as configured: {route_blocker}.",
                    "suggested_action": _readiness_suggested_action(code=code, entity_id=route["route_id"]),
                }
            )

    ai_only_valid = enabled_non_mock_provider and enabled_non_mock_model and enabled_ai_route
    mock_only_required = not ai_only_valid
    next_actions: list[str] = []
    if not enabled_non_mock_provider:
        next_actions.append("Create or enable a non-mock provider and configure its credential.")
'''
