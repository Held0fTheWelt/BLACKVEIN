"""Consistency checks for evidence-backed agency capability matrix."""

from __future__ import annotations

from pathlib import Path

from ai_stack.actor_survival_telemetry import build_actor_survival_telemetry
from ai_stack.runtime_turn_contracts import VITALITY_TELEMETRY_REQUIRED_FIELDS


def _sample_telemetry_fields() -> set[str]:
    sample = build_actor_survival_telemetry(
        {
            "turn_number": 1,
            "trace_id": "trace",
            "selected_responder_set": [{"actor_id": "annette_reille", "role": "primary_responder"}],
            "generation": {"metadata": {"structured_output": {"spoken_lines": [], "action_lines": [], "initiative_events": []}}},
            "visible_output_bundle": {"spoken_lines": [], "action_lines": []},
            "quality_class": "healthy",
            "degradation_signals": [],
        },
        generation_ok=True,
        validation_ok=True,
        commit_applied=True,
        fallback_taken=False,
    )
    vitality = sample.get("vitality_telemetry_v1") if isinstance(sample.get("vitality_telemetry_v1"), dict) else {}
    hints = sample.get("operator_diagnostic_hints") if isinstance(sample.get("operator_diagnostic_hints"), dict) else {}
    known = set(VITALITY_TELEMETRY_REQUIRED_FIELDS)
    known.update(vitality.keys())
    known.update(hints.keys())
    known.update({"why_turn_felt_passive", "primary_passivity_factors", "vitality_breakdown"})
    return known


def test_agency_capability_matrix_fields_and_test_refs_exist() -> None:
    matrix = Path("AGENCY_CAPABILITY_MATRIX.md")
    assert matrix.exists(), "AGENCY_CAPABILITY_MATRIX.md must exist"

    lines = matrix.read_text(encoding="utf-8").splitlines()
    known_fields = _sample_telemetry_fields()

    telemetry_blocks = [line for line in lines if line.startswith("- Telemetry fields:")]
    proving_test_lines = [line for line in lines if line.strip().startswith("- `") and "::" in line]
    support_lines = [line for line in lines if line.startswith("- Support level:")]

    assert telemetry_blocks, "Capability matrix must include telemetry fields per capability"
    assert proving_test_lines, "Capability matrix must include proving test references"
    assert support_lines, "Capability matrix must include support level per capability"

    for block in telemetry_blocks:
        raw = block.split(":", 1)[1]
        refs = [segment.strip() for segment in raw.split(",") if segment.strip()]
        for ref in refs:
            field = ref.strip(" `")
            assert field in known_fields, f"Unknown telemetry field in capability matrix: {field}"

    for line in proving_test_lines:
        raw = line.strip()[2:].strip()
        ref = raw.strip("`")
        path_str, test_name = ref.split("::", 1)
        path = Path(path_str)
        assert path.exists(), f"Proving test path does not exist: {path_str}"
        text = path.read_text(encoding="utf-8")
        assert f"def {test_name}(" in text, f"Proving test function missing: {ref}"
