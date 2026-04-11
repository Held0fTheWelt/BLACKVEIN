# ai_stack/tests/test_goc_dramatic_alignment.py
from __future__ import annotations

from ai_stack.goc_dramatic_alignment import (
    _FUNCTION_SUBSTRING_TOKENS,
    _MIN_CHARS_HIGH_STAKES,
    _MIN_CHARS_WITHHELD_OR_THIN,
)


def test_function_substring_tokens_coverage() -> None:
    expected_functions = {
        "escalate_conflict",
        "redirect_blame",
        "reveal_surface",
        "probe_motive",
        "repair_or_stabilize",
        "establish_pressure",
        "withhold_or_evade",
    }
    assert set(_FUNCTION_SUBSTRING_TOKENS.keys()) >= expected_functions


def test_min_char_thresholds() -> None:
    assert _MIN_CHARS_HIGH_STAKES > 0
    assert _MIN_CHARS_WITHHELD_OR_THIN > 0
    assert _MIN_CHARS_WITHHELD_OR_THIN < _MIN_CHARS_HIGH_STAKES


def test_token_lists_are_tuples() -> None:
    for func, tokens in _FUNCTION_SUBSTRING_TOKENS.items():
        assert isinstance(tokens, tuple)
        assert all(isinstance(t, str) for t in tokens)


def test_escalate_conflict_has_conflict_tokens() -> None:
    tokens = _FUNCTION_SUBSTRING_TOKENS.get("escalate_conflict", ())
    # Should contain confrontation-related tokens
    assert any(t in tokens for t in ["shout", "rage", "angry", "fight"])


def test_redirect_blame_has_blame_tokens() -> None:
    tokens = _FUNCTION_SUBSTRING_TOKENS.get("redirect_blame", ())
    assert any(t in tokens for t in ["blame", "fault", "responsib", "your"])


def test_reveal_surface_has_truth_tokens() -> None:
    tokens = _FUNCTION_SUBSTRING_TOKENS.get("reveal_surface", ())
    assert any(t in tokens for t in ["truth", "secret", "reveal", "confess"])


def test_probe_motive_has_question_tokens() -> None:
    tokens = _FUNCTION_SUBSTRING_TOKENS.get("probe_motive", ())
    assert any(t in tokens for t in ["why", "reason", "motive"])


def test_repair_or_stabilize_has_peace_tokens() -> None:
    tokens = _FUNCTION_SUBSTRING_TOKENS.get("repair_or_stabilize", ())
    assert any(t in tokens for t in ["apolog", "sorry", "peace", "calm"])


def test_establish_pressure_has_tension_tokens() -> None:
    tokens = _FUNCTION_SUBSTRING_TOKENS.get("establish_pressure", ())
    assert any(t in tokens for t in ["quiet", "tight", "wait", "still"])


def test_extract_proposed_narrative_text_empty_list() -> None:
    from ai_stack.goc_dramatic_alignment import extract_proposed_narrative_text
    result = extract_proposed_narrative_text([])
    assert result == ""


def test_extract_proposed_narrative_text_valid_descriptions() -> None:
    from ai_stack.goc_dramatic_alignment import extract_proposed_narrative_text
    proposed = [
        {"description": "The character speaks."},
        {"description": "The other replies."}
    ]
    result = extract_proposed_narrative_text(proposed)
    assert "speaks" in result
    assert "replies" in result


def test_extract_proposed_narrative_text_skips_non_string_descriptions() -> None:
    from ai_stack.goc_dramatic_alignment import extract_proposed_narrative_text
    proposed = [
        {"description": "Valid text"},
        {"description": None},
        {"description": 123},
        {}
    ]
    result = extract_proposed_narrative_text(proposed)
    assert result == "Valid text"


def test_extract_proposed_narrative_text_skips_non_dict_items() -> None:
    from ai_stack.goc_dramatic_alignment import extract_proposed_narrative_text
    proposed = [
        {"description": "First"},
        "not a dict",
        {"description": "Second"}
    ]
    result = extract_proposed_narrative_text(proposed)
    assert "First" in result
    assert "Second" in result


def test_silence_mode_with_valid_dict() -> None:
    from ai_stack.goc_dramatic_alignment import _silence_mode
    result = _silence_mode({"mode": "withheld"})
    assert result == "withheld"


def test_silence_mode_with_none() -> None:
    from ai_stack.goc_dramatic_alignment import _silence_mode
    result = _silence_mode(None)
    assert result == "normal"


def test_silence_mode_with_non_dict() -> None:
    from ai_stack.goc_dramatic_alignment import _silence_mode
    result = _silence_mode("invalid")
    assert result == "normal"


def test_silence_mode_missing_mode_key() -> None:
    from ai_stack.goc_dramatic_alignment import _silence_mode
    result = _silence_mode({})
    assert result == "normal"


def test_dramatic_alignment_legacy_fallback_withhold_or_evade_too_short() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_legacy_fallback_only
    result = dramatic_alignment_legacy_fallback_only(
        selected_scene_function="withhold_or_evade",
        pacing_mode="normal",
        silence_brevity_decision={"mode": "withheld"},
        proposed_narrative="hi"
    )
    assert result == "dramatic_alignment_withhold_requires_min_beat"


def test_dramatic_alignment_legacy_fallback_withhold_valid() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_legacy_fallback_only
    result = dramatic_alignment_legacy_fallback_only(
        selected_scene_function="withhold_or_evade",
        pacing_mode="normal",
        silence_brevity_decision={"mode": "withheld"},
        proposed_narrative="This is sufficient silence."
    )
    assert result is None


def test_dramatic_alignment_legacy_fallback_withhold_meta_commentary() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_legacy_fallback_only
    result = dramatic_alignment_legacy_fallback_only(
        selected_scene_function="withhold_or_evade",
        pacing_mode="normal",
        silence_brevity_decision={"mode": "withheld"},
        proposed_narrative="As a narrator, silence falls."
    )
    assert result == "dramatic_alignment_meta_commentary"


def test_dramatic_alignment_legacy_fallback_thin_insufficient_mass() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_legacy_fallback_only
    result = dramatic_alignment_legacy_fallback_only(
        selected_scene_function="probe_motive",
        pacing_mode="thin_edge",
        silence_brevity_decision=None,
        proposed_narrative="short"
    )
    assert result == "dramatic_alignment_insufficient_mass_thin_or_silence"


def test_dramatic_alignment_legacy_fallback_brief_mode_valid() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_legacy_fallback_only
    result = dramatic_alignment_legacy_fallback_only(
        selected_scene_function="probe_motive",
        pacing_mode="normal",
        silence_brevity_decision={"mode": "brief"},
        proposed_narrative="Long enough narrative here"
    )
    assert result is None


def test_dramatic_alignment_legacy_fallback_non_high_stakes_short() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_legacy_fallback_only
    result = dramatic_alignment_legacy_fallback_only(
        selected_scene_function="probe_motive",
        pacing_mode="normal",
        silence_brevity_decision=None,
        proposed_narrative="x"
    )
    assert result == "dramatic_alignment_narrative_too_short"


def test_dramatic_alignment_legacy_fallback_non_high_stakes_valid() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_legacy_fallback_only
    result = dramatic_alignment_legacy_fallback_only(
        selected_scene_function="probe_motive",
        pacing_mode="normal",
        silence_brevity_decision=None,
        proposed_narrative="Why did this happen?"
    )
    assert result is None


def test_dramatic_alignment_legacy_fallback_high_stakes_insufficient_mass() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_legacy_fallback_only
    result = dramatic_alignment_legacy_fallback_only(
        selected_scene_function="escalate_conflict",
        pacing_mode="normal",
        silence_brevity_decision=None,
        proposed_narrative="short"
    )
    assert result == "dramatic_alignment_insufficient_mass"


def test_dramatic_alignment_legacy_fallback_high_stakes_meta_commentary() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_legacy_fallback_only
    result = dramatic_alignment_legacy_fallback_only(
        selected_scene_function="escalate_conflict",
        pacing_mode="normal",
        silence_brevity_decision=None,
        proposed_narrative="From a narrative perspective, the conflict escalates significantly."
    )
    assert result == "dramatic_alignment_meta_commentary"


def test_dramatic_alignment_legacy_fallback_high_stakes_valid() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_legacy_fallback_only
    result = dramatic_alignment_legacy_fallback_only(
        selected_scene_function="escalate_conflict",
        pacing_mode="normal",
        silence_brevity_decision=None,
        proposed_narrative="They shout and rage furiously against each other in anger."
    )
    assert result is None


def test_dramatic_alignment_violation_delegates_to_legacy() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_violation
    result = dramatic_alignment_violation(
        selected_scene_function="withhold_or_evade",
        pacing_mode="normal",
        silence_brevity_decision={"mode": "withheld"},
        proposed_narrative="x"
    )
    assert result == "dramatic_alignment_withhold_requires_min_beat"


def test_dramatic_alignment_violation_no_function_support() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_violation
    result = dramatic_alignment_violation(
        selected_scene_function="escalate_conflict",
        pacing_mode="normal",
        silence_brevity_decision=None,
        proposed_narrative="This is a reasonably long narrative that talks about things happening in the scene."
    )
    assert result == "dramatic_alignment_no_function_support"


def test_dramatic_alignment_violation_with_function_support() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_violation
    result = dramatic_alignment_violation(
        selected_scene_function="escalate_conflict",
        pacing_mode="normal",
        silence_brevity_decision=None,
        proposed_narrative="They shout and rage furiously against each other in the scene."
    )
    assert result is None


def test_dramatic_alignment_violation_with_tokens_no_boilerplate() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_violation
    # escalate_conflict WITH conflict tokens and boilerplate - should pass since tokens present
    result = dramatic_alignment_violation(
        selected_scene_function="escalate_conflict",
        pacing_mode="normal",
        silence_brevity_decision=None,
        proposed_narrative="The tension in the air grows as they shout angrily at each other."
    )
    assert result is None  # Passes because function tokens override boilerplate check


def test_dramatic_alignment_legacy_fallback_non_high_stakes_meta_commentary() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_legacy_fallback_only
    # Test non-high-stakes function with meta-commentary
    result = dramatic_alignment_legacy_fallback_only(
        selected_scene_function="probe_motive",
        pacing_mode="normal",
        silence_brevity_decision=None,
        proposed_narrative="As a narrator, they explain their motivations clearly."
    )
    assert result == "dramatic_alignment_meta_commentary"


def test_dramatic_alignment_violation_multiple_boilerplate_phrases() -> None:
    from ai_stack.goc_dramatic_alignment import dramatic_alignment_violation
    # Test scenario with function tokens matching - multiple boilerplate phrases are skipped
    result = dramatic_alignment_violation(
        selected_scene_function="reveal_surface",
        pacing_mode="normal",
        silence_brevity_decision=None,
        proposed_narrative="The tension in the air builds as everyone feels the moment hangs heavy and they finally reveal the truth."
    )
    # Should pass because we have the reveal token
    assert result is None
