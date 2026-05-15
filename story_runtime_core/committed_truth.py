"""Shared filters for committed story-runtime truth rows.

Runtime history can contain player-visible recovery turns for auditability and
story-window continuity. Those rows are not committed story truth and must not
seed bounded feedback graphs such as callback-web or consequence-cascade.
"""

from __future__ import annotations

from typing import Any


RECOVERABLE_TURN_OUTCOMES = frozenset(
    {
        "recoverable_rejection",
        "recoverable_graph_exception",
        "recoverable_projection_failure",
    }
)

RECOVERABLE_TURN_KINDS = frozenset(
    {
        "player_rejected_recoverable",
        "player_graph_exception_playable",
        "player_projection_rejected_recoverable",
    }
)

RECOVERABLE_TURN_STATUSES = frozenset({"rejected_recoverable"})

RECOVERABLE_COMMIT_REASON_CODES = frozenset(
    {
        "recoverable_rejection",
        "graph_execution_exception",
        "runtime_aspect_projection_gate",
    }
)


def _text(value: Any) -> str:
    return str(value or "").strip().lower()


def is_committed_story_truth_row(row: dict[str, Any] | None) -> bool:
    """Return whether a history row may seed committed-truth feedback.

    ADR-0039 boundary: this predicate is based on schema/status/commit fields,
    not on generated narration, authored prose, or example-shaped strings.
    """

    if not isinstance(row, dict):
        return False
    if not str(row.get("canonical_turn_id") or "").strip():
        return False
    if bool(row.get("recoverable_outcome")):
        return False

    outcome = _text(row.get("turn_outcome"))
    if outcome in RECOVERABLE_TURN_OUTCOMES or outcome.startswith("recoverable"):
        return False

    turn_kind = _text(row.get("turn_kind"))
    if turn_kind in RECOVERABLE_TURN_KINDS:
        return False

    turn_status = _text(row.get("turn_status"))
    if turn_status in RECOVERABLE_TURN_STATUSES:
        return False

    validation = row.get("validation_outcome") if isinstance(row.get("validation_outcome"), dict) else {}
    if _text(validation.get("status")) == "rejected" and bool(validation.get("recoverable_rejection")):
        return False

    narrative_commit = row.get("narrative_commit") if isinstance(row.get("narrative_commit"), dict) else {}
    commit_reason = _text(narrative_commit.get("commit_reason_code"))
    if commit_reason in RECOVERABLE_COMMIT_REASON_CODES:
        return False

    committed_result = row.get("committed_result") if isinstance(row.get("committed_result"), dict) else {}
    if bool(committed_result.get("recoverable_rejection")):
        return False
    if committed_result.get("commit_applied") is False:
        return False

    return True


def committed_story_truth_rows(history: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Return copied history rows that are eligible committed-truth inputs."""

    return [dict(row) for row in (history or []) if is_committed_story_truth_row(row)]
