"""Deterministic callback-web derivation from committed story-runtime truth.

The callback web is bounded operator evidence. It connects later committed
turns back to earlier committed turns when continuity classes, narrative
threads, scene anchors, or selected branch paths show that an older pressure is
being reused. It never mutates canonical history.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from story_runtime_core.committed_truth import committed_story_truth_rows


CALLBACK_WEB_RECORD_SCHEMA_VERSION = "callback_web_record.v1"
CALLBACK_EDGE_SCHEMA_VERSION = "callback_edge.v1"
CALLBACK_OBSERVATION_SCHEMA_VERSION = "callback_observation.v1"
CALLBACK_WEB_SNAPSHOT_SCHEMA_VERSION = "callback_web_snapshot.v1"
CALLBACK_WEB_FEEDBACK_CONTRACT = "callback_web_feedback.v1"
CALLBACK_WEB_RECORD_SOURCE = "world_engine_callback_web"

CALLBACK_EDGE_KIND_REPEATED_CONTINUITY_CLASS = "repeated_continuity_class"
CALLBACK_EDGE_KIND_THREAD_CONTINUITY = "thread_continuity"
CALLBACK_EDGE_KIND_BRANCH_SELECTION_REALIZED = "branch_selection_realized"
CALLBACK_EDGE_KIND_REPEATED_SCENE_ANCHOR = "repeated_scene_anchor"
CALLBACK_EDGE_KINDS = (
    CALLBACK_EDGE_KIND_REPEATED_CONTINUITY_CLASS,
    CALLBACK_EDGE_KIND_THREAD_CONTINUITY,
    CALLBACK_EDGE_KIND_BRANCH_SELECTION_REALIZED,
    CALLBACK_EDGE_KIND_REPEATED_SCENE_ANCHOR,
)

CALLBACK_WEB_DEFAULT_MAX_EDGES = 80
CALLBACK_WEB_DEFAULT_MAX_OBSERVATIONS = 60
CALLBACK_WEB_DEFAULT_MAX_EVIDENCE_REFS = 8
CALLBACK_WEB_MIN_MAX_EDGES = 8
CALLBACK_WEB_MIN_MAX_OBSERVATIONS = 4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, set):
        return sorted(_json_safe(v) for v in value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _short(value: Any, limit: int = 96) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def _stable_hash(payload: Any, length: int = 16) -> str:
    raw = json.dumps(_json_safe(payload), sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def _dedupe_sorted(values: list[Any], *, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    out.sort()
    return out[:limit] if limit is not None else out


def default_callback_web_bounds() -> dict[str, int]:
    return {
        "max_edges": CALLBACK_WEB_DEFAULT_MAX_EDGES,
        "max_observations": CALLBACK_WEB_DEFAULT_MAX_OBSERVATIONS,
        "max_evidence_refs": CALLBACK_WEB_DEFAULT_MAX_EVIDENCE_REFS,
    }


def normalize_callback_web_bounds(bounds: dict[str, Any] | None = None) -> dict[str, int]:
    out = default_callback_web_bounds()
    if isinstance(bounds, dict):
        for key in tuple(out):
            if key in bounds:
                try:
                    out[key] = int(bounds[key])
                except (TypeError, ValueError):
                    continue
    out["max_edges"] = max(CALLBACK_WEB_MIN_MAX_EDGES, out["max_edges"])
    out["max_observations"] = max(CALLBACK_WEB_MIN_MAX_OBSERVATIONS, out["max_observations"])
    out["max_evidence_refs"] = max(1, out["max_evidence_refs"])
    return out


def stable_callback_web_id(*, story_session_id: str) -> str:
    digest = hashlib.sha256(str(story_session_id).encode("utf-8")).hexdigest()[:16]
    return f"callback_web_{digest}"


def _commit_from_row(row: dict[str, Any]) -> dict[str, Any]:
    commit = row.get("narrative_commit") if isinstance(row.get("narrative_commit"), dict) else {}
    return dict(commit)


def _planner_truth(commit: dict[str, Any]) -> dict[str, Any]:
    value = commit.get("planner_truth")
    return dict(value) if isinstance(value, dict) else {}


def _continuity_classes_from_impacts(impacts: Any) -> list[str]:
    if not isinstance(impacts, list):
        return []
    out: list[str] = []
    for item in impacts:
        if not isinstance(item, dict):
            continue
        for key in ("class", "continuity_class", "kind", "type"):
            value = str(item.get(key) or "").strip()
            if value:
                out.append(value)
                break
    return _dedupe_sorted(out)


def _continuity_classes_for_commit(commit: dict[str, Any]) -> list[str]:
    planner = _planner_truth(commit)
    classes = _continuity_classes_from_impacts(planner.get("continuity_impacts"))
    classes.extend(_continuity_classes_from_impacts(commit.get("continuity_impacts")))
    beat = commit.get("beat_progression") if isinstance(commit.get("beat_progression"), dict) else {}
    pressure = str(beat.get("pressure_state") or "").strip()
    if pressure:
        classes.append(pressure)
    return _dedupe_sorted(classes)


def _entities_for_commit(commit: dict[str, Any]) -> list[str]:
    planner = _planner_truth(commit)
    values: list[Any] = [
        planner.get("primary_responder_id"),
        planner.get("responder_id"),
        planner.get("interruption_actor_id"),
    ]
    for key in ("secondary_responder_ids", "responder_scope", "realized_secondary_responder_ids"):
        raw = planner.get(key)
        if isinstance(raw, list):
            values.extend(raw)
    return _dedupe_sorted(values, limit=12)


def _signals_for_commit(commit: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("open_pressures", "committed_consequences", "resolved_pressures"):
        raw = commit.get(key)
        if isinstance(raw, list):
            values.extend(_short(x, 80) for x in raw if str(x or "").strip())
    return _dedupe_sorted(values, limit=12)


def _thread_dicts(narrative_threads: Any) -> list[dict[str, Any]]:
    if hasattr(narrative_threads, "model_dump"):
        narrative_threads = narrative_threads.model_dump(mode="json")
    if not isinstance(narrative_threads, dict):
        return []
    out: list[dict[str, Any]] = []
    for key in ("active", "resolved_recent"):
        raw = narrative_threads.get(key)
        if not isinstance(raw, list):
            continue
        for item in raw:
            if isinstance(item, dict):
                out.append(dict(item))
    return out


def _threads_for_observation(*, scene_id: str, classes: list[str], signals: list[str], narrative_threads: Any) -> list[str]:
    scene = str(scene_id or "").strip()
    class_set = set(classes)
    signal_set = set(signals)
    out: list[str] = []
    for thread in _thread_dicts(narrative_threads):
        thread_id = str(thread.get("thread_id") or "").strip()
        if not thread_id:
            continue
        related_scenes = {str(x) for x in thread.get("related_scenes") or []}
        evidence_tokens = {str(x) for x in thread.get("evidence_tokens") or []}
        thread_kind = str(thread.get("thread_kind") or "").strip()
        if scene and (scene == str(thread.get("scene_anchor") or "") or scene in related_scenes):
            out.append(thread_id)
            continue
        if thread_kind and thread_kind in class_set:
            out.append(thread_id)
            continue
        if evidence_tokens and evidence_tokens.intersection(signal_set):
            out.append(thread_id)
    return _dedupe_sorted(out)


def _observation_for_row(
    *,
    row: dict[str, Any],
    narrative_threads: Any,
) -> dict[str, Any] | None:
    turn_id = str(row.get("canonical_turn_id") or "").strip()
    if not turn_id:
        return None
    commit = _commit_from_row(row)
    turn_number = int(row.get("turn_number") or commit.get("turn_number") or 0)
    scene_id = str(commit.get("committed_scene_id") or row.get("current_scene_id") or "").strip()
    classes = _continuity_classes_for_commit(commit)
    entities = _entities_for_commit(commit)
    signals = _signals_for_commit(commit)
    thread_ids = _threads_for_observation(
        scene_id=scene_id,
        classes=classes,
        signals=signals,
        narrative_threads=narrative_threads,
    )
    signal_hashes = [_stable_hash(signal, 12) for signal in signals]
    return {
        "schema_version": CALLBACK_OBSERVATION_SCHEMA_VERSION,
        "turn_id": turn_id,
        "turn_number": turn_number,
        "scene_id": scene_id or None,
        "continuity_classes": classes,
        "thread_ids": thread_ids,
        "related_entities": entities,
        "signal_hashes": signal_hashes,
        "has_callback_signal": bool(classes or thread_ids or signal_hashes),
    }


def _edge_id(seed: dict[str, Any]) -> str:
    return "callback_edge_" + _stable_hash(seed, 16)


def _make_edge(
    *,
    story_session_id: str,
    callback_kind: str,
    source: dict[str, Any],
    target: dict[str, Any],
    continuity_classes: list[str] | None = None,
    thread_ids: list[str] | None = None,
    related_entities: list[str] | None = None,
    branch_tree_ids: list[str] | None = None,
    evidence_fields: list[str] | None = None,
    evidence_hashes: list[str] | None = None,
    confidence: float = 0.5,
) -> dict[str, Any]:
    classes = _dedupe_sorted(continuity_classes or [])
    threads = _dedupe_sorted(thread_ids or [])
    entities = _dedupe_sorted(related_entities or [])
    branch_ids = _dedupe_sorted(branch_tree_ids or [])
    source_turn_id = str(source.get("turn_id") or "")
    target_turn_id = str(target.get("turn_id") or "")
    seed = {
        "story_session_id": story_session_id,
        "callback_kind": callback_kind,
        "source_turn_id": source_turn_id,
        "target_turn_id": target_turn_id,
        "continuity_classes": classes,
        "thread_ids": threads,
        "branch_tree_ids": branch_ids,
    }
    return {
        "schema_version": CALLBACK_EDGE_SCHEMA_VERSION,
        "edge_id": _edge_id(seed),
        "callback_kind": callback_kind,
        "source_turn_id": source_turn_id,
        "target_turn_id": target_turn_id,
        "source_turn_number": int(source.get("turn_number") or 0),
        "target_turn_number": int(target.get("turn_number") or 0),
        "thread_ids": threads,
        "continuity_classes": classes,
        "related_entities": entities,
        "branch_tree_ids": branch_ids,
        "evidence": {
            "source_fields": _dedupe_sorted(evidence_fields or []),
            "signal_hashes": _dedupe_sorted(evidence_hashes or []),
        },
        "confidence": max(0.0, min(1.0, float(confidence))),
        "non_authoritative": True,
        "mutates_canonical_state": False,
    }


def _edges_from_observations(*, story_session_id: str, observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: dict[str, dict[str, Any]] = {}
    for idx, target in enumerate(observations):
        target_turn = int(target.get("turn_number") or 0)
        for source in observations[:idx]:
            source_turn = int(source.get("turn_number") or 0)
            if not target_turn or source_turn >= target_turn:
                continue
            shared_classes = sorted(
                set(source.get("continuity_classes") or []).intersection(target.get("continuity_classes") or [])
            )
            if shared_classes:
                edge = _make_edge(
                    story_session_id=story_session_id,
                    callback_kind=CALLBACK_EDGE_KIND_REPEATED_CONTINUITY_CLASS,
                    source=source,
                    target=target,
                    continuity_classes=shared_classes,
                    related_entities=sorted(
                        set(source.get("related_entities") or []).intersection(target.get("related_entities") or [])
                    ),
                    evidence_fields=["narrative_commit.planner_truth.continuity_impacts"],
                    evidence_hashes=list(source.get("signal_hashes") or []) + list(target.get("signal_hashes") or []),
                    confidence=0.75,
                )
                edges[edge["edge_id"]] = edge
            shared_threads = sorted(set(source.get("thread_ids") or []).intersection(target.get("thread_ids") or []))
            if shared_threads:
                edge = _make_edge(
                    story_session_id=story_session_id,
                    callback_kind=CALLBACK_EDGE_KIND_THREAD_CONTINUITY,
                    source=source,
                    target=target,
                    thread_ids=shared_threads,
                    continuity_classes=shared_classes,
                    evidence_fields=["session.narrative_threads"],
                    confidence=0.7,
                )
                edges[edge["edge_id"]] = edge
            if source.get("scene_id") and source.get("scene_id") == target.get("scene_id") and target_turn - source_turn > 1:
                edge = _make_edge(
                    story_session_id=story_session_id,
                    callback_kind=CALLBACK_EDGE_KIND_REPEATED_SCENE_ANCHOR,
                    source=source,
                    target=target,
                    continuity_classes=shared_classes,
                    evidence_fields=["narrative_commit.committed_scene_id"],
                    confidence=0.45,
                )
                edges[edge["edge_id"]] = edge
    return list(edges.values())


def _turn_by_id(observations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(obs.get("turn_id")): obs for obs in observations if obs.get("turn_id")}


def _edges_from_branch_timeline(
    *,
    story_session_id: str,
    observations: list[dict[str, Any]],
    branch_timeline: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(branch_timeline, dict):
        return []
    by_id = _turn_by_id(observations)
    events = branch_timeline.get("events") if isinstance(branch_timeline.get("events"), list) else []
    tree_roots: dict[str, str] = {}
    edges: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "")
        tree_id = str(event.get("tree_id") or "").strip()
        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        root_turn_id = str(details.get("root_canonical_turn_id") or "").strip()
        if tree_id and root_turn_id:
            tree_roots.setdefault(tree_id, root_turn_id)
        if event_type not in {"selection_replay_committed", "selection_replay_conflict"}:
            continue
        target_turn_id = str(event.get("canonical_turn_id") or "").strip()
        source_turn_id = tree_roots.get(tree_id, "")
        if not source_turn_id or not target_turn_id:
            continue
        source = by_id.get(source_turn_id)
        target = by_id.get(target_turn_id)
        if not source or not target:
            continue
        edge = _make_edge(
            story_session_id=story_session_id,
            callback_kind=CALLBACK_EDGE_KIND_BRANCH_SELECTION_REALIZED,
            source=source,
            target=target,
            branch_tree_ids=[tree_id],
            continuity_classes=sorted(
                set(source.get("continuity_classes") or []).intersection(target.get("continuity_classes") or [])
            ),
            evidence_fields=["branch_timeline.events", "branching_tree.selection"],
            evidence_hashes=[_stable_hash(event, 12)],
            confidence=0.8,
        )
        edges.append(edge)
    return edges


def _bounded_edges(edges: list[dict[str, Any]], bounds: dict[str, int]) -> list[dict[str, Any]]:
    keyed = {str(edge.get("edge_id")): edge for edge in edges if edge.get("edge_id")}
    rows = []
    for edge in keyed.values():
        row = dict(edge)
        evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
        if evidence:
            row["evidence"] = {
                "source_fields": _dedupe_sorted(
                    evidence.get("source_fields") if isinstance(evidence.get("source_fields"), list) else [],
                    limit=bounds["max_evidence_refs"],
                ),
                "signal_hashes": _dedupe_sorted(
                    evidence.get("signal_hashes") if isinstance(evidence.get("signal_hashes"), list) else [],
                    limit=bounds["max_evidence_refs"],
                ),
            }
        rows.append(row)
    rows.sort(
        key=lambda edge: (
            int(edge.get("target_turn_number") or 0),
            int(edge.get("source_turn_number") or 0),
            str(edge.get("callback_kind") or ""),
            str(edge.get("edge_id") or ""),
        )
    )
    if len(rows) > bounds["max_edges"]:
        rows = rows[-bounds["max_edges"] :]
    return rows


def build_callback_web_snapshot(record: dict[str, Any]) -> dict[str, Any]:
    edges = record.get("edges") if isinstance(record.get("edges"), list) else []
    observations = record.get("observations") if isinstance(record.get("observations"), list) else []
    kind_counts: dict[str, int] = {}
    classes: list[str] = []
    thread_ids: list[str] = []
    branch_tree_ids: list[str] = []
    latest_turn_id = None
    latest_turn_number = 0
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        kind = str(edge.get("callback_kind") or "")
        if kind:
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        classes.extend(edge.get("continuity_classes") if isinstance(edge.get("continuity_classes"), list) else [])
        thread_ids.extend(edge.get("thread_ids") if isinstance(edge.get("thread_ids"), list) else [])
        branch_tree_ids.extend(edge.get("branch_tree_ids") if isinstance(edge.get("branch_tree_ids"), list) else [])
    for obs in observations:
        if not isinstance(obs, dict):
            continue
        turn_number = int(obs.get("turn_number") or 0)
        if turn_number >= latest_turn_number:
            latest_turn_number = turn_number
            latest_turn_id = obs.get("turn_id")
    return {
        "schema_version": CALLBACK_WEB_SNAPSHOT_SCHEMA_VERSION,
        "callback_web_id": record.get("callback_web_id"),
        "story_session_id": record.get("story_session_id"),
        "edge_count": len(edges),
        "observation_count": len(observations),
        "callback_kind_counts": dict(sorted(kind_counts.items())),
        "continuity_classes": _dedupe_sorted(classes, limit=16),
        "thread_ids": _dedupe_sorted(thread_ids, limit=16),
        "branch_tree_ids": _dedupe_sorted(branch_tree_ids, limit=16),
        "latest_turn_id": latest_turn_id,
        "latest_turn_number": latest_turn_number,
        "non_authoritative": True,
        "mutates_canonical_state": False,
    }


def build_graph_callback_web_export(
    record: dict[str, Any] | None,
    *,
    max_edges: int = 4,
) -> dict[str, Any] | None:
    """Project callback-web record into a tight graph feedback payload."""
    if not isinstance(record, dict):
        return None
    snapshot = record.get("snapshot") if isinstance(record.get("snapshot"), dict) else {}
    if not snapshot:
        snapshot = build_callback_web_snapshot(record)
    edges = record.get("edges") if isinstance(record.get("edges"), list) else []
    bounded_edges = [
        edge for edge in edges
        if isinstance(edge, dict) and edge.get("edge_id") and edge.get("target_turn_id")
    ]
    bounded_edges.sort(
        key=lambda edge: (
            int(edge.get("target_turn_number") or 0),
            int(edge.get("source_turn_number") or 0),
            str(edge.get("callback_kind") or ""),
            str(edge.get("edge_id") or ""),
        ),
        reverse=True,
    )
    edge_limit = max(1, min(16, int(max_edges or 4)))
    graph_edges: list[dict[str, Any]] = []
    for edge in bounded_edges[:edge_limit]:
        graph_edges.append(
            {
                "edge_id": edge.get("edge_id"),
                "callback_kind": edge.get("callback_kind"),
                "source_turn_id": edge.get("source_turn_id"),
                "target_turn_id": edge.get("target_turn_id"),
                "source_turn_number": int(edge.get("source_turn_number") or 0),
                "target_turn_number": int(edge.get("target_turn_number") or 0),
                "continuity_classes": list(edge.get("continuity_classes") or [])[:4],
                "thread_ids": list(edge.get("thread_ids") or [])[:4],
                "branch_tree_ids": list(edge.get("branch_tree_ids") or [])[:4],
                "confidence": edge.get("confidence"),
                "non_authoritative": True,
                "mutates_canonical_state": False,
            }
        )
    selected = graph_edges[0] if graph_edges else {}
    selected_classes = (
        selected.get("continuity_classes")
        if isinstance(selected.get("continuity_classes"), list)
        else []
    )
    selected_threads = (
        selected.get("thread_ids") if isinstance(selected.get("thread_ids"), list) else []
    )
    if not graph_edges and int(snapshot.get("observation_count") or 0) <= 0:
        return None
    return {
        "feedback_contract": CALLBACK_WEB_FEEDBACK_CONTRACT,
        "source": "session.callback_web",
        "callback_web_id": record.get("callback_web_id") or snapshot.get("callback_web_id"),
        "edge_count": int(snapshot.get("edge_count") or len(edges)),
        "observation_count": int(snapshot.get("observation_count") or 0),
        "exported_edge_count": len(graph_edges),
        "selected_callback_edge_id": selected.get("edge_id"),
        "selected_callback_kind": selected.get("callback_kind"),
        "selected_continuity_classes": selected_classes,
        "selected_thread_ids": selected_threads,
        "edges": graph_edges,
        "continuity_classes": list(snapshot.get("continuity_classes") or [])[:8],
        "thread_ids": list(snapshot.get("thread_ids") or [])[:8],
        "non_authoritative": True,
        "mutates_canonical_state": False,
    }


def build_callback_web_record(
    *,
    story_session_id: str,
    module_id: str | None = None,
    runtime_profile_id: str | None = None,
    history: list[dict[str, Any]] | None = None,
    narrative_threads: Any = None,
    branch_timeline: dict[str, Any] | None = None,
    current_session_fingerprint: dict[str, Any] | None = None,
    bounds: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    normalized_bounds = normalize_callback_web_bounds(bounds)
    rows = committed_story_truth_rows(history)
    observations = [
        obs
        for obs in (_observation_for_row(row=row, narrative_threads=narrative_threads) for row in rows)
        if isinstance(obs, dict)
    ]
    observations.sort(key=lambda obs: (int(obs.get("turn_number") or 0), str(obs.get("turn_id") or "")))
    if len(observations) > normalized_bounds["max_observations"]:
        observations = observations[-normalized_bounds["max_observations"] :]
    edges = _edges_from_observations(story_session_id=story_session_id, observations=observations)
    edges.extend(
        _edges_from_branch_timeline(
            story_session_id=story_session_id,
            observations=observations,
            branch_timeline=branch_timeline,
        )
    )
    edges = _bounded_edges(edges, normalized_bounds)
    now = created_at or _now_iso()
    record = {
        "schema_version": CALLBACK_WEB_RECORD_SCHEMA_VERSION,
        "source": CALLBACK_WEB_RECORD_SOURCE,
        "callback_web_id": stable_callback_web_id(story_session_id=story_session_id),
        "story_session_id": story_session_id,
        "module_id": module_id,
        "runtime_profile_id": runtime_profile_id,
        "status": "active",
        "bounds": normalized_bounds,
        "source_inputs": {
            "history_count": len(rows),
            "active_thread_count": len(
                [
                    thread
                    for thread in _thread_dicts(narrative_threads)
                    if str(thread.get("status") or "") != "resolved"
                ]
            ),
            "branch_timeline_event_count": len(branch_timeline.get("events") or [])
            if isinstance(branch_timeline, dict) and isinstance(branch_timeline.get("events"), list)
            else 0,
        },
        "current_session_fingerprint": _json_safe(current_session_fingerprint or {}),
        "observations": _json_safe(observations),
        "edges": _json_safe(edges),
        "created_at": now,
        "updated_at": _now_iso(),
        "non_authoritative": True,
        "mutates_canonical_state": False,
    }
    record["snapshot"] = build_callback_web_snapshot(record)
    return record
