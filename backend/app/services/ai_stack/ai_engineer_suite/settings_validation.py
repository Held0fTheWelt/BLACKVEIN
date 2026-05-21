"""Validation helpers for AI Engineer Suite settings."""

from __future__ import annotations

from .common import *

def _extract_values(payload: Any, key: str) -> list[Any]:
    out: list[Any] = []
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k == key:
                out.append(v)
            out.extend(_extract_values(v, key))
    elif isinstance(payload, list):
        for item in payload:
            out.extend(_extract_values(item, key))
    return out


def _extract_parser_errors(payload: Any) -> list[str]:
    out: list[str] = []
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k == "langchain_parser_error" and isinstance(v, str) and v.strip():
                out.append(v.strip())
            out.extend(_extract_parser_errors(v))
    elif isinstance(payload, list):
        for item in payload:
            out.extend(_extract_parser_errors(item))
    return out


def _validate_rag_settings_patch(payload: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(payload.keys()) - _RAG_ALLOWED_SETTINGS)
    if unknown:
        raise governance_error("setting_key_invalid", "Unsupported RAG setting keys.", 400, {"keys": unknown})
    out: dict[str, Any] = {}
    if "retrieval_execution_mode" in payload:
        mode = str(payload["retrieval_execution_mode"]).strip()
        if mode not in _RETRIEVAL_MODE_ALLOWED:
            raise governance_error("setting_value_invalid", "retrieval_execution_mode is invalid.", 400, {"value": mode})
        out["retrieval_execution_mode"] = mode
    if "embeddings_enabled" in payload:
        out["embeddings_enabled"] = bool(payload["embeddings_enabled"])
    if "retrieval_top_k" in payload:
        top_k = int(payload["retrieval_top_k"])
        if top_k < 1 or top_k > 12:
            raise governance_error("setting_value_invalid", "retrieval_top_k must be between 1 and 12.", 400, {"value": top_k})
        out["retrieval_top_k"] = top_k
    if "retrieval_min_score" in payload:
        min_score = float(payload["retrieval_min_score"])
        if min_score < 0.0 or min_score > 1.0:
            raise governance_error("setting_value_invalid", "retrieval_min_score must be between 0.0 and 1.0.", 400, {"value": min_score})
        out["retrieval_min_score"] = min_score
    if "retrieval_profile" in payload:
        profile = str(payload["retrieval_profile"]).strip()
        if not profile:
            raise governance_error("setting_value_invalid", "retrieval_profile must be non-empty.", 400, {})
        out["retrieval_profile"] = profile
    return out


def _validate_orchestration_settings_patch(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    unknown = sorted(set(payload.keys()) - _ORCH_ALLOWED_SETTINGS)
    if unknown:
        raise governance_error("setting_key_invalid", "Unsupported orchestration setting keys.", 400, {"keys": unknown})
    modes_patch: dict[str, Any] = {}
    world_engine_patch: dict[str, Any] = {}
    if "runtime_profile" in payload:
        profile = str(payload["runtime_profile"]).strip()
        if profile not in _RUNTIME_PROFILE_ALLOWED:
            raise governance_error("setting_value_invalid", "runtime_profile is invalid.", 400, {"value": profile})
        modes_patch["runtime_profile"] = profile
    if "enable_corrective_feedback" in payload:
        world_engine_patch["enable_corrective_feedback"] = bool(payload["enable_corrective_feedback"])
    if "runtime_diagnostics_verbosity" in payload:
        verbosity = str(payload["runtime_diagnostics_verbosity"]).strip()
        if verbosity not in _VERBOSITY_ALLOWED:
            raise governance_error("setting_value_invalid", "runtime_diagnostics_verbosity is invalid.", 400, {"value": verbosity})
        world_engine_patch["runtime_diagnostics_verbosity"] = verbosity
    if "max_retry_attempts" in payload:
        max_retry = int(payload["max_retry_attempts"])
        if max_retry < 0 or max_retry > 5:
            raise governance_error("setting_value_invalid", "max_retry_attempts must be between 0 and 5.", 400, {"value": max_retry})
        world_engine_patch["max_retry_attempts"] = max_retry
    return modes_patch, world_engine_patch



__all__ = (
    '_extract_values',
    '_extract_parser_errors',
    '_validate_rag_settings_patch',
    '_validate_orchestration_settings_patch',
)
