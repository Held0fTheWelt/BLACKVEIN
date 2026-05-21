"""Projection section builder for `scene_energy`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_SCENE_ENERGY_SECTION_PARAMS = ('scene_energy_actual', 'scene_energy_expected', 'scene_energy_rec', 'scene_energy_selected')


def build_scene_energy_section(**values: Any) -> dict[str, Any]:
    """Return the scene energy diagnostic section from normalized ledger records."""
    scene_energy_actual = values['scene_energy_actual']
    scene_energy_expected = values['scene_energy_expected']
    scene_energy_rec = values['scene_energy_rec']
    scene_energy_selected = values['scene_energy_selected']
    return {
                    "schema_version": scene_energy_expected.get("schema_version")
                    or scene_energy_selected.get("schema_version")
                    or scene_energy_actual.get("schema_version"),
                    "policy_present": bool(scene_energy_expected.get("policy_present")),
                    "policy_enabled": bool(scene_energy_expected.get("policy_enabled")),
                    "energy_level": _record_nested_value(
                        scene_energy_selected, "energy_level", "target"
                    ),
                    "pressure_vector": _record_nested_value(
                        scene_energy_selected, "pressure_vector", "target"
                    ),
                    "tempo": _record_nested_value(scene_energy_selected, "tempo", "target"),
                    "density": _record_nested_value(scene_energy_selected, "density", "target"),
                    "volatility": _record_nested_value(
                        scene_energy_selected, "volatility", "target"
                    ),
                    "target_transition": scene_energy_selected.get("target_transition")
                    or _record_nested_value(scene_energy_selected, "transition_intent", "transition"),
                    "minimum_actor_response_count": int(
                        scene_energy_selected.get("minimum_actor_response_count")
                        or (
                            scene_energy_selected.get("target", {}).get("minimum_actor_response_count")
                            if isinstance(scene_energy_selected.get("target"), dict)
                            else 0
                        )
                        or 0
                    ),
                    "actual_actor_response_count": int(
                        scene_energy_actual.get("actual_actor_response_count") or 0
                    ),
                    "visible_density_count": int(scene_energy_actual.get("visible_density_count") or 0),
                    "transition_allowed": scene_energy_actual.get("transition_allowed"),
                    "failure_codes": scene_energy_actual.get("failure_codes") or _record_reasons(scene_energy_rec),
                    "contract_pass": scene_energy_actual.get("contract_pass"),
                    "failure_reason": scene_energy_rec.get("failure_reason")
                    or (_record_reasons(scene_energy_rec)[0] if _record_reasons(scene_energy_rec) else None),
                    "status": scene_energy_rec.get("status"),
                }

