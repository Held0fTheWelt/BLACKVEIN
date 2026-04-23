from __future__ import annotations

from ai_stack.runtime_quality_semantics import canonical_quality_summary


def test_healthy_turn_has_clean_quality_surface() -> None:
    state = {
        "validation_outcome": {"status": "approved", "reason": "goc_default_validator_pass"},
        "committed_result": {"commit_applied": True},
        "visibility_class_markers": ["truth_aligned"],
        "generation": {"fallback_used": False},
        "self_correction": {"attempts": []},
    }
    quality = canonical_quality_summary(state=state, fallback_taken=False)
    assert quality["quality_class"] == "healthy"
    assert quality["degradation_signals"] == []


def test_weak_but_legal_not_classified_degraded() -> None:
    state = {
        "validation_outcome": {
            "status": "approved",
            "reason": "goc_default_validator_pass",
            "dramatic_quality_gate": "effect_gate_weak_signal",
            "dramatic_effect_weak_signal": True,
        },
        "committed_result": {"commit_applied": True},
        "visibility_class_markers": ["truth_aligned"],
        "generation": {"fallback_used": False},
        "self_correction": {"attempts": []},
    }
    quality = canonical_quality_summary(state=state, fallback_taken=False)
    assert quality["quality_class"] == "weak_but_legal"
    assert "weak_signal_accepted" in quality["degradation_signals"]


def test_fallback_path_always_emits_degraded_signal() -> None:
    state = {
        "validation_outcome": {"status": "approved", "reason": "goc_default_validator_pass"},
        "committed_result": {"commit_applied": True},
        "visibility_class_markers": ["truth_aligned"],
        "generation": {"fallback_used": True},
        "self_correction": {"attempts": []},
    }
    quality = canonical_quality_summary(state=state, fallback_taken=True)
    assert "fallback_used" in quality["degradation_signals"]
    assert quality["quality_class"] == "degraded"


def test_degraded_commit_emits_retry_exhausted_signal() -> None:
    state = {
        "validation_outcome": {"status": "approved", "reason": "degraded_commit_after_retries"},
        "committed_result": {"commit_applied": True},
        "visibility_class_markers": ["truth_aligned"],
        "generation": {"fallback_used": False},
        "self_correction": {"attempts": [{"attempt_index": 1}]},
    }
    quality = canonical_quality_summary(state=state, fallback_taken=False)
    assert "degraded_commit" in quality["degradation_signals"]
    assert "retry_exhausted" in quality["degradation_signals"]
    assert quality["quality_class"] == "degraded"


def test_rejected_validation_is_failed_quality() -> None:
    state = {
        "validation_outcome": {"status": "rejected", "reason": "actor_lane_illegal_actor"},
        "committed_result": {"commit_applied": False},
        "generation": {"fallback_used": False},
    }
    quality = canonical_quality_summary(state=state, fallback_taken=False)
    assert quality["quality_class"] == "failed"
