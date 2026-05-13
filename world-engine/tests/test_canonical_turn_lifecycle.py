"""ADR-0038 Phase B — canonical turn lifecycle ordering."""

from __future__ import annotations

import pytest

from app.story_runtime.canonical_turn_lifecycle import (
    CanonicalTurnLifecycleViolation,
    TurnLifecycleChain,
)


def test_turn_lifecycle_happy_path_reaches_observed() -> None:
    lc = TurnLifecycleChain()
    for name in (
        "received",
        "interpreted",
        "generated_or_resolved",
        "validated",
        "committed",
        "projected",
        "persisted",
        "observed",
    ):
        lc.advance(name)
    assert lc.states[-1] == "observed"


def test_projected_without_committed_raises() -> None:
    lc = TurnLifecycleChain()
    lc.advance("received")
    lc.advance("interpreted")
    lc.advance("generated_or_resolved")
    lc.advance("validated")
    with pytest.raises(CanonicalTurnLifecycleViolation):
        lc.advance("projected")


def test_committed_without_validated_raises() -> None:
    lc = TurnLifecycleChain()
    lc.advance("received")
    lc.advance("interpreted")
    lc.advance("generated_or_resolved")
    with pytest.raises(CanonicalTurnLifecycleViolation):
        lc.advance("committed")


def test_lifecycle_cannot_regress() -> None:
    lc = TurnLifecycleChain()
    lc.advance("received")
    lc.advance("interpreted")
    lc.advance("generated_or_resolved")
    lc.advance("validated")
    lc.advance("committed")
    lc.advance("projected")
    lc.advance("persisted")
    lc.advance("observed")
    with pytest.raises(CanonicalTurnLifecycleViolation):
        lc.advance("committed")
