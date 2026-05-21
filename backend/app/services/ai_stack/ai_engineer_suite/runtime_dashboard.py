"""AI Engineer Suite runtime dashboard aggregation functions."""

from __future__ import annotations

from .common import *
from .runtime_settings import _effective_config_payload
from .rag_operations import get_rag_operations_status
from .orchestration_status import get_orchestration_status

def _dashboard_operator_row(
    *,
    domain: str,
    message: str,
    suggested_action: str = "",
    code: str = "",
    fix_path: str = "",
) -> dict[str, str]:
    row: dict[str, str] = {"domain": domain, "message": message.strip()}
    action = suggested_action.strip().replace("**", "")
    if action:
        row["suggested_action"] = action
    if code:
        row["code"] = code
    if fix_path:
        row["fix_path"] = fix_path
    return row


def _merge_governance_blockers(governance: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for blocker in governance.get("blockers") or []:
        if not isinstance(blocker, dict):
            continue
        code = str(blocker.get("code") or "").strip()
        entity_id = blocker.get("entity_id")
        message = str(blocker.get("message") or code or "Governance readiness issue.").strip()
        if entity_id:
            message = f"[{entity_id}] {message}"
        elif code and not message.startswith("["):
            message = f"[{code}] {message}"
        rows.append(
            _dashboard_operator_row(
                domain="governance",
                code=code,
                message=message,
                suggested_action=str(blocker.get("suggested_action") or ""),
                fix_path="/manage/ai-runtime-governance",
            )
        )
    return rows


def _merge_world_engine_rows(world_engine: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    for blocker in world_engine.get("blockers") or []:
        if not isinstance(blocker, dict):
            continue
        blockers.append(
            _dashboard_operator_row(
                domain="world_engine",
                code=str(blocker.get("code") or "").strip(),
                message=str(blocker.get("message") or "World-engine control-plane blocker."),
                suggested_action=str(blocker.get("suggested_action") or ""),
                fix_path="/manage/world-engine-control-center",
            )
        )
    for warning in world_engine.get("warnings") or []:
        if not isinstance(warning, dict):
            continue
        warnings.append(
            _dashboard_operator_row(
                domain="world_engine",
                code=str(warning.get("code") or "").strip(),
                message=str(warning.get("message") or "World-engine warning."),
                suggested_action=str(warning.get("suggested_action") or ""),
                fix_path="/manage/world-engine-control-center",
            )
        )
    return blockers, warnings


def _append_guidance_rows(
    target: list[dict[str, str]],
    *,
    domain: str,
    guidance: list[Any],
    severities: set[str],
    default_fix_path: str,
) -> None:
    for row in guidance or []:
        if not isinstance(row, dict):
            continue
        severity = str(row.get("severity") or "").strip().lower()
        if severity not in severities:
            continue
        message = str(row.get("message") or "").strip()
        if not message:
            continue
        target.append(
            _dashboard_operator_row(
                domain=domain,
                message=message,
                suggested_action=str(row.get("next_step") or row.get("suggested_action") or ""),
                fix_path=str(row.get("fix_path") or default_fix_path).strip(),
            )
        )


def _build_dashboard_next_actions(
    *,
    blockers: list[dict[str, str]],
    degraded_or_warning: list[dict[str, str]],
    governance: dict[str, Any],
    ai_only_valid: bool,
) -> list[str]:
    seen: set[str] = set()
    actions: list[str] = []

    def _add(text: str) -> None:
        cleaned = text.strip().replace("**", "")
        if not cleaned or cleaned in seen:
            return
        seen.add(cleaned)
        actions.append(cleaned)

    for item in governance.get("next_actions") or []:
        _add(str(item))

    for row in blockers + degraded_or_warning:
        _add(str(row.get("suggested_action") or ""))

    if blockers or degraded_or_warning:
        return actions[:12]

    if ai_only_valid:
        _add("AI-only preconditions are met; switch generation_execution_mode to ai_only when you intend live model generation.")
    else:
        _add("No blocking or warning signals on this snapshot.")
    return actions[:12]


def get_runtime_dashboard(*, trace_id: str | None = None) -> dict[str, Any]:
    governance = evaluate_runtime_readiness()
    rag = get_rag_operations_status()
    orchestration = get_orchestration_status(trace_id=trace_id)
    world_engine = build_world_engine_control_center_snapshot(current_app._get_current_object(), trace_id=trace_id)
    blockers: list[dict[str, str]] = []
    blockers.extend(_merge_governance_blockers(governance))
    if not blockers and not governance.get("ai_only_valid"):
        blockers.append(
            _dashboard_operator_row(
                domain="governance",
                message=str(governance.get("readiness_headline") or "Governance readiness requires attention."),
                suggested_action="Open AI Runtime Governance and review provider, model, and route readiness rows.",
                fix_path="/manage/ai-runtime-governance",
            )
        )
    if str(rag.get("operational_state")) == "blocked":
        before = len(blockers)
        _append_guidance_rows(
            blockers,
            domain="rag",
            guidance=rag.get("guidance") or [],
            severities={"blocked"},
            default_fix_path="/manage/rag-operations",
        )
        if len(blockers) == before:
            blockers.append(
                _dashboard_operator_row(
                    domain="rag",
                    message="RAG is blocked and cannot provide runtime retrieval context.",
                    suggested_action="Run corpus refresh and a retrieval probe in RAG Operations.",
                    fix_path="/manage/rag-operations",
                )
            )
    langgraph = orchestration.get("langgraph") or {}
    if str(orchestration.get("overall_state")) == "blocked" or not langgraph.get("dependency_available"):
        before = len(blockers)
        _append_guidance_rows(
            blockers,
            domain="orchestration",
            guidance=orchestration.get("guidance") or [],
            severities={"blocked"},
            default_fix_path="/manage/ai-orchestration",
        )
        if len(blockers) == before:
            blockers.append(
                _dashboard_operator_row(
                    domain="orchestration",
                    message="LangGraph runtime dependency is unavailable.",
                    suggested_action="Review orchestration diagnostics in AI Orchestration before enabling strict runtime paths.",
                    fix_path="/manage/ai-orchestration",
                )
            )
    world_blockers, world_warnings = _merge_world_engine_rows(world_engine)
    blockers.extend(world_blockers)
    effective = _effective_config_payload()
    governance_state = str(governance.get("readiness_severity") or "unknown")
    if governance_state not in {"healthy", "degraded", "blocked", "configured_disabled", "unknown"}:
        governance_state = "unknown"
    rag_state = str(rag.get("operational_state") or "unknown")
    orchestration_state = str(orchestration.get("overall_state") or "unknown")
    world_status = world_engine.get("status") or {}
    world_state = "healthy"
    if world_status.get("control_plane_ok") is False:
        world_state = "blocked"
    elif int(world_status.get("warning_count") or 0) > 0:
        world_state = "degraded"
    domain_status = [
        {
            "domain": "governance",
            "state": governance_state,
            "consequence": "Provider/model/route readiness determines AI-only runtime validity.",
            "fix_path": "/manage/ai-runtime-governance",
        },
        {
            "domain": "runtime_settings",
            "state": (
                "degraded"
                if (effective.get("guardrail_warnings") or []) or (effective.get("drift_keys") or [])
                else "healthy"
            ),
            "consequence": "Preset intent can diverge when manual overrides are active.",
            "fix_path": "/manage/runtime-settings",
        },
        {
            "domain": "rag",
            "state": rag_state,
            "consequence": "Retrieval degradation can lower grounding quality.",
            "fix_path": "/manage/rag-operations",
        },
        {
            "domain": "orchestration",
            "state": orchestration_state,
            "consequence": "Orchestration degradation affects runtime traceability and structured output reliability.",
            "fix_path": "/manage/ai-orchestration",
        },
        {
            "domain": "world_engine",
            "state": world_state,
            "consequence": "Control-plane mismatch can block run/session operations.",
            "fix_path": "/manage/world-engine-control-center",
        },
    ]
    degraded_or_warning: list[dict[str, str]] = list(world_warnings)
    _append_guidance_rows(
        degraded_or_warning,
        domain="rag",
        guidance=rag.get("guidance") or [],
        severities={"degraded", "warn", "info"},
        default_fix_path="/manage/rag-operations",
    )
    _append_guidance_rows(
        degraded_or_warning,
        domain="orchestration",
        guidance=orchestration.get("guidance") or [],
        severities={"degraded", "warn", "info"},
        default_fix_path="/manage/ai-orchestration",
    )
    ai_only_valid = bool(governance.get("ai_only_valid"))
    next_actions = _build_dashboard_next_actions(
        blockers=blockers,
        degraded_or_warning=degraded_or_warning,
        governance=governance,
        ai_only_valid=ai_only_valid,
    )
    return {
        "summary": {
            "provider_readiness": governance.get("provider_summary", {}),
            "model_route_readiness": governance.get("route_summary", {}),
            "ai_only_valid": ai_only_valid,
            "task_routes_green": bool(governance.get("task_routes_green")),
            "rag": {
                "chunk_count": (rag.get("corpus") or {}).get("chunk_count", 0),
                "embedding_backend_available": (rag.get("embedding_backend") or {}).get("available", False),
                "dense_artifact_validity": (rag.get("dense_index") or {}).get("artifact_validity"),
            },
            "orchestration": {
                "langgraph_dependency_available": bool((orchestration.get("langgraph") or {}).get("dependency_available")),
                "langchain_bridge_available": bool((orchestration.get("langchain") or {}).get("bridge_available")),
                "recent_graph_errors": (orchestration.get("langgraph") or {}).get("fallback_posture", {}).get("graph_error_count_recent", 0),
            },
            "world_engine": world_engine.get("status", {}),
            "active_runtime": world_engine.get("active_runtime", {}),
            "settings_layer": {
                "active_preset_id": effective.get("active_preset_id"),
                "override_count": effective.get("override_count", 0),
                "drift_key_count": len(effective.get("drift_keys") or []),
                "guardrail_warning_count": len(effective.get("guardrail_warnings") or []),
            },
        },
        "status_semantics": STATUS_SEMANTICS,
        "domain_status": domain_status,
        "blockers": blockers,
        "degraded_or_warning": degraded_or_warning,
        "next_actions": next_actions,
        "links": [
            {"label": "AI Runtime Governance", "path": "/manage/ai-runtime-governance"},
            {"label": "World-Engine Control Center", "path": "/manage/world-engine-control-center"},
            {"label": "RAG Operations", "path": "/manage/rag-operations"},
            {"label": "AI Orchestration", "path": "/manage/ai-orchestration"},
            {"label": "Runtime Settings", "path": "/manage/runtime-settings"},
        ],
    }

__all__ = (
    '_dashboard_operator_row',
    '_merge_governance_blockers',
    '_merge_world_engine_rows',
    '_append_guidance_rows',
    '_build_dashboard_next_actions',
    'get_runtime_dashboard',
)
