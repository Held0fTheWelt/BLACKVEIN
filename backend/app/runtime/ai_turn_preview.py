"""Preview snapshot and diagnostics helpers for AI turn / tool-loop paths."""

from __future__ import annotations

from typing import Any


def build_preview_snapshot(preview_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "guard_outcome": preview_result.get("guard_outcome"),
        "preview_allowed": bool(preview_result.get("preview_allowed", False)),
        "accepted_delta_count": int(preview_result.get("accepted_delta_count", 0)),
        "rejected_delta_count": int(preview_result.get("rejected_delta_count", 0)),
        "partial_acceptance": bool(preview_result.get("partial_acceptance", False)),
        "input_targets": list((preview_result.get("input_targets") or [])[:20]),
        "summary": preview_result.get("summary"),
        "rejection_reasons": (preview_result.get("rejection_reasons") or [])[:5],
        "suggested_corrections": (preview_result.get("suggested_corrections") or [])[:5],
        "preview_safe_no_write": bool(preview_result.get("preview_safe_no_write", True)),
    }


def build_preview_diagnostics_payload(
    *,
    records: list[dict[str, Any]],
    final_targets: list[str],
) -> dict[str, Any]:
    last_record = records[-1]
    last_preview = last_record["result"]
    preview_targets = list(last_preview.get("input_targets", []) or [])
    return {
        "preview_count": len(records),
        "preview_iterations": [
            {
                "sequence_index": item.get("sequence_index"),
                "request_id": item.get("request_id"),
                "requesting_agent_id": item.get("requesting_agent_id"),
                "request_summary": item.get("request_summary"),
                "result_summary": build_preview_snapshot(item["result"]),
            }
            for item in records[-5:]
        ],
        "last_preview": build_preview_snapshot(last_preview),
        "last_preview_request": {
            "request_id": last_record.get("request_id"),
            "requesting_agent_id": last_record.get("requesting_agent_id"),
            "request_summary": last_record.get("request_summary"),
        },
        "revised_after_preview": final_targets != preview_targets if final_targets else False,
        "improved_acceptance_vs_last_preview": False,
    }


def set_preview_improvement_metric(
    diagnostics: dict[str, Any] | None,
    *,
    final_accepted_count: int,
) -> None:
    if diagnostics is None:
        return
    last_preview = diagnostics.get("last_preview") or {}
    baseline = int(last_preview.get("accepted_delta_count", 0))
    diagnostics["improved_acceptance_vs_last_preview"] = final_accepted_count > baseline
