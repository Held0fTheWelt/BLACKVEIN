from ai_stack.souffleuse_production_judge import (
    VIOLATION_SELF_LABEL,
    evaluate_souffleuse_visible_text_shadow,
)


def test_shadow_judge_passes_inner_voice_sample() -> None:
    out = evaluate_souffleuse_visible_text_shadow("Bleib ruhig. Atme.")
    assert out["passed"] is True
    assert out["violations"] == []


def test_shadow_judge_flags_souffleuse_label() -> None:
    out = evaluate_souffleuse_visible_text_shadow("Souffleuse: tu das jetzt.")
    assert out["passed"] is False
    assert VIOLATION_SELF_LABEL in out["violations"]
