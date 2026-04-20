import pytest
from unittest.mock import MagicMock
from app.runtime.helper_functions import (
    compress_context_for_llm,
    extract_active_triggers,
    normalize_proposed_deltas,
    precheck_guard_routing
)
from app.runtime.runtime_models import SessionState, SessionContextLayers


def test_compress_context_for_llm_reduces_character_list():
    """Helper reduces character list to active/salient characters only."""
    # Create mock SessionState with 10 characters, mark 2 as active
    session_state = SessionState(
        session_id="test",
        module_id="god_of_carnage",
        module_version="1.0.0",
        current_scene_id="opening",
        canonical_state={"characters": {f"char_{i}": {"name": f"Char {i}"} for i in range(10)}}
    )
    # Mock context_layers to mark 2 characters as salient
    session_state.context_layers = MagicMock()
    session_state.context_layers.relationship_axis_context = [
        ("char_0", "some_axis", 8.0),  # High salience
        ("char_1", "another_axis", 7.5)  # High salience
    ]

    compressed = compress_context_for_llm(session_state)
    assert len(compressed["characters"]) <= 3, "Should compress to salient + context characters"
    assert "char_0" in compressed["characters"], "Should include high-salience character"


def test_extract_active_triggers_finds_trigger_rules():
    """Helper finds matching trigger rules from decision policy."""
    session_state = SessionState(
        session_id="test",
        module_id="god_of_carnage",
        module_version="1.0.0",
        current_scene_id="opening",
        canonical_state={
            "triggers": ["escalation_detected", "character_betrayal"]
        }
    )

    triggers = extract_active_triggers(session_state)
    assert isinstance(triggers, list), "Should return list of trigger dicts"
    assert len(triggers) > 0, "Should find at least one matching trigger"
    assert all("name" in t for t in triggers), "Each trigger should have name"


def test_normalize_proposed_deltas_fixes_structural_issues():
    """Helper fixes structural issues in proposed deltas (type coercion, path fixing, etc)."""
    proposed_deltas = [
        {"path": "characters/char_0/name", "value": 123},  # Wrong type
        {"path": "characters/char_1/relationship", "value": "trust"},  # Valid
        {"path": "invalid//path", "value": "test"}  # Malformed path
    ]

    normalized = normalize_proposed_deltas(proposed_deltas, canonical_state={})
    assert len(normalized) >= 2, "Should normalize valid deltas"
    assert all("path" in d for d in normalized), "Each delta should have path"
    assert all("value" in d for d in normalized), "Each delta should have value"


def test_precheck_guard_routing_validates_before_guard():
    """Helper pre-validates deltas before guard evaluation."""
    deltas = [
        {"path": "characters/char_0/name", "value": "New Name"},
        {"path": "scene_id", "value": "new_scene"}
    ]

    result = precheck_guard_routing(deltas, canonical_state={})
    assert isinstance(result, dict), "Should return routing decision dict"
    assert "valid_deltas" in result, "Should separate valid from invalid"
    assert "invalid_deltas" in result, "Should separate valid from invalid"
    assert "routing_recommendation" in result, "Should recommend path (full_guard / soft_guard / bypass)"
