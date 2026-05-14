"""Generic hierarchical memory contracts for committed story-runtime turns.

Hierarchical memory is a bounded projection of canonical committed truth.  It is
not a prompt log, not a transcript store, and not an independent authority
source.  The engine owns generic selection, write, merge, and projection rules;
content modules own the policy that enables tiers and retention.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
from typing import Any


HIERARCHICAL_MEMORY_POLICY_SCHEMA_VERSION = "hierarchical_memory_policy.v1"
HIERARCHICAL_MEMORY_SNAPSHOT_SCHEMA_VERSION = "hierarchical_memory_snapshot.v1"
HIERARCHICAL_MEMORY_ITEM_SCHEMA_VERSION = "hierarchical_memory_item.v1"
HIERARCHICAL_MEMORY_WRITE_SCHEMA_VERSION = "hierarchical_memory_write.v1"
HIERARCHICAL_MEMORY_CONTEXT_SCHEMA_VERSION = "hierarchical_memory_context.v1"

MEMORY_TIERS: tuple[str, ...] = ("turn", "session", "actor", "module", "long_term")
DEFAULT_TIER_LIMITS: dict[str, int] = {
    "turn": 12,
    "session": 8,
    "actor": 16,
    "module": 4,
    "long_term": 0,
}
DEFAULT_CONTEXT_LIMITS: dict[str, int] = {
    "turn": 4,
    "session": 4,
    "actor": 6,
    "module": 2,
    "long_term": 2,
}
FORBIDDEN_TEXT_KEY_PARTS: tuple[str, ...] = (
    "authorization",
    "context_text",
    "password",
    "prompt",
    "rag_payload",
    "raw_prompt",
    "retrieval_context",
    "secret",
    "token",
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None:
        return []
    return [value]


def _text(value: Any, *, max_chars: int = 160) -> str:
    raw = str(value or "").replace("\n", " ").strip()
    text = " ".join(raw.split())
    if len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text


def _unique_texts(values: Any, *, max_items: int = 12, max_chars: int = 80) -> list[str]:
    out: list[str] = []
    def visit(value: Any) -> None:
        if len(out) >= max_items:
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                visit(item)
            return
        text = _text(value, max_chars=max_chars)
        if text and text not in out:
            out.append(text)

    for value in _as_list(values):
        visit(value)
        if len(out) >= max_items:
            break
    return out


def _safe_key(key: str) -> bool:
    lowered = str(key or "").lower()
    return not any(part in lowered for part in FORBIDDEN_TEXT_KEY_PARTS)


def _safe_dict(payload: dict[str, Any], *, max_items: int = 12) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if len(out) >= max_items:
            break
        skey = str(key)
        if not _safe_key(skey):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[skey] = _text(value) if isinstance(value, str) else value
        elif isinstance(value, list):
            out[skey] = _unique_texts(value)
        elif isinstance(value, dict):
            nested: dict[str, Any] = {}
            for nkey, nvalue in value.items():
                if len(nested) >= 6:
                    break
                if _safe_key(str(nkey)) and not isinstance(nvalue, (dict, list)):
                    nested[str(nkey)] = _text(nvalue) if isinstance(nvalue, str) else nvalue
            out[skey] = nested
    return _json_safe(out)


def _aspect_record(ledger: dict[str, Any], aspect_name: str) -> dict[str, Any]:
    aspects = ledger.get("turn_aspect_ledger") if isinstance(ledger.get("turn_aspect_ledger"), dict) else {}
    row = aspects.get(aspect_name) if isinstance(aspects, dict) else {}
    return row if isinstance(row, dict) else {}


def _aspect_block(ledger: dict[str, Any], aspect_name: str, block_name: str) -> dict[str, Any]:
    record = _aspect_record(ledger, aspect_name)
    block = record.get(block_name) if isinstance(record.get(block_name), dict) else {}
    return block if isinstance(block, dict) else {}


def _projection(ledger: dict[str, Any]) -> dict[str, Any]:
    projection = ledger.get("runtime_intelligence_projection")
    return projection if isinstance(projection, dict) else {}


def _stable_id(*parts: Any) -> str:
    base = "|".join(_text(part, max_chars=220) for part in parts)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class HierarchicalMemoryTierPolicy:
    id: str
    enabled: bool = True
    max_items: int = 8
    max_context_items: int = 4
    retention: str = "session"
    write_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class HierarchicalMemoryItem:
    tier: str
    item_id: str
    source_canonical_turn_id: str
    source_turn_number: int
    module_id: str | None = None
    runtime_profile_id: str | None = None
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    actor_ids: list[str] = field(default_factory=list)
    location_ids: list[str] = field(default_factory=list)
    capability_ids: list[str] = field(default_factory=list)
    beat_id: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    schema_version: str = HIERARCHICAL_MEMORY_ITEM_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class HierarchicalMemoryWriteResult:
    status: str
    policy_present: bool
    policy_enabled: bool
    write_allowed: bool
    source_canonical_turn_id: str | None = None
    selected_tiers: list[str] = field(default_factory=list)
    written_items: list[dict[str, Any]] = field(default_factory=list)
    skipped_tiers: list[str] = field(default_factory=list)
    failure_reason: str | None = None
    uncommitted_write_detected: bool = False
    schema_version: str = HIERARCHICAL_MEMORY_WRITE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


def normalize_hierarchical_memory_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return a JSON-safe, module-neutral hierarchical memory policy."""
    src = policy if isinstance(policy, dict) else {}
    enabled = bool(src.get("enabled", False))
    raw_tiers = src.get("tiers") if isinstance(src.get("tiers"), list) else []
    by_id: dict[str, dict[str, Any]] = {}
    for raw in raw_tiers:
        if not isinstance(raw, dict):
            continue
        tier_id = _text(raw.get("id"), max_chars=48)
        if tier_id in MEMORY_TIERS:
            by_id[tier_id] = raw

    tiers: list[dict[str, Any]] = []
    for tier_id in MEMORY_TIERS:
        raw = by_id.get(tier_id, {})
        default_max = DEFAULT_TIER_LIMITS[tier_id]
        try:
            max_items = int(raw.get("max_items", default_max))
        except Exception:
            max_items = default_max
        try:
            max_context_items = int(raw.get("max_context_items", DEFAULT_CONTEXT_LIMITS[tier_id]))
        except Exception:
            max_context_items = DEFAULT_CONTEXT_LIMITS[tier_id]
        if max_items < 0:
            max_items = default_max
        if max_context_items < 0:
            max_context_items = DEFAULT_CONTEXT_LIMITS[tier_id]
        tiers.append(
            HierarchicalMemoryTierPolicy(
                id=tier_id,
                enabled=bool(raw.get("enabled", enabled and tier_id != "long_term")),
                max_items=max_items,
                max_context_items=max_context_items,
                retention=_text(raw.get("retention") or "session", max_chars=40),
                write_sources=_unique_texts(raw.get("write_sources") or [], max_items=8, max_chars=80),
            ).to_dict()
        )

    return {
        "schema_version": _text(src.get("schema_version")) or HIERARCHICAL_MEMORY_POLICY_SCHEMA_VERSION,
        "enabled": enabled,
        "write_requires_committed_turn": bool(src.get("write_requires_committed_turn", True)),
        "allow_uncommitted_writes": bool(src.get("allow_uncommitted_writes", False)),
        "tiers": tiers,
        "context_projection": _safe_dict(
            src.get("context_projection") if isinstance(src.get("context_projection"), dict) else {}
        ),
        "metadata": _safe_dict(src.get("metadata") if isinstance(src.get("metadata"), dict) else {}),
    }


def _tier_policy(policy: dict[str, Any], tier_id: str) -> dict[str, Any]:
    tiers = policy.get("tiers") if isinstance(policy.get("tiers"), list) else []
    for tier in tiers:
        if isinstance(tier, dict) and tier.get("id") == tier_id:
            return tier
    return {}


def enabled_memory_tiers(memory_policy: dict[str, Any] | None) -> list[str]:
    policy = normalize_hierarchical_memory_policy(memory_policy)
    if not policy.get("enabled"):
        return []
    out: list[str] = []
    for tier in policy.get("tiers") or []:
        if isinstance(tier, dict) and tier.get("enabled"):
            tier_id = _text(tier.get("id"), max_chars=48)
            if tier_id in MEMORY_TIERS:
                out.append(tier_id)
    return out


def empty_hierarchical_memory_snapshot(
    *,
    module_id: str | None = None,
    runtime_profile_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": HIERARCHICAL_MEMORY_SNAPSHOT_SCHEMA_VERSION,
        "module_id": module_id,
        "runtime_profile_id": runtime_profile_id,
        "tiers": {tier_id: [] for tier_id in MEMORY_TIERS},
        "latest_source_canonical_turn_id": None,
        "item_count": 0,
    }


def normalize_hierarchical_memory_snapshot(
    snapshot: dict[str, Any] | None,
    *,
    module_id: str | None = None,
    runtime_profile_id: str | None = None,
) -> dict[str, Any]:
    src = snapshot if isinstance(snapshot, dict) else {}
    tiers_src = src.get("tiers") if isinstance(src.get("tiers"), dict) else {}
    tiers: dict[str, list[dict[str, Any]]] = {}
    total = 0
    for tier_id in MEMORY_TIERS:
        rows = tiers_src.get(tier_id) if isinstance(tiers_src, dict) else []
        clean_rows = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
        tiers[tier_id] = _json_safe(clean_rows)
        total += len(clean_rows)
    return {
        "schema_version": HIERARCHICAL_MEMORY_SNAPSHOT_SCHEMA_VERSION,
        "module_id": src.get("module_id") or module_id,
        "runtime_profile_id": src.get("runtime_profile_id") or runtime_profile_id,
        "tiers": tiers,
        "latest_source_canonical_turn_id": src.get("latest_source_canonical_turn_id"),
        "item_count": total,
    }


def _is_committed_turn(turn: dict[str, Any]) -> bool:
    if bool(turn.get("recoverable_outcome")):
        return False
    outcome = _text(turn.get("turn_outcome"), max_chars=80).lower()
    if outcome.startswith("recoverable") or outcome.startswith("rejected"):
        return False
    narrative_commit = turn.get("narrative_commit") if isinstance(turn.get("narrative_commit"), dict) else {}
    if narrative_commit.get("allowed") is False:
        return False
    return bool(turn.get("canonical_turn_id"))


def _turn_item(
    *,
    tier: str,
    turn: dict[str, Any],
    ledger: dict[str, Any],
    module_id: str | None,
    runtime_profile_id: str | None,
) -> HierarchicalMemoryItem:
    canonical_turn_id = _text(turn.get("canonical_turn_id"), max_chars=120)
    turn_number = int(turn.get("turn_number") or 0)
    projection = _projection(ledger)
    input_projection = projection.get("input") if isinstance(projection.get("input"), dict) else {}
    beat_projection = projection.get("beat") if isinstance(projection.get("beat"), dict) else {}
    cap_projection = projection.get("capability") if isinstance(projection.get("capability"), dict) else {}
    selected_beat = beat_projection.get("selected_beat") if isinstance(beat_projection.get("selected_beat"), dict) else {}
    beat_id = _text(selected_beat.get("id"), max_chars=100) or None
    capabilities = _unique_texts(cap_projection.get("selected_capabilities"), max_items=10)
    input_kind = _text(input_projection.get("player_input_kind"), max_chars=60)
    summary = f"turn={turn_number}; input_kind={input_kind or 'unknown'}; beat={beat_id or 'none'}; capabilities={len(capabilities)}"
    evidence_refs = [
        canonical_turn_id,
        *_unique_texts(cap_projection.get("realized_capabilities"), max_items=6),
    ]
    return HierarchicalMemoryItem(
        tier=tier,
        item_id=_stable_id(tier, canonical_turn_id, summary),
        source_canonical_turn_id=canonical_turn_id,
        source_turn_number=turn_number,
        module_id=module_id,
        runtime_profile_id=runtime_profile_id,
        summary=summary,
        tags=_unique_texts(["turn", input_kind, f"beat:{beat_id}" if beat_id else None], max_items=6),
        capability_ids=capabilities,
        beat_id=beat_id,
        evidence_refs=evidence_refs,
        data={
            "player_input_kind": input_kind,
            "semantic_move": _text(input_projection.get("semantic_move"), max_chars=80),
            "capability_status": cap_projection.get("status"),
            "commit_status": (projection.get("commit") or {}).get("status")
            if isinstance(projection.get("commit"), dict)
            else None,
        },
    )


def _session_item(
    *,
    tier: str,
    turn: dict[str, Any],
    module_id: str | None,
    runtime_profile_id: str | None,
) -> HierarchicalMemoryItem:
    canonical_turn_id = _text(turn.get("canonical_turn_id"), max_chars=120)
    turn_number = int(turn.get("turn_number") or 0)
    narrative_commit = turn.get("narrative_commit") if isinstance(turn.get("narrative_commit"), dict) else {}
    scene_id = _text(narrative_commit.get("committed_scene_id"), max_chars=100)
    situation = _text(narrative_commit.get("situation_status"), max_chars=80)
    consequences = _unique_texts(narrative_commit.get("committed_consequences"), max_items=4)
    pressures = _unique_texts(narrative_commit.get("open_pressures"), max_items=4)
    summary = (
        f"scene={scene_id or 'unknown'}; situation={situation or 'unknown'}; "
        f"consequences={len(consequences)}; pressures={len(pressures)}"
    )
    return HierarchicalMemoryItem(
        tier=tier,
        item_id=_stable_id(tier, canonical_turn_id, summary),
        source_canonical_turn_id=canonical_turn_id,
        source_turn_number=turn_number,
        module_id=module_id,
        runtime_profile_id=runtime_profile_id,
        summary=summary,
        tags=_unique_texts(["session", situation, scene_id], max_items=6),
        location_ids=_unique_texts([scene_id], max_items=4),
        evidence_refs=[canonical_turn_id],
        data={
            "situation_status": situation,
            "committed_scene_id": scene_id,
            "committed_consequence_count": len(consequences),
            "open_pressure_count": len(pressures),
            "is_terminal": bool(narrative_commit.get("is_terminal")),
        },
    )


def _actor_items(
    *,
    tier: str,
    turn: dict[str, Any],
    module_id: str | None,
    runtime_profile_id: str | None,
) -> list[HierarchicalMemoryItem]:
    actor_summary = turn.get("actor_turn_summary") if isinstance(turn.get("actor_turn_summary"), dict) else {}
    canonical_turn_id = _text(turn.get("canonical_turn_id"), max_chars=120)
    turn_number = int(turn.get("turn_number") or 0)
    actors = _unique_texts(
        [
            actor_summary.get("primary_responder_id"),
            actor_summary.get("secondary_responder_ids"),
            actor_summary.get("realized_actor_ids"),
        ],
        max_items=8,
    )
    if not actors:
        return []
    spoken_count = int(actor_summary.get("spoken_line_count") or 0)
    action_count = int(actor_summary.get("action_line_count") or 0)
    out: list[HierarchicalMemoryItem] = []
    for actor_id in actors:
        role_tag = "primary" if actor_id == _text(actor_summary.get("primary_responder_id")) else "related"
        summary = f"actor={actor_id}; role={role_tag}; spoken={spoken_count}; actions={action_count}"
        out.append(
            HierarchicalMemoryItem(
                tier=tier,
                item_id=_stable_id(tier, canonical_turn_id, actor_id, summary),
                source_canonical_turn_id=canonical_turn_id,
                source_turn_number=turn_number,
                module_id=module_id,
                runtime_profile_id=runtime_profile_id,
                summary=summary,
                tags=_unique_texts(["actor", role_tag], max_items=6),
                actor_ids=[actor_id],
                evidence_refs=[canonical_turn_id],
                data={
                    "role": role_tag,
                    "spoken_line_count": spoken_count,
                    "action_line_count": action_count,
                    "initiative_summary": _safe_dict(
                        actor_summary.get("initiative_summary")
                        if isinstance(actor_summary.get("initiative_summary"), dict)
                        else {}
                    ),
                },
            )
        )
    return out


def _module_item(
    *,
    tier: str,
    turn: dict[str, Any],
    runtime_policy: dict[str, Any],
    module_id: str | None,
    runtime_profile_id: str | None,
) -> HierarchicalMemoryItem:
    canonical_turn_id = _text(turn.get("canonical_turn_id"), max_chars=120)
    turn_number = int(turn.get("turn_number") or 0)
    sources = _unique_texts(runtime_policy.get("content_sources"), max_items=10)
    summary = f"module={module_id or 'unknown'}; runtime_profile={runtime_profile_id or 'none'}; content_sources={len(sources)}"
    return HierarchicalMemoryItem(
        tier=tier,
        item_id=_stable_id(tier, module_id, runtime_profile_id, "module_policy"),
        source_canonical_turn_id=canonical_turn_id,
        source_turn_number=turn_number,
        module_id=module_id,
        runtime_profile_id=runtime_profile_id,
        summary=summary,
        tags=_unique_texts(["module", runtime_profile_id], max_items=6),
        evidence_refs=[canonical_turn_id],
        data={"content_sources": sources},
    )


def build_hierarchical_memory_write(
    *,
    memory_policy: dict[str, Any] | None,
    committed_turn: dict[str, Any] | None,
    runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build tiered memory items from a canonical committed turn."""
    policy = normalize_hierarchical_memory_policy(memory_policy)
    turn = committed_turn if isinstance(committed_turn, dict) else {}
    runtime = runtime_policy if isinstance(runtime_policy, dict) else {}
    source_turn_id = _text(turn.get("canonical_turn_id"), max_chars=120) or None
    policy_present = bool(policy.get("enabled") or any(t.get("enabled") for t in policy.get("tiers") or [] if isinstance(t, dict)))
    if not policy_present:
        return HierarchicalMemoryWriteResult(
            status="not_applicable",
            policy_present=False,
            policy_enabled=False,
            write_allowed=False,
            source_canonical_turn_id=source_turn_id,
            skipped_tiers=list(MEMORY_TIERS),
        ).to_dict()

    committed = _is_committed_turn(turn)
    allow_uncommitted = bool(policy.get("allow_uncommitted_writes"))
    write_allowed = committed or allow_uncommitted
    uncommitted_write_detected = bool((not committed) and allow_uncommitted)
    if not write_allowed:
        return HierarchicalMemoryWriteResult(
            status="not_applicable",
            policy_present=True,
            policy_enabled=bool(policy.get("enabled")),
            write_allowed=False,
            source_canonical_turn_id=source_turn_id,
            selected_tiers=enabled_memory_tiers(policy),
            skipped_tiers=enabled_memory_tiers(policy),
            failure_reason=None if source_turn_id else "canonical_turn_id_missing",
            uncommitted_write_detected=False,
        ).to_dict()

    if not source_turn_id:
        return HierarchicalMemoryWriteResult(
            status="failed",
            policy_present=True,
            policy_enabled=bool(policy.get("enabled")),
            write_allowed=False,
            source_canonical_turn_id=None,
            selected_tiers=enabled_memory_tiers(policy),
            skipped_tiers=enabled_memory_tiers(policy),
            failure_reason="canonical_turn_id_missing",
            uncommitted_write_detected=uncommitted_write_detected,
        ).to_dict()

    module_id = _text(turn.get("module_id") or runtime.get("module_id"), max_chars=120) or None
    runtime_profile_id = _text(
        turn.get("runtime_profile_id") or runtime.get("runtime_profile_id"),
        max_chars=120,
    ) or None
    ledger = turn.get("turn_aspect_ledger") if isinstance(turn.get("turn_aspect_ledger"), dict) else {}
    selected = enabled_memory_tiers(policy)
    items: list[dict[str, Any]] = []
    skipped: list[str] = []
    if "turn" in selected:
        items.append(
            _turn_item(
                tier="turn",
                turn=turn,
                ledger=ledger,
                module_id=module_id,
                runtime_profile_id=runtime_profile_id,
            ).to_dict()
        )
    else:
        skipped.append("turn")
    if "session" in selected:
        items.append(
            _session_item(
                tier="session",
                turn=turn,
                module_id=module_id,
                runtime_profile_id=runtime_profile_id,
            ).to_dict()
        )
    else:
        skipped.append("session")
    if "actor" in selected:
        items.extend(
            item.to_dict()
            for item in _actor_items(
                tier="actor",
                turn=turn,
                module_id=module_id,
                runtime_profile_id=runtime_profile_id,
            )
        )
    else:
        skipped.append("actor")
    if "module" in selected:
        items.append(
            _module_item(
                tier="module",
                turn=turn,
                runtime_policy=runtime,
                module_id=module_id,
                runtime_profile_id=runtime_profile_id,
            ).to_dict()
        )
    else:
        skipped.append("module")
    if "long_term" in selected:
        skipped.append("long_term")

    status = "passed" if items and not uncommitted_write_detected else "partial" if items else "not_applicable"
    failure_reason = "uncommitted_memory_write_detected" if uncommitted_write_detected else None
    return HierarchicalMemoryWriteResult(
        status=status,
        policy_present=True,
        policy_enabled=bool(policy.get("enabled")),
        write_allowed=bool(items),
        source_canonical_turn_id=source_turn_id,
        selected_tiers=selected,
        written_items=items,
        skipped_tiers=skipped,
        failure_reason=failure_reason,
        uncommitted_write_detected=uncommitted_write_detected,
    ).to_dict()


def merge_hierarchical_memory_snapshot(
    *,
    prior_snapshot: dict[str, Any] | None,
    write_result: dict[str, Any] | None,
    memory_policy: dict[str, Any] | None,
    module_id: str | None = None,
    runtime_profile_id: str | None = None,
) -> dict[str, Any]:
    policy = normalize_hierarchical_memory_policy(memory_policy)
    snapshot = normalize_hierarchical_memory_snapshot(
        prior_snapshot,
        module_id=module_id,
        runtime_profile_id=runtime_profile_id,
    )
    result = write_result if isinstance(write_result, dict) else {}
    if result.get("uncommitted_write_detected"):
        return snapshot
    items = result.get("written_items") if isinstance(result.get("written_items"), list) else []
    tiers = snapshot.get("tiers") if isinstance(snapshot.get("tiers"), dict) else {}
    for item in items:
        if not isinstance(item, dict):
            continue
        tier_id = _text(item.get("tier"), max_chars=48)
        if tier_id not in MEMORY_TIERS:
            continue
        tier_rows = list(tiers.get(tier_id) or [])
        item_id = _text(item.get("item_id"), max_chars=80)
        tier_rows = [row for row in tier_rows if not (isinstance(row, dict) and row.get("item_id") == item_id)]
        tier_rows.insert(0, _json_safe(item))
        tier_policy = _tier_policy(policy, tier_id)
        try:
            max_items = int(tier_policy.get("max_items", DEFAULT_TIER_LIMITS[tier_id]))
        except Exception:
            max_items = DEFAULT_TIER_LIMITS[tier_id]
        tiers[tier_id] = tier_rows[: max(0, max_items)]
    snapshot["tiers"] = tiers
    snapshot["latest_source_canonical_turn_id"] = result.get("source_canonical_turn_id") or snapshot.get(
        "latest_source_canonical_turn_id"
    )
    snapshot["item_count"] = sum(
        len(rows) for rows in tiers.values() if isinstance(rows, list)
    )
    return _json_safe(snapshot)


def project_hierarchical_memory_context(
    *,
    snapshot: dict[str, Any] | None,
    memory_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    policy = normalize_hierarchical_memory_policy(memory_policy)
    normalized = normalize_hierarchical_memory_snapshot(snapshot)
    tiers_src = normalized.get("tiers") if isinstance(normalized.get("tiers"), dict) else {}
    projected_tiers: dict[str, list[dict[str, Any]]] = {}
    lines: list[str] = []
    total_included = 0
    total_available = 0
    for tier_id in MEMORY_TIERS:
        tier_policy = _tier_policy(policy, tier_id)
        if not tier_policy.get("enabled"):
            projected_tiers[tier_id] = []
            continue
        rows = tiers_src.get(tier_id) if isinstance(tiers_src.get(tier_id), list) else []
        total_available += len(rows)
        try:
            max_context = int(tier_policy.get("max_context_items", DEFAULT_CONTEXT_LIMITS[tier_id]))
        except Exception:
            max_context = DEFAULT_CONTEXT_LIMITS[tier_id]
        selected_rows: list[dict[str, Any]] = []
        for row in rows[: max(0, max_context)]:
            if not isinstance(row, dict):
                continue
            summary = _text(row.get("summary"), max_chars=160)
            safe_row = {
                "tier": tier_id,
                "item_id": row.get("item_id"),
                "source_canonical_turn_id": row.get("source_canonical_turn_id"),
                "summary": summary,
                "tags": _unique_texts(row.get("tags"), max_items=8),
                "actor_ids": _unique_texts(row.get("actor_ids"), max_items=8),
                "location_ids": _unique_texts(row.get("location_ids"), max_items=6),
                "capability_ids": _unique_texts(row.get("capability_ids"), max_items=8),
                "beat_id": row.get("beat_id"),
            }
            selected_rows.append(_json_safe(safe_row))
            if summary:
                lines.append(f"{tier_id}: {summary}")
        projected_tiers[tier_id] = selected_rows
        total_included += len(selected_rows)
    return {
        "schema_version": HIERARCHICAL_MEMORY_CONTEXT_SCHEMA_VERSION,
        "policy_present": bool(policy.get("enabled")),
        "memory_present": total_available > 0,
        "bounded": True,
        "item_count": total_included,
        "available_item_count": total_available,
        "omitted_item_count": max(0, total_available - total_included),
        "latest_source_canonical_turn_id": normalized.get("latest_source_canonical_turn_id"),
        "tiers": projected_tiers,
        "context_lines": lines[:24],
    }
