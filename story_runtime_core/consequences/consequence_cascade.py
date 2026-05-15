"""Deterministic consequence-cascade derivation from committed story truth.

The consequence cascade is a bounded committed-state projection. It connects
consequence atoms across turns when committed continuity classes, narrative
threads, or realized branch selections show that a consequence is still shaping
later play. It does not mutate canonical history.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from story_runtime_core.branching import (
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_CONFLICT,
)


CONSEQUENCE_CASCADE_RECORD_SCHEMA_VERSION = "consequence_cascade_record.v1"
CONSEQUENCE_ATOM_SCHEMA_VERSION = "consequence_atom.v1"
CONSEQUENCE_EDGE_SCHEMA_VERSION = "consequence_edge.v1"
CONSEQUENCE_CASCADE_SNAPSHOT_SCHEMA_VERSION = "consequence_cascade_snapshot.v1"
CONSEQUENCE_CASCADE_FEEDBACK_CONTRACT = "consequence_cascade_feedback.v1"
CONSEQUENCE_CASCADE_RECORD_SOURCE = "world_engine_consequence_cascade"

CONSEQUENCE_EDGE_KIND_CARRY_FORWARD = "carry_forward"
CONSEQUENCE_EDGE_KIND_THREAD_CONTINUITY = "thread_continuity"
CONSEQUENCE_EDGE_KIND_RESOLUTION = "resolution"
CONSEQUENCE_EDGE_KIND_BRANCH_SELECTION_REALIZED = "branch_selection_realized"
CONSEQUENCE_EDGE_KINDS = (
    CONSEQUENCE_EDGE_KIND_CARRY_FORWARD,
    CONSEQUENCE_EDGE_KIND_THREAD_CONTINUITY,
    CONSEQUENCE_EDGE_KIND_RESOLUTION,
    CONSEQUENCE_EDGE_KIND_BRANCH_SELECTION_REALIZED,
)

CONSEQUENCE_STATUS_ACTIVE = "active"
CONSEQUENCE_STATUS_FADING = "fading"
CONSEQUENCE_STATUS_RESOLVED = "resolved"
CONSEQUENCE_STATUSES = (
    CONSEQUENCE_STATUS_ACTIVE,
    CONSEQUENCE_STATUS_FADING,
    CONSEQUENCE_STATUS_RESOLVED,
)

CONSEQUENCE_CASCADE_DEFAULT_MAX_ATOMS = 80
CONSEQUENCE_CASCADE_DEFAULT_MAX_EDGES = 120
CONSEQUENCE_CASCADE_DEFAULT_MAX_EVIDENCE_REFS = 8
CONSEQUENCE_CASCADE_DEFAULT_DECAY_AFTER_TURNS = 4
CONSEQUENCE_CASCADE_MIN_MAX_ATOMS = 8
CONSEQUENCE_CASCADE_MIN_MAX_EDGES = 8


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


def _short(value: Any, limit: int = 96) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def default_consequence_cascade_bounds() -> dict[str, int]:
    return {
        "max_atoms": CONSEQUENCE_CASCADE_DEFAULT_MAX_ATOMS,
        "max_edges": CONSEQUENCE_CASCADE_DEFAULT_MAX_EDGES,
        "max_evidence_refs": CONSEQUENCE_CASCADE_DEFAULT_MAX_EVIDENCE_REFS,
        "decay_after_turns": CONSEQUENCE_CASCADE_DEFAULT_DECAY_AFTER_TURNS,
    }


def normalize_consequence_cascade_bounds(bounds: dict[str, Any] | None = None) -> dict[str, int]:
    out = default_consequence_cascade_bounds()
    if isinstance(bounds, dict):
        for key in tuple(out):
            if key in bounds:
                try:
                    out[key] = int(bounds[key])
                except (TypeError, ValueError):
                    continue
    out["max_atoms"] = max(CONSEQUENCE_CASCADE_MIN_MAX_ATOMS, out["max_atoms"])
    out["max_edges"] = max(CONSEQUENCE_CASCADE_MIN_MAX_EDGES, out["max_edges"])
    out["max_evidence_refs"] = max(1, out["max_evidence_refs"])
    out["decay_after_turns"] = max(1, out["decay_after_turns"])
    return out


def stable_consequence_cascade_id(*, story_session_id: str) -> str:
    digest = hashlib.sha256(str(story_session_id).encode("utf-8")).hexdigest()[:16]
    return f"consequence_cascade_{digest}"


def _commit_from_row(row: dict[str, Any]) -> dict[str, Any]:
    commit = row.get("narrative_commit") if isinstance(row.get("narrative_commit"), dict) else {}
    return dict(commit)


def _planner_truth(commit: dict[str, Any]) -> dict[str, Any]:
    value = commit.get("planner_truth")
    return dict(value) if isinstance(value, dict) else {}


def _continuity_impacts_for_commit(commit: dict[str, Any]) -> list[dict[str, Any]]:
    planner = _planner_truth(commit)
    out: list[dict[str, Any]] = []
    for raw in (planner.get("continuity_impacts"), commit.get("continuity_impacts")):
        if not isinstance(raw, list):
            continue
        for item in raw:
            if not isinstance(item, dict):
                continue
            label = ""
            for key in ("class", "continuity_class", "kind", "type"):
                label = str(item.get(key) or "").strip()
                if label:
                    break
            if label:
                out.append({**item, "continuity_class": label})
    beat = commit.get("beat_progression") if isinstance(commit.get("beat_progression"), dict) else {}
    pressure = str(beat.get("pressure_state") or "").strip()
    if pressure:
        out.append({"continuity_class": pressure, "source": "beat_progression.pressure_state"})
    deduped: dict[str, dict[str, Any]] = {}
    for item in out:
        deduped.setdefault(str(item["continuity_class"]), item)
    return list(deduped.values())


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


def _signal_hashes_for_commit(commit: dict[str, Any], *, max_refs: int) -> list[str]:
    values: list[str] = []
    for key in ("open_pressures", "committed_consequences", "resolved_pressures"):
        raw = commit.get(key)
        if isinstance(raw, list):
            values.extend(_short(x, 96) for x in raw if str(x or "").strip())
    return [_stable_hash(value, length=12) for value in _dedupe_sorted(values, limit=max_refs)]


def _resolved_classes_for_commit(commit: dict[str, Any]) -> list[str]:
    raw = commit.get("resolved_pressures")
    if not isinstance(raw, list):
        return []
    return _dedupe_sorted(raw, limit=16)


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


def _threads_for_atom(*, scene_id: str, continuity_class: str, narrative_threads: Any) -> list[str]:
    scene = str(scene_id or "").strip()
    out: list[str] = []
    for thread in _thread_dicts(narrative_threads):
        thread_id = str(thread.get("thread_id") or "").strip()
        if not thread_id:
            continue
        thread_kind = str(thread.get("thread_kind") or "").strip()
        related_scenes = {str(x) for x in thread.get("related_scenes") or []}
        if thread_kind and thread_kind == continuity_class:
            out.append(thread_id)
            continue
        if scene and (scene == str(thread.get("scene_anchor") or "") or scene in related_scenes):
            out.append(thread_id)
    return _dedupe_sorted(out, limit=8)


def _atoms_for_row(
    *,
    row: dict[str, Any],
    story_session_id: str,
    narrative_threads: Any,
    latest_turn_number: int,
    bounds: dict[str, int],
) -> list[dict[str, Any]]:
    turn_id = str(row.get("canonical_turn_id") or "").strip()
    if not turn_id:
        return []
    commit = _commit_from_row(row)
    turn_number = int(row.get("turn_number") or commit.get("turn_number") or 0)
    scene_id = str(commit.get("committed_scene_id") or row.get("current_scene_id") or "").strip()
    resolved_classes = set(_resolved_classes_for_commit(commit))
    entities = _entities_for_commit(commit)
    age = max(0, latest_turn_number - turn_number)
    atoms: list[dict[str, Any]] = []
    for idx, impact in enumerate(_continuity_impacts_for_commit(commit)):
        continuity_class = str(impact.get("continuity_class") or "").strip()
        if not continuity_class:
            continue
        status = CONSEQUENCE_STATUS_ACTIVE
        if continuity_class in resolved_classes:
            status = CONSEQUENCE_STATUS_RESOLVED
        elif age >= bounds["decay_after_turns"]:
            status = CONSEQUENCE_STATUS_FADING
        consequence_id = "cons_" + _stable_hash(
            {
                "story_session_id": story_session_id,
                "turn_id": turn_id,
                "turn_number": turn_number,
                "continuity_class": continuity_class,
                "idx": idx,
            },
            length=18,
        )
        source_note = str(impact.get("note") or impact.get("source") or "").strip()
        source_fields = ["narrative_commit.planner_truth.continuity_impacts"]
        if source_note == "beat_progression.pressure_state":
            source_fields = ["narrative_commit.beat_progression.pressure_state"]
        signal_hashes = _signal_hashes_for_commit(
            commit,
            max_refs=max(0, bounds["max_evidence_refs"] - len(source_fields)),
        )
        atoms.append(
            {
                "schema_version": CONSEQUENCE_ATOM_SCHEMA_VERSION,
                "consequence_id": consequence_id,
                "source_turn_id": turn_id,
                "source_turn_number": turn_number,
                "source_kind": "continuity_impact",
                "source_field": source_fields[0],
                "scene_id": scene_id or None,
                "continuity_class": continuity_class,
                "related_entities": entities,
                "thread_ids": _threads_for_atom(
                    scene_id=scene_id,
                    continuity_class=continuity_class,
                    narrative_threads=narrative_threads,
                ),
                "status": status,
                "freshness_turns": age,
                "salience": max(0.1, 1.0 - (age * 0.12)),
                "evidence": {
                    "source_fields": source_fields[: bounds["max_evidence_refs"]],
                    "signal_hashes": signal_hashes[: bounds["max_evidence_refs"]],
                },
                "derived_from_committed_truth": True,
                "mutates_canonical_state": False,
            }
        )
    return atoms


def _make_edge(
    *,
    story_session_id: str,
    edge_kind: str,
    source: dict[str, Any],
    target: dict[str, Any],
    continuity_class: str | None = None,
    thread_ids: list[str] | None = None,
    evidence_fields: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "story_session_id": story_session_id,
        "edge_kind": edge_kind,
        "source": source.get("consequence_id"),
        "target": target.get("consequence_id"),
        "continuity_class": continuity_class,
        "thread_ids": thread_ids or [],
    }
    return {
        "schema_version": CONSEQUENCE_EDGE_SCHEMA_VERSION,
        "edge_id": "cascade_edge_" + _stable_hash(payload, length=18),
        "edge_kind": edge_kind,
        "source_consequence_id": source.get("consequence_id"),
        "target_consequence_id": target.get("consequence_id"),
        "source_turn_id": source.get("source_turn_id"),
        "target_turn_id": target.get("source_turn_id"),
        "source_turn_number": source.get("source_turn_number"),
        "target_turn_number": target.get("source_turn_number"),
        "continuity_class": continuity_class,
        "thread_ids": _dedupe_sorted(thread_ids or [], limit=8),
        "evidence": {"source_fields": evidence_fields or []},
        "derived_from_committed_truth": True,
        "mutates_canonical_state": False,
        "inactive_branch_authoritative": False,
    }


def _edges_from_atoms(*, story_session_id: str, atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: dict[str, dict[str, Any]] = {}
    for idx, target in enumerate(atoms):
        target_turn = int(target.get("source_turn_number") or 0)
        target_class = str(target.get("continuity_class") or "").strip()
        for source in atoms[:idx]:
            source_turn = int(source.get("source_turn_number") or 0)
            if not target_turn or source_turn >= target_turn:
                continue
            source_class = str(source.get("continuity_class") or "").strip()
            if source_class and source_class == target_class:
                edge = _make_edge(
                    story_session_id=story_session_id,
                    edge_kind=CONSEQUENCE_EDGE_KIND_CARRY_FORWARD,
                    source=source,
                    target=target,
                    continuity_class=target_class,
                    evidence_fields=["narrative_commit.planner_truth.continuity_impacts"],
                )
                edges[edge["edge_id"]] = edge
            shared_threads = sorted(set(source.get("thread_ids") or []).intersection(target.get("thread_ids") or []))
            if shared_threads:
                edge = _make_edge(
                    story_session_id=story_session_id,
                    edge_kind=CONSEQUENCE_EDGE_KIND_THREAD_CONTINUITY,
                    source=source,
                    target=target,
                    continuity_class=target_class or source_class or None,
                    thread_ids=shared_threads,
                    evidence_fields=["session.narrative_threads"],
                )
                edges[edge["edge_id"]] = edge
            if target.get("status") == CONSEQUENCE_STATUS_RESOLVED and source_class == target_class:
                edge = _make_edge(
                    story_session_id=story_session_id,
                    edge_kind=CONSEQUENCE_EDGE_KIND_RESOLUTION,
                    source=source,
                    target=target,
                    continuity_class=target_class,
                    evidence_fields=["narrative_commit.resolved_pressures"],
                )
                edges[edge["edge_id"]] = edge
    return list(edges.values())


def _turn_by_id(atoms: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for atom in atoms:
        turn_id = str(atom.get("source_turn_id") or "").strip()
        if turn_id:
            out.setdefault(turn_id, []).append(atom)
    return out


def _edges_from_branch_timeline(
    *,
    story_session_id: str,
    atoms: list[dict[str, Any]],
    branch_timeline: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(branch_timeline, dict):
        return []
    by_turn = _turn_by_id(atoms)
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
        if event_type not in {
            BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
            BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_CONFLICT,
        }:
            continue
        target_turn_id = str(event.get("canonical_turn_id") or "").strip()
        source_turn_id = tree_roots.get(tree_id, "")
        if not source_turn_id or not target_turn_id:
            continue
        for source in by_turn.get(source_turn_id, [])[:2]:
            for target in by_turn.get(target_turn_id, [])[:2]:
                edge = _make_edge(
                    story_session_id=story_session_id,
                    edge_kind=CONSEQUENCE_EDGE_KIND_BRANCH_SELECTION_REALIZED,
                    source=source,
                    target=target,
                    continuity_class=target.get("continuity_class") or source.get("continuity_class"),
                    evidence_fields=["branch_timeline.events"],
                )
                edges.append(edge)
    return edges


def _snapshot(*, cascade_id: str, atoms: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    edge_kind_counts: dict[str, int] = {}
    classes: list[str] = []
    for atom in atoms:
        status = str(atom.get("status") or "").strip()
        if status:
            status_counts[status] = status_counts.get(status, 0) + 1
        cls = str(atom.get("continuity_class") or "").strip()
        if cls:
            classes.append(cls)
    for edge in edges:
        kind = str(edge.get("edge_kind") or "").strip()
        if kind:
            edge_kind_counts[kind] = edge_kind_counts.get(kind, 0) + 1
    return {
        "schema_version": CONSEQUENCE_CASCADE_SNAPSHOT_SCHEMA_VERSION,
        "cascade_id": cascade_id,
        "atom_count": len(atoms),
        "edge_count": len(edges),
        "active_atom_count": status_counts.get(CONSEQUENCE_STATUS_ACTIVE, 0),
        "status_counts": status_counts,
        "edge_kind_counts": edge_kind_counts,
        "continuity_classes": _dedupe_sorted(classes),
    }


def build_consequence_cascade_record(
    *,
    story_session_id: str | None,
    module_id: str | None,
    runtime_profile_id: str | None = None,
    history: list[dict[str, Any]] | None = None,
    narrative_threads: Any = None,
    branch_timeline: dict[str, Any] | None = None,
    callback_web: dict[str, Any] | None = None,
    bounds: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    bounded = normalize_consequence_cascade_bounds(bounds)
    rows = [dict(row) for row in (history or []) if isinstance(row, dict)]
    latest_turn_number = 0
    for row in rows:
        try:
            latest_turn_number = max(latest_turn_number, int(row.get("turn_number") or 0))
        except (TypeError, ValueError):
            continue
    session_id = str(story_session_id or "").strip()
    cascade_id = stable_consequence_cascade_id(story_session_id=session_id)
    atoms: list[dict[str, Any]] = []
    for row in rows:
        atoms.extend(
            _atoms_for_row(
                row=row,
                story_session_id=session_id,
                narrative_threads=narrative_threads,
                latest_turn_number=latest_turn_number,
                bounds=bounded,
            )
        )
    atoms.sort(
        key=lambda atom: (
            int(atom.get("source_turn_number") or 0),
            str(atom.get("continuity_class") or ""),
            str(atom.get("consequence_id") or ""),
        )
    )
    atoms = atoms[-bounded["max_atoms"] :]
    edges = _edges_from_atoms(story_session_id=session_id, atoms=atoms)
    edges.extend(
        _edges_from_branch_timeline(
            story_session_id=session_id,
            atoms=atoms,
            branch_timeline=branch_timeline,
        )
    )
    unique_edges: dict[str, dict[str, Any]] = {}
    for edge in edges:
        unique_edges[str(edge.get("edge_id"))] = edge
    edges = list(unique_edges.values())[-bounded["max_edges"] :]
    now = _now_iso()
    record = {
        "schema_version": CONSEQUENCE_CASCADE_RECORD_SCHEMA_VERSION,
        "cascade_id": cascade_id,
        "story_session_id": session_id,
        "module_id": str(module_id or "").strip() or None,
        "runtime_profile_id": str(runtime_profile_id or "").strip() or None,
        "source": CONSEQUENCE_CASCADE_RECORD_SOURCE,
        "created_at": created_at or now,
        "updated_at": now,
        "bounds": bounded,
        "derived_from_committed_truth": True,
        "mutates_canonical_state": False,
        "forecast_only": False,
        "inactive_branches_authoritative": False,
        "callback_web_id": callback_web.get("callback_web_id") if isinstance(callback_web, dict) else None,
        "atoms": atoms,
        "edges": edges,
    }
    record["snapshot"] = _snapshot(cascade_id=cascade_id, atoms=atoms, edges=edges)
    return _json_safe(record)


def build_graph_consequence_cascade_export(
    record: dict[str, Any] | None,
    *,
    max_items: int = 5,
) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    atoms = record.get("atoms") if isinstance(record.get("atoms"), list) else []
    edges = record.get("edges") if isinstance(record.get("edges"), list) else []
    max_n = max(1, int(max_items or 1))
    active_atoms = [
        atom for atom in atoms if isinstance(atom, dict) and atom.get("status") == CONSEQUENCE_STATUS_ACTIVE
    ]
    ranked_atoms = sorted(
        active_atoms or [atom for atom in atoms if isinstance(atom, dict)],
        key=lambda atom: (
            float(atom.get("salience") or 0),
            int(atom.get("source_turn_number") or 0),
        ),
        reverse=True,
    )[:max_n]
    selected_ids = [str(atom.get("consequence_id")) for atom in ranked_atoms if atom.get("consequence_id")]
    selected_classes = _dedupe_sorted([atom.get("continuity_class") for atom in ranked_atoms])
    selected_statuses = _dedupe_sorted([atom.get("status") for atom in ranked_atoms])
    selected_edges = [
        edge
        for edge in edges
        if isinstance(edge, dict)
        and (
            edge.get("source_consequence_id") in selected_ids
            or edge.get("target_consequence_id") in selected_ids
        )
    ][:max_n]
    return _json_safe(
        {
            "feedback_contract": CONSEQUENCE_CASCADE_FEEDBACK_CONTRACT,
            "cascade_id": record.get("cascade_id"),
            "atom_count": len(atoms),
            "edge_count": len(edges),
            "selected_consequence_ids": selected_ids,
            "selected_edge_ids": [
                str(edge.get("edge_id")) for edge in selected_edges if edge.get("edge_id")
            ],
            "selected_continuity_classes": selected_classes,
            "selected_statuses": selected_statuses,
            "exported_item_count": len(ranked_atoms),
            "items": [
                {
                    "consequence_id": atom.get("consequence_id"),
                    "source_turn_number": atom.get("source_turn_number"),
                    "source_turn_id": atom.get("source_turn_id"),
                    "continuity_class": atom.get("continuity_class"),
                    "status": atom.get("status"),
                    "freshness_turns": atom.get("freshness_turns"),
                    "thread_ids": list(atom.get("thread_ids") or [])[:4],
                }
                for atom in ranked_atoms
            ],
            "edges": [
                {
                    "edge_id": edge.get("edge_id"),
                    "edge_kind": edge.get("edge_kind"),
                    "source_consequence_id": edge.get("source_consequence_id"),
                    "target_consequence_id": edge.get("target_consequence_id"),
                    "continuity_class": edge.get("continuity_class"),
                    "thread_ids": list(edge.get("thread_ids") or [])[:4],
                }
                for edge in selected_edges
            ],
        }
    )
