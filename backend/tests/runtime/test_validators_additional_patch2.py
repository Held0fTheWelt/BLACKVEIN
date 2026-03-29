from __future__ import annotations

from types import SimpleNamespace

from app.runtime.validators import ValidationStatus, _entity_exists, _validate_delta, _validate_scene_transition, validate_decision


class _DecisionWithoutDeltas:
    pass


class _Delta:
    def __init__(self, target, next_value=None):
        self.target = target
        self.next_value = next_value


def _module_stub():
    return SimpleNamespace(
        characters={"veronique": object()},
        relationship_axes={"trust": object()},
        scene_phases={"courtesy": object(), "fracture": object()},
        phase_transitions={
            "go_fracture": SimpleNamespace(from_phase="courtesy", to_phase="fracture"),
        },
    )


def _session_stub(current_scene_id="courtesy"):
    return SimpleNamespace(current_scene_id=current_scene_id)


class TestValidatorsAdditionalCoverage:
    def test_validate_decision_rejects_missing_proposed_deltas_field(self):
        outcome = validate_decision(_DecisionWithoutDeltas(), _session_stub(), _module_stub())

        assert outcome.is_valid is False
        assert outcome.status == ValidationStatus.FAIL
        assert "Decision missing required 'proposed_deltas' field" in outcome.errors

    def test_validate_delta_rejects_non_string_and_unknown_entity_targets(self):
        module = _module_stub()
        session = _session_stub()

        assert _validate_delta(_Delta(target=123), session, module) == ["Delta target must be string, got int"]
        assert _validate_delta(_Delta(target="inventory.slot", next_value=5), session, module) == [
            "Unknown entity type in target: inventory"
        ]

    def test_validate_delta_rejects_unknown_character_and_out_of_range_numeric_values(self):
        errors = _validate_delta(_Delta(target="characters.unknown.emotional_state", next_value=150), _session_stub(), _module_stub())

        assert "Unknown character: unknown" in errors
        assert "Numeric delta values must be 0-100, got 150" in errors

    def test_validate_scene_transition_allows_self_transition_and_rejects_unreachable_target(self):
        module = _module_stub()
        session = _session_stub(current_scene_id="courtesy")

        assert _validate_scene_transition("courtesy", session, module) == []
        assert _validate_scene_transition("missing", session, module) == ["Unknown scene/phase: missing"]
        assert _validate_scene_transition("fracture", _session_stub(current_scene_id="missing"), module) == [
            "Current scene 'missing' not in module"
        ]

    def test_validate_decision_reports_accepted_and_rejected_delta_indices(self):
        decision = SimpleNamespace(
            proposed_deltas=[
                _Delta("characters.veronique.emotional_state", 55),
                _Delta("relationships.unknown.value", 10),
            ],
            proposed_scene_id="fracture",
        )

        outcome = validate_decision(decision, _session_stub(), _module_stub())

        assert outcome.is_valid is False
        assert outcome.accepted_delta_indices == [0]
        assert outcome.rejected_delta_indices == [1]
        assert outcome.details == {"delta_count": 2, "accepted_count": 1, "rejected_count": 1}
