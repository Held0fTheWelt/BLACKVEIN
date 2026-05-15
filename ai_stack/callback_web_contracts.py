"""Policy and validation helpers for bounded callback-web runtime evidence."""

from __future__ import annotations

from typing import Any


CALLBACK_WEB_POLICY_SCHEMA_VERSION = "callback_web_policy.v1"
CALLBACK_WEB_VALIDATION_SCHEMA_VERSION = "callback_web_validation.v1"
CALLBACK_WEB_ASPECT_CONTRACT = "callback_web_aspect.v1"

CALLBACK_WEB_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "callback_source_missing",
        "callback_unbounded_evidence",
        "callback_authority_mutation",
        "callback_forbidden_branch_leak",
    }
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _coerce_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError):
        out = int(default)
    return max(minimum, min(maximum, out))


def _string_list(value: Any, *, limit: int = 32) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def normalize_callback_web_policy(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize module callback-web policy into a neutral runtime contract."""
    raw = policy if isinstance(policy, dict) else {}
    present = bool(raw)
    max_edges = _coerce_int(raw.get("max_edges"), default=80, minimum=8, maximum=500)
    max_observations = _coerce_int(
        raw.get("max_observations"),
        default=60,
        minimum=4,
        maximum=500,
    )
    max_evidence_refs = _coerce_int(
        raw.get("max_evidence_refs_per_candidate") or raw.get("max_evidence_refs"),
        default=8,
        minimum=1,
        maximum=32,
    )
    max_graph_edges = _coerce_int(
        raw.get("max_graph_edges") or raw.get("max_export_callbacks"),
        default=4,
        minimum=1,
        maximum=16,
    )
    return {
        "schema_version": str(raw.get("schema_version") or CALLBACK_WEB_POLICY_SCHEMA_VERSION),
        "policy_present": present,
        "enabled": bool(raw.get("enabled", False)),
        "max_edges": max_edges,
        "max_observations": max_observations,
        "max_evidence_refs": max_evidence_refs,
        "max_graph_edges": max_graph_edges,
        "allowed_continuity_classes": _string_list(raw.get("allowed_continuity_classes")),
        "source": str(raw.get("source") or "module_runtime_policy"),
    }


def callback_web_bounds_from_policy(policy: dict[str, Any] | None = None) -> dict[str, int]:
    normalized = normalize_callback_web_policy(policy)
    return {
        "max_edges": int(normalized["max_edges"]),
        "max_observations": int(normalized["max_observations"]),
        "max_evidence_refs": int(normalized["max_evidence_refs"]),
    }


def callback_web_policy_from_module_runtime(
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = (
        module_runtime_policy.get("runtime_governance_policy")
        if isinstance(module_runtime_policy, dict)
        else {}
    )
    raw = runtime.get("callback_web") if isinstance(runtime, dict) else {}
    return normalize_callback_web_policy(raw if isinstance(raw, dict) else None)


def validate_callback_web_record(
    record: dict[str, Any] | None,
    *,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate bounded callback-web evidence without using generated prose."""
    normalized_policy = normalize_callback_web_policy(policy)
    if not normalized_policy.get("enabled"):
        return {
            "schema_version": CALLBACK_WEB_VALIDATION_SCHEMA_VERSION,
            "status": "not_applicable",
            "contract_pass": True,
            "failure_codes": [],
            "policy": normalized_policy,
        }
    source = record if isinstance(record, dict) else {}
    edges = source.get("edges") if isinstance(source.get("edges"), list) else []
    observations = (
        source.get("observations") if isinstance(source.get("observations"), list) else []
    )
    failure_codes: list[str] = []
    if not source or not source.get("callback_web_id") or not source.get("story_session_id"):
        failure_codes.append("callback_source_missing")
    if source.get("non_authoritative") is not True or source.get("mutates_canonical_state") is not False:
        failure_codes.append("callback_authority_mutation")
    if len(edges) > int(normalized_policy["max_edges"]) or len(observations) > int(
        normalized_policy["max_observations"]
    ):
        failure_codes.append("callback_unbounded_evidence")
    max_evidence_refs = int(normalized_policy["max_evidence_refs"])
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if not edge.get("source_turn_id") or not edge.get("target_turn_id"):
            failure_codes.append("callback_source_missing")
        evidence = edge.get("evidence") if isinstance(edge.get("evidence"), dict) else {}
        refs = list(evidence.get("source_fields") or []) + list(evidence.get("signal_hashes") or [])
        if len(refs) > max_evidence_refs:
            failure_codes.append("callback_unbounded_evidence")
        if edge.get("mutates_canonical_state") is not False or edge.get("non_authoritative") is not True:
            failure_codes.append("callback_authority_mutation")
    deduped_failures = sorted(set(failure_codes).intersection(CALLBACK_WEB_FAILURE_CODES))
    return {
        "schema_version": CALLBACK_WEB_VALIDATION_SCHEMA_VERSION,
        "status": "passed" if not deduped_failures else "failed",
        "contract_pass": not deduped_failures,
        "failure_codes": deduped_failures,
        "policy": normalized_policy,
        "edge_count": len(edges),
        "observation_count": len(observations),
        "source": source.get("source") if isinstance(source, dict) else None,
    }


def callback_web_aspect_blocks(
    *,
    record: dict[str, Any] | None,
    graph_export: dict[str, Any] | None,
    validation: dict[str, Any] | None,
    policy: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized_policy = normalize_callback_web_policy(policy)
    rec = record if isinstance(record, dict) else {}
    export = graph_export if isinstance(graph_export, dict) else {}
    val = validation if isinstance(validation, dict) else {}
    snapshot = rec.get("snapshot") if isinstance(rec.get("snapshot"), dict) else {}
    return _json_safe(
        {
            "contract": CALLBACK_WEB_ASPECT_CONTRACT,
            "expected": {
                "policy_present": bool(normalized_policy.get("policy_present")),
                "policy_enabled": bool(normalized_policy.get("enabled")),
                "max_edges": int(normalized_policy.get("max_edges") or 0),
                "max_observations": int(normalized_policy.get("max_observations") or 0),
                "max_evidence_refs": int(normalized_policy.get("max_evidence_refs") or 0),
                "graph_export_bounded": True,
                "non_authoritative": True,
                "mutates_canonical_state": False,
            },
            "selected": {
                "selected_callback_edge_id": export.get("selected_callback_edge_id"),
                "selected_callback_kind": export.get("selected_callback_kind"),
                "selected_continuity_classes": export.get("selected_continuity_classes") or [],
                "selected_thread_ids": export.get("selected_thread_ids") or [],
            },
            "actual": {
                "callback_web_id": rec.get("callback_web_id") or snapshot.get("callback_web_id"),
                "edge_count": int(snapshot.get("edge_count") or len(rec.get("edges") or [])),
                "observation_count": int(
                    snapshot.get("observation_count") or len(rec.get("observations") or [])
                ),
                "graph_edge_count": int(export.get("exported_edge_count") or 0),
                "callback_kind_counts": snapshot.get("callback_kind_counts") or {},
                "continuity_classes": snapshot.get("continuity_classes") or [],
                "thread_ids": snapshot.get("thread_ids") or [],
                "contract_pass": bool(val.get("contract_pass")),
                "failure_codes": val.get("failure_codes") or [],
                "non_authoritative": rec.get("non_authoritative"),
                "mutates_canonical_state": rec.get("mutates_canonical_state"),
            },
        }
    )
