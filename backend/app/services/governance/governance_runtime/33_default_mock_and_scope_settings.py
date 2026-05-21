"""Governance runtime source segment: default_mock_and_scope_settings.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''


def _ensure_default_mock_path(actor: str) -> None:
    provider = db.session.get(AIProviderConfig, "mock_default")
    if provider is None:
        provider = AIProviderConfig(
            provider_id="mock_default",
            provider_type="mock",
            display_name="Mock Default",
            is_enabled=True,
            is_local=True,
            supports_structured_output=True,
            credential_configured=False,
            health_status="healthy",
        )
        db.session.add(provider)
    model = db.session.get(AIModelConfig, "mock_deterministic")
    if model is None:
        model = AIModelConfig(
            model_id="mock_deterministic",
            provider_id=provider.provider_id,
            model_name="mock-deterministic",
            display_name="Mock Deterministic",
            model_role="mock",
            is_enabled=True,
            structured_output_capable=True,
            timeout_seconds=5,
            cost_method="none",
        )
        db.session.add(model)
    for task_kind in _REQUIRED_TASK_KINDS:
        route_id = f"{task_kind}_global"
        if db.session.get(AITaskRoute, route_id) is None:
            db.session.add(
                AITaskRoute(
                    route_id=route_id,
                    task_kind=task_kind,
                    workflow_scope="global",
                    preferred_model_id=model.model_id,
                    fallback_model_id=model.model_id,
                    mock_model_id=model.model_id,
                    is_enabled=True,
                    use_mock_when_provider_unavailable=True,
                )
            )
    _audit("mock_path_seeded", "ai_runtime", "mock_default", actor, "Default mock path ensured.", {})


def read_scope_settings(scope: str) -> dict:
    rows = SystemSettingRecord.query.filter_by(scope=scope).all()
    return {row.setting_key: row.setting_value_json for row in rows}


def update_scope_settings(scope: str, payload: dict, actor: str) -> dict:
    for setting_key, setting_value in payload.items():
        setting_id = _slug(f"{scope}_{setting_key}")
        row = db.session.get(SystemSettingRecord, setting_id)
        if row is None:
            row = SystemSettingRecord(
                setting_id=setting_id,
                scope=scope,
                setting_key=setting_key,
                setting_value_json=setting_value,
                is_secret_backed=False,
                is_user_visible=True,
                updated_by=actor,
            )
            db.session.add(row)
        else:
            row.setting_value_json = setting_value
            row.updated_by = actor
            row.updated_at = datetime.now(timezone.utc)
'''
