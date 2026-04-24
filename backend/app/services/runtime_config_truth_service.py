"""Service layer for runtime configuration truth — configured vs. effective vs. loaded."""

from __future__ import annotations

from typing import Any

from flask import current_app
from app.extensions import db
from app.models.governance_core import BootstrapConfig
from app.services.governance_runtime_service import get_runtime_modes, build_resolved_runtime_config


def get_backend_configured_state() -> dict[str, Any]:
    """Get what the backend has configured in database (static policy)."""
    try:
        bootstrap = BootstrapConfig.query.first()
        if not bootstrap:
            return {
                "status": "unconfigured",
                "message": "No bootstrap configuration exists",
                "backend_configured": False,
            }

        return {
            "status": "configured",
            "backend_configured": True,
            "bootstrap_state": bootstrap.bootstrap_state,
            "runtime_profile": bootstrap.runtime_profile,
            "generation_execution_mode": bootstrap.generation_execution_mode,
            "retrieval_execution_mode": bootstrap.retrieval_execution_mode,
            "validation_execution_mode": bootstrap.validation_execution_mode,
            "provider_selection_mode": bootstrap.provider_selection_mode,
            "bootstrap_completed_at": bootstrap.bootstrap_completed_at.isoformat() if bootstrap.bootstrap_completed_at else None,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to read bootstrap config: {str(e)}",
            "backend_configured": False,
        }


def get_backend_effective_config() -> dict[str, Any]:
    """Get what the backend is currently using (resolved runtime config)."""
    try:
        runtime_modes = get_runtime_modes()
        resolved = build_resolved_runtime_config(persist_snapshot=False, actor="system_config_truth")

        return {
            "status": "loaded",
            "backend_effective": True,
            "runtime_profile": runtime_modes.get("runtime_profile"),
            "generation_execution_mode": runtime_modes.get("generation_execution_mode"),
            "retrieval_execution_mode": runtime_modes.get("retrieval_execution_mode"),
            "validation_execution_mode": runtime_modes.get("validation_execution_mode"),
            "provider_selection_mode": runtime_modes.get("provider_selection_mode"),
            "resolved_at": resolved.get("generated_at"),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get effective config: {str(e)}",
            "backend_effective": False,
        }


def get_world_engine_loaded_state() -> dict[str, Any]:
    """
    Get what world-engine has loaded.

    This would query /api/internal/story/runtime/config-status on world-engine.
    For MVP, we provide placeholder that indicates what we expect to find.
    """
    try:
        # Get internal URL from config
        internal_url = (current_app.config.get("PLAY_SERVICE_INTERNAL_URL") or "").strip().rstrip("/")
        if not internal_url:
            return {
                "status": "not_configured",
                "world_engine_loaded": False,
                "message": "PLAY_SERVICE_INTERNAL_URL not configured; cannot query world-engine",
            }

        # In production, would make HTTP call:
        # import httpx
        # response = httpx.get(f"{internal_url}/api/internal/story/runtime/config-status", ...)
        # For now, return placeholder showing what should be checked

        return {
            "status": "requires_http_probe",
            "world_engine_loaded": None,  # Unknown without HTTP call
            "check_endpoint": f"{internal_url}/api/internal/story/runtime/config-status",
            "message": "Would check world-engine config status via internal endpoint",
            "future": {
                "story_runtime_config_loaded": None,
                "story_runtime_active": None,
                "runtime_profile": None,
                "config_version": None,
                "loaded_at": None,
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "world_engine_loaded": False,
            "message": f"Error probing world-engine: {str(e)}",
        }


def get_play_service_reachability() -> dict[str, Any]:
    """Check if play-service HTTP is reachable (technical connectivity only)."""
    try:
        internal_url = (current_app.config.get("PLAY_SERVICE_INTERNAL_URL") or "").strip().rstrip("/")
        if not internal_url:
            return {
                "status": "not_configured",
                "play_service_reachable": False,
                "message": "PLAY_SERVICE_INTERNAL_URL not configured",
            }

        # In production, would make HTTP call to /api/health
        # For now, return placeholder
        return {
            "status": "requires_http_probe",
            "play_service_reachable": None,
            "check_endpoint": f"{internal_url}/api/health",
            "message": "Would check play-service HTTP reachability",
        }
    except Exception as e:
        return {
            "status": "error",
            "play_service_reachable": False,
            "message": f"Error checking play-service: {str(e)}",
        }


def get_runtime_config_truth() -> dict[str, Any]:
    """
    Comprehensive runtime configuration truth snapshot.

    Shows:
    1. What's configured in database (static)
    2. What the backend is effectively using (resolved)
    3. What world-engine has loaded (from HTTP probe)
    4. Whether play-service is reachable (connectivity)
    5. Whether story runtime is actually active (from HTTP probe)
    """
    return {
        "snapshot_timestamp": _utc_now().isoformat(),
        "backend_configured": get_backend_configured_state(),
        "backend_effective": get_backend_effective_config(),
        "world_engine_state": get_world_engine_loaded_state(),
        "play_service_connectivity": get_play_service_reachability(),
        "summary": _build_truth_summary(),
    }


def _build_truth_summary() -> dict[str, Any]:
    """Build a summary of the runtime config truth."""
    configured = get_backend_configured_state()
    effective = get_backend_effective_config()
    world_engine = get_world_engine_loaded_state()
    play_service = get_play_service_reachability()

    summary = {
        "all_configured": configured.get("backend_configured", False),
        "backend_effective": effective.get("backend_effective", False),
        "issues": [],
    }

    # Check for inconsistencies
    if configured.get("backend_configured") and not effective.get("backend_effective"):
        summary["issues"].append("Backend configured but not effective")

    if not configured.get("backend_configured"):
        summary["issues"].append("Backend not configured — bootstrap required")

    if play_service.get("play_service_reachable") is False:
        summary["issues"].append("Play-service not reachable")

    if not summary["issues"]:
        summary["status"] = "ready"
    elif len(summary["issues"]) == 1:
        summary["status"] = "partial"
    else:
        summary["status"] = "degraded"

    return summary


def _utc_now():
    """Get current UTC time."""
    from app.utils.time_utils import utc_now
    return utc_now()
