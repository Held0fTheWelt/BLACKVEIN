"""ADR-0038 Phase B — canonical turn lifecycle (World-Engine).

Enforces forward ordering between critical phases so player-visible projection cannot
run before an explicit ``committed`` step, and durable persistence cannot precede
projection of the canonical envelope for the turn.
"""

from __future__ import annotations

# Normative names from ADR-0038 D2. Execution in ``StoryRuntimeManager`` builds the
# canonical envelope in memory, projects visible fields onto it, then appends one
# row to history/diagnostics; ranks therefore place ``projected`` before ``persisted``.
TURN_LIFECYCLE_STATES: tuple[str, ...] = (
    "received",
    "interpreted",
    "planned",
    "generated_or_resolved",
    "validated",
    "committed",
    "projected",
    "persisted",
    "observed",
)

_RANK: dict[str, int] = {name: idx for idx, name in enumerate(TURN_LIFECYCLE_STATES)}

# Minimum prior rank required before entering ``state`` (exclusive upper bound is
# the rank of the named prerequisite: we require max_rank >= rank(prereq)).
_HARD_PREREQS: dict[str, tuple[str, ...]] = {
    "interpreted": ("received",),
    "planned": ("interpreted",),
    "generated_or_resolved": ("interpreted",),
    "validated": ("generated_or_resolved",),
    "committed": ("validated",),
    "projected": ("committed",),
    "persisted": ("projected",),
    "observed": ("persisted",),
}


class CanonicalTurnLifecycleViolation(RuntimeError):
    """Raised when lifecycle ordering rules are violated."""


def lifecycle_rank(state: str) -> int:
    try:
        return _RANK[state]
    except KeyError as exc:
        raise CanonicalTurnLifecycleViolation(f"unknown lifecycle state: {state!r}") from exc


def max_lifecycle_rank(states: list[str]) -> int:
    if not states:
        return -1
    return max(lifecycle_rank(s) for s in states)


class TurnLifecycleChain:
    """In-method tracker: prerequisite checks plus monotonic forward motion."""

    __slots__ = ("_states",)

    def __init__(self) -> None:
        self._states: list[str] = []

    def advance(self, state: str) -> None:
        prereqs = _HARD_PREREQS.get(state)
        if prereqs:
            mr = max_lifecycle_rank(self._states)
            for need in prereqs:
                need_r = lifecycle_rank(need)
                if mr < need_r:
                    raise CanonicalTurnLifecycleViolation(
                        f"lifecycle {state!r} requires {need!r} first (max rank so far {mr})"
                    )
        new_r = lifecycle_rank(state)
        prev_max = max_lifecycle_rank(self._states)
        if new_r < prev_max:
            raise CanonicalTurnLifecycleViolation(
                f"lifecycle cannot regress: attempted {state!r} (rank {new_r}) after max rank {prev_max}"
            )
        self._states.append(state)

    @property
    def states(self) -> tuple[str, ...]:
        return tuple(self._states)
