"""Operational settings and runtime governance services.

The implementation lives in small named source slices under
``backend/app/services/governance/governance_runtime/``. This module remains the
stable public import path for routes, CLI commands, runtime code, and tests.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SEGMENT_FILES: tuple[str, ...] = (
    "01_imports_and_defaults.py",
    "02_provider_contracts_openai_ollama.py",
    "03_provider_contracts_remote_and_mock.py",
    "04_provider_secret_and_model_helpers.py",
    "05_provider_probe_http.py",
    "06_provider_probe_adapters.py",
    "07_runtime_rebind_and_audit.py",
    "08_bootstrap_status_and_baseline.py",
    "09_bootstrap_defaults_and_presets.py",
    "10_provider_listing_and_create.py",
    "11_provider_update_and_credentials.py",
    "12_provider_connection_health.py",
    "13_model_listing_and_create.py",
    "14_model_update_delete_rebind.py",
    "15_model_connection_health.py",
    "16_route_listing_and_readiness_helpers.py",
    "17_runtime_readiness_issues.py",
    "18_runtime_readiness_summary.py",
    "19_route_create_update.py",
    "20_runtime_modes.py",
    "21_runtime_route_resolution.py",
    "22_resolved_runtime_serializers.py",
    "23_resolved_runtime_snapshots.py",
    "24_default_provider_seed.py",
    "25_scope_settings.py",
    "26_usage_events_and_budgets.py",
    "27_rollups_audit_and_budget_guard.py",
    "28_operational_activity_and_runtime_secret.py",
    "29_runtime_mode_route_selection.py",
    "30_resolved_route_and_model_rows.py",
    "31_scope_settings_and_snapshot_persistence.py",
    "32_resolved_config_and_default_providers.py",
    "33_default_mock_and_scope_settings.py",
    "34_scope_delete_and_usage_ingest.py",
    "35_budget_policy_and_rollup_rebuild.py",
    "36_rollup_listing_and_budget_guard.py",
    "37_activity_and_provider_credentials.py",
)


def _read_segment_source(base_dir: Path, filename: str) -> str:
    """Load one source slice without importing it as app code."""
    path = base_dir / filename
    spec = importlib.util.spec_from_file_location(f"{__name__}.{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load governance runtime slice: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return str(getattr(module, "SOURCE"))


def _load_runtime_service_segments() -> None:
    """Execute the ordered governance-runtime slices in this module namespace."""
    base_dir = Path(__file__).with_name("governance_runtime")
    source_parts = [_read_segment_source(base_dir, filename) for filename in _SEGMENT_FILES]
    compiled = compile("\n".join(source_parts), f"{__name__}.__generated__", "exec")
    exec(compiled, globals())


_load_runtime_service_segments()
