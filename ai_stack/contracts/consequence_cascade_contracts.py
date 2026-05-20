"""Policy and validation helpers for bounded consequence-cascade evidence."""

from __future__ import annotations

from typing import Any


CONSEQUENCE_CASCADE_POLICY_SCHEMA_VERSION = "consequence_cascade_policy.v1"
CONSEQUENCE_CASCADE_VALIDATION_SCHEMA_VERSION = "consequence_cascade_validation.v1"
CONSEQUENCE_CASCADE_ASPECT_CONTRACT = "consequence_cascade_aspect.v1"

CONSEQUENCE_CASCADE_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "consequence_cascade_source_missing",
        "consequence_cascade_unbounded_evidence",
        "consequence_cascade_authority_mutation",
        "consequence_cascade_forbidden_continuity_class",
        "consequence_cascade_branch_preview_authoritative",
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


def _string_list(value: Any, *, limit: int = 64) -> list[str]:
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


def normalize_consequence_cascade_policy(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize module consequence-cascade policy into a neutral runtime contract."""

    raw = policy if isinstance(policy, dict) else {}
    present = bool(raw)
    max_atoms = _coerce_int(raw.get("max_atoms"), default=80, minimum=8, maximum=500)
    max_edges = _coerce_int(raw.get("max_edges"), default=120, minimum=8, maximum=800)
    max_evidence_refs = _coerce_int(
        raw.get("max_evidence_refs_per_consequence") or raw.get("max_evidence_refs"),
        default=8,
        minimum=1,
        maximum=32,
    )
    max_graph_items = _coerce_int(
        raw.get("max_graph_items") or raw.get("max_export_consequences"),
        default=5,
        minimum=1,
        maximum=24,
    )
    decay_after_turns = _coerce_int(
        raw.get("decay_after_turns"),
        default=4,
        minimum=1,
        maximum=100,
    )
    return {
        "schema_version": str(raw.get("schema_version") or CONSEQUENCE_CASCADE_POLICY_SCHEMA_VERSION),
        "policy_present": present,
        "enabled": bool(raw.get("enabled", False)),
        "max_atoms": max_atoms,
        "max_edges": max_edges,
        "max_evidence_refs": max_evidence_refs,
        "max_graph_items": max_graph_items,
        "decay_after_turns": decay_after_turns,
        "allowed_continuity_classes": _string_list(raw.get("allowed_continuity_classes")),
        "source": str(raw.get("source") or "module_runtime_policy"),
    }


def consequence_cascade_bounds_from_policy(policy: dict[str, Any] | None = None) -> dict[str, int]:
    normalized = normalize_consequence_cascade_policy(policy)
    return {
        "max_atoms": int(normalized["max_atoms"]),
        "max_edges": int(normalized["max_edges"]),
        "max_evidence_refs": int(normalized["max_evidence_refs"]),
        "decay_after_turns": int(normalized["decay_after_turns"]),
    }


def consequence_cascade_policy_from_module_runtime(
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = (
        module_runtime_policy.get("runtime_governance_policy")
        if isinstance(module_runtime_policy, dict)
        else {}
    )
    raw = runtime.get("consequence_cascade") if isinstance(runtime, dict) else {}
    return normalize_consequence_cascade_policy(raw if isinstance(raw, dict) else None)


def validate_consequence_cascade_record(
    record: dict[str, Any] | None,
    *,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate bounded consequence-cascade evidence without using generated prose."""

    normalized_policy = normalize_consequence_cascade_policy(policy)
    if not normalized_policy.get("enabled"):
        return {
            "schema_version": CONSEQUENCE_CASCADE_VALIDATION_SCHEMA_VERSION,
            "status": "not_applicable",
            "contract_pass": True,
            "failure_codes": [],
            "policy": normalized_policy,
        }
    source = record if isinstance(record, dict) else {}
    atoms = source.get("atoms") if isinstance(source.get("atoms"), list) else []
    edges = source.get("edges") if isinstance(source.get("edges"), list) else []
    allowed_classes = set(normalized_policy.get("allowed_continuity_classes") or [])
    max_evidence_refs = int(normalized_policy["max_evidence_refs"])

    failure_codes: list[str] = []
    if not source or not source.get("cascade_id") or not source.get("story_session_id"):
        failure_codes.append("consequence_cascade_source_missing")
    if source.get("derived_from_committed_truth") is not True or source.get("mutates_canonical_state") is not False:
        failure_codes.append("consequence_cascade_authority_mutation")
    if len(atoms) > int(normalized_policy["max_atoms"]) or len(edges) > int(normalized_policy["max_edges"]):
        failure_codes.append("consequence_cascade_unbounded_evidence")

    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        consequence_class = str(atom.get("continuity_class") or "").strip()
        if not atom.get("consequence_id") or not atom.get("source_turn_id"):
            failure_codes.append("consequence_cascade_source_missing")
        if allowed_classes and consequence_class and consequence_class not in allowed_classes:
            failure_codes.append("consequence_cascade_forbidden_continuity_class")
        evidence = atom.get("evidence") if isinstance(atom.get("evidence"), dict) else {}
        refs = list(evidence.get("source_fields") or []) + list(evidence.get("signal_hashes") or [])
        if len(refs) > max_evidence_refs:
            failure_codes.append("consequence_cascade_unbounded_evidence")

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if not edge.get("source_consequence_id") or not edge.get("target_consequence_id"):
            failure_codes.append("consequence_cascade_source_missing")
        if edge.get("mutates_canonical_state") is not False:
            failure_codes.append("consequence_cascade_authority_mutation")
        if edge.get("inactive_branch_authoritative") is True:
            failure_codes.append("consequence_cascade_branch_preview_authoritative")
        edge_class = str(edge.get("continuity_class") or "").strip()
        if allowed_classes and edge_class and edge_class not in allowed_classes:
            failure_codes.append("consequence_cascade_forbidden_continuity_class")

    deduped_failures = sorted(set(failure_codes).intersection(CONSEQUENCE_CASCADE_FAILURE_CODES))
    return {
        "schema_version": CONSEQUENCE_CASCADE_VALIDATION_SCHEMA_VERSION,
        "status": "passed" if not deduped_failures else "failed",
        "contract_pass": not deduped_failures,
        "failure_codes": deduped_failures,
        "policy": normalized_policy,
        "atom_count": len(atoms),
        "edge_count": len(edges),
        "source": source.get("source") if isinstance(source, dict) else None,
    }


def consequence_cascade_aspect_blocks(
    *,
    record: dict[str, Any] | None,
    graph_export: dict[str, Any] | None,
    validation: dict[str, Any] | None,
    policy: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized_policy = normalize_consequence_cascade_policy(policy)
    rec = record if isinstance(record, dict) else {}
    export = graph_export if isinstance(graph_export, dict) else {}
    val = validation if isinstance(validation, dict) else {}
    snapshot = rec.get("snapshot") if isinstance(rec.get("snapshot"), dict) else {}
    return _json_safe(
        {
            "contract": CONSEQUENCE_CASCADE_ASPECT_CONTRACT,
            "expected": {
                "policy_present": bool(normalized_policy.get("policy_present")),
                "policy_enabled": bool(normalized_policy.get("enabled")),
                "max_atoms": int(normalized_policy.get("max_atoms") or 0),
                "max_edges": int(normalized_policy.get("max_edges") or 0),
                "max_evidence_refs": int(normalized_policy.get("max_evidence_refs") or 0),
                "graph_export_bounded": True,
                "derived_from_committed_truth": True,
                "mutates_canonical_state": False,
                "inactive_branches_authoritative": False,
            },
            "selected": {
                "selected_consequence_ids": export.get("selected_consequence_ids") or [],
                "selected_edge_ids": export.get("selected_edge_ids") or [],
                "selected_continuity_classes": export.get("selected_continuity_classes") or [],
                "selected_statuses": export.get("selected_statuses") or [],
            },
            "actual": {
                "cascade_id": rec.get("cascade_id") or snapshot.get("cascade_id"),
                "atom_count": int(snapshot.get("atom_count") or len(rec.get("atoms") or [])),
                "edge_count": int(snapshot.get("edge_count") or len(rec.get("edges") or [])),
                "active_atom_count": int(snapshot.get("active_atom_count") or 0),
                "graph_item_count": int(export.get("exported_item_count") or 0),
                "continuity_classes": snapshot.get("continuity_classes") or [],
                "status_counts": snapshot.get("status_counts") or {},
                "edge_kind_counts": snapshot.get("edge_kind_counts") or {},
                "contract_pass": bool(val.get("contract_pass")),
                "failure_codes": val.get("failure_codes") or [],
                "derived_from_committed_truth": rec.get("derived_from_committed_truth"),
                "mutates_canonical_state": rec.get("mutates_canonical_state"),
            },
        }
    )
