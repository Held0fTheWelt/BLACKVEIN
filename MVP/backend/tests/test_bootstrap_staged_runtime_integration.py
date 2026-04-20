"""Task 4: prove staged Runtime works through real Flask create_app bootstrap (not helper-only)."""

from __future__ import annotations

import asyncio

import pytest

from app import create_app
from app.config import TestingConfig
from app.content.module_models import ContentModule, ModuleMetadata
from app.runtime.adapter_registry import clear_registry, get_adapter
from app.runtime.ai_turn_executor import execute_turn_with_ai
from app.runtime.runtime_models import SessionState


class BootstrapEnabledTestingConfig(TestingConfig):
    """Production-like bootstrap for registry-backed routing in an isolated test app."""

    ROUTING_REGISTRY_BOOTSTRAP = True


@pytest.fixture
def minimal_module() -> ContentModule:
    meta = ModuleMetadata(
        module_id="m1",
        title="T",
        version="1",
        contract_version="1.0.0",
    )
    return ContentModule(metadata=meta, scenes={}, characters={})


@pytest.mark.asyncio
async def test_create_app_with_bootstrap_registers_mock_and_staged_runtime_runs(
    minimal_module: ContentModule,
):
    """G-BOOT-01: create_app(..., ROUTING_REGISTRY_BOOTSTRAP=True) + full staged execute_turn_with_ai."""

    clear_registry()
    app = create_app(BootstrapEnabledTestingConfig)
    try:
        assert app.config["ROUTING_REGISTRY_BOOTSTRAP"] is True
        mock_adapter = get_adapter("mock")
        assert mock_adapter is not None

        session = SessionState(
            session_id="s-bootstrap-staged",
            execution_mode="ai",
            adapter_name="mock",
            module_id="m1",
            module_version="1",
            current_scene_id="scene1",
        )
        session.canonical_state = {}

        result = await execute_turn_with_ai(session, 1, mock_adapter, minimal_module)
        assert result.execution_status == "success"

        logs = session.metadata.get("ai_decision_logs") or []
        assert logs
        log = logs[-1]
        assert log.runtime_stage_traces, "staged traces must exist when orchestration default applies"
        assert log.operator_audit is not None
        assert log.operator_audit.get("audit_schema_version")
        summary = log.runtime_orchestration_summary or {}
        assert summary.get("final_path") in {
            "slm_only",
            "slm_then_llm",
            "ranked_then_llm",
            "ranked_slm_only",
            "degraded_early_skip_then_synthesis",
            "degraded_parse_forced_synthesis",
            "degraded_ranking_parse_forcing_synthesis",
            "degraded_ranking_no_eligible_fallback",
        }
    finally:
        clear_registry()
