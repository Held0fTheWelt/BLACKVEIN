"""Semantischer Entscheidungsfluss und Support-Posture (DS-018)."""

from __future__ import annotations

from typing import Any

from ai_stack.dramatic_effect_contract import SemanticPlannerSupportLevel
from ai_stack.semantic_planner_effect_surface import (
    resolve_dramatic_effect_evaluator,
    support_level_for_module,
)

from app.services.inspector_turn_projection_sections_constants import (
    PLANNER_BOUND_STAGES,
    SEMANTIC_FLOW_STAGES,
    SUPPORT_NOTE_FULL_GOC,
    SUPPORT_NOTE_NON_GOC,
)
from app.services.inspector_turn_projection_sections_utils import non_empty_dict, non_empty_list


def support_posture(*, module_id: Any) -> dict[str, Any] | None:
    if not isinstance(module_id, str) or not module_id.strip():
        return None
    mid = module_id.strip()
    level = support_level_for_module(mid)
    evaluator = resolve_dramatic_effect_evaluator(mid)
    note = SUPPORT_NOTE_FULL_GOC if level == SemanticPlannerSupportLevel.full_goc else SUPPORT_NOTE_NON_GOC
    return {
        "semantic_planner_support_level": level.value,
        "dramatic_effect_evaluator_class": type(evaluator).__name__,
        "support_note": note,
    }


def build_semantic_decision_flow(
    *,
    support_level: SemanticPlannerSupportLevel,
    canonical_record: dict[str, Any],
    last_turn: dict[str, Any],
    gate_outcome: dict[str, Any],
    validation: dict[str, Any],
    committed: dict[str, Any],
) -> dict[str, Any]:
    """Backend-only semantic stage list with explicit per-stage presence (operator Mermaid input)."""

    def presence_for(stage_id: str) -> str:
        if stage_id in PLANNER_BOUND_STAGES and support_level != SemanticPlannerSupportLevel.full_goc:
            return "unsupported"
        if stage_id == "player_input":
            raw = last_turn.get("raw_input")
            if isinstance(raw, str) and raw.strip():
                return "present"
            ii = last_turn.get("interpreted_input")
            if non_empty_dict(ii):
                return "present"
            return "absent"
        if stage_id == "semantic_move":
            return "present" if non_empty_dict(canonical_record.get("semantic_move_record")) else "absent"
        if stage_id == "social_state":
            return "present" if non_empty_dict(canonical_record.get("social_state_record")) else "absent"
        if stage_id == "character_mind":
            return "present" if non_empty_list(canonical_record.get("character_mind_records")) else "absent"
        if stage_id == "scene_plan":
            return "present" if non_empty_dict(canonical_record.get("scene_plan_record")) else "absent"
        if stage_id == "proposed_narrative":
            if non_empty_dict(last_turn.get("narrative_commit")):
                return "present"
            gen = (last_turn.get("model_route") or {}).get("generation")
            if isinstance(gen, dict) and any(
                gen.get(k) not in (None, "", [], {})
                for k in ("primary_text", "text", "narrative", "content", "structured_output")
            ):
                return "present"
            return "absent"
        if stage_id == "dramatic_effect_gate":
            return "present" if non_empty_dict(gate_outcome) else "absent"
        if stage_id == "validation":
            if isinstance(validation, dict) and validation.get("status") is not None:
                return "present"
            return "absent"
        if stage_id == "commit":
            return "present" if isinstance(committed, dict) else "absent"
        if stage_id == "visible_output":
            vo = last_turn.get("visible_output_bundle")
            if isinstance(vo, dict) and bool(vo):
                return "present"
            if isinstance(vo, list) and bool(vo):
                return "present"
            return "absent"
        return "absent"

    stages_out: list[dict[str, Any]] = []
    for sid, label in SEMANTIC_FLOW_STAGES:
        stages_out.append({"id": sid, "label": label, "presence": presence_for(sid)})

    edges: list[dict[str, str]] = []
    for idx in range(len(stages_out) - 1):
        edges.append({"from_stage": stages_out[idx]["id"], "to_stage": stages_out[idx + 1]["id"]})

    return {"stages": stages_out, "edges": edges}
