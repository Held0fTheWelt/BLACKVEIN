"""Record construction and stable serialization for runtime aspect ledgers.

These helpers own the canonical per-aspect storage format. Projection modules
may derive richer views from the records, but they should not mutate the record
shape directly.
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .constants import (
    ASPECT_FAILURE_CLASSES,
    ASPECT_KEYS,
    ASPECT_STATUSES,
    RUNTIME_ASPECT_LEDGER_VERSION,
    RUNTIME_ASPECT_RECORD_VERSION,
    TURN_ASPECT_LEDGER_SCHEMA_VERSION,
)

@dataclass(frozen=True)
class RuntimeAspectLedger:
    """JSON-safe canonical per-turn runtime intelligence envelope."""

    schema_version: str = TURN_ASPECT_LEDGER_SCHEMA_VERSION
    record_version: str = RUNTIME_ASPECT_LEDGER_VERSION
    module_id: str | None = None
    runtime_profile_id: str | None = None
    canonical_turn_id: str | None = None
    story_session_id: str | None = None
    turn_number: int = 0
    turn_kind: str = "player"
    turn_aspect_ledger: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return the dataclass payload using only JSON-safe values."""
        return _json_safe(asdict(self))
def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
def make_aspect_record(
    *,
    applicable: bool,
    status: str,
    expected: dict[str, Any] | None = None,
    selected: dict[str, Any] | None = None,
    actual: dict[str, Any] | None = None,
    reasons: list[str] | None = None,
    source: str = "runtime",
    record_version: str = RUNTIME_ASPECT_RECORD_VERSION,
    failure_class: str | None = None,
    failure_reason: str | None = None,
    offending_actor_id: str | None = None,
    offending_block_id: str | None = None,
    missing_field: str | None = None,
    expected_owner: str | None = None,
    actual_owner: str | None = None,
    selected_capability: str | None = None,
    realized_capability: str | None = None,
    selected_beat: str | None = None,
    lost_at_stage: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build one stable aspect record."""
    st = str(status or "missing").strip() or "missing"
    if st not in ASPECT_STATUSES:
        st = "missing"
    fc = str(failure_class or "").strip() or None
    if fc and fc not in ASPECT_FAILURE_CLASSES:
        fc = "observability_gap"
    record: dict[str, Any] = {
        "applicable": bool(applicable),
        "status": st,
        "expected": _json_safe(expected or {}),
        "selected": _json_safe(selected or {}),
        "actual": _json_safe(actual or {}),
        "reasons": [str(r) for r in (reasons or []) if str(r).strip()],
        "source": str(source or "runtime"),
        "record_version": record_version,
        "failure_class": fc,
        "failure_reason": failure_reason,
        "offending_actor_id": offending_actor_id,
        "offending_block_id": offending_block_id,
        "missing_field": missing_field,
        "expected_owner": expected_owner,
        "actual_owner": actual_owner,
        "selected_capability": selected_capability,
        "realized_capability": realized_capability,
        "selected_beat": selected_beat,
        "lost_at_stage": lost_at_stage,
    }
    for key, value in extra.items():
        record[str(key)] = _json_safe(value)
    return record
def empty_aspect_record(*, applicable: bool = True, source: str = "runtime") -> dict[str, Any]:
    """Create a placeholder aspect record for missing or unavailable evidence."""
    return make_aspect_record(
        applicable=applicable,
        status="missing" if applicable else "not_applicable",
        source=source,
    )
def stable_ledger_json(
    ledger: dict[str, Any],
    *,
    normalizer: Any | None = None,
) -> str:
    """Serialize a normalized ledger with deterministic key and separator order."""
    if normalizer is None:
        from .normalization import normalize_runtime_aspect_ledger as normalizer

    return json.dumps(
        normalizer(ledger),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
