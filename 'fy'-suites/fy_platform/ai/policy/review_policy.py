from __future__ import annotations

ALLOWED_REVIEW_STATES = {"raw", "accepted", "superseded", "rejected"}
ALLOWED_REVIEW_TRANSITIONS = {
    "raw": {"accepted", "rejected", "superseded"},
    "accepted": {"superseded"},
    "superseded": set(),
    "rejected": set(),
}


def is_valid_transition(current: str, new: str) -> bool:
    if current not in ALLOWED_REVIEW_TRANSITIONS:
        return False
    return new in ALLOWED_REVIEW_TRANSITIONS[current]
